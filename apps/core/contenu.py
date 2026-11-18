"""Contenus éditoriaux de la landing (indicateurs pays sourcés, acteurs, incitations, chaînes, outils).
Les chiffres pays sont à vérifier avant toute décision ; ils sont datés et sourcés."""

INDICATEURS_PAYS = [
    {'titre': 'Croissance du PIB', 'valeur': '3,3 %', 'detail': 'prévue en 2026', 'serie': [('2022', 3.6), ('2023', 3.2), ('2024', 3.5), ('2025', 3.1), ('2026', 3.3)],
     'sens': 'Régulière autour de 3 % : la demande des PME suit.', 'source': 'FMI, mars 2026 · 2022–2023 à vérifier'},
    {'titre': 'Inflation', 'valeur': '2,9 %', 'detail': 'prévue en 2026', 'serie': [('2022', 6.3), ('2023', 7.4), ('2024', 4.5), ('2025', 3.4), ('2026', 2.9)],
     'sens': 'Repasse sous le plafond CEMAC de 3 % : marges mieux protégées.', 'source': 'FMI, mars 2026 · 2022–2024 à vérifier', 'plafond': 3},
    {'titre': 'Taux directeur BEAC', 'valeur': '4,50 %', 'detail': 'septembre 2026', 'sens': 'Le plancher de rendement d’un financement en FCFA.', 'source': 'BEAC, sept. 2026'},
    {'titre': 'Notation souveraine', 'valeur': 'B-', 'detail': 'S&P · Caa1 chez Moody’s', 'sens': 'Catégorie spéculative : exiger une prime et des garanties.', 'source': 'S&P, Moody’s'},
    {'titre': 'Monnaie', 'valeur': '655,957', 'detail': 'FCFA pour 1 €', 'sens': 'Parité fixe depuis 1999 : pas de risque de change face à l’euro.', 'source': 'Zone franc, BEAC'},
    {'titre': 'Investissements étrangers', 'valeur': '599 M$', 'detail': 'en 2025', 'sens': '−36 % : peu de concurrence des grands fonds.', 'source': 'CNUCED 2026, selon la presse'},
]

ATOUTS = [('carte', 'Première économie de la CEMAC', '6 pays, une seule monnaie'), ('reseau', 'Une population jeune', '≈ 29 M d’habitants'),
          ('import', 'Deux ports majeurs', 'Douala et Kribi, porte du Tchad et de la RCA'), ('balance', 'Droit des affaires OHADA', 'les mêmes règles dans 17 pays'),
          ('bouclier', 'FCFA arrimé à l’euro', 'parité fixe depuis 1999'), ('decouvrir', 'Ouvert sur la ZLECAf', 'le marché continental africain')]

ACTEURS = [
    ('MINPMEESA', 'tutelle', 'Ministère des PME, de l’économie sociale et de l’artisanat', 'Tutelle des PME : peut lire un dossier.'),
    ('MINEPAT', 'tutelle', 'Ministère de l’économie, de la planification et de l’aménagement du territoire', 'Planification et programmes de développement.'),
    ('MINFI', 'tutelle', 'Ministère des finances', 'Fiscalité et finances publiques.'),
    ('API', 'agence', 'Agence de promotion des investissements', 'Instruit les agréments de la loi sur les incitations.'),
    ('APME', 'agence', 'Agence de promotion des PME', 'Accompagne la création et le développement des PME.'),
    ('OHADA', 'regulateur', 'Droit des affaires harmonisé', 'Droit des sociétés et comptabilité, actes uniformes.'),
    ('COBAC', 'regulateur', 'Commission bancaire de l’Afrique centrale', 'Supervision bancaire, pour les prêteurs.'),
    ('COSUMAF', 'regulateur', 'Surveillance du marché financier de l’Afrique centrale', 'Seulement en cas d’appel public à l’épargne.'),
    ('DONNÉES', 'regulateur', 'Autorité de protection des données personnelles', 'Loi n° 2024/017 du 23 décembre 2024.'),
    ('ANTIC', 'regulateur', 'Agence nationale des TIC', 'Reçoit les incidents de sécurité informatique.'),
]

CHAINES = [('Manioc et plantain', [('Producteurs', 'intrants, récoltes'), ('Transformation', 'farines'), ('Marchés', 'local et CEMAC')]),
           ('Lait', [('Éleveurs', 'hauts plateaux'), ('Transformation', 'lait frais et yaourts'), ('Marchés', 'distribution urbaine')]),
           ('Cacao', [('Coopérateurs', 'fermentation'), ('Traçage', 'qualité et origine'), ('Marchés', 'export')])]

OUTILS = [('jauge', 'Préparation', 'Score sur 100', 'Savoir où l’on en est, dimension par dimension, et quoi faire ensuite.'),
          ('dossier', 'Gestion', 'Data room et preuves', 'Chaque pièce classée, chaque chiffre relié à sa preuve.'),
          ('financer', 'Financement', 'Montant juste', 'Un montant défendable, calculé de trois façons.'),
          ('boussole', 'Stratégie', 'Compétitivité et risques', 'Situer l’entreprise face à son marché et à ses risques.'),
          ('check', 'Croissance', 'Plan de mise à niveau', 'Les actions qui rapportent le plus de points, dans l’ordre.'),
          ('cible', 'Mise en relation', 'Investisseurs compatibles', 'Une compatibilité expliquée critère par critère, jamais une probabilité.')]
