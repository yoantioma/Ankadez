from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.forms import TheseForm
from apps.annuaire.models import Organisation, Secteur
from apps.core.decorators import role_requis
from apps.pme import services as pme_services
from apps.pme.models import EntrepriseProfile

from . import tableaux

from .models import DemandeAcces, These
from .services import SEUIL_AFFICHAGE, compatibilite


def _these(request):
    return getattr(request.user.organisation, 'these', None)


GRADES = [('40', 'Pré-Ready et plus'), ('60', 'Investment-Ready et plus'), ('75', 'Série A et plus')]


def _entier(v):
    try:
        return int(str(v).replace(' ', ''))
    except (TypeError, ValueError):
        return None


@role_requis('investisseur')
def marketplace(request):
    """Marketplace des PME (maquette w20) : grille, liste ou pile, filtres à gauche."""
    these = _these(request)
    qs = Organisation.objects.entreprises().select_related('secteur', 'profil_pme').prefetch_related('exercices', 'pieces')
    f = {'q': request.GET.get('q', '').strip(), 'secteurs': request.GET.getlist('secteur'), 'grade': request.GET.get('grade', ''),
         'tmin': request.GET.get('tmin', ''), 'tmax': request.GET.get('tmax', ''), 'instruments': request.GET.getlist('instrument'),
         'zlecaf': request.GET.get('zlecaf') == '1', 'comptes': request.GET.get('comptes') == '1', 'tri': request.GET.get('tri', 'indice')}
    if f['q']:
        qs = qs.filter(Q(nom__icontains=f['q']) | Q(description__icontains=f['q']) | Q(ville__icontains=f['q']))
    if f['secteurs']:
        qs = qs.filter(secteur__slug__in=f['secteurs'])
    if f['instruments']:
        qs = qs.filter(profil_pme__instrument_souhaite__in=f['instruments'])
    if f['zlecaf']:
        qs = qs.filter(profil_pme__export_zlecaf=True)
    if f['comptes']:
        qs = qs.filter(exercices__isnull=False).distinct()
    tmin, tmax = _entier(f['tmin']), _entier(f['tmax'])
    if tmin is not None:
        qs = qs.filter(profil_pme__ticket_recherche__gte=tmin * 1_000_000)
    if tmax is not None:
        qs = qs.filter(profil_pme__ticket_recherche__lte=tmax * 1_000_000)
    grade = _entier(f['grade'])
    lignes, masquees = [], 0
    for org in qs:
        c = compatibilite(these, org)
        if not c['visible']:
            masquees += 1
            continue
        ligne = tableaux.carte_pme(org, c)
        if grade and ligne['score'].total < grade:
            continue
        lignes.append(ligne)
    if f['tri'] == 'ticket':
        lignes.sort(key=lambda x: -(x['ticket'] or 0))
    elif f['tri'] == 'score':
        lignes.sort(key=lambda x: (-x['score'].total, -x['c']['total']))
    else:
        lignes.sort(key=lambda x: (-x['c']['total'], x['org'].nom))
    page = Paginator(lignes, 12).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    secteurs = (Secteur.objects.filter(organisations__kind__in=Organisation.KINDS_ENTREPRISE)
                .annotate(n=Count('organisations')).order_by('-n', 'nom'))
    return render(request, 'investissement/marketplace.html', {
        'page': page, 'f': f, 'masquees': masquees, 'seuil': SEUIL_AFFICHAGE, 'these': these, 'secteurs': secteurs, 'grades': GRADES,
        'instruments': EntrepriseProfile.Instrument.choices, 'params': params.urlencode(), 'filtre_actif': bool(params),
        'demandees': set(request.user.organisation.demandes_envoyees.values_list('entreprise_id', flat=True))})


