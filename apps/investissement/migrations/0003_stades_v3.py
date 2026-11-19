"""Stades v3 (Angel, Seed, Série A, Série B+, Développement) : on convertit les thèses existantes."""
from django.db import migrations

CORRESPONDANCE = {'amorcage': ['angel', 'seed'], 'croissance': ['serie_a'], 'maturite': ['serie_b', 'developpement']}


def convertir(apps, schema_editor):
    These = apps.get_model('investissement', 'These')
    for t in These.objects.all():
        nouveaux = []
        for s in t.stades or []:
            for n in CORRESPONDANCE.get(s, [s]):
                if n not in nouveaux:
                    nouveaux.append(n)
        t.stades = nouveaux
        t.save(update_fields=['stades'])


class Migration(migrations.Migration):
    dependencies = [('investissement', '0002_these_contact_accompagnateur_these_mutuelle_apport_and_more')]
    operations = [migrations.RunPython(convertir, migrations.RunPython.noop)]
