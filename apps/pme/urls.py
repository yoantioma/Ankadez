from django.urls import path

from . import views

app_name = 'pme'
urlpatterns = [
    path('', views.tableau, name='tableau'),
    path('data-room/', views.dossier, name='dossier'),
    path('data-room/<int:pk>/retirer/', views.supprimer_piece, name='supprimer_piece'),
    path('data-room/<int:pk>/fichier/', views.telecharger_piece, name='telecharger_piece'),
    path('finances/', views.finances, name='finances'),
    path('profil/', views.profil, name='profil'),
    path('investisseurs/', views.investisseurs, name='investisseurs'),
    path('demandes/<int:pk>/accepter/', views.accepter_demande, name='accepter_demande'),
]