@role_requis('investisseur')
def fiche(request, slug):
    """Fiche d’une PME vue par l’investisseur (maquette w22) : onglets, chiffres et preuves."""
    org = get_object_or_404(Organisation.objects.entreprises().select_related('secteur', 'profil_pme').prefetch_related('pieces', 'exercices'), slug=slug)
    these = _these(request)
    c = compatibilite(these, org)
    request.session['derniere_fiche'] = org.slug
    demande = DemandeAcces.objects.filter(investisseur=request.user.organisation, entreprise=org).first()
    exercices = sorted(org.exercices.all(), key=lambda e: e.annee)
    dernier = exercices[-1] if exercices else None
    score = pme_services.score_preparation(org)
    preuves = pme_services.couverture_preuves(org)
    pieces = sorted(org.pieces.all(), key=lambda p: -tableaux.POIDS.get(p.niveau_preuve, 0))
    cases = [(tableaux.COULEURS_PREUVE[p.niveau_preuve], f'{p.titre} · {tableaux.LIBELLES_PREUVE[p.niveau_preuve]}') for p in pieces]
    cases += [('var(--ligne)', 'Pièce manquante')] * preuves['manquantes']
    # Position parmi les PME du même secteur : part des PME à un niveau inférieur ou égal (médiane à 50 %)
    pairs, n_pairs = [], 0
    if org.secteur_id:
        autres = list(Organisation.objects.entreprises().filter(secteur_id=org.secteur_id).prefetch_related('exercices', 'pieces'))
        if len(autres) >= 3:
            n_pairs = len(autres)

            def rang(val, vals):
                vals = [v for v in vals if v is not None]
                return round(sum(1 for v in vals if v <= val) / len(vals) * 100) if val is not None and vals else None

            def dern(o):
                return max(o.exercices.all(), key=lambda e: e.annee, default=None)

            mesures = [('Score de préparation', score.total, [pme_services.score_preparation(o).total for o in autres], str(score.total)),
                       ('Marge EBITDA', dernier.marge_ebitda if dernier else None,
                        [dern(o).marge_ebitda for o in autres if dern(o)], tableaux.pct(dernier.marge_ebitda if dernier else None)),
                       ('Confiance des données', score.confiance, [pme_services.confiance_donnees(o) for o in autres], f'{score.confiance} %')]
            pairs = [(lab, rang(v, vals), txt) for lab, v, vals, txt in mesures if v is not None and rang(v, vals) is not None]
    return render(request, 'investissement/fiche.html', {
        'org': org, 'c': c, 'demande': demande, 'exercices': exercices, 'dernier': dernier,
        'score': score, 'montant': pme_services.montant_legitime(org), 'preuves': preuves, 'donut': tableaux.donut(preuves['compte']),
        'barres': tableaux.barres_exercices(exercices), 'kpis': tableaux.kpis(exercices, score.confiance),
        'stress': tableaux.stress_tests(dernier), 'cases': cases, 'pairs': pairs, 'n_pairs': n_pairs,
        'photo': tableaux.photo(org), 'matrice': pme_services.matrice_pieces(org),
        'recentes': sorted(org.pieces.all(), key=lambda p: p.created_at, reverse=True)[:4],
        'attestees': preuves['compte'].get('certifie', 0),
        'acces': demande is not None and demande.statut not in ('demande', 'abandon'),
    })


@role_requis('investisseur')
def secteurs(request, slug=None):
    """Tableau de bord d’un secteur (maquette w19), calculé sur les PME inscrites."""
    these = _these(request)
    classement, tous, groupes = tableaux.classement_secteurs(these)
    if not classement:
        return render(request, 'investissement/secteur.html', {'vide': True})
    if slug is None:
        preferes = set(these.secteurs.values_list('id', flat=True)) if these else set()
        choix = next((s for _, s in classement if s.id in preferes), classement[0][1])
        return redirect('investissement:secteur', slug=choix.slug)
    secteur = get_object_or_404(Secteur, slug=slug)
    if secteur not in tous:
        raise Http404
    rang = next(i for i, (_, s) in enumerate(classement, 1) if s == secteur)
    score, axes = next(a for a, s in classement if s == secteur)
    st = tous[secteur]
    return render(request, 'investissement/secteur.html', {
        'st': st, 'score': score, 'axes': axes, 'rang': rang, 'n_secteurs': len(classement), 'jauge': tableaux.jauge(score),
        'classement': [(s, a[0], len(groupes[s])) for a, s in classement], 'matrice': tableaux.matrice_marges(st['marges']),
        'sucettes': tableaux.sucettes(st['tickets']), 'these': these,
        'dans_these': bool(these and these.secteurs.filter(pk=secteur.pk).exists()),
        'photo': next((l['photo'] for l in st['lignes'] if l['photo']), ''), 'top': st['lignes'][:5],
        'ticket_median': tableaux.millions(st['ticket_median']) if st['ticket_median'] else '—',
        'total_tickets': tableaux.millions(st['total_tickets']), 'marge_mediane': tableaux.pct(st['marge_mediane']),
        'score_median': round(st['score_median']) if st['score_median'] is not None else None,
        'confiance_mediane': round(st['confiance_mediane']) if st['confiance_mediane'] is not None else None})


@role_requis('investisseur')
def cameroun(request):
    """Page d’arrivée de l’investisseur connecté : la même vue du Cameroun que sur l’accueil public,
    avec en haut à droite les trois secteurs les plus porteurs."""
    from apps.core import vitrine
    from apps.core.services import accueil_investisseur
    m = accueil_investisseur()
    classement, _, groupes = tableaux.classement_secteurs(_these(request))
    top3 = [(s, a[0], len(groupes[s])) for a, s in classement[:3]]
    return render(request, 'investissement/cameroun.html', {'m': m, 'v': vitrine.composants(m), 'top3': top3})


