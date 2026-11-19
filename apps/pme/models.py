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
    # v3 · 5.3 indicateurs de préparation
    clients_top3_pct = models.PositiveSmallIntegerField('part des 3 premiers clients dans le CA (%)', null=True, blank=True)
    revenus_recurrents_pct = models.PositiveSmallIntegerField('revenus récurrents (% du CA)', null=True, blank=True)
    tresorerie = models.BigIntegerField('trésorerie disponible (FCFA)', null=True, blank=True)
    sorties_mensuelles = models.BigIntegerField('sorties nettes mensuelles hors financement (FCFA)', null=True, blank=True)
    usage_fonds = models.JSONField('usage des fonds (poste, montant, effet attendu)', default=list, blank=True)
    part_dirigeant = models.PositiveSmallIntegerField('part investie par le dirigeant (%)', null=True, blank=True)
    reporting_mensuel = models.BooleanField('reporting mensuel fiable', default=False)
    concurrents = models.TextField('trois concurrents nommés, forces et faiblesses', blank=True)
    ouvertures = models.JSONField('ouvertures à court terme', default=list, blank=True)
    ouvert_reprise = models.BooleanField('ouvert à une reprise, partielle ou totale', default=False)
    # v3 · 5.1 People et 6.2 portes de preuve
    beneficiaires_identifies = models.BooleanField('bénéficiaires effectifs identifiés', default=False)
    identite_verifiee = models.BooleanField('identité des dirigeants vérifiée (KYC)', default=False)
    consentement_donnees = models.DateTimeField('consentement au traitement des données', null=True, blank=True)
    contact_banque_autorise = models.BooleanField('accord pour contacter la banque principale et le comptable', default=False)
    # v3 · 5.4 impact (vue PTF) et 3 · ZLECAf
    dirigeante = models.BooleanField('dirigée ou détenue par une femme', default=False)
    emplois_femmes = models.PositiveIntegerField('emplois occupés par des femmes', null=True, blank=True)
    emplois_jeunes = models.PositiveIntegerField('emplois de jeunes (moins de 35 ans)', null=True, blank=True)
    salaries_cnps = models.PositiveIntegerField('salariés déclarés à la CNPS', null=True, blank=True)
    part_export = models.PositiveSmallIntegerField('part de l’export dans le CA (%)', null=True, blank=True)
    regles_origine = models.CharField('règles d’origine ZLECAf (produit, origine)', max_length=200, blank=True)
    energie_propre = models.BooleanField('utilise une énergie propre mesurée', default=False)
    zone_rurale = models.BooleanField('implantée en zone rurale', default=False)
    zone_incitative = models.CharField('zone incitative ou sinistrée', max_length=60, blank=True)
    financement_ptf = models.BigIntegerField('financement reçu d’un PTF (FCFA)', null=True, blank=True)
    financement_prive = models.BigIntegerField('financement privé mobilisé à côté (FCFA)', null=True, blank=True)
    # v3 · 4.1 et 8 : diagnostic, accompagnement, académie
    diagnostic = models.JSONField('dernier diagnostic de 45 secondes', default=dict, blank=True)
    accompagnateur = models.ForeignKey('annuaire.Organisation', on_delete=models.SET_NULL, null=True, blank=True, related_name='pme_accompagnees')
    accompagnateur_peut_repondre = models.BooleanField('mon accompagnateur peut répondre en mon nom pour un premier contact', default=False)
    cabinet = models.ForeignKey('annuaire.Organisation', on_delete=models.SET_NULL, null=True, blank=True, related_name='pme_clientes',
                                help_text='Cabinet comptable, fiscaliste ou CGA autorisé à verser et attester vos pièces.')
    badge_eduque = models.BooleanField('badge « Éduqué financièrement »', default=False)
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
    # v3 · 5.2 bilan et cycle (lignes de la liasse SYSCOHADA)
    capitaux_propres = models.BigIntegerField('capitaux propres', null=True, blank=True)
    total_bilan = models.BigIntegerField('total du bilan', null=True, blank=True)
    actif_circulant = models.BigIntegerField('actif circulant', null=True, blank=True)
    dettes_court_terme = models.BigIntegerField('dettes à court terme', null=True, blank=True)
    dettes_financieres = models.BigIntegerField('dettes financières', null=True, blank=True)
    caf = models.BigIntegerField('capacité d’autofinancement', null=True, blank=True)
    charges_personnel = models.BigIntegerField('charges de personnel', null=True, blank=True)
    valeur_ajoutee = models.BigIntegerField('valeur ajoutée', null=True, blank=True)
    creances_clients = models.BigIntegerField('créances clients', null=True, blank=True)
    dettes_fournisseurs = models.BigIntegerField('dettes fournisseurs', null=True, blank=True)
    achats = models.BigIntegerField('achats', null=True, blank=True)
    stocks = models.BigIntegerField('stocks', null=True, blank=True)
    flux_exploitation = models.BigIntegerField('flux de trésorerie d’exploitation', null=True, blank=True)
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
        """Les 12 dossiers du cahier des charges v2 : ils recouvrent les 9 chapitres d’une due diligence d’investisseur."""
        PITCH = '01', '01 · Pitch et business plan'
        ETATS = '02', '02 · États financiers et projections'
        JURIDIQUE = '03', '03 · Juridique et gouvernance'
        FISCAL = '04', '04 · Fiscal (DSF, attestation de non-redevance)'
        LICENCES = '05', '05 · Licences et autorisations'
        CONTRATS = '06', '06 · Contrats et lettres d’intention'
        ACTIONNARIAT = '07', '07 · Actionnariat et table de capitalisation'
        RISQUES = '08', '08 · Risques et PESTEL'
        ESG = '09', '09 · ESG et traçabilité'
        SORTIE = '10', '10 · Stratégie de sortie'
        EQUIPE = '11', '11 · Équipe, RH et CNPS'
        ACTIFS = '12', '12 · Actifs et propriété intellectuelle'

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


