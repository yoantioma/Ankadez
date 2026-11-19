"""Règles du cahier des charges v3, écrites en clair pour être montrées à la PME et à l’investisseur.

5.1 les 4 P · 5.2 ratios · 5.3 indicateurs de préparation · 6.1 stade · 6.2 portes de preuve, points rouges,
12 familles de contrôle et divulgation spontanée · 6.3 vieillissement du passeport."""
from datetime import timedelta

from django.utils import timezone

# ------------------------------------------------------------------ 6.1 Stade d’investissement (second axe)
STADES = {'angel': 'Angel / Pré-seed', 'seed': 'Seed', 'serie_a': 'Série A', 'serie_b': 'Série B+', 'developpement': 'Développement et reprise'}


def _exercices(org):
    return sorted(org.exercices.all(), key=lambda e: e.annee)


def croissance(ex):
    ex = [e for e in ex if e.chiffre_affaires]
    if len(ex) < 2 or ex[-1].annee <= ex[0].annee:
        return None
    return ((ex[-1].chiffre_affaires / ex[0].chiffre_affaires) ** (1 / (ex[-1].annee - ex[0].annee)) - 1) * 100


def stade(org):
    """Où en est l’entreprise, d’après sa traction et son historique (indépendant du grade de préparation)."""
    ex = _exercices(org)
    profil = getattr(org, 'profil_pme', None)
    pieces = {p.dossier for p in org.pieces.all()}
    g = croissance(ex)
    rentable = bool(ex) and ((ex[-1].resultat_net or 0) > 0 or (ex[-1].ebitda or 0) > 0)
    export = bool(profil and ((profil.part_export or 0) >= 10 or profil.export_zlecaf))
    if len(ex) >= 3 and rentable and export and {'03', '07'} <= pieces:
        return 'serie_b'
    if len(ex) >= 2 and g is not None and g >= 15:
        return 'serie_a'
    if len(ex) >= 3 and rentable:
        return 'developpement'
    if ex and ex[-1].chiffre_affaires:
        return 'seed'
    return 'angel'


# ------------------------------------------------------------------ 5.2 Ratios du compte de résultat et du bilan
def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def ratios(org):
    """Ratios calculés sur le dernier exercice (et le précédent pour la croissance). Valeur None quand une ligne manque."""
    ex = _exercices(org)
    if not ex:
        return []
    d = ex[-1]
    p = ex[-2] if len(ex) > 1 else None
    bfr = (d.creances_clients or 0) + (d.stocks or 0) - (d.dettes_fournisseurs or 0) if d.creances_clients is not None else None
    service = d.service_dette
    lignes = [
        ('Activité', 'Croissance du chiffre d’affaires', 'CA N ÷ CA N-1 − 1', _div(d.chiffre_affaires, p.chiffre_affaires if p else None), '%', 'L’entreprise grandit-elle, et de façon régulière ?'),
        ('Rentabilité', 'Marge d’EBE', 'EBE ÷ CA', _div(d.ebitda, d.chiffre_affaires), '%', 'Ce que l’activité rapporte avant amortissements et frais financiers'),
        ('Rentabilité', 'Marge nette', 'Résultat net ÷ CA', _div(d.resultat_net, d.chiffre_affaires), '%', 'Ce qui reste après tout'),
        ('Rentabilité', 'Poids du personnel', 'Charges de personnel ÷ valeur ajoutée', _div(d.charges_personnel, d.valeur_ajoutee), '%', 'La masse salariale est-elle tenable ?'),
        ('Structure', 'Autonomie financière', 'Capitaux propres ÷ total du bilan', _div(d.capitaux_propres, d.total_bilan), '%', 'Repère courant : environ un tiers'),
        ('Structure', 'Endettement', 'Dettes financières ÷ capitaux propres', _div(d.dettes_financieres, d.capitaux_propres), 'x', 'Place restante pour de la dette'),
        ('Remboursement', 'Capacité de remboursement', 'Dettes financières ÷ CAF', _div(d.dettes_financieres, d.caf), 'ans', 'En combien d’années elle rembourserait'),
        ('Remboursement', 'Couverture du service de la dette', 'CAF ÷ échéances de l’année', _div(d.caf if d.caf is not None else d.ebitda, service), 'x', 'Peut-elle payer les échéances ? Repère bancaire : 1,2'),
        ('Liquidité', 'Liquidité générale', 'Actif circulant ÷ dettes à court terme', _div(d.actif_circulant, d.dettes_court_terme), 'x', 'Peut-elle tenir 12 mois ?'),
        ('Cycle', 'Besoin en fonds de roulement', 'BFR ÷ CA × 360', _div(bfr * 360 if bfr is not None else None, d.chiffre_affaires), 'jours', 'Jours de chiffre d’affaires immobilisés'),
        ('Cycle', 'Délai clients', 'Créances clients ÷ CA TTC × 360', _div((d.creances_clients or 0) * 360 if d.creances_clients is not None else None, d.chiffre_affaires * 1.1925), 'jours', 'Est-elle payée vite ?'),
        ('Cycle', 'Délai fournisseurs', 'Dettes fournisseurs ÷ achats TTC × 360', _div((d.dettes_fournisseurs or 0) * 360 if d.dettes_fournisseurs is not None else None, (d.achats or 0) * 1.1925 or None), 'jours', 'Paie-t-elle vite ?'),
        ('Qualité', 'Qualité du résultat', 'Flux de trésorerie d’exploitation ÷ EBE', _div(d.flux_exploitation, d.ebitda), 'x', 'Le bénéfice se transforme-t-il en argent ?'),
    ]
    sortie = []
    for fam, lab, formule, v, unite, sens in lignes:
        if v is not None and unite == '%':
            txt = f'{v * 100:.1f} %'.replace('.', ',')
        elif v is not None:
            txt = f'{v:.1f} {unite}'.replace('.', ',') if unite != 'x' else f'{v:.2f}'.replace('.', ',')
        else:
            txt = '—'
        sortie.append({'famille': fam, 'libelle': lab, 'formule': formule, 'valeur': v, 'texte': txt, 'sens': sens,
                       'annee': d.annee, 'preuve': d.get_niveau_preuve_display()})
    return sortie


