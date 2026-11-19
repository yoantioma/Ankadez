"""Charge les données du cahier des charges v3 (rejouable sans doublon).

Acteurs réels (9.3) : uniquement des informations publiques ; ce que la source ne donne pas reste « non publié ».
Produits (7.1), programmes (7.4) et incitations (9.1) : source et date sur chaque ligne ; « à confirmer » quand la
source est un guide commercial ou un commentaire de cabinet. Statut de contact « non contacté » par défaut."""
import re
from datetime import date

from django.core.management.base import BaseCommand

from apps.annuaire.models import Organisation
from apps.offres.models import Incitation, ProduitFinancier, Programme, QuestionDiagnostic

VERIF = date(2026, 11, 18)
CDC3 = 'Cahier des charges AnkadeZ v3.0 (sources publiques citées)'
CIF = 'Programme officiel CIF 2026'

ACTEURS = [
    # nom, kind, type_acteur, source, url
    ('Afreximbank', 'investisseur', 'multilateral', CIF, 'https://www.afreximbank.com'),
    ('Société financière internationale (SFI/IFC)', 'investisseur', 'multilateral', CIF, 'https://www.ifc.org'),
    ('Banque africaine de développement (BAD)', 'investisseur', 'multilateral', CIF, 'https://www.afdb.org'),
    ('Fonds d’équipement des Nations unies (UNCDF)', 'investisseur', 'ptf', CIF, 'https://www.uncdf.org'),
    ('Fonds international de développement agricole (FIDA)', 'investisseur', 'ptf', CIF, 'https://www.ifad.org'),
    ('Afriland First Bank', 'investisseur', 'banque', 'IFC, communiqué du 2 avril 2025', ''),
    ('CCA Bank', 'investisseur', 'banque', 'EcoMatin, 6 mars 2026', ''),
    ('Ecobank Cameroun', 'investisseur', 'banque', 'Fab Afriq, lancement d’Ellevate au Cameroun', 'https://www.ecobank.com'),
    ('Union Bank of Cameroon', 'investisseur', 'banque', CIF, ''),
    ('FAGACE', 'investisseur', 'garantie', 'Cahier des charges AnkadeZ v2.0', ''),
    ('CDEC', 'investisseur', 'garantie', 'Cahier des charges AnkadeZ v2.0', ''),
    ('BVMAC', 'institution', 'marche', 'Cahier des charges AnkadeZ v2.0', ''),
    ('Agence de Promotion des Investissements (API)', 'institution', 'public', CIF, ''),
    ('Agence de promotion des PME (APME)', 'institution', 'public', CIF, ''),
    ('MINPMEESA', 'institution', 'public', CIF, ''),
    ('MINFI', 'institution', 'public', CIF, ''),
    ('MINEPAT', 'institution', 'public', CIF, ''),
]

PRODUITS = [
    dict(institution_nom='Afriland First Bank', nom='Ligne SFI pour les PME (incitations WEOF pour les entreprises de femmes)', type='ligne',
         public='PME clientes de la banque ; incitations liées aux prêts aux entreprises dirigées ou détenues par des femmes',
         montant='Prêt SFI à la banque jusqu’à 60 millions USD ; montant à la PME fixé par la banque',
         source_libelle='IFC, communiqué du 2 avril 2025', verifie_le=VERIF, pieces_exigees=['02', '04', '03'], grade_min=40, ordre=1,
         a_confirmer='Le communiqué ne fixe pas de part minimale pour les femmes : montant, taux et garanties sont ceux de la banque.'),
    dict(institution_nom='CCA Bank', nom='Women Banking (CCA First Lady Club, CCA Business Series)', type='programme', femme=True,
         public='Femmes entrepreneures', montant='non publié',
         source_libelle='EcoMatin, 6 mars 2026', verifie_le=VERIF, pieces_exigees=['03', '01'], grade_min=0, ordre=2,
         a_confirmer='L’offre « Gisèle » citée par l’équipe n’apparaît pas dans les sources publiques : à faire confirmer par la banque.'),
    dict(institution_nom='Ecobank Cameroun', nom='Ellevate : taux préférentiels, trésorerie, formation, mentorat', type='programme', femme=True,
         public='Entreprises de femmes (au moins 10 % du portefeuille de prêts de la banque commerciale)',
         source_libelle='Fab Afriq, lancement d’Ellevate à Douala le 30 mars 2021', verifie_le=VERIF, pieces_exigees=['02', '03'], grade_min=20, ordre=3,
         a_confirmer='Taux et conditions chiffrés non publiés : à demander à la banque.'),
    dict(institution_nom='FAGACE', nom='Garantie de prêts aux entreprises', type='garantie', public='PME ayant un prêt bancaire en cours d’instruction',
         source_libelle='Cahier des charges AnkadeZ v2.0', verifie_le=None, pieces_exigees=['02', '04', '06'], grade_min=60, ordre=10,
         a_confirmer='Conditions à vérifier auprès du FAGACE avant affichage.'),
]