class Attestation(models.Model):
    """v3 · 8.4 : un cabinet, un CGA ou une mutuelle atteste une pièce ou un exercice (niveau A). Datée, nommée, révocable."""
    organisation = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='attestations')
    attestateur = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='attestations_donnees')
    piece = models.ForeignKey(Piece, on_delete=models.CASCADE, null=True, blank=True, related_name='attestations')
    exercice = models.ForeignKey(ExerciceFinancier, on_delete=models.CASCADE, null=True, blank=True, related_name='attestations')
    portee = models.CharField('portée', max_length=255)
    niveau_avant = models.CharField(max_length=12, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoquee_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.attestateur} atteste {self.piece or self.exercice}'


class Partage(models.Model):
    """v3 · 6.3 : le passeport n’est jamais envoyé sans le clic de la PME ; chaque envoi est journalisé et révocable."""
    DESTINATAIRES = [('apme', 'APME · structuration'), ('api', 'API · investissement'), ('bvmac', 'BVMAC · marché financier'),
                     ('investisseur', 'Investisseur'), ('accompagnateur', 'Accompagnateur')]
    SECTIONS = [('profil', 'Profil'), ('grade', 'Grade, stade et confiance'), ('scores', 'Scores par dimension'), ('pieces', 'Liste des pièces et empreintes'),
                ('finances', 'États financiers'), ('usage', 'Usage des fonds'), ('accompagnement', 'Attestations d’accompagnateurs'), ('impact', 'Indicateurs d’impact')]
    organisation = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='partages')
    destinataire_type = models.CharField(max_length=16, choices=DESTINATAIRES)
    destinataire = models.ForeignKey('annuaire.Organisation', on_delete=models.SET_NULL, null=True, blank=True, related_name='passeports_recus')
    perimetre = models.JSONField(default=list)
    statut_retour = models.CharField('statut renvoyé par l’institution', max_length=120, blank=True)
    message_retour = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoque_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class Signalement(models.Model):
    """v3 · 6.2 : dette, garantie ou litige. Déclaré par la PME avant contrôle (divulgation spontanée) : pas de pénalité.
    Découvert par un investisseur : point rouge."""
    TYPES = [('dette', 'Dette non déclarée'), ('garantie', 'Garantie ou sûreté donnée'), ('litige', 'Litige ou contrôle en cours'), ('autre', 'Autre faiblesse')]
    organisation = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='signalements')
    auteur = models.ForeignKey('annuaire.Organisation', on_delete=models.SET_NULL, null=True, blank=True, related_name='signalements_faits')
    type = models.CharField(max_length=10, choices=TYPES)
    description = models.CharField(max_length=255)
    divulgation_spontanee = models.BooleanField(default=True)
    majeur = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class FicheCession(models.Model):
    """v3 · 7.2 : reprise, transmission, coentreprise ou fusion. Publiée en fiche anonyme ; le nom n’est révélé qu’avec l’accord du cédant."""
    OPERATIONS = [('cession_totale', 'Cession totale'), ('cession_partielle', 'Cession partielle'), ('transmission', 'Transmission familiale ou aux salariés'),
                  ('coentreprise', 'Coentreprise'), ('partenariat', 'Partenariat industriel'), ('fusion', 'Fusion'), ('rachat', 'Rachat d’un concurrent')]
    organisation = models.OneToOneField('annuaire.Organisation', on_delete=models.CASCADE, related_name='fiche_cession')
    operation = models.CharField('type d’opération', max_length=20, choices=OPERATIONS, default='cession_totale')
    motif = models.CharField(max_length=255, blank=True)
    dependance_dirigeant = models.CharField('dépendance au dirigeant', max_length=255, blank=True)
    actifs = models.TextField(blank=True)
    dettes = models.TextField(blank=True)
    contrats_cles = models.TextField('contrats clés', blank=True)
    salaries = models.PositiveIntegerField(null=True, blank=True)
    valeur_min = models.BigIntegerField('valeur basse (FCFA)', null=True, blank=True)
    valeur_max = models.BigIntegerField('valeur haute (FCFA)', null=True, blank=True)
    maintien_emplois = models.BooleanField('maintien des emplois exigé', default=True)
    publiee = models.BooleanField('publier la fiche anonyme', default=False)
    nom_revele = models.BooleanField('accord pour révéler le nom', default=False)
    updated_at = models.DateTimeField(auto_now=True)
