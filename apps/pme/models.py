from django.db import models


class NiveauPreuve(models.TextChoices):
    DECLARATIF = 'declaratif', 'Déclaratif'
    COHERENT = 'coherent', 'Cohérent'
    RECOUPE = 'recoupe', 'Recoupé'
    CERTIFIE = 'certifie', 'Certifié'


POIDS_PREUVE = {'declaratif': 1, 'coherent': 2, 'recoupe': 3, 'certifie': 4}


class EntrepriseProfile(models.Model):
    """Ce que la PME déclare pour se préparer : forme, effectif, besoin de financement, sortie."""

    class Forme(models.TextChoices):
        SA = 'SA', 'Société anonyme (SA)'
        SARL = 'SARL', 'Société à responsabilité limitée (SARL)'
        SAS = 'SAS', 'Société par actions simplifiée (SAS)'
        SNC = 'SNC', 'Société en nom collectif (SNC)'
        GIE = 'GIE', 'Groupement d’intérêt économique (GIE)'
        COOP = 'COOP', 'Société coopérative'
        EI = 'EI', 'Entreprise individuelle'
        AUTRE = 'AUTRE', 'Autre'

    class Stade(models.TextChoices):
        AMORCAGE = 'amorcage', 'Amorçage'
        CROISSANCE = 'croissance', 'Croissance'
        MATURITE = 'maturite', 'Maturité'

    class Instrument(models.TextChoices):
        EQUITY = 'equity', 'Capital (equity)'
        DETTE = 'dette', 'Dette'
        QUASI = 'quasi', 'Quasi-fonds propres'
        MIXTE = 'mixte', 'Mixte'

    organisation = models.OneToOneField('annuaire.Organisation', on_delete=models.CASCADE, related_name='profil_pme')
    forme_juridique = models.CharField('forme juridique', max_length=8, choices=Forme.choices, blank=True)
    rccm = models.CharField('RCCM', max_length=60, blank=True)
    annee_creation = models.PositiveSmallIntegerField('année de création', null=True, blank=True)
    effectif = models.PositiveIntegerField(null=True, blank=True)
    stade = models.CharField(max_length=12, choices=Stade.choices, blank=True)
    ticket_recherche = models.BigIntegerField('montant recherché (FCFA)', null=True, blank=True)
    part_investissement = models.PositiveSmallIntegerField('part investissement (%)', null=True, blank=True)
    instrument_souhaite = models.CharField('instrument souhaité', max_length=10, choices=Instrument.choices, blank=True)
    export_zlecaf = models.BooleanField('export régional (ZLECAf)', default=False)
    strategie_sortie = models.TextField('stratégie de sortie', blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'profil PME'
        verbose_name_plural = 'profils PME'

    def __str__(self):
        return f'Profil · {self.organisation}'

    @property
    def sortie_ecrite(self):
        return bool(self.strategie_sortie.strip())

    @property
    def dernier_exercice(self):
        return self.organisation.exercices.order_by('-annee').first()


class ExerciceFinancier(models.Model):
    """Un exercice comptable déclaré (montants en FCFA). Le niveau de preuve dit à quel point il est vérifié."""
    organisation = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='exercices')
    annee = models.PositiveSmallIntegerField('année')
    chiffre_affaires = models.BigIntegerField('chiffre d’affaires')
    marge_brute = models.BigIntegerField('marge brute', null=True, blank=True)
    ebitda = models.BigIntegerField('EBITDA', null=True, blank=True)
    resultat_net = models.BigIntegerField('résultat net', null=True, blank=True)
    dette_nette = models.BigIntegerField('dette nette', null=True, blank=True)
    service_dette = models.BigIntegerField('service annuel de la dette', null=True, blank=True)
    niveau_preuve = models.CharField('niveau de preuve', max_length=12, choices=NiveauPreuve.choices, default=NiveauPreuve.DECLARATIF)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'exercice financier'
        ordering = ['-annee']
        constraints = [models.UniqueConstraint(fields=['organisation', 'annee'], name='un_exercice_par_annee')]

    def __str__(self):
        return f'{self.organisation} · {self.annee}'

    @property
    def dscr(self):
        if self.ebitda and self.service_dette:
            return round(self.ebitda / self.service_dette, 2)
        return None

    @property
    def marge_ebitda(self):
        if self.ebitda is not None and self.chiffre_affaires:
            return round(self.ebitda / self.chiffre_affaires * 100, 1)
        return None


class Piece(models.Model):
    """Une pièce de la data room, rangée dans l’un des 10 dossiers imposés."""

    class Dossier(models.TextChoices):
        PITCH = '01', '01 · Pitch et business plan'
        ETATS = '02', '02 · États financiers et projections'
        JURIDIQUE = '03', '03 · Juridique et gouvernance'
        FISCAL = '04', '04 · Fiscal et social'
        EQUIPE = '05', '05 · Équipe et ressources humaines'
        CONTRATS = '06', '06 · Contrats clients et fournisseurs'
        LICENCES = '07', '07 · Licences et propriété intellectuelle'
        RISQUES = '08', '08 · Risques et PESTEL'
        ESG = '09', '09 · Environnement, social, gouvernance'
        SORTIE = '10', '10 · Stratégie de sortie'

    organisation = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='pieces')
    dossier = models.CharField(max_length=2, choices=Dossier.choices)
    titre = models.CharField(max_length=200)
    fichier = models.FileField(upload_to='dataroom/%Y/%m/', blank=True)
    niveau_preuve = models.CharField('niveau de preuve', max_length=12, choices=NiveauPreuve.choices, default=NiveauPreuve.DECLARATIF)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['dossier', '-created_at']
        indexes = [models.Index(fields=['organisation', 'dossier'])]

    def __str__(self):
        return self.titre


class ScoreSnapshot(models.Model):
    """Historique du score de préparation (un point par calcul), pour tracer la progression."""
    organisation = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='scores')
    total = models.PositiveSmallIntegerField()
    dimensions = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
