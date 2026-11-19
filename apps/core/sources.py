"""Registre des sources (cahier des charges v3 · 9.4) : chaque chiffre affiché porte une icône « i » qui dit ce que c’est,
d’où ça vient, la date, le niveau de preuve, le calcul, et qui contacter pour signaler une erreur."""
CONTACT = 'Pour signaler une erreur : l’équipe AnkadeZ (adresse de contact à publier).'

SOURCES = {
    'score': ('Score de préparation sur 100', 'Calculé par AnkadeZ à partir du profil, des exercices et des pièces de la data room', 'à chaque ouverture',
              'calculé', 'Six dimensions pondérées ; plafond à 59 sans pièce justifiée ; portes de preuve et points rouges du cahier des charges v3'),
    'confiance': ('Indice de confiance', 'Niveaux de preuve des pièces et des exercices', 'à chaque ouverture', 'calculé',
                  '(attestées × 1 + justifiées × 0,7) ÷ nombre de données, réduit quand les chiffres ont plus de 6 mois ou les pièces plus de 12 mois'),
    'stade': ('Stade d’investissement', 'Historique des exercices, croissance, rentabilité, export', 'à chaque ouverture', 'calculé',
              'Angel sans ventes ; Seed avec un exercice ; Série A avec 2 exercices et 15 % de croissance ; Série B+ rentable, exportatrice, gouvernance ; Développement établi'),
    'indice': ('Indice de compatibilité', 'Thèse de l’investisseur et dossier de l’entreprise', 'à chaque ouverture', 'calculé',
               'Secteur 25, ticket 20, zone 15, stade 15, instrument 15, ESG 10 ; filtres éliminatoires ; jamais une probabilité'),
    'montant': ('Montant légitime', 'Exercice le plus récent et besoin déclaré', 'à chaque ouverture', 'calculé',
                'Besoin déclaré, capacité d’endettement (4 ans d’EBITDA à 1,2 moins la dette nette), capacité en capital (30 % de 5 × EBITDA)'),
    'pieces': ('Pièces versées', 'Data room de l’entreprise', 'temps réel', 'déclaré (D) à justifié (J) ou attesté (A) selon chaque pièce', 'Nombre de pièces sur 45 exigées'),
    'ratio': ('Ratio financier', 'Liasse SYSCOHADA saisie par l’entreprise ou son cabinet', 'date de l’exercice', 'selon le niveau de preuve de l’exercice', 'Formule affichée dans le tableau'),
    'quatre_p': ('Jauge des 4 P', 'Profil, pièces et exercices', 'à chaque ouverture', 'calculé', 'Somme des critères remplis, sur 100 (détail sous la jauge)'),
    'attractivite': ('Score d’attractivité du secteur', 'PME inscrites du secteur', 'à chaque ouverture', 'calculé',
                     'Demande 25 %, nombre de PME 20 %, rentabilité 20 %, préparation 20 %, confiance 15 % (pondération AnkadeZ)'),
    'impact': ('Indicateur d’impact', 'Déclaré par les entreprises', 'date de mise à jour du profil', 'déclaré (D) sauf pièce attestée', 'Somme ou moyenne sur la portée choisie'),
    'diagnostic': ('Score du diagnostic de 45 secondes', 'Réponses de l’entreprise', 'au moment du diagnostic', 'déclaré (D)',
                   'Somme des poids des réponses « oui » (poids paramétrés dans l’administration, à calibrer avec les mentors)'),
    'fictif': ('Donnée fictive', 'Jeu de démonstration AnkadeZ', 'génération du jeu', 'fictif', 'Entreprise inventée pour la démonstration'),
}


def info(cle, niveau=None, origine=None):
    lab, src, date, niv, calcul = SOURCES.get(cle, (cle, 'non documenté', '—', '—', '—'))
    return {'libelle': lab, 'origine': origine or src, 'date': date, 'niveau': niveau or niv, 'calcul': calcul, 'contact': CONTACT}
