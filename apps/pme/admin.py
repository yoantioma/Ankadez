from django.contrib import admin

from .models import EntrepriseProfile, ExerciceFinancier, Piece, ScoreSnapshot


class ExerciceInline(admin.TabularInline):
    model = ExerciceFinancier
    extra = 0


@admin.register(EntrepriseProfile)
class EntrepriseProfileAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'forme_juridique', 'stade', 'ticket_recherche', 'export_zlecaf']
    list_filter = ['forme_juridique', 'stade', 'instrument_souhaite']
    search_fields = ['organisation__nom']
    autocomplete_fields = ['organisation']


@admin.register(ExerciceFinancier)
class ExerciceAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'annee', 'chiffre_affaires', 'marge_brute', 'ebitda', 'niveau_preuve']
    list_filter = ['annee', 'niveau_preuve']
    search_fields = ['organisation__nom']
    autocomplete_fields = ['organisation']


@admin.register(Piece)
class PieceAdmin(admin.ModelAdmin):
    list_display = ['titre', 'organisation', 'dossier', 'niveau_preuve', 'created_at']
    list_filter = ['dossier', 'niveau_preuve']
    list_editable = ['niveau_preuve']
    search_fields = ['titre', 'organisation__nom']
    autocomplete_fields = ['organisation']


admin.site.register(ScoreSnapshot)
