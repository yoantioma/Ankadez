"""Données des écrans investisseur, mises en forme pour les maquettes web du canevas.
Tout est calculé sur la base : aucune valeur inventée. Quand une donnée manque, le bloc le dit."""
from statistics import median

from django.templatetags.static import static

from apps.core.vitrine import _radial
from apps.pme import services as pme
from apps.pme.models import POIDS_PREUVE as POIDS

# Photo de couverture d’une PME, selon son secteur (les autres ont un aplat violet avec les initiales).
PHOTOS = [(('cacao',), 'cacao'), (('lait',), 'lait'), (('agro', 'agri', 'aliment'), 'agro'), (('port', 'logist', 'transport'), 'port'),
          (('energie', 'solaire', 'green'), 'solaire'), (('textile', 'couture', 'mode'), 'couture')]

COULEURS_PREUVE = {'declaratif': '#5E5B70', 'coherent': '#8F5A00', 'recoupe': '#17754E', 'certifie': '#1F5FD1'}
CLASSES_PREUVE = {'declaratif': 'p-decl', 'coherent': 'p-coh', 'recoupe': 'p-rec', 'certifie': 'p-cert'}
LIBELLES_PREUVE = {'declaratif': 'Déclaratif', 'coherent': 'Cohérent', 'recoupe': 'Recoupé', 'certifie': 'Certifié'}


def photo(org):
    cle = f'{org.secteur.slug if org.secteur else ""} {org.description[:80].lower()}'
    for mots, nom in PHOTOS:
        if any(m in cle for m in mots):
            return static(f'img/photos/{nom}.webp')
    return ''


def millions(v):
    """500 000 000 → « 500 M », 1 240 000 000 → « 1,24 Md »."""
    if v is None:
        return '—'
    if abs(v) >= 1e9:
        return f'{v / 1e9:.2f}'.replace('.', ',') + ' Md'
    return f'{v / 1e6:.0f} M'


def pct(v, d=0):
    return '—' if v is None else (f'{v:.{d}f}'.replace('.', ',') + ' %')


def donut(compte):
    """Anneau des niveaux de preuve (même tracé que la maquette)."""
    total = sum(compte.values())
    if not total:
        return ''
    arcs, decalage = '', 0.0
    for niv in ('declaratif', 'coherent', 'recoupe', 'certifie'):
        part = compte.get(niv, 0) / total * 100
        if part:
            arcs += (f'<circle cx="60" cy="60" r="46" fill="none" stroke="{COULEURS_PREUVE[niv]}" stroke-width="16" pathLength="100" '
                     f'stroke-dasharray="{part:.1f} 100" stroke-dashoffset="{-decalage:.1f}" transform="rotate(-90 60 60)"/>')
        decalage += part
    verif = round((compte.get('recoupe', 0) + compte.get('certifie', 0)) / total * 100)
    return (f'<svg width="120" height="120" viewBox="0 0 120 120" role="img" aria-label="Répartition des niveaux de preuve">{arcs}'
            f'<text x="60" y="58" text-anchor="middle" style="font:300 26px var(--f);fill:var(--encre)">{verif} %</text>'
            f'<text x="60" y="76" text-anchor="middle" style="font:500 10px var(--f);fill:var(--t3)">pièces vérifiées</text></svg>')


def barres_exercices(exercices):
    """Barres CA (violet) et EBITDA (vert) par exercice, hauteurs relatives au plus grand CA."""
    haut = max((e.chiffre_affaires for e in exercices), default=0)
    if not haut:
        return []
    return [{'annee': e.annee, 'ca': millions(e.chiffre_affaires), 'ebitda': millions(e.ebitda),
             'h_ca': round(e.chiffre_affaires / haut * 90), 'h_eb': round(max(e.ebitda or 0, 0) / haut * 90)} for e in exercices]


def kpis(exercices, confiance):
    if not exercices:
        return []
    d = exercices[-1]
    p = exercices[-2] if len(exercices) > 1 else None
    preuve = (CLASSES_PREUVE[d.niveau_preuve], LIBELLES_PREUVE[d.niveau_preuve])
    croissance = round((d.chiffre_affaires / p.chiffre_affaires - 1) * 100) if p and p.chiffre_affaires else None
    mb = d.marge_brute / d.chiffre_affaires * 100 if d.marge_brute and d.chiffre_affaires else None
    levier = f'{d.dette_nette / d.ebitda:.2f}'.replace('.', ',') + ' × EBITDA' if d.dette_nette is not None and d.ebitda else 'à renseigner'
    return [
        (f'Chiffre d’affaires {d.annee}', millions(d.chiffre_affaires), f'{croissance:+d} % sur un an' if croissance is not None else 'un seul exercice', preuve),
        (f'EBITDA {d.annee}', millions(d.ebitda), f'marge {pct(d.marge_ebitda)}' if d.marge_ebitda is not None else 'à renseigner', preuve),
        ('Marge brute', pct(mb), f'{millions(d.marge_brute)} FCFA' if d.marge_brute else 'à renseigner', preuve),
        ('Dette nette', millions(d.dette_nette), levier, preuve),
        ('DSCR', f'{d.dscr:.2f}'.replace('.', ',') if d.dscr else '—', 'seuil bancaire 1,2', preuve),
        ('Confiance des données', f'{confiance} %', 'pièces justifiées ou attestées', None),
    ]


