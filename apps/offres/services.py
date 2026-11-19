"""Services v3 : diagnostic de 45 secondes (4.1), accompagnateurs recommandés (8.1, 8.2), vitrine de produits (7.1),
détecteur d’incitations (9.1), programmes par niche (7.4) et vue d’impact des PTF (5.4)."""
from django.db.models import Q

from apps.annuaire.models import Organisation

from .models import Incitation, ProduitFinancier, Programme, QuestionDiagnostic

PHRASES = [(80, 'Votre dossier est presque prêt pour un financeur.'), (60, 'Vous avez fait plus de la moitié du chemin.'),
           (40, 'Vous êtes à la moitié du chemin.'), (20, 'Les bases sont posées, il reste l’essentiel à rassembler.'),
           (0, 'Tout commence ici : quelques pièces suffisent pour avancer vite.')]

# 8.1 : quel accompagnateur à quelle étape
ETAPES_ACCOMPAGNEMENT = [
    ('formalisation', 'Formalisation', 'RCCM ou NIU manquant', 'Guichet d’entreprise, conseil administratif'),
    ('comptabilite', 'Comptabilité', 'Pas d’états SYSCOHADA', 'Expert-comptable, CGA'),
    ('fiscalite', 'Fiscalité', 'Attestation de non-redevance absente', 'Fiscaliste, CGA'),
    ('montage', 'Plan d’affaires et usage des fonds', 'Besoin non chiffré', 'Mentor financement, consultant en montage de projet'),
    ('structuration', 'Structuration financière', 'Dette ou capital ?', 'Conseil en structuration financière'),
    ('juridique', 'Juridique', 'Pacte, term sheet, prêt convertible', 'Avocat OHADA'),
    ('pi', 'Propriété intellectuelle', 'Marque non déposée, droits non cédés', 'Conseil en propriété industrielle (OAPI)'),
    ('normes', 'Normes et licences', 'Certification, exigences sanitaires', 'ANOR et organismes sectoriels'),
    ('mentor', 'Pitch et salle de données', 'Dossier désordonné', 'Mentor, incubateur, accélérateur'),
]
LIBELLES_SPECIALITE = {s: (lab, qui) for s, lab, _, qui in ETAPES_ACCOMPAGNEMENT}


def questions():
    return list(QuestionDiagnostic.objects.filter(actif=True))


def diagnostic(reponses):
    """reponses : {ordre: True/False}. Score déclaré (indice de confiance D) : il oriente, il ne donne aucun grade."""
    qs = questions()
    total = sum(q.poids for q in qs) or 100
    score = round(sum(q.poids for q in qs if reponses.get(q.ordre)) / total * 100)
    manquantes = sorted([q for q in qs if not reponses.get(q.ordre)], key=lambda q: (-q.poids, q.ordre))
    phrase = next(t for s, t in PHRASES if score >= s)
    prochaine = manquantes[0].action if manquantes else 'Créez votre passeport : vos réponses sont reprises.'
    specialites = []
    for q in manquantes:
        if q.specialite not in specialites:
            specialites.append(q.specialite)
    return {'score': score, 'phrase': phrase, 'manquantes': manquantes[:3], 'prochaine': prochaine,
            'accompagnateurs': recommander(specialites[0] if specialites else 'mentor', 3), 'specialite': specialites[0] if specialites else 'mentor'}


def recommander(specialite, n=3, region=None):
    """8.2 : le rang repose sur des faits (qualification vérifiée, dossiers menés, complétude de la fiche), jamais sur un paiement.
    Le référencement payant donne un badge « partenaire » séparé, sans effet sur le rang."""
    qs = Organisation.objects.accompagnement().filter(specialites__icontains=specialite)
    if region:
        locaux = qs.filter(Q(region__iexact=region) | Q(ville__icontains=region))
        if locaux.count() >= n:
            qs = locaux
    return list(qs.order_by('-qualification_verifiee', '-dossiers_menes', '-completude', 'nom')[:n])


def recommandations_par_etape(org, score):
    """Pour la PME : 2 à 3 accompagnateurs à chaque marche bloquante (déclencheurs du tableau 8.1)."""
    profil = getattr(org, 'profil_pme', None)
    pieces = {p.dossier for p in org.pieces.all()}
    bloque = []
    if not (profil and profil.rccm):
        bloque.append('formalisation')
    if not org.exercices.exists():
        bloque.append('comptabilite')
    if '04' not in pieces:
        bloque.append('fiscalite')
    if not (profil and profil.usage_fonds and profil.ticket_recherche):
        bloque.append('montage')
    if profil and profil.instrument_souhaite in ('', 'mixte'):
        bloque.append('structuration')
    if '12' not in pieces:
        bloque.append('pi')
    if '05' not in pieces:
        bloque.append('normes')
    if score.total < 60:
        bloque.append('mentor')
    if '07' not in pieces:
        bloque.append('juridique')
    region = org.region if org.region else None
    return [(s, LIBELLES_SPECIALITE[s][0], LIBELLES_SPECIALITE[s][1], recommander(s, 3, region)) for s in bloque[:4]]