PROGRAMMES = [
    ('Ecobank Cameroun', 'Ellevate', 'Entreprises de femmes', 'Taux préférentiels, gestion de trésorerie, formation à la direction, mentorat, mise en réseau.',
     ['femmes', 'financement'], 'Fab Afriq, lancement d’Ellevate au Cameroun'),
    ('CCA Bank', 'Women Banking et CCA Business Series', 'Femmes entrepreneures',
     'Financement via le CCA First Lady Club, comptes dédiés, bancassurance ; séances mensuelles pour structurer dossiers de crédit et plans d’affaires.',
     ['femmes', 'montage'], 'EcoMatin, 6 mars 2026'),
    ('SFI et Afriland First Bank', 'Ligne SFI et assistance technique', 'PME, incitations pour les entreprises de femmes',
     'Ligne de crédit et assistance technique de la SFI via Afriland First Bank.', ['femmes', 'financement'], 'IFC, communiqué du 2 avril 2025'),
    ('FAO', 'Boîte à outils Rural Invest', 'Projets agricoles et agro-industriels', 'Méthode et outils pour préparer un projet d’investissement rural.',
     ['agro', 'montage'], CIF),
    ('CIF 2026', 'Masterclass agro-transformation (19 novembre)', 'Entreprises agro', 'Session du Cameroon Investment Forum.', ['agro'], CIF),
    ('BAD', 'Masterclass croissance et financement (20 novembre)', 'PME en croissance', 'Masterclass de la Banque africaine de développement.',
     ['financement'], CIF),
    ('Marché de l’Investissement (MI 2026)', 'Deal rooms (19 novembre, 13 h 30 à 17 h 30)', 'Projets bancables et prêts à investir',
     'Rencontres avec Afreximbank, la SFI, la BAD, le système des Nations unies et les banques camerounaises.', ['financement'], CIF),
    ('OIT', 'Masterclass travail décent (18 novembre)', 'Toutes entreprises', 'Conformité sociale et travail décent.', ['social'], CIF),
    ('Solutionneurs', 'Formation au montage de projets (méthode P.R.O.J.E.T.)', 'Porteurs de projet et PME', 'Méthode Problème, Recherche, Offre, Justification, Exécution, Transformation.',
     ['montage'], 'Brief P.R.O.J.E.T. (Solutionneurs)'),
]

