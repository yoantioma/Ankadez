from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Ankadez · administration'
admin.site.site_title = 'Ankadez'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('compte/', include('apps.accounts.urls')),
    path('ecosysteme/', include('apps.annuaire.urls')),
    path('pme/', include('apps.pme.urls')),
    path('investisseur/', include('apps.investissement.urls')),
]

# Les fichiers de data room ne sont jamais servis en accès libre : ils passent par pme:telecharger_piece.
handler404 = 'apps.core.views.erreur_404'