def produits_pour(org, score):
    """7.1 : « Pour vous, maintenant » (toutes les conditions remplies) et « À votre portée avec 2 pièces de plus »."""
    profil = getattr(org, 'profil_pme', None)
    pieces = {p.dossier for p in org.pieces.all()}
    secteur = f'{org.secteur.nom if org.secteur else ""} {org.description}'.lower()
    maintenant, portee = [], []
    from apps.pme.models import Piece
    noms = dict(Piece.Dossier.choices)
    for p in ProduitFinancier.objects.filter(actif=True):
        if p.femme and not (profil and profil.dirigeante):
            continue
        if p.secteurs and not any(m in secteur for m in p.secteurs):
            continue
        manque = [noms[d].split(' · ')[1] for d in p.pieces_exigees if d not in pieces]
        if score.total < p.grade_min:
            manque.append(f'Score de préparation de {p.grade_min} au moins')
        if not manque:
            maintenant.append((p, []))
        elif len(manque) <= 2:
            portee.append((p, manque))
    return maintenant[:5], portee[:5]


def incitations_pour(org):
    """9.1 : éligibilité probable, jamais présentée comme acquise ; rappel de la comptabilité séparée."""
    profil = getattr(org, 'profil_pme', None)
    texte = f'{org.secteur.nom if org.secteur else ""} {org.description} {org.kind}'.lower()
    sortie = []
    for i in Incitation.objects.filter(actif=True, cote_investisseur=False):
        raisons = []
        if i.secteurs and any(m in texte for m in i.secteurs):
            raisons.append('secteur')
        if i.regions and org.region in i.regions:
            raisons.append(f'région {org.region}')
        if i.zones and profil and profil.zone_incitative and any(z in profil.zone_incitative.lower() for z in i.zones):
            raisons.append(f'zone {profil.zone_incitative}')
        if i.export and profil and (profil.part_export or 0) >= 50:
            raisons.append('exportatrice')
        if i.jeunes and profil and profil.emplois_jeunes:
            raisons.append('emploi de jeunes')
        regle_secteur = not i.secteurs or 'secteur' in raisons
        regle_region = not i.regions or any(r.startswith('région') for r in raisons) or any(r.startswith('zone') for r in raisons)
        if raisons and regle_secteur and regle_region:
            sortie.append((i, raisons))
    return sortie


def programmes(niche=None):
    qs = Programme.objects.filter(actif=True)
    return [p for p in qs if not niche or niche in p.niches]


def impact(orgs):
    """5.4 : ce qu’un PTF regarde, pour une entreprise ou un portefeuille."""
    from apps.pme.models import EntrepriseProfile
    profils = [getattr(o, 'profil_pme', None) for o in orgs]
    profils = [p for p in profils if p]
    somme = lambda attr: sum(getattr(p, attr) or 0 for p in profils)
    n = len(profils) or 1
    ptf, prive = somme('financement_ptf'), somme('financement_prive')
    regions = {}
    for o in orgs:
        regions[o.region or 'Non précisée'] = regions.get(o.region or 'Non précisée', 0) + 1
    return {
        'n': len(profils), 'emplois': somme('effectif'), 'femmes': somme('emplois_femmes'), 'jeunes': somme('emplois_jeunes'),
        'dirigeantes': round(sum(1 for p in profils if p.dirigeante) / n * 100), 'rurales': sum(1 for p in profils if p.zone_rurale),
        'incitatives': sum(1 for p in profils if p.zone_incitative), 'export': round(sum((p.part_export or 0) for p in profils) / n),
        'zlecaf': sum(1 for p in profils if p.export_zlecaf), 'energie': sum(1 for p in profils if p.energie_propre),
        'cnps': somme('salaries_cnps'), 'levier': round(prive / ptf, 1) if ptf else None, 'regions': sorted(regions.items(), key=lambda x: -x[1]),
        'objectifs': [('Investisseurs mobilisés', 30), ('FCFA mobilisés', 500_000_000), ('Emplois', 100), ('Projets', 5)],
    }