DELOITTE = 'Deloitte Avocats, « Cameroun : les principales innovations de la loi de finances pour 2026 »'
LEFISK = 'LeFisk, guide des zones franches (guide commercial)'
INCITATIONS = [
    dict(famille='Zones économiquement sinistrées', concerne='Entreprise qui investit dans une zone classée ; banque qui la finance',
         description='Exonération de TVA limitée aux importations d’équipements et aux prestations de services ; exonération de TVA sur les intérêts des prêts '
                     'finançant l’investissement dans la zone ; phase d’installation prorogée de 3 à 5 ans sous conditions (LF 2026).',
         fiabilite='Commentaire de cabinet : à valider', source_libelle=DELOITTE, zones=['sinistree']),
    dict(famille='Zone économique spéciale de Kribi', concerne='Industrie, logistique, transformation, export et transit CEMAC',
         description='0 % d’impôt sur les sociétés pendant 5 ans puis 15 % pendant 5 ans ; zone en développement.',
         fiabilite='Guide commercial, chiffres non cohérents : à valider', source_libelle=LEFISK, regions=['Sud'], zones=['portuaire'],
         secteurs=['logist', 'port', 'industri', 'transform', 'export']),
    dict(famille='ZES HiTech de Yaoundé (Melen)', concerne='Entreprises du numérique',
         description='0 % d’impôt sur les sociétés pendant 10 ans après mise en service ; numérique, logiciels, cybersécurité, fintech.',
         fiabilite='Guide commercial : à valider', source_libelle=LEFISK, regions=['Centre'],
         secteurs=['numér', 'logiciel', 'cyber', 'fintech', 'web', 'data', 'digital']),
    dict(famille='Zones franches industrielles', concerne='Industries exportatrices (100 % export)',
         description='Zones de Douala, Yaoundé et Bafoussam ; régime pour les entreprises tournées à 100 % vers l’export ; agrément de la structure gestionnaire.',
         fiabilite='Guide commercial : à valider', source_libelle=LEFISK, export=True),
    dict(famille='Zones agricoles spéciales', concerne='Agro-transformation',
         description='En création (Adamaoua, Est, Littoral) dans le cadre du Plan national cacao 2025 ; exonération de 5 ans prévue pour la transformation agroalimentaire.',
         fiabilite='À valider', source_libelle=LEFISK, regions=['Adamaoua', 'Est', 'Littoral'], secteurs=['agro', 'agri', 'cacao', 'aliment']),
    dict(famille='Start-ups', concerne='Jeunes entreprises à contenu technologique',
         description='Exonérations de droits d’importation sur les équipements des start-ups en développement (LF 2026).',
         fiabilite='Commentaire de cabinet : à valider', source_libelle=DELOITTE, secteurs=['startup', 'numér', 'tech', 'logiciel', 'web']),
    dict(famille='Emploi des jeunes', concerne='Toute entreprise qui recrute',
         description='Crédit d’impôt de 20 % des charges de formation, d’encadrement et d’insertion de jeunes diplômés (LF 2026).',
         fiabilite='Commentaire de cabinet : à valider', source_libelle=DELOITTE, jeunes=True),
    dict(famille='Eau potable, énergies renouvelables, équipements médicaux', concerne='Projets concernés',
         description='Exonérations douanières ou prorogations (LF 2026).', fiabilite='Commentaire de cabinet : à valider', source_libelle=DELOITTE,
         secteurs=['eau', 'énergie', 'energie', 'solaire', 'santé', 'medical', 'médical']),
    dict(famille='Côté investisseur : titres de dette CEMAC', concerne='Investisseur en titres publics, pas en PME',
         description='Exonération de l’impôt sur le revenu des capitaux mobiliers sur les titres de dette des États de la CEMAC (LF 2026).',
         fiabilite='Commentaire de cabinet : à valider', source_libelle=DELOITTE, cote_investisseur=True),
]

QUESTIONS = [
    (1, 'Mon entreprise est immatriculée et à jour (RCCM, NIU, déclaration statistique et fiscale déposée) ?', 15,
     'RCCM, NIU et déclaration statistique et fiscale', 'Pas à pas de régularisation et guichet unique', 'formalisation', '03'),
    (2, 'J’ai les états financiers des deux derniers exercices, au format SYSCOHADA ?', 15,
     'États financiers SYSCOHADA des deux derniers exercices', 'Gabarit standard et cabinet comptable recommandé', 'comptabilite', '02'),
    (3, 'J’ai un plan d’affaires à jour avec un usage des fonds chiffré ?', 15,
     'Plan d’affaires avec usage des fonds chiffré', 'Modèle guidé et mentor', 'montage', '01'),
    (4, 'Je sais dire combien je cherche, sous quelle forme (dette, capital, mixte) et pourquoi ?', 15,
     'Besoin chiffré et forme du financement', 'Arbre de décision : dette, capital ou mixte', 'structuration', '01'),
    (5, 'Je produis un reporting mensuel fiable (ventes, trésorerie, créances) ?', 10,
     'Reporting mensuel (ventes, trésorerie, créances)', 'Tableau de suivi prêt à remplir', 'comptabilite', '02'),
    (6, 'Mes statuts, PV et registre des associés sont à jour ?', 10,
     'Statuts, PV et registre des associés', 'Liste des pièces de gouvernance', 'juridique', '03'),
    (7, 'Mes impôts et cotisations sociales (dont CNPS) sont à jour ?', 10,
     'Attestation de non-redevance et attestation CNPS', 'Mise à niveau fiscale', 'fiscalite', '04'),
    (8, 'J’ai rangé mes documents dans un dossier numérique que je peux partager ?', 10,
     'Dossier numérique partageable', 'Création automatique de la salle de données', 'mentor', ''),
]