def stress_tests(dernier):
    """Couverture de la dette (DSCR) sous trois chocs simples, à partir du dernier exercice."""
    if not dernier or not dernier.ebitda or not dernier.service_dette:
        return []
    eb, sd = dernier.ebitda, dernier.service_dette
    cas = [('EBITDA −10 %', eb * .9 / sd), ('EBITDA −20 %', eb * .8 / sd), ('Service de la dette +20 %', eb / (sd * 1.2)), ('Les deux à la fois', eb * .8 / (sd * 1.2))]
    return [(lab, f'{v:.2f}'.replace('.', ','), v < 1.2) for lab, v in cas]


def carte_pme(org, c, these=None):
    """Une ligne de la marketplace ou d’une liste : tout ce qu’affiche une carte de la maquette."""
    profil = getattr(org, 'profil_pme', None)
    s = pme.score_preparation(org)
    attestees = sum(1 for p in org.pieces.all() if p.niveau_preuve == 'certifie')
    return {'org': org, 'c': c, 'score': s, 'profil': profil, 'photo': photo(org), 'attestees': attestees,
            'ticket': profil.ticket_recherche if profil else None, 'zlecaf': bool(profil and profil.export_zlecaf)}


def _mediane(vals):
    vals = [v for v in vals if v is not None]
    return median(vals) if vals else None


def stats_secteur(secteur, orgs, these):
    """Indicateurs d’un secteur, calculés sur les PME inscrites. Le score d’attractivité est expliqué axe par axe."""
    from .services import compatibilite
    lignes = []
    for o in orgs:
        ex = sorted(o.exercices.all(), key=lambda e: e.annee)
        lignes.append({**carte_pme(o, compatibilite(these, o)), 'dernier': ex[-1] if ex else None, 'confiance': pme.confiance_donnees(o)})
    tickets = [l['ticket'] for l in lignes if l['ticket']]
    marges = [l['dernier'].marge_ebitda for l in lignes if l['dernier'] and l['dernier'].marge_ebitda is not None]
    return {'secteur': secteur, 'lignes': sorted(lignes, key=lambda l: -l['c']['total']), 'n': len(lignes), 'tickets': tickets,
            'total_tickets': sum(tickets), 'ticket_median': _mediane(tickets), 'marges': marges, 'marge_mediane': _mediane(marges),
            'score_median': _mediane([l['score'].total for l in lignes]), 'confiance_mediane': _mediane([l['confiance'] for l in lignes]),
            'avec_comptes': sum(1 for l in lignes if l['dernier']), 'attestees': sum(l['attestees'] for l in lignes),
            'indice_moyen': round(sum(l['c']['total'] for l in lignes) / len(lignes)) if lignes else 0,
            'au_dessus': sum(1 for l in lignes if l['c']['visible'])}


def attractivite(st, max_n, max_tickets):
    """Cinq axes notés sur 100, pondérés : demande 25, nombre de PME 20, rentabilité 20, préparation 20, confiance 15."""
    axes = [('Demande (montants recherchés)', round(st['total_tickets'] / max_tickets * 100) if max_tickets else 0, 25),
            ('Nombre de PME', round(st['n'] / max_n * 100) if max_n else 0, 20),
            ('Rentabilité (marge EBITDA)', min(100, round((st['marge_mediane'] or 0) / 25 * 100)), 20),
            ('Préparation des dossiers', round(st['score_median'] or 0), 20),
            ('Confiance des données', round(st['confiance_mediane'] or 0), 15)]
    total = round(sum(v * p for _, v, p in axes) / 100)
    return total, axes


def matrice_marges(marges, hauteur=6):
    """Matrice de points : une colonne par tranche de marge EBITDA, un point par PME."""
    tranches = [('< 5 %', None, 5), ('5–10', 5, 10), ('10–15', 10, 15), ('15–20', 15, 20), ('> 20 %', 20, None)]
    cols = []
    for lab, lo, hi in tranches:
        n = sum(1 for m in marges if (lo is None or m >= lo) and (hi is None or m < hi))
        cols.append({'lab': lab, 'n': n, 'pleins': range(min(n, hauteur)), 'vides': range(hauteur - min(n, hauteur))})
    return cols


def sucettes(tickets):
    haut = max(tickets, default=0)
    return [{'v': millions(t), 'h': round(t / haut * 90) if haut else 0} for t in sorted(tickets)]


def jauge(score, sous='sur 100'):
    from django.utils.safestring import mark_safe
    return mark_safe(_radial(score / 100, str(score), sous))


def classement_secteurs(these):
    """Tous les secteurs ayant au moins une PME, rangés par score d’attractivité. Renvoie (classement, stats, groupes)."""
    from apps.annuaire.models import Organisation
    base = (Organisation.objects.entreprises().filter(secteur__isnull=False)
            .select_related('secteur', 'profil_pme').prefetch_related('exercices', 'pieces'))
    groupes = {}
    for o in base:
        groupes.setdefault(o.secteur, []).append(o)
    if not groupes:
        return [], {}, {}
    max_n = max(len(v) for v in groupes.values())
    tous = {s: stats_secteur(s, orgs, these) for s, orgs in groupes.items()}
    max_t = max(st['total_tickets'] for st in tous.values())
    classement = sorted(((attractivite(st, max_n, max_t), s) for s, st in tous.items()), key=lambda x: (-x[0][0], x[1].nom))
    return classement, tous, groupes


def croissance(exercices):
    """Croissance annuelle moyenne du chiffre d’affaires, en %, sur les exercices disponibles (au moins deux)."""
    ex = sorted((e for e in exercices if e.chiffre_affaires), key=lambda e: e.annee)
    if len(ex) < 2:
        return None
    n = ex[-1].annee - ex[0].annee
    return round(((ex[-1].chiffre_affaires / ex[0].chiffre_affaires) ** (1 / n) - 1) * 100, 1) if n > 0 else None