@role_requis('investisseur')
def entreprises(request):
    """Comparatif des PME (maquette w23) : croissance et marge en nuage de points, à retenir, tableau."""
    these = _these(request)
    slug = request.GET.get('secteur', '')
    secteur = Secteur.objects.filter(slug=slug).first() if slug else None
    qs = Organisation.objects.entreprises().select_related('secteur', 'profil_pme').prefetch_related('exercices', 'pieces')
    if secteur:
        qs = qs.filter(secteur=secteur)
    lignes = []
    for org in qs:
        c = compatibilite(these, org)
        if not c['visible']:
            continue
        ex = sorted(org.exercices.all(), key=lambda e: e.annee)
        d = ex[-1] if ex else None
        preuves = pme_services.couverture_preuves(org)
        lignes.append({**tableaux.carte_pme(org, c), 'croissance': tableaux.croissance(ex), 'marge': d.marge_ebitda if d else None,
                       'dscr': d.dscr if d else None, 'verifie': preuves['pct_verifiees'] if preuves['deposees'] else None,
                       'montant': pme_services.montant_legitime(org)})
    lignes.sort(key=lambda x: (-x['c']['total'], x['org'].nom))
    seuil_c = tableaux._mediane([x['croissance'] for x in lignes])
    seuil_m = tableaux._mediane([x['marge'] for x in lignes])
    # Nuage : croissance (axe horizontal, 0 à 30 %) et marge EBITDA (axe vertical, 0 à 25 %)
    points = []
    for i, x in enumerate(lignes):
        if x['croissance'] is None or x['marge'] is None:
            continue
        points.append({'l': x, 'top': i < 3, 'x': max(0, min(100, x['croissance'] / 35 * 100)), 'y': max(0, min(100, x['marge'] / 25 * 100)),
                       'taille': 14 + min(12, (x['ticket'] or 0) / 50_000_000)})
    for x in lignes[:3]:
        raisons = []
        if x['croissance'] is not None and seuil_c is not None:
            raisons.append(x['croissance'] >= seuil_c)
        if x['marge'] is not None and seuil_m is not None:
            raisons.append(x['marge'] >= seuil_m)
        if x['dscr'] is not None:
            raisons.append(x['dscr'] >= 1.2)
        if not raisons:
            x['verdict'], x['pourquoi'] = 'à compléter', 'Comptes à déclarer'
        elif all(raisons):
            x['verdict'], x['pourquoi'] = 'à voir', f'Au-dessus des {len(raisons)} seuils'
        else:
            x['verdict'] = 'vigilance'
            x['pourquoi'] = ('DSCR sous 1,2' if x['dscr'] is not None and x['dscr'] < 1.2 else
                             'Marge sous la médiane' if x['marge'] is not None and seuil_m is not None and x['marge'] < seuil_m else 'Croissance sous la médiane')
    return render(request, 'investissement/entreprises.html', {
        'lignes': lignes, 'points': points, 'secteur': secteur, 'seuil_c': seuil_c, 'seuil_m': seuil_m,
        'secteurs': Secteur.objects.filter(organisations__kind__in=Organisation.KINDS_ENTREPRISE).annotate(n=Count('organisations')).order_by('-n', 'nom'),
        'qx': [(round(v / 35 * 100, 1), f'{v} %') for v in (0, 10, 20, 30)], 'qy': [(v * 4, f'{v} %') for v in (0, 10, 20)],
        'pos_c': round(min(100, seuil_c / 35 * 100), 1) if seuil_c is not None else None,
        'pos_m': round(min(100, seuil_m / 25 * 100), 1) if seuil_m is not None else None})


@role_requis('investisseur')
def fiche_courante(request):
    """Onglet « Fiche PME » : la dernière fiche ouverte, sinon la PME la plus compatible."""
    slug = request.session.get('derniere_fiche')
    if slug and Organisation.objects.entreprises().filter(slug=slug).exists():
        return redirect('investissement:fiche', slug=slug)
    these = _these(request)
    meilleure = max(Organisation.objects.entreprises().prefetch_related('pieces'), key=lambda o: compatibilite(these, o)['total'], default=None)
    if not meilleure:
        return redirect('investissement:marketplace')
    return redirect('investissement:fiche', slug=meilleure.slug)


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
    demandes = list(request.user.organisation.demandes_envoyees.select_related('entreprise__secteur', 'entreprise__profil_pme'))
    for d in demandes:
        d.photo = tableaux.photo(d.entreprise)
        profil = getattr(d.entreprise, 'profil_pme', None)
        d.ticket = tableaux.millions(profil.ticket_recherche) if profil and profil.ticket_recherche else None
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
