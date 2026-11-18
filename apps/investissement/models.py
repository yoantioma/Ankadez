from django.db import models


class These(models.Model):
    """Thèse d’investissement d’un investisseur : ce qu’il cherche. Elle alimente l’indice de compatibilité."""
    STADES = [('amorcage', 'Amorçage'), ('croissance', 'Croissance'), ('maturite', 'Maturité')]
    INSTRUMENTS = [('equity', 'Capital'), ('dette', 'Dette'), ('quasi', 'Quasi-fonds propres'), ('mixte', 'Mixte')]

    organisation = models.OneToOneField('annuaire.Organisation', on_delete=models.CASCADE, related_name='these')
    secteurs = models.ManyToManyField('annuaire.Secteur', blank=True, related_name='theses')
    ticket_min = models.BigIntegerField('ticket minimum (FCFA)', null=True, blank=True)
    ticket_max = models.BigIntegerField('ticket maximum (FCFA)', null=True, blank=True)
    zones = models.JSONField('régions ou pays', default=list, blank=True)
    stades = models.JSONField(default=list, blank=True)
    instruments = models.JSONField(default=list, blank=True)
    exigence_esg = models.BooleanField('exigence ESG', default=False)
    horizon_annees = models.PositiveSmallIntegerField('horizon (années)', null=True, blank=True)
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
