"""Critères de réussite du cahier des charges v3 (10.5), vérifiés automatiquement.

python manage.py test apps.core"""
import pathlib
import re

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.annuaire.models import Organisation, Secteur
from apps.investissement.models import DemandeAcces, These
from apps.investissement.services import compatibilite, nom_public
from apps.offres import services as offres
from apps.pme.models import EntrepriseProfile, ExerciceFinancier, Partage, Piece, Signalement
from apps.pme.services import score_preparation

BASE = pathlib.Path(settings.BASE_DIR)


@override_settings(ALLOWED_HOSTS=['*'])
class CriteresV3(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('charger_v3', verbosity=0)
        cls.secteur = Secteur.objects.create(nom='Agritech et transformation agroalimentaire')
        cls.pme = Organisation.objects.create(kind='pme', nom='Test Agro FICTIF', secteur=cls.secteur, region='Littoral', ville='Douala',
                                              description='Transformation de manioc', est_demo=True)
        EntrepriseProfile.objects.create(organisation=cls.pme, forme_juridique='SA', rccm='RC/TEST', effectif=20, ticket_recherche=300_000_000,
                                         instrument_souhaite='equity', identite_verifiee=True, beneficiaires_identifies=True,
                                         consentement_donnees=timezone.now(), dirigeante=True)
        for a in (2023, 2024, 2025):
            ExerciceFinancier.objects.create(organisation=cls.pme, annee=a, chiffre_affaires=500_000_000 + (a - 2023) * 100_000_000,
                                             marge_brute=150_000_000, ebitda=70_000_000, service_dette=40_000_000, niveau_preuve='recoupe', dette_nette=50_000_000)
        for d in ('03', '04', '06', '09', '11'):
            Piece.objects.create(organisation=cls.pme, dossier=d, titre=f'Pièce {d} (FICTIF)', niveau_preuve='coherent')
        cls.inv = Organisation.objects.create(kind='investisseur', nom='Fonds Test', est_demo=True)
        cls.these = These.objects.create(organisation=cls.inv, ticket_min=100_000_000, ticket_max=400_000_000, zones=['CEMAC'], stades=['serie_a'],
                                         instruments=['equity'], type_acteur='fonds')
        cls.u_pme = User.objects.create_user(email='pme@test.cm', password='x' * 12, role='pme', organisation=cls.pme)
        cls.u_inv = User.objects.create_user(email='inv@test.cm', password='x' * 12, role='investisseur', organisation=cls.inv)

    # 10.5 · Chaque chiffre marqué a une source
    def test_chaque_chiffre_marque_porte_sa_source(self):
        pages = [(self.u_pme, '/pme/'), (self.u_pme, '/pme/passeport/'), (self.u_pme, '/pme/finances/'),
                 (self.u_inv, f'/investisseur/entreprise/{self.pme.slug}/'), (self.u_inv, '/investisseur/marketplace/'), (self.u_inv, '/investisseur/entreprises/')]
        for u, url in pages:
            self.client.force_login(u)
            html = self.client.get(url).content.decode()
            for bloc in re.findall(r'<span class="chiffre" data-chiffre="[^"]+">.*?</span>', html, re.S):
                self.assertIn('class="src-i"', bloc, f'{url} : chiffre sans source')
            self.assertIn('data-chiffre', html, f'{url} : aucun chiffre marqué')

    # 4.1 · Diagnostic : 8 questions, score déclaré, 3 pièces manquantes classées par poids
    def test_diagnostic_45_secondes(self):
        self.assertEqual(len(offres.questions()), 8)
        r = offres.diagnostic({1: True, 2: False, 3: True, 4: False, 5: True, 6: False, 7: True, 8: True})
        self.assertEqual(r['score'], 60)
        self.assertEqual(len(r['manquantes']), 3)
        self.assertGreaterEqual(r['manquantes'][0].poids, r['manquantes'][-1].poids)

    # 6.2 · Une porte non franchie bloque le grade
    def test_porte_de_preuve_bloque_le_grade(self):
        avant = score_preparation(self.pme).total
        p = self.pme.profil_pme
        p.identite_verifiee = False
        p.save()
        self.assertLessEqual(score_preparation(self.pme).total, 39)
        p.identite_verifiee = True
        p.save()
        self.assertEqual(score_preparation(self.pme).total, avant)

    # 6.2 · Divulgation spontanée : pas de pénalité ; découverte : pénalité
    def test_divulgation_spontanee(self):
        avant = score_preparation(self.pme).total
        Signalement.objects.create(organisation=self.pme, auteur=self.pme, type='garantie', description='Caution', divulgation_spontanee=True)
        self.assertEqual(score_preparation(self.pme).total, avant)
        Signalement.objects.create(organisation=self.pme, auteur=self.inv, type='dette', description='Prêt caché', divulgation_spontanee=False)
        s = score_preparation(self.pme)
        self.assertEqual(s.penalite, 5)
        self.assertLessEqual(s.total, avant)
        self.assertIn('Dette ou garantie non déclarée découverte au contrôle', s.points_rouges)

    # Filtres éliminatoires et trois colonnes
    def test_filtres_eliminatoires(self):
        self.assertEqual(compatibilite(self.these, self.pme)['exclus'], [])
        self.these.non_negociables = ['comptes_certifies']
        self.these.save()
        c = compatibilite(self.these, self.pme)
        self.assertIn('Comptes non certifiés', c['exclus'])
        self.assertEqual(c['colonne'], 'exclu')

    # Profil anonymisé avant consentement, nom révélé après l’accord de confidentialité
    def test_anonymisation(self):
        self.assertNotIn('Test Agro', nom_public(self.pme, self.inv))
        DemandeAcces.objects.create(investisseur=self.inv, entreprise=self.pme, statut='nda')
        self.assertEqual(nom_public(self.pme, self.inv), 'Test Agro FICTIF')

    # 6.3 · Le passeport ne part jamais sans le clic de l’entreprise
    def test_passeport_exige_le_consentement(self):
        self.client.force_login(self.u_pme)
        self.client.post('/pme/passeport/', {'destinataire_type': 'api', 'perimetre': ['profil', 'grade']})
        self.assertEqual(Partage.objects.count(), 0)
        self.client.post('/pme/passeport/', {'destinataire_type': 'api', 'perimetre': ['profil', 'grade'], 'consentement': '1'})
        self.assertEqual(Partage.objects.count(), 1)
        r = self.client.get('/pme/passeport/passeport-ankadez.json')
        self.assertIn('signature_sha256', r.content.decode())

    # Vue investisseur filtrée par secteur, montant, région et stade (fiche Défi 3)
    def test_filtres_vue_investisseur(self):
        self.client.force_login(self.u_inv)
        for q in ('secteur=' + self.secteur.slug, 'tmin=100&tmax=500', 'region=Littoral', 'stade=serie_a'):
            self.assertEqual(self.client.get(f'/investisseur/marketplace/?{q}').status_code, 200)

    # 10.3 · Zéro occurrence de l’ancien nom dans l’interface et le code applicatif
    def test_zero_occurrence_ancien_nom(self):
        trouve = []
        for dossier in ('templates', 'apps', 'static/js', 'config'):
            for f in (BASE / dossier).rglob('*'):
                if f.suffix in ('.html', '.py', '.js') and 'migrations' not in f.parts and f.name != 'tests.py':
                    if 'readymatch' in f.read_text(encoding='utf-8', errors='ignore').lower():
                        trouve.append(str(f.relative_to(BASE)))
        self.assertEqual(trouve, [])
