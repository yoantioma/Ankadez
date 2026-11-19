"""Crée les données de démonstration du prototype (6 PME avec comptes, 1 investisseur avec thèse).

  python manage.py seed_demo
  python manage.py seed_demo --comptes --mot-de-passe "UnMotDePasseSolide"   # crée aussi les comptes de test

Toutes les données créées ici sont fictives et marquées « démonstration ».
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.annuaire.models import Organisation, Secteur
from apps.investissement.models import DemandeAcces, These
from apps.pme.models import EntrepriseProfile, ExerciceFinancier, Piece

M = 1_000_000
PME = [
    # nom, secteur, activité, ville, région, forme, effectif, ticket M, stade, instrument, CA M, marge brute M, EBITDA M, service dette M, zlecaf, sortie
    ('Savane Agro SA', 'Agro-industrie', 'Farines de manioc et de plantain', 'Douala', 'Littoral', 'SA', 86, 500, 'croissance', 'equity', 1240, 422, 186, 139, True, ''),
    ('Kribi Logistique SARL', 'Logistique portuaire', 'Manutention et entreposage au port de Kribi', 'Kribi', 'Sud', 'SARL', 54, 320, 'croissance', 'mixte', 860, 258, 120, 95, True, ''),
    ('Bafoussam Lait SA', 'Agro-industrie', 'Lait frais et yaourts des hauts plateaux', 'Bafoussam', 'Ouest', 'SA', 41, 180, 'croissance', 'dette', 540, 173, 65, 54, False, ''),
    ('Sanaga Solaire SAS', 'Énergie', 'Mini-réseaux solaires pour villages', 'Édéa', 'Littoral', 'SAS', 23, 650, 'amorcage', 'equity', 410, 185, 70, None, False, ''),
    ('Lékié Cacao Coop', 'Agro-industrie', 'Cacao fermenté et tracé pour l’export', 'Obala', 'Centre', 'COOP', 120, 240, 'croissance', 'quasi', 720, 158, 79, 67, True, ''),
    ('Akwa Couture SARL', 'Textile', 'Confection en pagne pour la distribution', 'Douala', 'Littoral', 'SARL', 18, 90, 'amorcage', 'dette', 190, 72, 21, None, False, ''),
]
PIECES_SAVANE = [('01', 'Pitch 2026', 'recoupe'), ('02', 'États financiers 2025', 'recoupe'), ('02', 'États financiers 2024', 'certifie'),
                 ('03', 'Statuts', 'certifie'), ('03', 'RCCM', 'certifie'), ('04', 'Attestation fiscale', 'recoupe'), ('11', 'Organigramme', 'coherent'), ('07', 'Table de capitalisation', 'coherent'),
                 ('06', 'Contrat distributeur Gabon (projet)', 'declaratif'), ('06', 'Contrat fournisseur manioc', 'coherent'), ('08', 'PESTEL', 'coherent')]


class Command(BaseCommand):
    help = 'Crée les données de démonstration de AnkadeZ.'

    def add_arguments(self, parser):
        parser.add_argument('--comptes', action='store_true', help='Créer aussi les comptes de test pme@demo.cm et investisseur@demo.cm')
        parser.add_argument('--mot-de-passe', default='', help='Mot de passe des comptes de test (obligatoire avec --comptes)')

    @transaction.atomic
    def handle(self, *args, **o):
        orgs = {}
        for (nom, sect, act, ville, region, forme, eff, ticket, stade, instr, ca, mb, ebitda, sd, zl, sortie) in PME:
            secteur, _ = Secteur.objects.get_or_create(nom=sect)
            org, _ = Organisation.objects.update_or_create(nom=nom, est_demo=True, defaults={
                'kind': 'pme', 'secteur': secteur, 'description': act, 'ville': ville, 'region': region, 'completude': 80, 'a_verifier': False})
            EntrepriseProfile.objects.update_or_create(organisation=org, defaults={
                'forme_juridique': forme, 'effectif': eff, 'ticket_recherche': ticket * M, 'stade': stade, 'instrument_souhaite': instr,
                'export_zlecaf': zl, 'strategie_sortie': sortie, 'part_investissement': 70, 'rccm': 'CM-DEMO' if forme in ('SA', 'SARL', 'SAS') else ''})
            ExerciceFinancier.objects.update_or_create(organisation=org, annee=2025, defaults={
                'chiffre_affaires': ca * M, 'marge_brute': mb * M, 'ebitda': ebitda * M, 'service_dette': sd * M if sd else None,
                'dette_nette': 140 * M if nom.startswith('Savane') else None, 'niveau_preuve': 'recoupe' if nom.startswith('Savane') else 'declaratif'})
            orgs[nom] = org
        sav = orgs['Savane Agro SA']
        for annee, ca, mb, eb in [(2023, 760, 228, 92), (2024, 980, 314, 140)]:
            ExerciceFinancier.objects.update_or_create(organisation=sav, annee=annee, defaults={
                'chiffre_affaires': ca * M, 'marge_brute': mb * M, 'ebitda': eb * M, 'niveau_preuve': 'certifie'})
        if not sav.pieces.exists():
            Piece.objects.bulk_create([Piece(organisation=sav, dossier=d, titre=t, niveau_preuve=n) for d, t, n in PIECES_SAVANE])

        fonds, _ = Organisation.objects.update_or_create(nom='Fonds Baobab Croissance', est_demo=True, defaults={
            'kind': 'investisseur', 'ville': 'Douala', 'region': 'Littoral', 'description': 'Fonds de croissance, démonstration.', 'a_verifier': False})
        these, _ = These.objects.update_or_create(organisation=fonds, defaults={
            'ticket_min': 200 * M, 'ticket_max': 600 * M, 'zones': ['CEMAC'], 'stades': ['croissance'], 'instruments': ['equity', 'quasi'],
            'exigence_esg': True, 'horizon_annees': 6})
        these.secteurs.set(Secteur.objects.filter(nom__in=['Agro-industrie', 'Logistique portuaire']))
        DemandeAcces.objects.get_or_create(investisseur=fonds, entreprise=sav, defaults={'statut': 'reunion', 'indice': 92})

        if o['comptes']:
            mdp = o['mot_de_passe']
            if len(mdp) < 8:
                self.stderr.write('Indiquez --mot-de-passe (8 caractères au moins) pour créer les comptes de test.')
            else:
                for email, role, org, prenom in [('pme@demo.cm', 'pme', sav, 'Awa'), ('investisseur@demo.cm', 'investisseur', fonds, 'Analyste')]:
                    u, cree = User.objects.get_or_create(email=email, defaults={'role': role, 'organisation': org, 'first_name': prenom})
                    u.set_password(mdp)
                    u.save()
                self.stdout.write('Comptes de test : pme@demo.cm et investisseur@demo.cm')
        self.stdout.write(self.style.SUCCESS('Données de démonstration prêtes : 6 PME, 1 investisseur.'))
