from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm

from apps.annuaire.models import Secteur
from apps.investissement.models import These
from apps.pme.models import EntrepriseProfile

from .models import User

REGIONS = ['Adamaoua', 'Centre', 'Est', 'Extrême-Nord', 'Littoral', 'Nord', 'Nord-Ouest', 'Ouest', 'Sud', 'Sud-Ouest']


class ConnexionForm(AuthenticationForm):
    username = forms.EmailField(label='Adresse e-mail', widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email'}))
    error_messages = {'invalid_login': 'E-mail ou mot de passe incorrect.', 'inactive': 'Ce compte est désactivé.'}


class CompteForm(forms.ModelForm):
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
                                help_text='8 caractères au moins, pas uniquement des chiffres.')
    password2 = forms.CharField(label='Confirmer le mot de passe', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'telephone']
        labels = {'first_name': 'Prénom', 'last_name': 'Nom', 'email': 'Adresse e-mail professionnelle', 'telephone': 'Téléphone'}

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Un compte existe déjà avec cette adresse. Connectez-vous.')
        return email

    def clean(self):
        data = super().clean()
        p1, p2 = data.get('password1'), data.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Les deux mots de passe ne correspondent pas.')
        if p1:
            try:
                password_validation.validate_password(p1, User(email=data.get('email'), first_name=data.get('first_name', '')))
            except forms.ValidationError as e:
                self.add_error('password1', e)
        return data

    def save(self, role, commit=True):
        user = super().save(commit=False)
        user.role = role
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user


class MillionsField(forms.IntegerField):
    """Saisie en millions de FCFA, stockage en FCFA."""

    def __init__(self, *a, **kw):
        kw.setdefault('min_value', 0)
        kw.setdefault('widget', forms.NumberInput(attrs={'inputmode': 'numeric', 'placeholder': 'en millions de FCFA'}))
        super().__init__(*a, **kw)

    def clean(self, value):
        v = super().clean(value)
        return None if v is None else v * 1_000_000


class EntrepriseForm(forms.Form):
    nom = forms.CharField(label='Raison sociale', max_length=200)
    forme_juridique = forms.ChoiceField(label='Forme juridique (OHADA)', choices=[('', '—')] + list(EntrepriseProfile.Forme.choices), required=False)
    secteur = forms.ModelChoiceField(label='Secteur d’activité', queryset=Secteur.objects.all(), required=False, empty_label='—')
    ville = forms.CharField(max_length=120, required=False)
    region = forms.ChoiceField(label='Région', choices=[('', '—')] + [(r, r) for r in REGIONS], required=False)
    annee_creation = forms.IntegerField(label='Année de création', min_value=1950, max_value=2100, required=False)
    effectif = forms.IntegerField(label='Effectif', min_value=0, required=False)
    description = forms.CharField(label='Activité en une phrase', widget=forms.Textarea(attrs={'rows': 3}), required=False)


class FinancementForm(forms.Form):
    ticket_recherche = MillionsField(label='Montant recherché', required=False)
    part_investissement = forms.IntegerField(label='Part investissement (le reste en roulement), %', min_value=0, max_value=100, required=False)
    instrument_souhaite = forms.ChoiceField(label='Instrument souhaité', choices=[('', '—')] + list(EntrepriseProfile.Instrument.choices), required=False)
    stade = forms.ChoiceField(choices=[('', '—')] + list(EntrepriseProfile.Stade.choices), required=False)
    annee = forms.IntegerField(label='Dernier exercice clos', min_value=2000, max_value=2100, required=False)
    chiffre_affaires = MillionsField(label='Chiffre d’affaires', required=False)
    marge_brute = MillionsField(label='Marge brute', required=False)
    ebitda = MillionsField(label='EBITDA', required=False)

    def clean(self):
        data = super().clean()
        if data.get('chiffre_affaires') and not data.get('annee'):
            self.add_error('annee', 'Indiquez l’année de l’exercice.')
        return data


ZONES_V3 = ([('CEMAC', 'Toute la CEMAC'), ('ZLECAf', 'Pays de la ZLECAf')] + [(r, r) for r in REGIONS] +
            [('Douala', 'Douala'), ('Yaoundé', 'Yaoundé'), ('sinistree', 'Zones sinistrées'), ('portuaire', 'Zones portuaires'), ('franche', 'Zones franches')])


