"""Pages publiques du cahier des charges v3 : académie (10.1), programmes par niche (7.4), conseil consultatif (10.2),
observatoire anonymisé k ≥ 5 (v2 maintenu) et cartographie des parties prenantes du CIF (3)."""
from statistics import median

from django.contrib import messages
from django.shortcuts import redirect, render

from apps.annuaire.models import Organisation
from apps.offres import services as offres
from apps.offres.models import Programme

PARCOURS_ACADEMIE = [
    ('Lire ses comptes', 'Bilan, compte de résultat et ratios, avec les chiffres de votre propre entreprise.', 'Ratios du tableau de bord'),
    ('Préparer sa salle de données', 'Les 12 familles de contrôle, avec des exemples de bonnes pièces.', 'Portes de preuve'),
    ('Dette ou capital ?', 'Arbre de décision et simulateur de dilution.', 'Simulateurs de Financer'),
    ('Comprendre un term sheet', 'Les clauses clés en mots simples ; exercice de repérage.', 'Radar de clauses'),
    ('Pitcher en 7 minutes', 'Méthode P.R.O.J.E.T. et test « choisissable ? ».', 'Brief P.R.O.J.E.T. (avec l’accord de son autrice)'),
    ('Accompagnement et réseau', 'Qui consulter, quand, combien ça coûte.', 'Accompagnateurs recommandés'),
]

# Un seul quiz interactif pour la démo du hackathon (le reste est la phase suivante)
QUIZ = [
    ('Votre chiffre d’affaires est de 200 M et votre EBE de 30 M. Quelle est votre marge d’EBE ?', ['6 %', '15 %', '30 %'], 1),
    ('Un DSCR de 0,9 signifie que…', ['l’entreprise couvre largement ses échéances', 'l’EBE ne couvre pas les échéances de l’année', 'la dette est remboursée'], 1),
    ('Céder 20 % du capital pour 200 M signifie une valorisation après apport de…', ['800 M', '1 Md', '200 M'], 1),
    ('Une faiblesse déclarée avant le contrôle de l’investisseur…', ['pénalise toujours l’indice', 'ne pénalise pas l’indice', 'fait perdre le grade'], 1),
    ('L’indice de compatibilité AnkadeZ est…', ['une probabilité d’être financé', 'une adéquation à la thèse, critère par critère', 'une note de crédit'], 1),
]


def academie(request):
    resultat = None
    if request.method == 'POST':
        bonnes = sum(1 for i, (_, _, juste) in enumerate(QUIZ) if request.POST.get(f'q{i}') == str(juste))
        resultat = round(bonnes / len(QUIZ) * 100)
        u = request.user
        if resultat >= 70 and u.is_authenticated and u.role == 'pme' and u.organisation:
            from apps.pme.models import EntrepriseProfile
            p, _ = EntrepriseProfile.objects.get_or_create(organisation=u.organisation)
            p.badge_eduque = True
            p.save(update_fields=['badge_eduque'])
            messages.success(request, 'Badge « Éduqué financièrement » ajouté à votre passeport.')
    return render(request, 'core/academie.html', {'parcours': PARCOURS_ACADEMIE, 'quiz': QUIZ, 'resultat': resultat})


def programmes(request):
    niche = request.GET.get('niche', '')
    return render(request, 'core/programmes.html', {'programmes': offres.programmes(niche or None), 'niches': Programme.NICHES, 'niche': niche})


