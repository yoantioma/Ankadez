from django.urls import path

from . import views

app_name = 'accounts'
urlpatterns = [
    path('connexion/', views.Connexion.as_view(), name='connexion'),
    path('deconnexion/', views.Deconnexion.as_view(), name='deconnexion'),
    path('inscription/', views.inscription, name='inscription'),
    path('inscription/<str:role>/', views.inscription_compte, name='inscription_compte'),
    path('bienvenue/<str:role>/', views.onboarding, name='onboarding'),
]
