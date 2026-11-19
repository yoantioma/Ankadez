from django.contrib import admin

from .models import Incitation, ProduitFinancier, Programme, QuestionDiagnostic


@admin.register(ProduitFinancier)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['institution_nom', 'nom', 'type', 'verifie_le', 'actif']
    list_filter = ['type', 'actif', 'femme']
    search_fields = ['institution_nom', 'nom']


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ['porteur', 'nom', 'prix', 'verifie_le', 'actif']
    search_fields = ['porteur', 'nom']


@admin.register(Incitation)
class IncitationAdmin(admin.ModelAdmin):
    list_display = ['famille', 'concerne', 'fiabilite', 'actif']


@admin.register(QuestionDiagnostic)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['ordre', 'texte', 'poids', 'specialite', 'actif']
    list_editable = ['poids', 'actif']