# ------------------------------------------------------------------ 5.3 Indicateurs de préparation à l’investissement
def indicateurs_preparation(org):
    profil = getattr(org, 'profil_pme', None)
    ex = _exercices(org)
    d = ex[-1] if ex else None
    g = croissance(ex)
    marge = d.marge_ebitda if d else None
    sorties = (profil.sorties_mensuelles if profil else None)
    tres = (profil.tresorerie if profil else None)
    if d and d.flux_exploitation is not None and d.flux_exploitation > 0:
        autonomie = 'flux positif'
    elif sorties and tres:
        autonomie = f'{tres / sorties:.0f} mois'
    else:
        autonomie = 'à renseigner'
    top3 = profil.clients_top3_pct if profil else None
    return [
        ('Marché et concurrence', 'renseigné' if profil and profil.concurrents.strip() else 'à renseigner', '3 concurrents nommés, avantage défendable'),
        ('Concentration clients', f'{top3} %' if top3 is not None else 'à renseigner', 'Alerte au-delà de 40 % (seuil à calibrer)' if top3 is None or top3 <= 40 else 'Alerte : plus de 40 % du CA sur 3 clients'),
        ('Revenus récurrents', f'{profil.revenus_recurrents_pct} %' if profil and profil.revenus_recurrents_pct is not None else 'à renseigner', 'Rassure la dette comme le capital'),
        ('Croissance du CA', f'{g:.1f} %'.replace('.', ',') if g is not None else 'à renseigner', 'Se lit avec la marge, pas seule'),
        ('Autonomie de trésorerie', autonomie, 'Trésorerie ÷ sorties nettes mensuelles'),
        ('Règle des 40', f'{g + marge:.0f}'.replace('.', ',') if g is not None and marge is not None else '—', 'Affichée pour information, jamais utilisée comme filtre'),
        ('Usage des fonds', f'{len(profil.usage_fonds)} postes' if profil and profil.usage_fonds else 'à renseigner', 'Pièce obligatoire pour toute demande'),
        ('Stratégie de sortie', 'écrite' if profil and profil.sortie_ecrite else 'à écrire', 'Alimente l’horizon du matching'),
        ('Ouverture à court terme', ', '.join(profil.ouvertures) if profil and profil.ouvertures else 'aucune', 'Déclenche le parcours reprise'),
    ]


# ------------------------------------------------------------------ 6.2 Les 12 familles de contrôle (non fourni, fourni, vérifié)
FAMILLES = [
    ('Identité, bénéficiaires effectifs, lutte contre le blanchiment', ['03'], 'identite'),
    ('Capital et table de capitalisation', ['07'], None),
    ('Statuts, registres, procès-verbaux, pactes', ['03'], None),
    ('États financiers, dettes, subventions', ['02'], None),
    ('Conformité fiscale et sociale (non-redevance, DSF, CNPS)', ['04'], None),
    ('Clients : dix premiers, carnet de commandes', ['06'], None),
    ('Fournisseurs, dépendances, baux, assurances', ['06', '12'], None),
    ('Équipe : organigramme, dépendances, intéressement', ['11'], None),
    ('Propriété intellectuelle (OAPI, cession des droits)', ['12'], None),
    ('Licences, normes (ANOR, sanitaire), autorisations', ['05'], None),
    ('ESG, impact, cybersécurité, données personnelles', ['09'], None),
    ('Risques : matrice, réponses, hypothèses testées', ['08'], None),
]


