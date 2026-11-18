from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.forms import TheseForm
from apps.annuaire.models import Organisation, Secteur
from apps.core.decorators import est_partiel, role_requis
from apps.pme import services as pme_services

from .models import DemandeAcces, These
from .services import SEUIL_AFFICHAGE, compatibilite


def _these(request):
    return getattr(request.user.organisation, 'these', None)


@role_requis('investisseur')
def marketplace(request):
    these = _these(request)
    qs = Organisation.objects.entreprises().select_related('secteur', 'profil_pme').prefetch_related('exercices', 'pieces')
    q = request.GET.get('q', '').strip()
    secteur = request.GET.get('secteur', '')
    comptes = request.GET.get('comptes', '')
    tri = request.GET.get('tri', 'indice')
    if q:
        qs = qs.filter(Q(nom__icontains=q) | Q(description__icontains=q) | Q(ville__icontains=q))
    if secteur:
        qs = qs.filter(secteur__slug=secteur)
    if comptes == '1':
        qs = qs.filter(exercices__isnull=False).distinct()
    lignes = []
    masquees = 0
    for org in qs:
        c = compatibilite(these, org)
        if not c['visible']:
            masquees += 1
            continue
        lignes.append({'org': org, 'c': c, 'ex': next(iter(org.exercices.all()), None), 'profil': getattr(org, 'profil_pme', None)})
    if tri == 'ticket':
        lignes.sort(key=lambda l: -((l['profil'].ticket_recherche if l['profil'] else 0) or 0))
    else:
        lignes.sort(key=lambda l: (-l['c']['total'], l['org'].nom))
    page = Paginator(lignes, 12).get_page(request.GET.get('page'))
    ctx = {'page': page, 'q': q, 'secteur': secteur, 'comptes': comptes, 'tri': tri, 'masquees': masquees, 'seuil': SEUIL_AFFICHAGE,
           'secteurs': Secteur.objects.filter(organisations__kind__in=Organisation.KINDS_ENTREPRISE).distinct(), 'these': these,
           'demandees': set(request.user.organisation.demandes_envoyees.values_list('entreprise_id', flat=True))}
    if est_partiel(request):
        return render(request, 'investissement/_cartes.html', ctx)
    return render(request, 'investissement/marketplace.html', ctx)


@role_requis('investisseur')
def fiche(request, slug):
    org = get_object_or_404(Organisation.objects.entreprises().select_related('secteur', 'profil_pme'), slug=slug)
    these = _these(request)
    c = compatibilite(these, org)
    demande = DemandeAcces.objects.filter(investisseur=request.user.organisation, entreprise=org).first()
    exercices = list(org.exercices.order_by('annee'))
    max_ca = max((e.chiffre_affaires for e in exercices), default=0)
    return render(request, 'investissement/fiche.html', {
        'org': org, 'c': c, 'demande': demande, 'exercices': exercices, 'max_ca': max_ca, 'dernier': exercices[-1] if exercices else None,
        'score': pme_services.score_preparation(org), 'montant': pme_services.montant_legitime(org),
        'preuves': pme_services.couverture_preuves(org), 'matrice': pme_services.matrice_pieces(org),
        'acces': demande is not None and demande.statut not in ('demande', 'abandon'),
    })


@role_requis('investisseur')
@require_POST
def demander_acces(request, slug):
    org = get_object_or_404(Organisation.objects.entreprises(), slug=slug)
    c = compatibilite(_these(request), org)
    _, cree = DemandeAcces.objects.get_or_create(investisseur=request.user.organisation, entreprise=org, defaults={'indice': c['total']})
    if cree:
        messages.success(request, f'Demande d’accès envoyée à {org.nom}. Vous serez prévenu dès la signature de l’accord de confidentialité.')
    return redirect('investissement:fiche', slug=slug)


@role_requis('investisseur')
def pipeline(request):
    demandes = request.user.organisation.demandes_envoyees.select_related('entreprise__secteur')
    colonnes = [(s, lab, [d for d in demandes if d.statut == s]) for s, lab in DemandeAcces.Statut.choices]
    return render(request, 'investissement/pipeline.html', {'colonnes': colonnes, 'total': len(demandes)})


@role_requis('investisseur')
@require_POST
def faire_avancer(request, pk):
    d = get_object_or_404(DemandeAcces, pk=pk, investisseur=request.user.organisation)
    action = request.POST.get('action')
    if action == 'abandon':
        motif = request.POST.get('motif', '').strip()
        if not motif:
            messages.error(request, 'Un abandon exige un motif.')
            return redirect('investissement:pipeline')
        d.statut, d.motif_abandon = DemandeAcces.Statut.ABANDON, motif[:255]
    elif d.statut == DemandeAcces.Statut.DEMANDE:
        messages.info(request, 'La PME doit d’abord signer l’accord de confidentialité.')
        return redirect('investissement:pipeline')
    elif d.statut_suivant():
        d.statut = d.statut_suivant()
    d.save()
    messages.success(request, f'{d.entreprise} : {d.get_statut_display()}.')
    return redirect('investissement:pipeline')


@role_requis('investisseur')
def these(request):
    org = request.user.organisation
    t = getattr(org, 'these', None) or These(organisation=org)
    initial = {'nom': org.nom, 'ville': org.ville, 'pays': org.pays, 'zones': t.zones, 'stades': t.stades, 'instruments': t.instruments,
               'exigence_esg': t.exigence_esg, 'horizon_annees': t.horizon_annees,
               'ticket_min': t.ticket_min // 1_000_000 if t.ticket_min else None, 'ticket_max': t.ticket_max // 1_000_000 if t.ticket_max else None,
               'secteurs': list(t.secteurs.all()) if t.pk else []}
    form = TheseForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        org.nom, org.ville, org.pays = d['nom'], d['ville'], d['pays'] or 'Cameroun'
        org.save()
        for k in ('ticket_min', 'ticket_max', 'zones', 'stades', 'instruments', 'exigence_esg', 'horizon_annees'):
            setattr(t, k, d[k])
        t.save()
        t.secteurs.set(d['secteurs'])
        messages.success(request, 'Thèse mise à jour : les indices ont été recalculés.')
        return redirect('investissement:marketplace')
    return render(request, 'investissement/these.html', {'form': form})
