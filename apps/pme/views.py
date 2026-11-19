from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from apps.annuaire.models import Organisation
from apps.core.vitrine import _radial
from apps.core.decorators import role_requis
from apps.investissement import tableaux
from apps.investissement.models import DemandeAcces
from apps.investissement.services import SEUIL_AFFICHAGE, compatibilite

from . import services
from .forms import ExerciceForm, PieceForm, ProfilForm
from .models import EntrepriseProfile, ExerciceFinancier, Piece, ScoreSnapshot

NIVEAUX = ['declaratif', 'coherent', 'recoupe', 'certifie']

# Voies de sortie proposées dans « Niveau » (maquette w15)
SORTIES = [('Cession à un tiers (M&A)', '5 à 7 ans'), ('Rachat par l’équipe (MBO / LBO)', '5 à 8 ans'), ('Fusion', '4 à 6 ans'),
           ('Introduction en bourse', 'long terme, sous le contrôle de la COSUMAF'), ('Cession d’actifs', 'variable'), ('Transfert familial', '10 ans et plus')]


def _org(request):
    return request.user.organisation


def _investisseurs(org):
    """Investisseurs ayant une thèse, avec leur indice de compatibilité pour cette PME, du plus haut au plus bas."""
    lignes = []
    for inv in Organisation.objects.investisseurs().select_related('these').prefetch_related('these__secteurs'):
        these = getattr(inv, 'these', None)
        if these is not None:
            lignes.append((inv, compatibilite(these, org)))
    return sorted(lignes, key=lambda x: -x[1]['total'])


def _historique_svg(points):
    """Courbe du score de préparation (maquette « Votre progression ») : abscisses régulières, ordonnées de 30 à 80."""
    if len(points) < 2:
        return None
    bas, haut = 30, 80
    n = len(points)
    pos = [(3 + i * 94 / (n - 1), 100 - (min(max(s.total, bas), haut) - bas) / (haut - bas) * 100) for i, s in enumerate(points)]
    ligne = ' '.join(f'{x:.1f},{y:.1f}' for x, y in pos)
    return {'ligne': ligne, 'aire': f'{pos[0][0]:.1f},100 {ligne} {pos[-1][0]:.1f},100',
            'points': [{'x': f'{x:.1f}', 'y': f'{y:.1f}', 's': p.total, 'd': p.created_at} for (x, y), p in zip(pos, points)],
            'seuil75': f'{100 - (75 - bas) / (haut - bas) * 100:.1f}', 'seuil40': f'{100 - (40 - bas) / (haut - bas) * 100:.1f}'}


@role_requis('pme')
def tableau(request):
    """Accueil PME (maquette w10)."""
    org = _org(request)
    score = services.score_preparation(org)
    dernier = org.scores.first()
    if not dernier or dernier.total != score.total:
        ScoreSnapshot.objects.create(organisation=org, total=score.total, dimensions={k: v for k, _, v, _ in score.dims})
    historique = list(reversed(org.scores.all()[:8]))
    demandes = list(org.demandes_recues.select_related('investisseur'))
    invs = _investisseurs(org)
    compatibles = sum(1 for _, c in invs if c['total'] >= SEUIL_AFFICHAGE)
    n_acces = sum(1 for d in demandes if d.statut != 'abandon')
    n_reunion = sum(1 for d in demandes if d.statut in ('reunion', 'due_diligence', 'term_sheet', 'closing'))
    preuves = services.couverture_preuves(org)
    # Matrice de points : une colonne par dossier, une case par pièce (couleur du niveau), cases vides jusqu'à 4
    colonnes = []
    for code, lab, niveaux in services.matrice_pieces(org):
        cases = sorted(niveaux, key=lambda n: -NIVEAUX.index(n))[:6]
        colonnes.append({'code': code, 'lab': lab, 'cases': cases, 'vides': range(max(0, 4 - len(cases))), 'n': len(niveaux)})
    montant = services.montant_legitime(org)
    profil = getattr(org, 'profil_pme', None)
    return render(request, 'pme/tableau.html', {
        'org': org, 'score': score, 'restant': (score.prochain_palier[0] - score.total) if score.prochain_palier else 0,
        'montant': montant, 'actions': services.actions_prioritaires(org), 'preuves': preuves, 'colonnes': colonnes,
        'courbe': _historique_svg(historique), 'historique': historique,
        'progression': (historique[-1].total - historique[0].total) if len(historique) > 1 else 0,
        'demandes': demandes, 'a_signer': [d for d in demandes if d.statut == 'demande'],
        'compatibles': compatibles, 'n_acces': n_acces, 'n_reunion': n_reunion,
        'jauge': mark_safe(_radial(compatibles / len(invs), str(compatibles), f'sur {len(invs)} avec une thèse')) if invs else None,
        'photo': tableaux.photo(org), 'profil': profil,
        'n_a_faire': len(services.actions_prioritaires(org)) + sum(1 for d in demandes if d.statut == 'demande'),
    })