def familles(org):
    profil = getattr(org, 'profil_pme', None)
    par = {}
    for p in org.pieces.all():
        par.setdefault(p.dossier, []).append(p.niveau_preuve)
    sortie = []
    for lab, dossiers, extra in FAMILLES:
        niveaux = [n for d in dossiers for n in par.get(d, [])]
        if extra == 'identite' and profil and profil.identite_verifiee and profil.beneficiaires_identifies:
            niveaux.append('recoupe')
        etat = 'verifie' if any(n in ('recoupe', 'certifie') for n in niveaux) else 'fourni' if niveaux else 'non_fourni'
        sortie.append((lab, etat, dossiers))
    return sortie


# ------------------------------------------------------------------ 6.2 Points rouges et portes par grade
def points_rouges(org):
    profil = getattr(org, 'profil_pme', None)
    pieces = {p.dossier for p in org.pieces.all()}
    sig = list(org.signalements.all())
    rouges = []
    if not org.exercices.exists():
        rouges.append('Aucun état financier')
    if '04' not in pieces:
        rouges.append('Pas d’attestation de non-redevance')
    if not (profil and profil.rccm):
        rouges.append('RCCM manquant')
    if not (profil and profil.beneficiaires_identifies):
        rouges.append('Bénéficiaire effectif non identifié')
    if any(s.type in ('dette', 'garantie') and not s.divulgation_spontanee for s in sig):
        rouges.append('Dette ou garantie non déclarée découverte au contrôle')
    if any(s.type == 'litige' and s.majeur and not s.divulgation_spontanee for s in sig):
        rouges.append('Litige majeur non déclaré')
    return rouges


def portes(org):
    """Portes ajoutées par la v3 à chaque grade. Une porte non franchie bloque le grade, même si le score l’atteint."""
    profil = getattr(org, 'profil_pme', None)
    ex = _exercices(org)
    par = {}
    for p in org.pieces.all():
        par.setdefault(p.dossier, []).append(p.niveau_preuve)
    verifie = lambda n: n in ('recoupe', 'certifie')
    sig = list(org.signalements.all())
    rouges = points_rouges(org)
    return [
        (40, 'Pré-Ready', [
            ('Identité des dirigeants et des bénéficiaires effectifs vérifiée', bool(profil and profil.identite_verifiee and profil.beneficiaires_identifies)),
            ('Consentement au traitement des données personnelles', bool(profil and profil.consentement_donnees)),
        ]),
        (60, 'Investment-Ready', [
            ('Aucun point rouge', not rouges),
            ('Liste des dettes, garanties et sûretés données', bool(ex and ex[-1].dette_nette is not None)),
            ('Trois premiers clients et fournisseurs', bool(profil and profil.clients_top3_pct is not None)),
            ('Tableau d’usage des fonds', bool(profil and profil.usage_fonds)),
            ('Accord pour contacter la banque principale et le comptable', bool(profil and profil.contact_banque_autorise)),
        ]),
        (75, 'Série A / Growth-Ready', [
            ('Prévisions et test de sensibilité (dossier 02, au moins deux pièces)', len(par.get('02', [])) >= 2),
            ('Chiffre d’affaires rapproché des relevés bancaires', bool(ex and verifie(ex[-1].niveau_preuve))),
            ('Cession de la propriété intellectuelle (dossier 12)', bool(par.get('12'))),
            ('Litiges et contrôles en cours déclarés', not any(s.type == 'litige' and not s.divulgation_spontanee for s in sig)),
        ]),
        (90, 'Institutional-Ready', [
            ('Audit externe de deux exercices', sum(1 for e in ex if e.niveau_preuve == 'certifie') >= 2),
            ('Revue juridique indépendante (dossier 03 certifié)', any(n == 'certifie' for n in par.get('03', []))),
            ('Politique ESG et plan de continuité (dossier 09)', bool(par.get('09'))),
            ('Contrôle de l’assurance et rapport tiers (dossier 08 vérifié)', any(verifie(n) for n in par.get('08', []))),
        ]),
    ]


def plafond_portes(org):
    """Score maximum permis par les portes : une porte manquante plafonne juste sous le seuil du grade qu’elle garde."""
    for seuil, lab, liste in portes(org):
        if not all(ok for _, ok in liste):
            return seuil - 1, lab, [l for l, ok in liste if not ok]
    return 100, None, []


def penalite_divulgation(org):
    """Faiblesse déclarée avant contrôle : aucune pénalité. Découverte par un investisseur : 5 points chacune."""
    return 5 * sum(1 for s in org.signalements.all() if not s.divulgation_spontanee)


