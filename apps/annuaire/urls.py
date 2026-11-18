from django.urls import path

from . import views

app_name = 'annuaire'
urlpatterns = [path('', views.ecosysteme, name='ecosysteme')]
