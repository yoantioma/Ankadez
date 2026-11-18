from django.urls import path

from . import views

app_name = 'core'
urlpatterns = [
    path('', views.landing, name='landing'),
    path('espace/', views.espace, name='espace'),
    path('apercu/<str:vue>/', views.apercu, name='apercu'),
    path('landing-simple/', views.landing_simple, name='landing_simple'),
]
