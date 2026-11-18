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
    ticket_recherche = MillionsField(label='Montant recherché (M FCFA)', required=False)

    class Meta:
        model = EntrepriseProfile
        fields = ['forme_juridique', 'rccm', 'annee_creation', 'effectif', 'stade', 'ticket_recherche', 'part_investissement',
                  'instrument_souhaite', 'export_zlecaf', 'strategie_sortie']
        widgets = {'strategie_sortie': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Cession à un industriel, rachat par la direction, entrée d’un nouveau fonds…'})}

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        t = self.instance.ticket_recherche
        if t and not self.is_bound:
            self.initial['ticket_recherche'] = t // 1_000_000
