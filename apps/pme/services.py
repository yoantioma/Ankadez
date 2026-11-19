"""Calculs explicables côté PME : score de préparation, montant légitime, actions prioritaires.
Chaque règle est écrite en clair pour pouvoir être montrée à la PME et à l’investisseur."""
from dataclasses import dataclass, field

from .models import POIDS_PREUVE, ExerciceFinancier, Piece

DIMENSIONS = [('finance', 'Finance', 30), ('juridique', 'Juridique et gouvernance', 20), ('marche', 'Marché et traction', 20),
              ('equipe', 'Équipe', 10), ('conformite', 'Conformité', 10), ('sortie', 'Risques et sortie', 10)]

# Deux lectures du même dossier (cahier des charges v2, 5.1) : une banque et un fonds ne regardent pas la même chose.
LUNETTE_DETTE = {'finance': 40, 'juridique': 15, 'marche': 15, 'equipe': 5, 'conformite': 15, 'sortie': 10}
LUNETTE_FONDS_PROPRES = {'finance': 20, 'juridique': 20, 'marche': 30, 'equipe': 20, 'conformite': 5, 'sortie': 5}

# Grades v2 : le score ouvre la porte, les pièces la tiennent ouverte.
PALIERS = [(90, 'Institutional-Ready'), (75, 'Série A / Growth-Ready'), (60, 'Investment-Ready'), (40, 'Pré-Ready'), (0, 'Structuring')]
PLAFOND_DECLARATIF = 59       # sans pièce justifiée, le score plafonne à 59

PIECES_EXIGEES = 45           # pack Standard (Léger : 25, Institutionnel : 90 et plus)


@dataclass
class Score:
    total: int
    dims: list = field(default_factory=list)  # (clé, libellé, points, max)
    palier: str = ''
    prochain_palier: tuple | None = None       # (seuil, libellé)
    dette: int = 0                             # lecture « banque »
    fonds_propres: int = 0                     # lecture « fonds »
    confiance: int = 0                         # % de données justifiées ou attestées
    plafonne: bool = False
    stade: str = ''                            # v3 · 6.1 second axe
    stade_libelle: str = ''
    points_rouges: list = field(default_factory=list)
    porte_bloquante: str = ''                  # grade gardé par une porte non franchie
    portes_manquantes: list = field(default_factory=list)
    penalite: int = 0                          # faiblesses découvertes (divulgation non spontanée)

    @property
    def affichage(self):
        return f'{self.palier} ({self.total}/100) · Stade {self.stade_libelle} · Confiance {self.confiance} %'


def confiance_donnees(org):
    """Indice de confiance : chaque donnée est Déclarée, Justifiée (pièce) ou Attestée (tiers).
    Confiance = (A × 1,0 + J × 0,7) ÷ nombre de données. Ici : pièces et exercices financiers."""
    niveaux = [p.niveau_preuve for p in org.pieces.all()] + [e.niveau_preuve for e in org.exercices.all()]
    if not niveaux:
        return 0
    attestees = sum(1 for n in niveaux if n == 'certifie')
    justifiees = sum(1 for n in niveaux if n in ('coherent', 'recoupe'))
    from .v3 import coefficient_fraicheur   # v3 · 6.3 : un passeport vieillit
    return round((attestees + 0.7 * justifiees) / len(niveaux) * 100 * coefficient_fraicheur(org)[0])


def _pieces_par_dossier(org):
    compte = {}
    for p in org.pieces.all():
        compte.setdefault(p.dossier, []).append(p)
    return compte


def score_preparation(org):
    profil = getattr(org, 'profil_pme', None)
    exercices = list(org.exercices.all())
    pieces = _pieces_par_dossier(org)
    n = lambda d: len(pieces.get(d, []))

    finance = min(len(exercices), 3) * 4
    if exercices:
        dernier = exercices[0]
        finance += POIDS_PREUVE.get(dernier.niveau_preuve, 1) * 2
        finance += 5 if dernier.marge_brute else 0
        finance += 5 if (dernier.dscr or 0) >= 1.2 else 0
    juridique = (5 if profil and profil.forme_juridique else 0) + (3 if profil and profil.rccm else 0) + min(n('03') * 3, 12)
    marche = (5 if org.description else 0) + (5 if org.secteur_id else 0) + min(n('06') * 3, 10)
    equipe = (4 if profil and profil.effectif else 0) + min(n('11') * 3, 6)
    conformite = min((n('04') + n('09')) * 3, 10)
    sortie = (6 if profil and profil.sortie_ecrite else 0) + min(n('08') * 2, 4)
    valeurs = {'finance': finance, 'juridique': juridique, 'marche': marche, 'equipe': equipe, 'conformite': conformite, 'sortie': sortie}
    dims = [(k, lab, min(valeurs[k], mx), mx) for k, lab, mx in DIMENSIONS]
    total = sum(d[2] for d in dims)
    justifie = any(p.niveau_preuve != 'declaratif' for p in org.pieces.all()) or any(e.niveau_preuve != 'declaratif' for e in exercices)
    plafonne = not justifie and total > PLAFOND_DECLARATIF
    if plafonne:
        total = PLAFOND_DECLARATIF
    # v3 · 6.2 : pénalité des faiblesses découvertes, puis portes de preuve et points rouges
    from . import v3
    penalite = v3.penalite_divulgation(org)
    total = max(0, total - penalite)
    maxi, porte, manquantes = v3.plafond_portes(org)
    if total > maxi:
        total = maxi
    else:
        porte, manquantes = (porte, manquantes) if maxi < 100 and total >= maxi else ('', [])
    st = v3.stade(org)
    lecture = lambda poids: round(sum(v / mx * poids[k] for k, _, v, mx in dims))
    palier = next(lab for seuil, lab in PALIERS if total >= seuil)
    suivant = next(((s, lab) for s, lab in reversed(PALIERS) if s > total), None)
    return Score(total=total, dims=dims, palier=palier, prochain_palier=suivant, dette=lecture(LUNETTE_DETTE),
                 fonds_propres=lecture(LUNETTE_FONDS_PROPRES), confiance=confiance_donnees(org), plafonne=plafonne,
                 stade=st, stade_libelle=v3.STADES[st], points_rouges=v3.points_rouges(org), porte_bloquante=porte or '',
                 portes_manquantes=manquantes, penalite=penalite)