# ------------------------------------------------------------------ 6.3 Vieillissement : 6 mois pour les chiffres, 12 mois pour le reste
def coefficient_fraicheur(org):
    maintenant = timezone.now()
    ex = list(org.exercices.all())
    pieces = list(org.pieces.all())
    total = len(ex) + len(pieces)
    if not total:
        return 1.0, []
    vieux_ex = sum(1 for e in ex if e.created_at < maintenant - timedelta(days=183))
    vieux_p = sum(1 for p in pieces if p.created_at < maintenant - timedelta(days=365))
    alertes = []
    if vieux_ex:
        alertes.append(f'{vieux_ex} exercice(s) de plus de 6 mois : à actualiser')
    if vieux_p:
        alertes.append(f'{vieux_p} pièce(s) de plus de 12 mois : à actualiser')
    return 1 - 0.5 * (vieux_ex + vieux_p) / total, alertes


# ------------------------------------------------------------------ 5.1 Les 4 P transposés à la PME
def quatre_p(org):
    """Chaque bloc : une jauge de 0 à 100, une phrase de lecture et les pièces qui prouvent. Le score global reste l’indice du passeport."""
    profil = getattr(org, 'profil_pme', None)
    ex = _exercices(org)
    d = ex[-1] if ex else None
    par = {}
    for pc in org.pieces.all():
        par.setdefault(pc.dossier, []).append(pc.niveau_preuve)
    a = lambda attr: bool(profil and getattr(profil, attr))
    g = croissance(ex)
    blocs = [
        ('People', 'Les personnes', 'Puis-je faire confiance à ceux qui dirigent, et que se passe-t-il s’ils partent ?', [
            ('Identité des dirigeants vérifiée (KYC)', 25, a('identite_verifiee')), ('Bénéficiaires effectifs identifiés', 25, a('beneficiaires_identifies')),
            ('Équipe clé documentée (dossier 11)', 20, bool(par.get('11'))), ('Table des associés (dossier 07)', 20, bool(par.get('07'))),
            ('Effectif déclaré', 10, a('effectif'))], 'CV, registre des associés, pièces d’identité, contrats de travail'),
        ('Performance', 'Les chiffres', 'Les chiffres sont-ils vrais, et que disent-ils ?', [
            ('Trois exercices déclarés', 30, len(ex) >= 3), ('Croissance positive', 15, g is not None and g > 0),
            ('Marge d’EBE supérieure à 10 %', 15, bool(d and (d.marge_ebitda or 0) > 10)), ('Couverture de la dette ≥ 1,2', 15, bool(d and (d.dscr or 0) >= 1.2)),
            ('Bénéfice transformé en trésorerie (≥ 70 %)', 10, bool(d and d.flux_exploitation and d.ebitda and d.flux_exploitation / d.ebitda >= 0.7)),
            ('Chiffres recoupés ou certifiés', 15, bool(d and d.niveau_preuve in ('recoupe', 'certifie')))], 'États financiers, DSF, relevés bancaires, balance âgée clients'),
        ('Philosophy', 'La logique et l’alignement', 'La stratégie tient-elle, et mes intérêts sont-ils alignés avec ceux du dirigeant ?', [
            ('Usage des fonds chiffré', 25, a('usage_fonds')), ('Stratégie de sortie écrite', 20, bool(profil and profil.sortie_ecrite)),
            ('Part investie par le dirigeant (≥ 10 %)', 15, bool(profil and (profil.part_dirigeant or 0) >= 10)),
            ('Politique ESG (dossier 09)', 20, bool(par.get('09'))), ('Contrat ou lettre d’intention (dossier 06)', 20, bool(par.get('06')))],
         'Plan d’affaires, tableau d’usage des fonds, politique ESG, lettre d’intention'),
        ('Process', 'La mécanique', 'L’entreprise est-elle tenue de façon répétable, pas seulement par son fondateur ?', [
            ('Gouvernance (statuts, PV : dossier 03)', 20, bool(par.get('03'))), ('Reporting mensuel fiable', 20, a('reporting_mensuel')),
            ('Conformité fiscale (dossier 04)', 20, bool(par.get('04'))), ('Salariés déclarés à la CNPS', 20, a('salaries_cnps')),
            ('Assurance, cybersécurité, risques (dossiers 08 ou 09)', 20, bool(par.get('08') or par.get('09')))], 'Statuts, PV, procédures, attestations fiscales et CNPS, assurances'),
    ]
    sortie = []
    for cle, titre, question, criteres, preuves in blocs:
        score = sum(p for _, p, ok in criteres if ok)
        lecture = ('Solide : un financeur y trouve ses preuves.' if score >= 75 else 'En bonne voie : quelques preuves manquent.' if score >= 50
                   else 'Fragile : c’est ici que le financeur posera ses questions.')
        sortie.append({'cle': cle, 'titre': titre, 'question': question, 'score': score, 'lecture': lecture, 'criteres': criteres, 'preuves': preuves})
    return sortie
