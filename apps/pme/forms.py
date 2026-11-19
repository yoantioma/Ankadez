from django import forms

from apps.accounts.forms import MillionsField

from .models import EntrepriseProfile, ExerciceFinancier, Piece

MAX_FICHIER = 10 * 1024 * 1024
EXTENSIONS = ('.pdf', '.png', '.jpg', '.jpeg', '.xlsx', '.xls', '.csv', '.docx', '.doc')


class PieceForm(forms.ModelForm):
    class Meta:
        model = Piece
        fields = ['dossier', 'titre', 'fichier']
        labels = {'titre': 'Intitulé de la pièce', 'fichier': 'Fichier (PDF, image, tableur, 10 Mo max)'}

    def clean_fichier(self):
        f = self.cleaned_data.get('fichier')
        if f:
            if f.size > MAX_FICHIER:
                raise forms.ValidationError('Fichier trop lourd : 10 Mo au maximum.')
            if not f.name.lower().endswith(EXTENSIONS):
                raise forms.ValidationError('Format non accepté.')
        return f


class ExerciceForm(forms.ModelForm):
    chiffre_affaires = MillionsField(label='Chiffre d’affaires (M FCFA)')
    marge_brute = MillionsField(label='Marge brute (M FCFA)', required=False)
    ebitda = MillionsField(label='EBITDA (M FCFA)', required=False)
    resultat_net = forms.IntegerField(label='Résultat net (M FCFA)', required=False)
    dette_nette = MillionsField(label='Dette nette (M FCFA)', required=False)
    service_dette = MillionsField(label='Service annuel de la dette (M FCFA)', required=False)

    class Meta:
        model = ExerciceFinancier
        fields = ['annee', 'chiffre_affaires', 'marge_brute', 'ebitda', 'resultat_net', 'dette_nette', 'service_dette']

    def clean_resultat_net(self):
        v = self.cleaned_data.get('resultat_net')
        return None if v is None else v * 1_000_000


class ProfilForm(forms.ModelForm):
    """Profil de l’entreprise. Les champs v3 alimentent les 4 P (5.1), les indicateurs de préparation (5.3), la vue PTF (5.4),
    les portes de preuve (6.2) et la ZLECAf (section 3)."""
    ticket_recherche = MillionsField(label='Montant recherché (M FCFA)', required=False)
    tresorerie = MillionsField(label='Trésorerie disponible (M FCFA)', required=False)
    sorties_mensuelles = MillionsField(label='Sorties nettes mensuelles hors financement (M FCFA)', required=False)
    financement_ptf = MillionsField(label='Financement reçu d’un partenaire technique et financier (M FCFA)', required=False)
    financement_prive = MillionsField(label='Financement privé mobilisé à côté (M FCFA)', required=False)
    usage_fonds_texte = forms.CharField(label='Usage des fonds : « 100 FCFA levés servent à… »', required=False,
                                        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Une ligne par poste : poste ; montant en M ; effet attendu\nLigne de production ; 350 ; +60 % de capacité'}))
    ouvertures = forms.MultipleChoiceField(label='Ouverture à court terme', required=False, widget=forms.CheckboxSelectMultiple,
                                           choices=[('coentreprise', 'Coentreprise'), ('partenariat', 'Partenariat'), ('rachat', 'Rachat'),
                                                    ('fusion', 'Fusion'), ('reprise', 'Entrée d’un repreneur')])
    consentement = forms.BooleanField(label='J’accepte le traitement de mes données personnelles pour la préparation de mon dossier', required=False)

    GROUPES = [
        ('Identité et financement', ['forme_juridique', 'rccm', 'annee_creation', 'effectif', 'stade', 'ticket_recherche', 'part_investissement', 'instrument_souhaite']),
        ('Confiance et portes de preuve', ['beneficiaires_identifies', 'consentement', 'contact_banque_autorise', 'reporting_mensuel', 'part_dirigeant']),
        ('Préparation à l’investissement', ['clients_top3_pct', 'revenus_recurrents_pct', 'tresorerie', 'sorties_mensuelles', 'concurrents', 'usage_fonds_texte', 'strategie_sortie', 'ouvertures']),
        ('Impact et territoire', ['dirigeante', 'emplois_femmes', 'emplois_jeunes', 'salaries_cnps', 'zone_rurale', 'zone_incitative', 'energie_propre', 'financement_ptf', 'financement_prive']),
        ('Afrique et ZLECAf', ['export_zlecaf', 'part_export', 'regles_origine']),
    ]

    class Meta:
        model = EntrepriseProfile
        fields = ['forme_juridique', 'rccm', 'annee_creation', 'effectif', 'stade', 'ticket_recherche', 'part_investissement',
                  'instrument_souhaite', 'export_zlecaf', 'strategie_sortie', 'clients_top3_pct', 'revenus_recurrents_pct', 'tresorerie',
                  'sorties_mensuelles', 'part_dirigeant', 'reporting_mensuel', 'concurrents', 'beneficiaires_identifies', 'contact_banque_autorise',
                  'dirigeante', 'emplois_femmes', 'emplois_jeunes', 'salaries_cnps', 'part_export', 'regles_origine', 'energie_propre',
                  'zone_rurale', 'zone_incitative', 'financement_ptf', 'financement_prive']
        widgets = {'strategie_sortie': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Cession à un industriel, rachat par la direction, entrée d’un nouveau fonds…'}),
                   'concurrents': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Trois concurrents nommés, leurs forces et faiblesses, votre avantage'}),
                   'zone_incitative': forms.Select(choices=[('', 'Aucune'), ('sinistree', 'Zone économiquement sinistrée'), ('portuaire', 'Zone portuaire (Kribi)'),
                                                            ('franche', 'Zone franche industrielle'), ('agricole', 'Zone agricole spéciale'), ('hitech', 'ZES HiTech')])}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        for nom in ('ticket_recherche', 'tresorerie', 'sorties_mensuelles', 'financement_ptf', 'financement_prive'):
            v = getattr(self.instance, nom)
            if v and not self.is_bound:
                self.initial[nom] = v // 1_000_000
        if not self.is_bound:
            self.initial['usage_fonds_texte'] = '\n'.join(f'{l[0]} ; {int(l[1]) // 1_000_000} ; {l[2]}' for l in (self.instance.usage_fonds or []) if len(l) >= 3)
            self.initial['ouvertures'] = self.instance.ouvertures
            self.initial['consentement'] = bool(self.instance.consentement_donnees)

    def groupes(self):
        return [(titre, [self[n] for n in noms]) for titre, noms in self.GROUPES]

    def save(self, commit=True):
        from django.utils import timezone
        obj = super().save(commit=False)
        lignes = []
        for brut in (self.cleaned_data.get('usage_fonds_texte') or '').splitlines():
            parts = [x.strip() for x in brut.split(';')]
            if len(parts) >= 2 and parts[0]:
                try:
                    montant = int(float(parts[1].replace(',', '.')) * 1_000_000)
                except ValueError:
                    continue
                lignes.append([parts[0], montant, parts[2] if len(parts) > 2 else ''])
        obj.usage_fonds = lignes
        obj.ouvertures = self.cleaned_data.get('ouvertures') or []
        if self.cleaned_data.get('consentement') and not obj.consentement_donnees:
            obj.consentement_donnees = timezone.now()
        elif not self.cleaned_data.get('consentement'):
            obj.consentement_donnees = None
        if commit:
            obj.save()
        return obj