def montant_legitime(org):
    """Trois méthodes, une fourchette indicative. Retourne None si les données manquent."""
    profil = getattr(org, 'profil_pme', None)
    dernier = org.exercices.order_by('-annee').first()
    if not profil or not profil.ticket_recherche or not dernier or not dernier.ebitda:
        return None
    besoin = profil.ticket_recherche
    dette = max(int(dernier.ebitda / 1.2 * 4) - (dernier.dette_nette or 0), 0)   # 4 ans de couverture à 1,2
    equity = int(dernier.ebitda * 5 * 0.30)                                      # 5× EBITDA, 30 % de dilution
    capacite = dette + equity
    haut = min(besoin, capacite)
    bas = int(haut * 0.9)
    return {'bas': bas, 'haut': haut, 'demande': besoin, 'methodes': [('Besoin déclaré', besoin), ('Capacité d’endettement', dette), ('Capacité en capital', equity)],
            'couverture_pct': round(haut / besoin * 100) if besoin else None}


def actions_prioritaires(org, limite=5):
    profil = getattr(org, 'profil_pme', None)
    pieces = _pieces_par_dossier(org)
    actions = []
    if not org.exercices.exists():
        actions.append(('Déclarer vos états financiers', 'Finance', 12, 'pme:finances'))
    elif org.exercices.count() < 3:
        actions.append(('Ajouter les exercices précédents', 'Finance', 4, 'pme:finances'))
    if not (profil and profil.sortie_ecrite):
        actions.append(('Écrire une stratégie de sortie', 'Risques et sortie', 6, 'pme:profil'))
    if not pieces.get('03'):
        actions.append(('Déposer les statuts et le RCCM', 'Juridique', 6, 'pme:dossier'))
    if not pieces.get('04'):
        actions.append(('Joindre la dernière DSF et l’attestation de non-redevance', 'Fiscal', 6, 'pme:dossier'))
    if not pieces.get('07'):
        actions.append(('Documenter la table de capitalisation', 'Actionnariat', 3, 'pme:dossier'))
    if not pieces.get('06'):
        actions.append(('Joindre un contrat client ou une lettre d’intention', 'Marché', 3, 'pme:dossier'))
    if not any(p.niveau_preuve != 'declaratif' for p in org.pieces.all()):
        actions.append(('Faire attester une pièce (expert-comptable, CGA, banque)', 'Confiance', 0, 'pme:dossier'))
    if not pieces.get('09'):
        actions.append(('Décrire votre politique environnementale et sociale', 'Conformité', 3, 'pme:dossier'))
    if not (profil and profil.ticket_recherche):
        actions.append(('Indiquer le montant recherché', 'Financement', 0, 'pme:profil'))
    return sorted(actions, key=lambda a: -a[2])[:limite]


def couverture_preuves(org):
    compte = {k: 0 for k in POIDS_PREUVE}
    for p in org.pieces.all():
        compte[p.niveau_preuve] = compte.get(p.niveau_preuve, 0) + 1
    deposees = sum(compte.values())
    verifiees = compte['recoupe'] + compte['certifie']
    return {'compte': compte, 'deposees': deposees, 'exigees': PIECES_EXIGEES, 'manquantes': max(PIECES_EXIGEES - deposees, 0),
            'pct_verifiees': round(verifiees / deposees * 100) if deposees else 0}


def matrice_pieces(org):
    """Pour le visuel en points : par dossier, la liste des niveaux de preuve des pièces déposées."""
    pieces = _pieces_par_dossier(org)
    return [(code, lab.split(' · ')[1], [p.niveau_preuve for p in pieces.get(code, [])]) for code, lab in Piece.Dossier.choices]
