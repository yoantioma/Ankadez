from django.db import models
from django.utils.text import slugify


class Secteur(models.Model):
    nom = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)

    class Meta:
        ordering = ['nom']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nom)[:140]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom


class OrganisationQuerySet(models.QuerySet):
    def entreprises(self):
        """Vivier de matching : PME fictives (FICTIF), PME inscrites et PME importées des fichiers d’annuaire (CSV).
        Pour l’investisseur, toutes restent anonymisées jusqu’à l’accord de confidentialité ; aucun contact n’est affiché."""
        return self.filter(kind__in=Organisation.KINDS_ENTREPRISE, actif=True)

    def importees(self):
        """Entreprises venues des fichiers d’annuaire (CSV), hors jeu fictif."""
        return self.filter(external_id__isnull=False).exclude(external_id__startswith='FICTIF-')

    def investisseurs(self):
        return self.filter(kind=Organisation.Kind.INVESTISSEUR, actif=True)

    def accompagnement(self):
        return self.filter(kind__in=Organisation.KINDS_ACCOMPAGNEMENT, actif=True)


class Organisation(models.Model):
    """Tout acteur de l’écosystème : une seule table, un type. Les données propres à chaque type
    vivent dans des tables liées (profil PME, thèse d’investissement), ce qui garde le modèle simple et extensible."""

    class Kind(models.TextChoices):
        PME = 'pme', 'PME'
        STARTUP = 'startup', 'Startup'
        INVESTISSEUR = 'investisseur', 'Investisseur'
        INSTITUTION = 'institution', 'Institution'
        INCUBATEUR = 'incubateur', 'Incubateur'
        ASSOCIATION = 'association', 'Association'
        CONSULTANT = 'consultant', 'Consultant'

    KINDS_ENTREPRISE = (Kind.PME, Kind.STARTUP)
    KINDS_ACCOMPAGNEMENT = (Kind.INCUBATEUR, Kind.INSTITUTION, Kind.ASSOCIATION, Kind.CONSULTANT)

    kind = models.CharField('type', max_length=20, choices=Kind.choices, db_index=True)
    nom = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    secteur = models.ForeignKey(Secteur, on_delete=models.SET_NULL, null=True, blank=True, related_name='organisations')
    categorie = models.CharField('catégorie', max_length=160, blank=True)
    description = models.TextField(blank=True)
    ville = models.CharField(max_length=120, blank=True)
    region = models.CharField('région', max_length=80, blank=True, db_index=True)
    pays = models.CharField(max_length=80, default='Cameroun')
    adresse = models.CharField(max_length=255, blank=True)
    site_web = models.URLField(max_length=300, blank=True)
    linkedin = models.URLField(max_length=300, blank=True)
    email = models.EmailField(blank=True)
    telephone = models.CharField('téléphone', max_length=80, blank=True)
    source_url = models.URLField('source', max_length=500, blank=True)
    external_id = models.CharField('identifiant externe', max_length=40, unique=True, null=True, blank=True)
    completude = models.PositiveSmallIntegerField('complétude (%)', default=0)
    a_verifier = models.BooleanField('à vérifier', default=True)
    est_demo = models.BooleanField('donnée fictive (démonstration)', default=False)
    # v3 · 9.3 et 9.4 : source visible, date de vérification, statut de contact
    source_libelle = models.CharField('source (libellé)', max_length=255, blank=True)
    verifie_le = models.DateField('dernière vérification', null=True, blank=True)
    statut_contact = models.CharField('statut de contact', max_length=12, default='non_contacte',
                                      choices=[('non_contacte', 'Non contacté'), ('contacte', 'Contacté'), ('accord', 'Accord donné')])
    type_acteur = models.CharField('type d’acteur', max_length=16, blank=True, choices=[
        ('banque', 'Banque'), ('fonds', 'Fonds d’investissement'), ('business_angel', 'Business angel'), ('diaspora', 'Diaspora'),
        ('mutuelle', 'Mutuelle d’entreprises'), ('ptf', 'Partenaire technique et financier'), ('repreneur', 'Repreneur'),
        ('multilateral', 'Financeur multilatéral'), ('garantie', 'Fonds de garantie'), ('marche', 'Marché financier'),
        ('incubateur', 'Incubateur ou structure d’appui'), ('cabinet', 'Cabinet comptable, fiscaliste ou CGA'),
        ('juridique', 'Avocat ou conseil juridique'), ('public', 'Institution publique')])
    # v3 · 8.2 : règles publiques de référencement des accompagnateurs
    specialites = models.JSONField('spécialités d’accompagnement', default=list, blank=True)
    qualification_verifiee = models.BooleanField('qualification vérifiée (ordre, agrément)', default=False)
    dossiers_menes = models.PositiveSmallIntegerField('PME menées à un grade supérieur', default=0)
    tarif = models.CharField('prix affiché', max_length=120, blank=True)
    remuneration_succes = models.BooleanField('rémunération au succès', default=False)
    partenaire_payant = models.BooleanField('référencement payant (badge séparé, sans effet sur le rang)', default=False)
    conflits = models.CharField('conflits d’intérêts déclarés', max_length=255, blank=True)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrganisationQuerySet.as_manager()

    class Meta:
        ordering = ['nom']
        indexes = [models.Index(fields=['kind', 'secteur']), models.Index(fields=['kind', 'region'])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nom)[:200] or 'organisation'
            slug, i = base, 2
            while Organisation.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, i = f'{base}-{i}', i + 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nom

    @property
    def est_entreprise(self):
        return self.kind in self.KINDS_ENTREPRISE

    @property
    def initiales(self):
        mots = [m for m in self.nom.replace('-', ' ').split() if m[:1].isalnum()]
        return ''.join(m[0] for m in mots[:2]).upper() or '?'