@role_requis('pme')
def dossier(request):
    """Data room (maquette w11) : les douze dossiers, l'ajout d'une pièce, les accès et leur journal."""
    org = _org(request)
    form = PieceForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        piece = form.save(commit=False)
        piece.organisation = org
        piece.save()
        messages.success(request, f'Pièce « {piece.titre} » ajoutée : niveau déclaratif, en attente de vérification.')
        return redirect('pme:dossier')
    pieces = {}
    for p in org.pieces.all():
        pieces.setdefault(p.dossier, []).append(p)
    dossiers = []
    for code, lab in Piece.Dossier.choices:
        liste = pieces.get(code, [])
        meilleur = max((p.niveau_preuve for p in liste), key=NIVEAUX.index, default=None)
        dossiers.append({'code': code, 'lab': lab.split(' · ', 1)[-1], 'pieces': liste, 'meilleur': meilleur,
                         'classe': tableaux.CLASSES_PREUVE.get(meilleur, ''), 'libelle': tableaux.LIBELLES_PREUVE.get(meilleur, ''),
                         'maj': max((p.created_at for p in liste), default=None)})
    demandes = list(org.demandes_recues.select_related('investisseur'))
    journal = sorted([(d.created_at, d.investisseur.nom, 'a demandé l’accès') for d in demandes] +
                     [(d.updated_at, d.investisseur.nom, d.get_statut_display().lower()) for d in demandes if d.statut != 'demande'],
                     key=lambda x: x[0], reverse=True)[:6]
    return render(request, 'pme/dossier.html', {
        'org': org, 'form': form, 'dossiers': dossiers, 'preuves': services.couverture_preuves(org), 'journal': journal,
        'actifs': [d for d in demandes if d.statut not in ('demande', 'abandon')], 'en_attente': [d for d in demandes if d.statut == 'demande']})


@role_requis('pme')
@require_POST
def supprimer_piece(request, pk):
    piece = get_object_or_404(Piece, pk=pk, organisation=_org(request))
    piece.fichier.delete(save=False)
    piece.delete()
    messages.info(request, 'Pièce retirée.')
    return redirect('pme:dossier')