# Spécialités déduites de la catégorie et de la description publiques (aucune n’est inventée)
SPECIALITES = [('comptabilite', r'comptab|expert-compt|\bcga\b|audit'), ('fiscalite', r'fisc'), ('juridique', r'jurid|avocat|droit|ohada'),
               ('pi', r'propriété intellectuelle|oapi|brevet|marque'), ('normes', r'norme|anor|certif|qualité'),
               ('mentor', r'incubat|accélér|mentor|coach'), ('structuration', r'financ|levée|invest|capital'),
               ('montage', r'formation|montage|accompagn|conseil'), ('formalisation', r'création d|formalis|guichet|apme|minpmeesa')]


class Command(BaseCommand):
    help = 'Charge les acteurs, produits, programmes, incitations et questions du cahier des charges v3.'

    def handle(self, *args, **opts):
        n = 0
        for nom, kind, typ, src, url in ACTEURS:
            cle = nom.split(' (')[0]
            o = Organisation.objects.filter(nom__iexact=nom).first() or Organisation.objects.filter(nom__icontains=cle).first()
            if not o:
                o = Organisation(nom=nom, kind=kind, pays='Cameroun', a_verifier=True)
                n += 1
            o.type_acteur = o.type_acteur or typ
            o.source_libelle = o.source_libelle or src
            if url and not o.source_url:
                o.source_url = url
            o.verifie_le = o.verifie_le or VERIF
            o.save()
        self.stdout.write(f'Acteurs réels : {n} ajoutés, {len(ACTEURS) - n} complétés.')

        for d in PRODUITS:
            inst = Organisation.objects.filter(nom__iexact=d['institution_nom']).first()
            ProduitFinancier.objects.update_or_create(institution_nom=d['institution_nom'], nom=d['nom'], defaults={**d, 'institution': inst})
        for porteur, nom, public, contenu, niches, src in PROGRAMMES:
            Programme.objects.update_or_create(porteur=porteur, nom=nom, defaults=dict(public=public, contenu=contenu, niches=niches,
                                                                                      source_libelle=src, verifie_le=VERIF))
        for d in INCITATIONS:
            Incitation.objects.update_or_create(famille=d['famille'], defaults={**d, 'verifie_le': VERIF,
                                                                                'a_confirmer': 'Éligibilité probable, à confirmer auprès de l’administration.'})
        for ordre, texte, poids, piece, action, spec, dossier in QUESTIONS:
            QuestionDiagnostic.objects.update_or_create(ordre=ordre, defaults=dict(texte=texte, poids=poids, piece=piece, action=action,
                                                                                    specialite=spec, dossier=dossier))
        m = 0
        for o in Organisation.objects.accompagnement():
            texte = f'{o.categorie} {o.description} {o.nom}'.lower()
            specs = [s for s, motif in SPECIALITES if re.search(motif, texte)]
            if not specs:
                specs = {'incubateur': ['mentor'], 'consultant': ['montage'], 'association': ['montage']}.get(o.kind, [])
            if specs and specs != o.specialites:
                o.specialites = specs
                o.save(update_fields=['specialites'])
                m += 1
        self.stdout.write(self.style.SUCCESS(f'{ProduitFinancier.objects.count()} produits, {Programme.objects.count()} programmes, '
                                             f'{Incitation.objects.count()} incitations, {QuestionDiagnostic.objects.count()} questions, '
                                             f'{m} accompagnateurs classés par spécialité.'))