SIEGES = [('Agence de Promotion des Investissements', 'Dossiers d’investissement, porte d’entrée des projets d’envergure'),
          ('Ministère des PME (MINPMEESA) ou APME', 'Tutelle PME, programmes d’appui'),
          ('Ministère des Finances ou des Investissements publics', 'Incitations, garanties, cadre fiscal'),
          ('Banque commerciale (via l’association des banques)', 'Ce qu’un crédit exige vraiment'),
          ('Financeur multilatéral ou PTF', 'Indicateurs d’impact et lignes dédiées'), ('BVMAC', 'Route vers le marché financier'),
          ('Ordre des experts-comptables ou réseau de CGA', 'Standardisation des états'), ('Avocat OHADA', 'Conformité des contenus juridiques'),
          ('Chambre de commerce ou organisation patronale', 'Voix des entreprises'), ('Entrepreneure en activité', 'Voix de l’utilisatrice'),
          ('Représentant de la diaspora', 'Capitaux et réseaux de l’extérieur'), ('Universitaire', 'Méthodologie du score')]


def conseil(request):
    return render(request, 'core/conseil.html', {'sieges': SIEGES})


K_MIN = 5


def observatoire(request):
    """Statistiques agrégées par secteur et par région, publiées seulement pour les groupes d’au moins 5 entreprises (k ≥ 5)."""
    from apps.pme.services import score_preparation
    groupes = {}
    for o in Organisation.objects.entreprises().select_related('secteur', 'profil_pme').prefetch_related('exercices', 'pieces', 'signalements'):
        s = score_preparation(o)
        for cle in (('Secteur', o.secteur.nom if o.secteur else 'Non précisé'), ('Région', o.region or 'Non précisée')):
            groupes.setdefault(cle, []).append((s.total, s.confiance, getattr(o, 'profil_pme', None)))
    lignes, masques = [], 0
    for (axe, nom), v in sorted(groupes.items()):
        if len(v) < K_MIN:
            masques += 1
            continue
        tickets = [p.ticket_recherche for _, _, p in v if p and p.ticket_recherche]
        lignes.append({'axe': axe, 'nom': nom, 'n': len(v), 'score': round(median(x[0] for x in v)), 'confiance': round(median(x[1] for x in v)),
                       'ticket': median(tickets) if tickets else None})
    return render(request, 'core/observatoire.html', {'lignes': lignes, 'masques': masques, 'k': K_MIN})


PARTIES = [
    ('Organisateur et porteur', 'Agence de Promotion des Investissements (API), Présidence de la République ; BG Finance, mandataire d’assistance technique du hackathon',
     'Détient le guichet d’investissement du pays ; premier utilisateur institutionnel du passeport.', 'Outil de flux de dossiers pour l’API (échelon API du passeport).'),
    ('Tutelles', 'MINEPAT, MINFI, MINPMEESA, ministères du Commerce, des Mines et de l’Agriculture',
     'Fixent les incitations, les labels PME et les priorités sectorielles.', 'Alimentent le détecteur d’incitations et les filtres sectoriels.'),
    ('Financeurs multilatéraux', 'Afreximbank, SFI/IFC, Banque africaine de développement, UNCDF, FIDA',
     'Lignes de crédit, garanties, réduction des risques, financements agricoles.', 'Fiches produits en première page ; vue d’impact des PTF.'),
    ('Banques', 'Banques partenaires du MI 2026 ; APPECAM ; Union Bank of Cameroon', 'Première source de dette ; matérialisent la bancabilité.',
     'Vitrine des produits bancaires, avec critères d’éligibilité publics.'),
    ('Privé organisé', 'CCIMA, GECAM, SYNDUSTRICAM, Chambre d’agriculture, interprofessions', 'Relèvent et présélectionnent les entreprises.',
     'Canal d’inscription des PME et de recommandation d’accompagnateurs.'),
    ('Accompagnement technique', 'FAO (Rural Invest), OIT, PNUD, UNESCO, ANOR, ANTIC, IRAD, CENEEMA, FEICOM',
     'Outils, normes et programmes dont une PME a besoin avant de lever.', 'Catalogue d’accompagnateurs et Académie.'),
    ('Intégration régionale', 'Secrétariat de la ZLECAf, Système des Nations unies au Cameroun, WAIPA', 'Ouvrent les marchés et relient les agences d’investissement.',
     'Champ « règles d’origine / ZLECAf » dans le profil PME.'),
]