@role_requis('pme')
def finances(request):
    """Financer (maquette w12) : montant légitime, exercices, stress tests, simulateurs."""
    org = _org(request)
    form = ExerciceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        ExerciceFinancier.objects.update_or_create(organisation=org, annee=d['annee'], defaults={k: d[k] for k in form.Meta.fields if k != 'annee'})
        messages.success(request, f'Exercice {d["annee"]} enregistré.')
        return redirect('pme:finances')
    exercices = sorted(org.exercices.all(), key=lambda e: e.annee)
    montant = services.montant_legitime(org)
    curseur = None
    if montant:
        mx = max(montant['demande'], montant['haut']) * 1.4
        curseur = {'min': 0, 'max': round(mx / 1e6 / 10) * 10, 'demande': montant['demande'] // 1_000_000,
                   'bas': montant['bas'] // 1_000_000, 'haut': montant['haut'] // 1_000_000}
        curseur['zone_g'] = round(curseur['bas'] / curseur['max'] * 100, 1)
        curseur['zone_l'] = round((curseur['haut'] - curseur['bas']) / curseur['max'] * 100, 1)
    return render(request, 'pme/finances.html', {
        'org': org, 'form': form, 'exercices': exercices, 'montant': montant, 'curseur': curseur,
        'stress': tableaux.stress_tests(exercices[-1] if exercices else None), 'kpis': tableaux.kpis(exercices, services.confiance_donnees(org)),
        'profil': getattr(org, 'profil_pme', None), 'ouvrir_exercices': request.method == 'POST'})


@role_requis('pme')
def profil(request):
    org = _org(request)
    profil_pme, _ = EntrepriseProfile.objects.get_or_create(organisation=org)
    form = ProfilForm(request.POST or None, instance=profil_pme)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profil mis à jour. Votre score a été recalculé.')
        return redirect('pme:tableau')
    return render(request, 'pme/profil.html', {'org': org, 'form': form})


@role_requis('pme')
def investisseurs(request):
    """Investisseurs compatibles (maquette w13) : le top 10 au-dessus du seuil, critère par critère, puis les écartés."""
    org = _org(request)
    lignes = _investisseurs(org)
    haut = [(i, c) for i, c in lignes if c['total'] >= SEUIL_AFFICHAGE][:10]
    ecartes = [(i, c, min(c['lignes'], key=lambda x: x[1] / x[2])) for i, c in lignes if c['total'] < SEUIL_AFFICHAGE][:8]
    references = Organisation.objects.investisseurs().filter(these__isnull=True)
    return render(request, 'pme/investisseurs.html', {'org': org, 'haut': haut, 'ecartes': ecartes, 'seuil': SEUIL_AFFICHAGE,
                                                       'n_references': references.count(), 'references': references[:8]})


@role_requis('pme')
def deals(request):
    """Suivi des deals (maquette w14) : l'étape du deal le plus avancé, puis tous les deals."""
    org = _org(request)
    demandes = list(org.demandes_recues.select_related('investisseur'))
    ordre = DemandeAcces.ORDRE
    actifs = [d for d in demandes if d.statut != 'abandon']
    principal = max(actifs, key=lambda d: (ordre.index(d.statut), d.updated_at), default=None)
    etapes = []
    if principal:
        i = ordre.index(principal.statut)
        etapes = [(lab, 'done' if k < i else 'cur' if k == i else '') for k, (code, lab) in enumerate(
            (c, l) for c, l in DemandeAcces.Statut.choices if c != 'abandon')]
    maintenant = timezone.now()
    for d in demandes:
        d.age = (maintenant - d.updated_at).days
    return render(request, 'pme/deals.html', {'org': org, 'demandes': demandes, 'principal': principal, 'etapes': etapes,
                                               'jours': (maintenant - principal.created_at).days if principal else 0})


@role_requis('pme')
def niveau(request):
    """Mise à niveau (maquette w15) : stratégie de sortie, actions, conformité, accompagnement."""
    org = _org(request)
    profil_pme, _ = EntrepriseProfile.objects.get_or_create(organisation=org)
    if request.method == 'POST':
        voie = request.POST.get('voie', '').strip()
        detail = request.POST.get('detail', '').strip()
        if voie:
            profil_pme.strategie_sortie = f'{voie}. {detail}'.strip().rstrip('.') + '.' if detail else voie
            profil_pme.save(update_fields=['strategie_sortie', 'updated_at'])
            messages.success(request, 'Stratégie de sortie enregistrée. Votre score a été recalculé.')
        else:
            messages.error(request, 'Choisissez une voie de sortie.')
        return redirect('pme:niveau')
    pieces = {p.dossier for p in org.pieces.all()}
    conformite = [('Statuts, RCCM et gouvernance (AUSCGIE)', '03' in pieces, 'dossier 03'),
                  ('DSF et attestation de non-redevance', '04' in pieces, 'dossier 04'),
                  ('États financiers SYSCOHADA (AUDCIF)', org.exercices.exists(), 'Financer'),
                  ('Table de capitalisation', '07' in pieces, 'dossier 07'),
                  ('Politique environnementale et sociale', '09' in pieces, 'dossier 09')]
    actuelle = profil_pme.strategie_sortie
    return render(request, 'pme/niveau.html', {
        'org': org, 'score': services.score_preparation(org), 'actions': services.actions_prioritaires(org, limite=8),
        'sorties': SORTIES, 'actuelle': actuelle, 'voie': next((v for v, _ in SORTIES if actuelle.startswith(v)), ''),
        'conformite': conformite, 'n_conformes': sum(1 for _, ok, _ in conformite if ok),
        'accompagnement': Organisation.objects.accompagnement().filter(pays='Cameroun').exclude(description='').order_by('-completude')[:5]})


@login_required
def telecharger_piece(request, pk):
    """Pièce de data room : visible par la PME propriétaire, ou par un investisseur dont l’accès est ouvert (accord signé)."""
    piece = get_object_or_404(Piece.objects.select_related('organisation'), pk=pk)
    org = request.user.organisation
    autorise = request.user.is_superuser or (org is not None and org.pk == piece.organisation_id) or (
        org is not None and DemandeAcces.objects.filter(investisseur=org, entreprise=piece.organisation)
        .exclude(statut__in=['demande', 'abandon']).exists())
    if not autorise or not piece.fichier:
        raise Http404
    if settings.DEBUG:
        return FileResponse(piece.fichier.open('rb'), as_attachment=False, filename=piece.fichier.name.rsplit('/', 1)[-1])
    reponse = HttpResponse()
    reponse['X-Accel-Redirect'] = settings.MEDIA_URL + piece.fichier.name   # servi par Nginx (location /media/ interne)
    reponse['Content-Disposition'] = f'inline; filename="{piece.fichier.name.rsplit("/", 1)[-1]}"'
    return reponse


@role_requis('pme')
@require_POST
def accepter_demande(request, pk):
    d = get_object_or_404(DemandeAcces, pk=pk, entreprise=_org(request))
    if d.statut == DemandeAcces.Statut.DEMANDE:
        d.statut = DemandeAcces.Statut.NDA
        d.save(update_fields=['statut', 'updated_at'])
        messages.success(request, f'Accord de confidentialité signé avec {d.investisseur}. Votre data room lui est ouverte.')
    suite = request.POST.get('suite')
    return redirect(suite if suite in ('pme:tableau', 'pme:dossier', 'pme:deals') else 'pme:deals')
