"""Chiffres de l’accueil investisseur : calculés sur les entreprises réellement présentes en base."""
from statistics import median

from django.conf import settings
from django.db.models import Count

from apps.annuaire.models import Organisation
from apps.pme.models import ExerciceFinancier


def accueil_investisseur():
    entreprises = Organisation.objects.entreprises()
    n_entreprises = entreprises.count()
    n_secteurs = entreprises.exclude(secteur=None).values('secteur').distinct().count()

    # Dernier exercice de chaque entreprise, s’il existe
    derniers = {}
    for ex in ExerciceFinancier.objects.filter(organisation__in=entreprises).select_related('organisation__secteur').order_by('organisation_id', '-annee'):
        derniers.setdefault(ex.organisation_id, ex)
    avec_mb = [ex for ex in derniers.values() if ex.marge_brute]
    potentiel = sum(ex.marge_brute for ex in avec_mb)
    par_secteur = {}
    for ex in avec_mb:
        nom = ex.organisation.secteur.nom if ex.organisation.secteur else 'Autres'
        par_secteur[nom] = par_secteur.get(nom, 0) + ex.marge_brute
    top = sorted(par_secteur.items(), key=lambda kv: -kv[1])
    top3 = [(nom, v, round(v / potentiel * 100) if potentiel else 0) for nom, v in top[:3]]
    autres = potentiel - sum(v for _, v, _ in top3)

    tickets = sorted(t for t in entreprises.exclude(profil_pme__ticket_recherche=None).values_list('profil_pme__ticket_recherche', flat=True) if t)
    total_tickets = sum(tickets)
    deux_plus_gros = sum(tickets[-2:]) if tickets else 0
    cibles = settings.READYMATCH_CIBLES
    avec_comptes = len(derniers)
    dscr = sorted((ex.dscr for ex in derniers.values() if ex.dscr), reverse=True)
    sorties = entreprises.exclude(profil_pme__strategie_sortie='').exclude(profil_pme__strategie_sortie__isnull=True).count()

    if potentiel >= 1e9:
        potentiel_aff = (f'{potentiel / 1e9:.2f}'.replace('.', ','), 'Md')
    else:
        potentiel_aff = (f'{potentiel / 1e6:.0f}', 'M')
    if tickets:
        med = median(tickets)
        span = (tickets[-1] - tickets[0]) or 1
        tickets_info = {'min': tickets[0], 'med': med, 'max': tickets[-1], 'n': len(tickets), 'pos': round((med - tickets[0]) / span * 100, 1)}
    else:
        tickets_info = None
    return {
        'potentiel': potentiel,
        'potentiel_aff': potentiel_aff,
        'n_avec_marge': len(avec_mb),
        'top3': top3,
        'autres': autres,
        'n_entreprises': n_entreprises,
        'n_secteurs': n_secteurs,
        'tickets': tickets_info,
        'tickets_liste': tickets,
        'n_zlecaf': entreprises.filter(profil_pme__export_zlecaf=True).count(),
        'total_tickets': total_tickets,
        'profondeur_pct': round(total_tickets / cibles['capital_cible_milieu_fcfa'] * 100, 1) if total_tickets else 0,
        'concentration_pct': round(deux_plus_gros / total_tickets * 100) if total_tickets else 0,
        'avec_comptes': avec_comptes,
        'dscr': dscr,
        'dscr_sous_seuil': sum(1 for d in dscr if d < 1.2),
        'sorties_ecrites': sorties,
        'cibles': cibles,
        'n_investisseurs': Organisation.objects.investisseurs().count(),
        'acteurs_accompagnement': Organisation.objects.accompagnement().values('kind').annotate(n=Count('id')).order_by('-n'),
    }
