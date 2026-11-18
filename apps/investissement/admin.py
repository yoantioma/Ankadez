from django.contrib import admin

from .models import DemandeAcces, These


@admin.register(These)
class TheseAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'ticket_min', 'ticket_max', 'exigence_esg']
    filter_horizontal = ['secteurs']
    autocomplete_fields = ['organisation']


@admin.register(DemandeAcces)
class DemandeAccesAdmin(admin.ModelAdmin):
    list_display = ['investisseur', 'entreprise', 'statut', 'indice', 'updated_at']
    list_filter = ['statut']
    search_fields = ['investisseur__nom', 'entreprise__nom']
    autocomplete_fields = ['investisseur', 'entreprise']
