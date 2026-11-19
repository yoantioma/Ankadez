from django.urls import path

from . import views, vues_v3

app_name = 'pme'
urlpatterns = [
    path('', views.tableau, name='tableau'),
    path('data-room/', views.dossier, name='dossier'),
    path('data-room/<int:pk>/retirer/', views.supprimer_piece, name='supprimer_piece'),
    path('data-room/<int:pk>/fichier/', views.telecharger_piece, name='telecharger_piece'),
    path('finances/', views.finances, name='finances'),
    path('profil/', views.profil, name='profil'),
    path('investisseurs/', views.investisseurs, name='investisseurs'),
    path('deals/', views.deals, name='deals'),
    path('niveau/', views.niveau, name='niveau'),
    path('passeport/', vues_v3.passeport, name='passeport'),
    path('passeport/passeport-ankadez.json', vues_v3.passeport_json, name='passeport_json'),
    path('passeport/imprimer/', vues_v3.passeport_imprimer, name='passeport_imprimer'),
    path('reprise/', vues_v3.reprise, name='reprise'),
    path('radar-clauses/', vues_v3.radar, name='radar'),
    path('data-room/divulguer/', vues_v3.divulguer, name='divulguer'),
    path('niveau/accompagnement/', vues_v3.choisir_accompagnateur, name='choisir_accompagnateur'),
    path('demandes/<int:pk>/accepter/', views.accepter_demande, name='accepter_demande'),
]
