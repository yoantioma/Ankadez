from django.urls import path

from . import views

app_name = 'investissement'
urlpatterns = [
    path('', views.cameroun, name='cameroun'),
    path('marketplace/', views.marketplace, name='marketplace'),
    path('entreprises/', views.entreprises, name='entreprises'),
    path('fiche/', views.fiche_courante, name='fiche_courante'),
    path('secteurs/', views.secteurs, name='secteurs'),
    path('secteurs/<slug:slug>/', views.secteurs, name='secteur'),
    path('these/', views.these, name='these'),
    path('pipeline/', views.pipeline, name='pipeline'),
    path('pipeline/<int:pk>/avancer/', views.faire_avancer, name='faire_avancer'),
    path('entreprise/<slug:slug>/', views.fiche, name='fiche'),
    path('entreprise/<slug:slug>/acces/', views.demander_acces, name='demander_acces'),
]
