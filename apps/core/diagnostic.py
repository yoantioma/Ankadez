"""Diagnostic de 45 secondes (cahier des charges v3 · 4.1) : 8 questions oui/non, résultat actionnable, passage au passeport."""
from django.shortcuts import render
from django.utils import timezone

from apps.accounts.forms import REGIONS
from apps.annuaire.models import Organisation, Secteur
from apps.offres import services as offres

TRANCHES_CA = [('0', 'Moins de 50 M FCFA'), ('50', '50 à 250 M'), ('250', '250 M à 1 Md'), ('1000', 'Plus de 1 Md')]
NICHE_PAR_MOT = [('agro', 'agro'), ('agri', 'agro'), ('numér', 'numerique'), ('digital', 'numerique'), ('data', 'numerique'),
                 ('fintech', 'financement'), ('commerce', 'export'), ('zlecaf', 'export'), ('santé', 'social')]


def page(request):
    qs = offres.questions()
    ctx = {'questions': qs, 'secteurs': Secteur.objects.order_by('nom'), 'regions': REGIONS, 'tranches': TRANCHES_CA}
    if request.method != 'POST':
        return render(request, 'core/diagnostic.html', ctx)
    reponses = {q.ordre: request.POST.get(f'q{q.ordre}') == '1' for q in qs}
    r = offres.diagnostic(reponses)
    secteur = Secteur.objects.filter(pk=request.POST.get('secteur') or 0).first()
    region = request.POST.get('region', '')
    ca = request.POST.get('ca', '')
    financeurs, programmes = [], []
    if secteur or region:
        for inv in Organisation.objects.investisseurs().select_related('these').prefetch_related('these__secteurs'):
            t = getattr(inv, 'these', None)
            if not t:
                continue
            ok_secteur = not secteur or not t.secteurs.exists() or t.secteurs.filter(pk=secteur.pk).exists()
            zones = [z.lower() for z in t.zones or []]
            ok_region = not region or not zones or region.lower() in zones or 'cemac' in zones
            if ok_secteur and ok_region:
                financeurs.append(inv)
        mots = (secteur.nom.lower() if secteur else '')
        niches = {n for m, n in NICHE_PAR_MOT if m in mots} | {'financement', 'montage'}
        programmes = [p for p in offres.programmes() if set(p.niches) & niches][:4]
    request.session['diagnostic'] = {'reponses': {str(k): v for k, v in reponses.items()}, 'score': r['score'], 'date': timezone.now().isoformat(),
                                     'secteur': secteur.pk if secteur else None, 'region': region, 'ca': ca}
    return render(request, 'core/diagnostic.html', {**ctx, 'r': r, 'reponses': reponses, 'financeurs': financeurs[:6], 'n_financeurs': len(financeurs),
                                                    'programmes': programmes, 'secteur_choisi': secteur, 'region_choisie': region})
