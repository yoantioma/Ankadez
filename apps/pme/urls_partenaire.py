from django.urls import path

from . import partenaire as v

app_name = 'partenaire'
urlpatterns = [
    path('', v.tableau, name='tableau'),
    path('pme/<int:pk>/', v.client, name='client'),
    path('pme/<int:pk>/attester/', v.attester, name='attester'),
    path('pme/<int:pk>/revoquer/<int:att>/', v.revoquer, name='revoquer'),
    path('pme/<int:pk>/export/<str:fmt>/', v.export, name='export'),
    path('question/<int:q>/repondre/', v.repondre, name='repondre'),
]
