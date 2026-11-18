from django.contrib import admin

from .models import Organisation, Secteur


@admin.register(Secteur)
class SecteurAdmin(admin.ModelAdmin):
    search_fields = ['nom']
    prepopulated_fields = {'slug': ('nom',)}
    list_display = ['nom', 'slug']


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['nom', 'kind', 'secteur', 'ville', 'region', 'completude', 'a_verifier', 'est_demo', 'actif']
    list_filter = ['kind', 'a_verifier', 'est_demo', 'actif', 'region', 'secteur']
    search_fields = ['nom', 'description', 'ville', 'external_id']
    autocomplete_fields = ['secteur']
    readonly_fields = ['created_at', 'updated_at']
