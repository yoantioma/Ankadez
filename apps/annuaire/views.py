from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from apps.core.decorators import est_partiel

from .models import Organisation, Secteur

TYPES = [('', 'Tous'), ('incubateur', 'Incubateurs'), ('institution', 'Institutions'), ('association', 'Associations'),
         ('consultant', 'Consultants'), ('investisseur', 'Investisseurs')]


def ecosysteme(request):
    kinds = [k for k, _ in TYPES if k]
    qs = Organisation.objects.filter(kind__in=kinds, actif=True).select_related('secteur')
    kind = request.GET.get('type', '')
    q = request.GET.get('q', '').strip()
    secteur = request.GET.get('secteur', '')
    if kind in kinds:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(description__icontains=q) | Q(ville__icontains=q) | Q(categorie__icontains=q))
    if secteur:
        qs = qs.filter(secteur__slug=secteur)
    page = Paginator(qs, 18).get_page(request.GET.get('page'))
    ctx = {'page': page, 'types': TYPES, 'kind': kind, 'q': q, 'secteur': secteur,
           'secteurs': Secteur.objects.filter(organisations__kind__in=kinds).distinct(),
           'compteurs': dict(Organisation.objects.filter(kind__in=kinds, actif=True).values_list('kind').annotate(n=Count('id')))}
    if est_partiel(request):
        return render(request, 'annuaire/_liste.html', ctx)
    return render(request, 'annuaire/ecosysteme.html', ctx)
