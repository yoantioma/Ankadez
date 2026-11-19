from django.urls import path

from . import diagnostic, pages_v3, views

app_name = 'core'
urlpatterns = [
    path('', views.landing, name='landing'),
    path('espace/', views.espace, name='espace'),
    path('diagnostic/', diagnostic.page, name='diagnostic'),
    path('academie/', pages_v3.academie, name='academie'),
    path('programmes/', pages_v3.programmes, name='programmes'),
    path('conseil-consultatif/', pages_v3.conseil, name='conseil'),
    path('observatoire/', pages_v3.observatoire, name='observatoire'),
    path('apercu/<str:vue>/', views.apercu, name='apercu'),
    path('vitrine-v1/', views.landing_vitrine, name='landing_vitrine'),
    path('landing-simple/', views.landing_simple, name='landing_simple'),
]
