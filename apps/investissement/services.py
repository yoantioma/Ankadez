"""Indice de compatibilité : 6 critères, 100 points, une raison écrite par critère.
Ce n’est jamais une probabilité de closing (v3, décision D9).

v3 : stades d’investissement (Angel à Série B+, Développement), filtres éliminatoires (ticket hors fourchette et critères
non négociables), trois colonnes (compatibles, presque compatibles, à surveiller) et profil anonymisé avant consentement."""
from apps.pme import v3 as regles_v3

SEUIL_AFFICHAGE = 55
SEUIL_PRESQUE = 45


def compatibilite(these, org):
    profil = getattr(org, 'profil_pme', None)
    lignes = []

    secteurs = set(these.secteurs.values_list('id', flat=True)) if these else set()
    if not secteurs:
        lignes.append(('Secteur', 15, 25, 'Thèse ouverte à tous les secteurs'))
    elif org.secteur_id in secteurs:
        lignes.append(('Secteur', 25, 25, f'{org.secteur} fait partie de votre thèse'))
    else:
        lignes.append(('Secteur', 0, 25, 'Secteur hors de votre thèse'))

    # Ticket (cahier des charges v2) : recouvrement de [Tmin ; Tmax] et [10 % ; 100 %] du besoin : 20 points.
    # Sinon décroissance linéaire, nulle à 50 % d’écart de la borne la plus proche.
    besoin = profil.ticket_recherche if profil else None
    if not besoin or not these or (not these.ticket_min and not these.ticket_max):
        lignes.append(('Ticket', 10, 20, 'Montant ou fourchette non renseigné'))
    else:
        tmin, tmax = these.ticket_min or 0, these.ticket_max or besoin
        bas, haut = besoin * 0.10, besoin
        if tmin <= haut and tmax >= bas:
            lignes.append(('Ticket', 20, 20, 'Votre ticket couvre une part du besoin (10 à 100 %)'))
        else:
            borne = bas if tmax < bas else haut
            ecart = (bas - tmax) if tmax < bas else (tmin - haut)
            pts = max(0, round(20 * (1 - ecart / (borne * 0.5)))) if borne else 0
            lignes.append(('Ticket', pts, 20, 'Ticket trop petit pour ce besoin' if tmax < bas else 'Ticket supérieur au besoin'))

    zones = [z.lower() for z in (these.zones if these else [])]
    if not zones:
        lignes.append(('Zone', 10, 15, 'Zone non précisée'))
    elif org.region.lower() in zones or org.pays.lower() in zones or 'cemac' in zones or org.ville.lower() in zones:
        lignes.append(('Zone', 15, 15, f'{org.region or org.pays} dans votre zone'))
    elif profil and profil.zone_incitative and profil.zone_incitative.lower() in zones:
        lignes.append(('Zone', 15, 15, f'Zone {profil.zone_incitative} dans votre zone'))
    else:
        lignes.append(('Zone', 0, 15, 'Hors de votre zone'))

    stades = these.stades if these else []
    stade = regles_v3.stade(org)
    if not stades:
        lignes.append(('Stade', 8, 15, 'Stade non précisé dans votre thèse'))
    else:
        lignes.append(('Stade', 15, 15, f'Stade {regles_v3.STADES[stade]} accepté') if stade in stades
                      else ('Stade', 0, 15, f'Stade {regles_v3.STADES[stade]} hors de vos stades'))

    instruments = these.instruments if these else []
    instr = profil.instrument_souhaite if profil else ''
    if not instruments or not instr:
        lignes.append(('Instrument', 8, 15, 'Instrument non renseigné'))
    elif instr in instruments or instr == 'mixte' or 'mixte' in instruments:
        lignes.append(('Instrument', 15, 15, 'Instrument compatible'))
    else:
        lignes.append(('Instrument', 0, 15, 'Instrument différent'))

    esg = org.pieces.filter(dossier='09').exists()
    if these and these.exigence_esg:
        lignes.append(('ESG', 10 if esg else 3, 10, 'Politique ESG fournie' if esg else 'Politique ESG à fournir'))
    else:
        lignes.append(('ESG', 10 if esg else 6, 10, 'Pas d’exigence ESG' if not esg else 'Politique ESG fournie'))

    total = sum(l[1] for l in lignes)
    exclus = eliminatoires(these, org, lignes)
    manque = min(lignes, key=lambda l: l[1] / l[2])
    return {'total': total, 'lignes': lignes, 'visible': total >= SEUIL_AFFICHAGE and not exclus, 'exclus': exclus,
            'colonne': colonne(total, exclus), 'manque': manque[3]}


def eliminatoires(these, org, lignes=None):
    """Filtres éliminatoires (v2 maintenu, v3 écran 7) : une seule raison suffit à écarter l’entreprise."""
    if not these:
        return []
    profil = getattr(org, 'profil_pme', None)
    raisons = []
    if lignes and any(l[0] == 'Ticket' and l[1] == 0 for l in lignes):
        raisons.append('Ticket hors de votre fourchette')
    nn = these.non_negociables or []
    ex = list(org.exercices.all())
    if 'comptes_certifies' in nn and not any(e.niveau_preuve == 'certifie' for e in ex):
        raisons.append('Comptes non certifiés')
    if 'esg' in nn and not org.pieces.filter(dossier='09').exists():
        raisons.append('Pas de politique ESG')
    if 'dirigeante' in nn and not (profil and profil.dirigeante):
        raisons.append('Entreprise non dirigée par une femme')
    if 'emplois' in nn and not (profil and (profil.effectif or 0) >= 10):
        raisons.append('Moins de 10 emplois')
    if 'garanties' in nn and not org.pieces.filter(dossier='12').exists():
        raisons.append('Aucune garantie ou actif déclaré')
    return raisons


def colonne(total, exclus):
    """Tableau de bord investisseur en trois colonnes (v3 · 4.2)."""
    if exclus:
        return 'exclu'
    if total >= SEUIL_AFFICHAGE:
        return 'compatible'
    if total >= SEUIL_PRESQUE:
        return 'presque'
    return 'surveiller'


def en_progression(org):
    scores = list(org.scores.all()[:6])
    return len(scores) >= 2 and scores[0].total > scores[-1].total


def acces_ouvert(investisseur, org):
    from .models import DemandeAcces
    return DemandeAcces.objects.filter(investisseur=investisseur, entreprise=org).exclude(statut__in=['demande', 'abandon']).exists()


def nom_public(org, investisseur=None, acces=None):
    """Avant le consentement de l’entreprise, l’investisseur voit un profil anonymisé (v2, rappelé en v3 · 4.2)."""
    if acces is None:
        acces = bool(investisseur) and acces_ouvert(investisseur, org)
    if acces:
        return org.nom
    secteur = org.secteur.nom.split(',')[0] if org.secteur else 'PME'
    return f'{secteur} · {org.region or org.pays} · n° {org.pk:04d}'