class TheseForm(forms.Form):
    """« À quoi ressemble votre monde idéal ? » (cahier des charges v3 · 4.2) : neuf écrans, un geste chacun.
    Les réponses construisent le tableau de bord : compatibles, presque compatibles, à surveiller."""
    nom = forms.CharField(label='Nom de votre structure', max_length=200)
    ville = forms.CharField(max_length=120, required=False)
    pays = forms.CharField(max_length=80, initial='Cameroun')
    type_acteur = forms.ChoiceField(label='Qui êtes-vous ?', choices=These.TYPES, widget=forms.RadioSelect)
    ticket_min = MillionsField(label='Ticket minimum par dossier (M FCFA)', required=False)
    ticket_max = MillionsField(label='Ticket maximum par dossier (M FCFA)', required=False)
    instruments = forms.MultipleChoiceField(label='Sous quelle forme intervenez-vous ?', choices=These.INSTRUMENTS, required=False, widget=forms.CheckboxSelectMultiple)
    secteurs = forms.ModelMultipleChoiceField(label='Quels secteurs voulez-vous voir en premier ?', queryset=Secteur.objects.all(), required=False,
                                              widget=forms.CheckboxSelectMultiple, help_text='Aucun coché : tous les secteurs.')
    zones = forms.MultipleChoiceField(label='Où ?', choices=ZONES_V3, required=False, widget=forms.CheckboxSelectMultiple)
    stades = forms.MultipleChoiceField(label='À quel stade préférez-vous entrer ?', choices=These.STADES, required=False, widget=forms.CheckboxSelectMultiple)
    non_negociables = forms.MultipleChoiceField(label='Qu’est-ce qui est non négociable ?', choices=These.NON_NEGOCIABLES, required=False,
                                                widget=forms.CheckboxSelectMultiple, help_text='Filtres éliminatoires : une entreprise qui ne les remplit pas est écartée.')
    exigence_esg = forms.BooleanField(label='J’exige une politique environnementale et sociale', required=False)
    horizon_annees = forms.IntegerField(label='Horizon (années)', min_value=1, max_value=20, required=False)
    sorties = forms.MultipleChoiceField(label='Quelle sortie ?', choices=These.SORTIES, required=False, widget=forms.CheckboxSelectMultiple)
    contact_accompagnateur = forms.BooleanField(label='Je veux parler d’abord à la structure qui accompagne l’entreprise', required=False)
    mutuelle_beneficiaires = forms.CharField(label='Qui peut bénéficier (membres, secteur, ancienneté)', max_length=200, required=False)
    mutuelle_apport = forms.CharField(label='Ce que vous apportez (petit prêt, garantie collective, caution, achat groupé)', max_length=200, required=False)
    mutuelle_delai = forms.CharField(label='Délai de décision annoncé', max_length=80, required=False)
    mutuelle_regle = forms.CharField(label='Règle de la communauté (garants, comité de crédit)', max_length=200, required=False)

    ECRANS = [
        ('Qui êtes-vous ?', 'Le type de vue, de vocabulaire et de critères proposés ensuite.', ['nom', 'ville', 'pays', 'type_acteur']),
        ('Quel ticket par dossier ?', 'Filtre éliminatoire et part du besoin couverte.', ['ticket_min', 'ticket_max']),
        ('Sous quelle forme ?', 'Instruments pris en compte dans le matching.', ['instruments']),
        ('Quels secteurs en premier ?', 'Tri et mise en avant.', ['secteurs']),
        ('Où ?', 'Régions, villes, zones incitatives ou sinistrées, pays de la ZLECAf.', ['zones']),
        ('À quel stade ?', 'Angel, Seed, Série A, Série B+, développement et reprise.', ['stades']),
        ('Qu’est-ce qui est non négociable ?', 'Filtres éliminatoires.', ['non_negociables', 'exigence_esg']),
        ('Quel horizon et quelle sortie ?', 'Compatibilité horizon et instrument.', ['horizon_annees', 'sorties']),
        ('Parler d’abord à l’accompagnateur ?', 'Active le contact via la structure d’appui, si l’entreprise l’a autorisé.',
         ['contact_accompagnateur', 'mutuelle_beneficiaires', 'mutuelle_apport', 'mutuelle_delai', 'mutuelle_regle']),
    ]

    def ecrans(self):
        return [(i + 1, t, aide, [self[n] for n in noms]) for i, (t, aide, noms) in enumerate(self.ECRANS)]

    def clean(self):
        data = super().clean()
        lo, hi = data.get('ticket_min'), data.get('ticket_max')
        if lo and hi and lo > hi:
            self.add_error('ticket_max', 'Le maximum doit dépasser le minimum.')
        return data


CHAMPS_THESE = ['ticket_min', 'ticket_max', 'zones', 'stades', 'instruments', 'exigence_esg', 'horizon_annees', 'type_acteur',
                'non_negociables', 'sorties', 'contact_accompagnateur', 'mutuelle_beneficiaires', 'mutuelle_apport', 'mutuelle_delai', 'mutuelle_regle']


def enregistrer_these(org, d):
    """Enregistre le monde idéal et garde une version datée (fraîcheur de la thèse)."""
    from apps.investissement.models import TheseVersion
    these, _ = These.objects.update_or_create(organisation=org, defaults={k: d[k] for k in CHAMPS_THESE})
    these.secteurs.set(d['secteurs'])
    if d.get('type_acteur') and not org.type_acteur:
        org.type_acteur = d['type_acteur']
        org.save(update_fields=['type_acteur'])
    TheseVersion.objects.create(these=these, donnees={**{k: d[k] for k in CHAMPS_THESE}, 'secteurs': [s.nom for s in d['secteurs']]})
    return these


def initial_these(org, t):
    data = {'nom': org.nom, 'ville': org.ville, 'pays': org.pays}
    if t and t.pk:
        data.update({k: getattr(t, k) for k in CHAMPS_THESE})
        for k in ('ticket_min', 'ticket_max'):
            data[k] = data[k] // 1_000_000 if data[k] else None
        data['secteurs'] = list(t.secteurs.all())
    return data
