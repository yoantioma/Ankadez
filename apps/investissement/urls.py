from django.urls import path

from . import views

app_name = 'investissement'
urlpatterns = [
    path('', views.marketplace, name='marketplace'),
    path('these/', views.these, name='these'),
    path('pipeline/', views.pipeline, name='pipeline'),
    path('pipeline/<int:pk>/avancer/', views.faire_avancer, name='faire_avancer'),
    path('entreprise/<slug:slug>/', views.fiche, name='fiche'),
    path('entreprise/<slug:slug>/acces/', views.demander_acces, name='demander_acces'),
]
