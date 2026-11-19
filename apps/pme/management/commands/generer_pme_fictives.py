"""Génère les 100 PME fictives du cahier des charges v3 (9.2) : 10 axes du BIH × 5 grades × 2 variantes.

« Plafond » coche les portes de son grade avec un score en haut de la bande ; « plancher » vient de franchir le seuil.
Bilans équilibrés, ratios recalculables, pièces marquées « FICTIF » (sans fichier : aucun faux document ne circule).
Noms inventés (syllabes sans signification), à vérifier contre le registre du commerce avant toute diffusion publique.
La PME héroïne du cas pratique (Savane Agro SA, agroalimentaire, Série A, 500 M FCFA, trois marchés africains) est
mise à jour au passage. Rejouable : les PME fictives existantes sont recréées."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.annuaire.models import Organisation, Secteur
from apps.pme.models import EntrepriseProfile, ExerciceFinancier, Piece
from apps.pme.services import score_preparation

AXES = [  # termes de référence du BIH, § 8.2
    ('Transformation numérique des entreprises', 'Digital', 'Solutions de gestion en ligne pour commerçants'),
    ('Intelligence artificielle et données', 'Data', 'Analyse de données et automatisation pour les entreprises'),
    ('FinTech et inclusion financière', 'Pay', 'Paiement mobile et microcrédit pour artisans'),
    ('Agritech et transformation agroalimentaire', 'Agro', 'Transformation de manioc, plantain et céréales locales'),
    ('Industrie 4.0 et production intelligente', 'Industries', 'Atelier de fabrication de pièces métalliques'),
    ('Mobilité, transport et logistique', 'Logistique', 'Transport de marchandises et entreposage'),
    ('Énergie, GreenTech et transition écologique', 'Énergie', 'Kits solaires et mini-réseaux villageois'),
    ('GovTech et administration numérique', 'Services publics', 'Logiciels pour collectivités territoriales'),
    ('Santé, éducation et inclusion sociale', 'Santé', 'Cliniques de proximité et télé-consultation'),
    ('Commerce, investissement et ZLECAf', 'Négoce', 'Négoce régional de produits transformés vers la CEMAC'),
]
RADICAUX = ['Zoléka', 'Vimbaro', 'Quatalé', 'Bréniko', 'Ylango', 'Folimba', 'Xénaro', 'Wakéla', 'Ruvesto', 'Jalimbo',
            'Okévia', 'Pranéla', 'Duvanko', 'Méliska', 'Tézora', 'Gaviro', 'Sunéla', 'Hokara', 'Lévimo', 'Cotéla']
REGIONS = [('Littoral', 'Douala'), ('Centre', 'Yaoundé'), ('Ouest', 'Bafoussam'), ('Sud', 'Kribi'), ('Nord-Ouest', 'Bamenda'),
           ('Adamaoua', 'Ngaoundéré'), ('Est', 'Bertoua'), ('Nord', 'Garoua'), ('Sud-Ouest', 'Buea'), ('Extrême-Nord', 'Maroua')]
GRADES = [(0, 39, 'Structuring'), (40, 59, 'Pré-Ready'), (60, 74, 'Investment-Ready'), (75, 89, 'Série A'), (90, 100, 'Institutional-Ready')]

# Étapes cumulatives : chacune ajoute des données réelles au dossier (et donc des points)
ETAPES = ['forme', 'effectif', 'ex1', 'p03', 'rccm', 'p04', 'p06', 'mb', 'ex2', 'p11', 'p03', 'sortie', 'p06', 'p09', 'p08', 'dscr',
          'ex3', 'p03', 'p11', 'p06', 'p04', 'p08', 'p03', 'p09', 'p06', 'preuve']


class Command(BaseCommand):
    help = 'Génère les 100 PME fictives (10 axes × 5 grades × 2) et met à jour la PME héroïne.'

    def handle(self, *args, **opts):
        with transaction.atomic():
            supprimees, _ = Organisation.objects.filter(est_demo=True, external_id__startswith='FICTIF-').delete()
            n = 0
            for i, (axe, court, activite) in enumerate(AXES):
                secteur, _ = Secteur.objects.get_or_create(nom=axe)
                for g, (bas, haut, lab) in enumerate(GRADES):
                    for v, variante in enumerate(('plafond', 'plancher')):
                        k = (g * 2 + v + i * 3) % len(RADICAUX)
                        region, ville = REGIONS[(i + g + v) % len(REGIONS)]
                        org = Organisation.objects.create(
                            kind='pme', nom=f'{RADICAUX[k]} {court}', secteur=secteur, ville=ville, region=region, est_demo=True,
                            description=f'{activite} (entreprise fictive, grade {lab}, variante {variante}).', a_verifier=False,
                            external_id=f'FICTIF-{i + 1:02d}-{g}-{v}', source_libelle='Jeu de démonstration AnkadeZ · FICTIF')
                        self.ajuster(org, bas, haut, variante, g, i)
                        n += 1
            self.heroine()
        self.stdout.write(self.style.SUCCESS(f'{n} PME fictives générées ({supprimees} objets anciens remplacés), héroïne mise à jour.'))

    # ------------------------------------------------------------------
    def ajuster(self, org, bas, haut, variante, g, i):
        """Cherche le nombre d’étapes qui place le score dans la bande : en haut pour « plafond », au seuil pour « plancher »."""
        meilleur = None
        for k in range(len(ETAPES) + 1):
            self.construire(org, k, g, i)
            s = score_preparation(org).total
            if bas <= s <= haut:
                meilleur = (k, s)
                if variante == 'plancher':
                    break
            elif s > haut:
                break
        if meilleur is None:
            meilleur = (k, s)
        self.construire(org, meilleur[0], g, i)

    def construire(self, org, k, g, i):
        org.pieces.all().delete()
        org.exercices.all().delete()
        EntrepriseProfile.objects.filter(organisation=org).delete()
        etapes = ETAPES[:k]
        ca = (90 + 140 * g + 13 * i) * 1_000_000
        p = EntrepriseProfile(organisation=org, ticket_recherche=(40 + 90 * g) * 1_000_000, part_investissement=70,
                              instrument_souhaite=['dette', 'mixte', 'equity', 'equity', 'mixte'][g], stade='croissance' if g >= 2 else 'amorcage',
                              dirigeante=(i + g) % 3 == 0, export_zlecaf=g >= 3, part_export=[0, 0, 5, 15, 30][g],
                              emplois_femmes=(4 + 6 * g) // 2, emplois_jeunes=3 + 4 * g, salaries_cnps=(6 + 12 * g) if g >= 1 else None,
                              energie_propre=i == 6, zone_rurale=i in (3, 6), zone_incitative='portuaire' if i == 5 else '')
        if 'forme' in etapes:
            p.forme_juridique = ['EI', 'SARL', 'SARL', 'SA', 'SA'][g]
        if 'effectif' in etapes:
            p.effectif = 6 + 12 * g
        if 'rccm' in etapes:
            p.rccm = f'RC/FICTIF/{2015 + g}/B/{100 + i}'
        if 'sortie' in etapes:
            p.strategie_sortie = ['Remboursement de la dette sur 5 ans.', 'Rachat par la direction.', 'Cession à un industriel du secteur.',
                                  'Entrée d’un fonds puis revente à 5–7 ans.', 'Préparation à une admission à la BVMAC, sans promesse.'][g]
        # Portes du grade visé et des grades inférieurs (6.2)
        if g >= 1:
            p.identite_verifiee = p.beneficiaires_identifies = True
            p.consentement_donnees = timezone.now()
        if g >= 2:
            p.clients_top3_pct = [0, 0, 38, 30, 24][g]
            p.usage_fonds = [['Équipement de production', p.ticket_recherche * 7 // 10, '+30 % de capacité'],
                             ['Besoin en fonds de roulement', p.ticket_recherche * 3 // 10, 'stocks pour l’export']]
            p.contact_banque_autorise = True
            p.revenus_recurrents_pct = 20 + 10 * g
            p.tresorerie = ca // 12
            p.sorties_mensuelles = ca // 40
            p.concurrents = 'Trois concurrents nommés dans le plan d’affaires (fictif).'
            p.reporting_mensuel = True
        p.save()
        niveau_ex = ['declaratif', 'declaratif', 'coherent', 'recoupe', 'certifie'][g] if 'preuve' in etapes or g >= 2 else 'declaratif'
        nb_ex = 3 if 'ex3' in etapes else 2 if 'ex2' in etapes else 1 if 'ex1' in etapes else 0
        for j in range(nb_ex):
            annee = 2025 - (nb_ex - 1 - j)
            c = int(ca / (1.18 ** (nb_ex - 1 - j)))
            self.exercice(org, annee, c, g, 'mb' in etapes, 'dscr' in etapes, niveau_ex if (j == nb_ex - 1 or g == 4) else 'coherent' if g >= 2 else 'declaratif')
        compte = {}
        niveau_p = ['declaratif', 'declaratif', 'coherent', 'recoupe', 'certifie'][g]
        for e in etapes:
            if e.startswith('p') and e[1:].isdigit():
                d = e[1:]
                compte[d] = compte.get(d, 0) + 1
                Piece.objects.create(organisation=org, dossier=d, titre=f'{dict(Piece.Dossier.choices)[d].split(" · ")[1]} n°{compte[d]} (FICTIF)',
                                     niveau_preuve=niveau_p if g >= 2 else 'declaratif')
        # Pièces qui ouvrent les portes des grades élevés
        if g >= 3:
            for d, t in [('02', 'Prévisions à 5 ans et test de sensibilité'), ('02', 'Rapprochement CA et relevés bancaires'), ('12', 'Cession de PI dans les contrats')]:
                Piece.objects.create(organisation=org, dossier=d, titre=f'{t} (FICTIF)', niveau_preuve=niveau_p)
        if g >= 4:
            for d, t in [('03', 'Revue juridique indépendante'), ('09', 'Politique ESG et plan de continuité'), ('08', 'Rapport de due diligence tiers')]:
                Piece.objects.create(organisation=org, dossier=d, titre=f'{t} (FICTIF)', niveau_preuve='certifie')

    def exercice(self, org, annee, ca, g, avec_mb, avec_dscr, niveau):
        """Compte de résultat et bilan cohérents : actif = passif, ratios recalculables."""
        ebitda = int(ca * (0.06 + 0.025 * g))
        rn = int(ebitda * 0.45)
        dettes_fin = int(ca * 0.25)
        service = int(ebitda / (1.4 if avec_dscr else 0.95))
        creances, stocks, tres = int(ca * 0.16), int(ca * 0.10), int(ca * 0.05)
        fournisseurs = int(ca * 0.09)
        actif_circ = creances + stocks + tres
        dettes_ct = fournisseurs + int(ca * 0.04)
        cp = int(ca * (0.22 + 0.04 * g))
        total = cp + dettes_fin + dettes_ct           # passif
        ExerciceFinancier.objects.create(
            organisation=org, annee=annee, chiffre_affaires=ca, marge_brute=int(ca * 0.33) if avec_mb else None, ebitda=ebitda,
            resultat_net=rn, dette_nette=dettes_fin - tres, service_dette=service, niveau_preuve=niveau,
            capitaux_propres=cp, total_bilan=total, actif_circulant=actif_circ, dettes_court_terme=dettes_ct, dettes_financieres=dettes_fin,
            caf=int(ebitda * 0.8), charges_personnel=int(ca * 0.14), valeur_ajoutee=int(ca * 0.30), creances_clients=creances,
            dettes_fournisseurs=fournisseurs, achats=int(ca * 0.55), stocks=stocks, flux_exploitation=int(ebitda * 0.85))

    def heroine(self):
        """Cas pratique de la fiche Défi 3 : agroalimentaire, Série A, 500 M FCFA, capacité et trois marchés africains."""
        org = Organisation.objects.filter(nom='Savane Agro SA').first()
        if not org:
            return
        secteur, _ = Secteur.objects.get_or_create(nom='Agritech et transformation agroalimentaire')
        org.secteur = secteur
        org.est_demo = True
        org.source_libelle = 'Jeu de démonstration AnkadeZ · FICTIF (PME héroïne du cas pratique)'
        org.description = 'Farines de manioc et de plantain ; augmente sa capacité et vise le Gabon, le Congo et le Tchad (FICTIF).'
        org.save()
        p, _ = EntrepriseProfile.objects.get_or_create(organisation=org)
        p.ticket_recherche = 500_000_000
        p.identite_verifiee = p.beneficiaires_identifies = p.contact_banque_autorise = p.reporting_mensuel = True
        p.consentement_donnees = p.consentement_donnees or timezone.now()
        p.clients_top3_pct, p.revenus_recurrents_pct, p.part_export, p.export_zlecaf = 46, 35, 18, True
        p.regles_origine = 'Farines produites au Cameroun à partir de manioc local : origine CEMAC'
        p.usage_fonds = [['Ligne de production', 350_000_000, '+60 % de capacité'], ['BFR export', 150_000_000, 'trois marchés africains']]
        p.concurrents = 'Trois transformateurs régionaux nommés dans le plan d’affaires (fictif).'
        p.tresorerie, p.sorties_mensuelles = 90_000_000, 25_000_000
        p.dirigeante = True
        p.emplois_femmes, p.emplois_jeunes, p.salaries_cnps = 41, 30, 80
        p.ouvertures = ['partenariat']
        p.save()
        p.strategie_sortie = p.strategie_sortie or 'Entrée d’un fonds agro puis revente à un industriel régional à 5–7 ans (FICTIF).'
        p.save(update_fields=['strategie_sortie'])
        for d, t in [('02', 'Prévisions à 5 ans et test de sensibilité'), ('12', 'Cession de PI dans les contrats de travail'),
                     ('04', 'Attestation de non-redevance'), ('09', 'Politique environnementale et sociale'), ('03', 'Registre des associés à jour'),
                     ('08', 'Matrice des risques et plan de réponse')]:
            Piece.objects.get_or_create(organisation=org, dossier=d, titre=f'{t} (FICTIF)', defaults={'niveau_preuve': 'recoupe'})
        for e in org.exercices.all():
            if e.capitaux_propres is None:
                ca = e.chiffre_affaires
                e.capitaux_propres, e.dettes_financieres = int(ca * 0.34), int(ca * 0.12)
                e.dettes_court_terme, e.actif_circulant = int(ca * 0.13), int(ca * 0.31)
                e.total_bilan = e.capitaux_propres + e.dettes_financieres + e.dettes_court_terme
                e.caf, e.creances_clients, e.stocks = int((e.ebitda or 0) * 0.8), int(ca * 0.16), int(ca * 0.10)
                e.dettes_fournisseurs, e.achats, e.flux_exploitation = int(ca * 0.09), int(ca * 0.55), int((e.ebitda or 0) * 0.85)
                e.charges_personnel, e.valeur_ajoutee = int(ca * 0.14), int(ca * 0.30)
                e.save()
        s = score_preparation(org)
        self.stdout.write(f'Héroïne : {s.affichage}' + (f' · porte : {s.porte_bloquante} ({", ".join(s.portes_manquantes)})' if s.porte_bloquante else ''))
