"""Offres et paramètres du cahier des charges v3 : produits financiers (7.1), programmes par niche (7.4),
incitations (9.1) et questions du diagnostic de 45 secondes (4.1). Tout est éditable dans l’administration,
rien n’est écrit en dur dans le code. Aucune donnée n’est affichée sans source ni date."""
from datetime import date, timedelta

from django.db import models


class Source(models.Model):
    """Champs communs : d’où vient l’information et quand elle a été vérifiée."""
    source_libelle = models.CharField('source', max_length=255)
    source_url = models.URLField('lien de la source', max_length=500, blank=True)
    verifie_le = models.DateField('vérifié le', null=True, blank=True)
    a_confirmer = models.CharField('à confirmer avant affichage', max_length=255, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        abstract = True

    @property
    def perime(self):
        """Non vérifié depuis plus de 6 mois : affiché en gris avec « à reconfirmer » (7.1, règle de vérité)."""
        return not self.verifie_le or self.verifie_le < date.today() - timedelta(days=183)


class ProduitFinancier(Source):
    TYPES = [('credit', 'Crédit'), ('ligne', 'Ligne dédiée'), ('garantie', 'Garantie'), ('credit_bail', 'Crédit-bail'),
             ('affacturage', 'Affacturage'), ('chaine_valeur', 'Financement de la chaîne de valeur'), ('programme', 'Programme bancaire')]
    institution = models.ForeignKey('annuaire.Organisation', on_delete=models.SET_NULL, null=True, blank=True, related_name='produits')
    institution_nom = models.CharField('institution', max_length=160)
    nom = models.CharField('nom du produit', max_length=200)
    type = models.CharField(max_length=16, choices=TYPES)
    public = models.CharField('public visé', max_length=255)
    montant = models.CharField(max_length=160, default='non publié')
    taux = models.CharField('taux ou TEG', max_length=120, default='non publié')
    garanties = models.CharField('garanties demandées', max_length=255, default='non publié')
    delai = models.CharField('délai', max_length=120, default='non publié')
    # Conditions lues par l’outil : chaque condition manquante devient une pièce à fournir
    pieces_exigees = models.JSONField('dossiers de pièces exigés (codes 01 à 12)', default=list, blank=True)
    femme = models.BooleanField('réservé aux entreprises dirigées ou détenues par des femmes', default=False)
    grade_min = models.PositiveSmallIntegerField('score de préparation minimum', default=0)
    secteurs = models.JSONField('mots-clés de secteur (vide : tous)', default=list, blank=True)
    ordre = models.PositiveSmallIntegerField(default=50)

    class Meta:
        ordering = ['ordre', 'institution_nom']
        verbose_name = 'produit financier'

    def __str__(self):
        return f'{self.institution_nom} · {self.nom}'


class Programme(Source):
    NICHES = [('femmes', 'Femmes entrepreneures'), ('jeunes', 'Jeunes'), ('agro', 'Agro-transformation'), ('numerique', 'Numérique'),
              ('export', 'Export ZLECAf'), ('financement', 'Croissance et financement bancable'), ('social', 'Travail décent et conformité sociale'),
              ('montage', 'Montage de projets'), ('diaspora', 'Diaspora'), ('artisanat', 'Artisanat et économie sociale')]
    porteur = models.CharField(max_length=160)
    nom = models.CharField(max_length=200)
    public = models.CharField('public visé', max_length=255)
    contenu = models.TextField()
    duree = models.CharField('durée', max_length=120, default='non publié')
    prix = models.CharField('prix ou gratuité', max_length=120, default='non publié')
    criteres = models.CharField('critères', max_length=255, default='non publié')
    prochaine_session = models.CharField('prochaine session', max_length=120, default='non publié')
    niches = models.JSONField(default=list)

    class Meta:
        ordering = ['porteur', 'nom']

    def __str__(self):
        return f'{self.porteur} · {self.nom}'


class Incitation(Source):
    famille = models.CharField(max_length=160)
    description = models.TextField()
    concerne = models.CharField('qui est concerné', max_length=255)
    fiabilite = models.CharField('fiabilité de la source', max_length=160)
    # Règles de détection (toutes facultatives)
    secteurs = models.JSONField('mots-clés de secteur', default=list, blank=True)
    regions = models.JSONField('régions', default=list, blank=True)
    zones = models.JSONField('zones (sinistrée, portuaire, franche…)', default=list, blank=True)
    export = models.BooleanField('réservé aux entreprises exportatrices', default=False)
    jeunes = models.BooleanField('lié à l’emploi des jeunes', default=False)
    cote_investisseur = models.BooleanField('concerne l’investisseur, pas la PME', default=False)

    class Meta:
        ordering = ['famille']

    def __str__(self):
        return self.famille


class QuestionDiagnostic(models.Model):
    """Les 8 questions du diagnostic de 45 secondes. Les poids sont une hypothèse à calibrer avec les mentors finance :
    ils vivent dans cette table, pas dans le code."""
    ordre = models.PositiveSmallIntegerField()
    texte = models.CharField(max_length=255)
    poids = models.PositiveSmallIntegerField()
    piece = models.CharField('pièce manquante si « non »', max_length=160)
    action = models.CharField('ce que l’outil propose si « non »', max_length=200)
    specialite = models.CharField('accompagnateur recommandé (spécialité)', max_length=30)
    dossier = models.CharField('dossier de la salle de données', max_length=2, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ['ordre']
        verbose_name = 'question du diagnostic'
        verbose_name_plural = 'questions du diagnostic'

    def __str__(self):
        return f'{self.ordre}. {self.texte}'
