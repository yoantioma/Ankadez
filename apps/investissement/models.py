from django.db import models


class These(models.Model):
    """Thèse d’investissement d’un investisseur : ce qu’il cherche. Elle alimente l’indice de compatibilité."""
    # v3 · 6.1 : stades d’investissement (second axe du passeport)
    STADES = [('angel', 'Angel / Pré-seed'), ('seed', 'Seed'), ('serie_a', 'Série A'), ('serie_b', 'Série B+'),
              ('developpement', 'Développement et reprise')]
    INSTRUMENTS = [('equity', 'Capital'), ('dette', 'Dette'), ('quasi', 'Quasi-fonds propres'), ('mixte', 'Mixte'),
                   ('subvention', 'Subvention'), ('garantie', 'Garantie'), ('credit_bail', 'Crédit-bail')]
    TYPES = [('banque', 'Banque'), ('fonds', 'Fonds d’investissement'), ('business_angel', 'Business angel'), ('diaspora', 'Diaspora'),
             ('mutuelle', 'Mutuelle d’entreprises'), ('ptf', 'Partenaire technique et financier'), ('repreneur', 'Repreneur'),
             ('incubateur', 'Incubateur ou structure d’appui')]
    NON_NEGOCIABLES = [('comptes_certifies', 'Comptes certifiés'), ('esg', 'Politique ESG'), ('dirigeante', 'Entreprise dirigée par une femme'),
                       ('emplois', 'Au moins 10 emplois'), ('garanties', 'Garanties disponibles')]
    SORTIES = [('remboursement', 'Remboursement'), ('revente', 'Revente à un tiers'), ('rachat_dirigeant', 'Rachat par le dirigeant'),
               ('introduction', 'Introduction en bourse'), ('industriel', 'Cession à un industriel')]

    organisation = models.OneToOneField('annuaire.Organisation', on_delete=models.CASCADE, related_name='these')
    secteurs = models.ManyToManyField('annuaire.Secteur', blank=True, related_name='theses')
    ticket_min = models.BigIntegerField('ticket minimum (FCFA)', null=True, blank=True)
    ticket_max = models.BigIntegerField('ticket maximum (FCFA)', null=True, blank=True)
    zones = models.JSONField('régions ou pays', default=list, blank=True)
    stades = models.JSONField(default=list, blank=True)
    instruments = models.JSONField(default=list, blank=True)
    exigence_esg = models.BooleanField('exigence ESG', default=False)
    horizon_annees = models.PositiveSmallIntegerField('horizon (années)', null=True, blank=True)
    type_acteur = models.CharField('qui êtes-vous ?', max_length=16, choices=TYPES, blank=True)
    non_negociables = models.JSONField('critères non négociables (filtres éliminatoires)', default=list, blank=True)
    sorties = models.JSONField('sorties acceptées', default=list, blank=True)
    contact_accompagnateur = models.BooleanField('parler d’abord à la structure qui accompagne l’entreprise', default=False)
    # v3 · 7.3 : critères propres aux mutuelles
    mutuelle_beneficiaires = models.CharField('mutuelle · qui peut bénéficier', max_length=200, blank=True)
    mutuelle_apport = models.CharField('mutuelle · ce qu’elle apporte', max_length=200, blank=True)
    mutuelle_delai = models.CharField('mutuelle · délai de décision annoncé', max_length=80, blank=True)
    mutuelle_regle = models.CharField('mutuelle · règle de la communauté', max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'thèse d’investissement'
        verbose_name_plural = 'thèses d’investissement'

    def __str__(self):
        return f'Thèse · {self.organisation}'


class DemandeAcces(models.Model):
    """Le fil d’un deal, de la demande d’accès au closing. Un abandon exige un motif."""

    class Statut(models.TextChoices):
        DEMANDE = 'demande', 'Accès demandé'
        NDA = 'nda', 'Accord de confidentialité signé'
        REUNION = 'reunion', 'Réunion tenue'
        DUE_DILIGENCE = 'due_diligence', 'Due diligence'
        TERM_SHEET = 'term_sheet', 'Term sheet'
        CLOSING = 'closing', 'Closing'
        ABANDON = 'abandon', 'Abandon'

    ORDRE = ['demande', 'nda', 'reunion', 'due_diligence', 'term_sheet', 'closing']

    investisseur = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='demandes_envoyees')
    entreprise = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='demandes_recues')
    statut = models.CharField(max_length=16, choices=Statut.choices, default=Statut.DEMANDE, db_index=True)
    indice = models.PositiveSmallIntegerField('indice de compatibilité au moment de la demande', null=True, blank=True)
    motif_abandon = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'demande d’accès'
        verbose_name_plural = 'demandes d’accès'
        ordering = ['-updated_at']
        constraints = [models.UniqueConstraint(fields=['investisseur', 'entreprise'], name='une_demande_par_couple')]

    def __str__(self):
        return f'{self.investisseur} → {self.entreprise} ({self.get_statut_display()})'

    @property
    def etape_index(self):
        return self.ORDRE.index(self.statut) if self.statut in self.ORDRE else -1

    def statut_suivant(self):
        i = self.etape_index
        return self.ORDRE[i + 1] if 0 <= i < len(self.ORDRE) - 1 else None


class TheseVersion(models.Model):
    """v3 · 4.2 : chaque changement du monde idéal est daté (fraîcheur de la thèse)."""
    these = models.ForeignKey(These, on_delete=models.CASCADE, related_name='versions')
    donnees = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class QuestionAccompagnateur(models.Model):
    """v3 · 8.3 : l’investisseur interroge la structure d’appui avant la PME, si la PME l’a autorisé. Journal visible de la PME."""
    investisseur = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='questions_posees')
    entreprise = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='questions_recues_pme')
    structure = models.ForeignKey('annuaire.Organisation', on_delete=models.CASCADE, related_name='questions_a_traiter')
    question = models.TextField()
    reponse = models.TextField(blank=True)
    signaler_pme = models.BooleanField('réponse plus précise : la PME est sollicitée', default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    repondu_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
