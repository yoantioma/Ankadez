from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.annuaire.models import Organisation
from apps.core.decorators import role_requis
from apps.investissement.models import DemandeAcces
from apps.investissement.services import compatibilite

from . import services
from .forms import ExerciceForm, PieceForm, ProfilForm
from .models import EntrepriseProfile, ExerciceFinancier, Piece, ScoreSnapshot


def _org(request):
    return request.user.organisation


@role_requis('pme')
def tableau(request):
    org = _org(request)
    score = services.score_preparation(org)
    dernier = org.scores.first()
    if not dernier or dernier.total != score.total:
        ScoreSnapshot.objects.create(organisation=org, total=score.total, dimensions={k: v for k, _, v, _ in score.dims})
    historique = list(reversed(org.scores.all()[:8]))
    demandes = org.demandes_recues.select_related('investisseur')
    return render(request, 'pme/tableau.html', {
        'org': org, 'score': score, 'restant': (score.prochain_palier[0] - score.total) if score.prochain_palier else 0,
        'montant': services.montant_legitime(org), 'actions': services.actions_prioritaires(org),
        'preuves': services.couverture_preuves(org), 'matrice': services.matrice_pieces(org), 'historique': historique,
        'demandes': demandes, 'n_nda': demandes.exclude(statut__in=['demande', 'abandon']).count(),
        'dernier_exercice': org.exercices.first(),
    })


@role_requis('pme')
def dossier(request):
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
    dossiers = [(code, lab, pieces.get(code, [])) for code, lab in Piece.Dossier.choices]
    return render(request, 'pme/dossier.html', {'org': org, 'form': form, 'dossiers': dossiers, 'preuves': services.couverture_preuves(org)})


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
    org = _org(request)
    form = ExerciceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        ExerciceFinancier.objects.update_or_create(organisation=org, annee=d['annee'], defaults={k: d[k] for k in form.Meta.fields if k != 'annee'})
        messages.success(request, f'Exercice {d["annee"]} enregistré.')
        return redirect('pme:finances')
    return render(request, 'pme/finances.html', {'org': org, 'form': form, 'exercices': org.exercices.all(), 'montant': services.montant_legitime(org)})


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
    org = _org(request)
    lignes = []
    for inv in Organisation.objects.investisseurs().select_related('these').prefetch_related('these__secteurs'):
        these = getattr(inv, 'these', None)
        if these is None:
            continue
        c = compatibilite(these, org)
        lignes.append((inv, c))
    lignes.sort(key=lambda x: -x[1]['total'])
    references = Organisation.objects.investisseurs().filter(these__isnull=True)[:12]
    demandes = org.demandes_recues.select_related('investisseur')
    return render(request, 'pme/investisseurs.html', {'org': org, 'lignes': lignes, 'references': references, 'demandes': demandes,
                                                       'n_references': Organisation.objects.investisseurs().filter(these__isnull=True).count()})


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
    return redirect('pme:investisseurs')
