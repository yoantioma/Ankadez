"""Importe les fichiers CSV « ajouts_panaf_*.csv » dans l’annuaire.

  python manage.py import_panaf ../ajouts_panaf_*.csv
  python manage.py import_panaf fichier.csv --avec-contacts   # importe aussi e-mail et téléphone

Règles :
- les lignes « Talent » (des personnes) ne sont pas importées ;
- les noms des dirigeants et les messages de prospection ne sont jamais importés ;
- l’import est idempotent : une ligne déjà importée (même ID) est mise à jour, pas dupliquée.
"""
import csv
import glob

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.annuaire.models import Organisation, Secteur
from apps.pme.models import EntrepriseProfile

KIND = {'Entreprise': 'pme', 'Startup': 'startup', 'Investisseur': 'investisseur', 'Institution': 'institution',
        'Incubateur': 'incubateur', 'Association': 'association', 'Consultant': 'consultant'}


def _url(v):
    v = (v or '').strip()
    if v and not v.startswith(('http://', 'https://')):
        v = 'https://' + v
    return v[:300]


class Command(BaseCommand):
    help = 'Importe les acteurs des fichiers CSV panaf dans l’annuaire AnkadeZ.'

    def add_arguments(self, parser):
        parser.add_argument('fichiers', nargs='+', help='Chemins ou motifs de fichiers CSV')
        parser.add_argument('--avec-contacts', action='store_true', help='Importer aussi e-mail et téléphone des organisations')

    @transaction.atomic
    def handle(self, *args, **opts):
        chemins = sorted({p for motif in opts['fichiers'] for p in (glob.glob(motif) or [motif])})
        if not chemins:
            raise CommandError('Aucun fichier trouvé.')
        crees = maj = ignores = 0
        secteurs = {}
        for chemin in chemins:
            try:
                fh = open(chemin, encoding='utf-8-sig', newline='')
            except OSError as exc:
                raise CommandError(f'Lecture impossible : {chemin} ({exc})')
            with fh:
                for ligne in csv.DictReader(fh, delimiter=';'):
                    kind = KIND.get((ligne.get('acteur') or '').strip())
                    if not kind or (ligne.get('supprime') or '').strip().lower() == 'true':
                        ignores += 1
                        continue
                    nom_secteur = (ligne.get('Secteur') or '').strip()
                    secteur = None
                    if nom_secteur:
                        secteur = secteurs.get(nom_secteur) or Secteur.objects.get_or_create(nom=nom_secteur)[0]
                        secteurs[nom_secteur] = secteur
                    try:
                        completude = int(ligne.get('Completude') or 0)
                    except ValueError:
                        completude = 0
                    valeurs = {
                        'kind': kind,
                        'nom': (ligne.get('Nom') or ligne.get('Organisation') or '').strip()[:200],
                        'secteur': secteur,
                        'categorie': (ligne.get('Categorie') or '').strip()[:160],
                        'description': (ligne.get('Role') or '').strip(),
                        'ville': (ligne.get('Ville') or '').strip()[:120],
                        'region': (ligne.get('Region') or '').strip()[:80],
                        'pays': (ligne.get('Pays') or '').strip()[:80] or 'Cameroun',
                        'adresse': (ligne.get('Adresse') or '').strip()[:255],
                        'site_web': _url(ligne.get('Site')),
                        'linkedin': _url(ligne.get('LinkedIn')),
                        'source_url': _url(ligne.get('Source'))[:500],
                        'completude': min(completude, 100),
                        'a_verifier': (ligne.get('A_verifier') or 'Oui').strip().lower() != 'non',
                    }
                    if opts['avec_contacts']:
                        email = (ligne.get('Email') or '').strip()
                        valeurs['email'] = email if '@' in email and ' ' not in email else ''
                        valeurs['telephone'] = (ligne.get('Telephone') or '').strip()[:80]
                    if not valeurs['nom']:
                        ignores += 1
                        continue
                    org, cree = Organisation.objects.update_or_create(external_id=ligne['ID'].strip(), defaults=valeurs)
                    if org.est_entreprise:
                        EntrepriseProfile.objects.get_or_create(organisation=org)
                    crees += cree
                    maj += not cree
        self.stdout.write(self.style.SUCCESS(f'{crees} acteurs créés, {maj} mis à jour, {ignores} lignes ignorées (talents, lignes supprimées ou vides).'))
