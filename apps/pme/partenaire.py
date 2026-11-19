"""Espace cabinet, fiscaliste, CGA ou structure d’appui (cahier des charges v3 · 8.3 et 8.4).

Le cabinet voit les PME qui l’ont choisi, verse et atteste leurs pièces (niveau A, nom, date, portée, révocable), vérifie l’identité
des dirigeants, répond aux questions des investisseurs que la PME l’a autorisé à traiter, et génère le format pivot puis les exports
par financeur à partir d’un seul travail comptable."""
import csv

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.annuaire.models import Organisation
from apps.core.decorators import role_requis
from apps.investissement.models import QuestionAccompagnateur

from . import services
from .forms import PieceForm
from .models import Attestation, ExerciceFinancier, Piece

FORMATS = [('pivot', 'Format pivot AnkadeZ (liasse SYSCOHADA, N et N-1)'), ('banque', 'Banque : liasse, plan de financement, couverture de la dette'),
           ('capital', 'Capital-risque ou business angel : trois derniers comptes (modèle EBAN)'), ('ptf', 'PTF : rapport d’impact'),
           ('api', 'API : dossier d’investissement (format à valider avec l’API)'), ('bvmac', 'BVMAC : dossier d’admission (format à valider)')]
LIGNES = [('chiffre_affaires', 'Chiffre d’affaires'), ('marge_brute', 'Marge brute'), ('valeur_ajoutee', 'Valeur ajoutée'), ('charges_personnel', 'Charges de personnel'),
          ('ebitda', 'Excédent brut d’exploitation'), ('resultat_net', 'Résultat net'), ('caf', 'Capacité d’autofinancement'), ('capitaux_propres', 'Capitaux propres'),
          ('dettes_financieres', 'Dettes financières'), ('dettes_court_terme', 'Dettes à court terme'), ('total_bilan', 'Total du bilan'),
          ('actif_circulant', 'Actif circulant'), ('stocks', 'Stocks'), ('creances_clients', 'Créances clients'), ('dettes_fournisseurs', 'Dettes fournisseurs'),
          ('achats', 'Achats'), ('flux_exploitation', 'Flux de trésorerie d’exploitation'), ('dette_nette', 'Dette nette'), ('service_dette', 'Service annuel de la dette')]


def _clients(org):
    return Organisation.objects.entreprises().filter(Q(profil_pme__cabinet=org) | Q(profil_pme__accompagnateur=org)).distinct().select_related('profil_pme', 'secteur')


def _client(request, pk):
    return get_object_or_404(_clients(request.user.organisation), pk=pk)


@role_requis('partenaire')
def tableau(request):
    org = request.user.organisation
    clients = []
    for o in _clients(org):
        clients.append({'org': o, 'score': services.score_preparation(o), 'cabinet': getattr(o.profil_pme, 'cabinet_id', None) == org.pk,
                        'attestations': o.attestations.filter(attestateur=org, revoquee_le__isnull=True).count()})
    return render(request, 'partenaire/tableau.html', {'org': org, 'clients': clients, 'formats': FORMATS,
                                                       'questions': QuestionAccompagnateur.objects.filter(structure=org).select_related('entreprise')})


@role_requis('partenaire')
def client(request, pk):
    o = _client(request, pk)
    form = PieceForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        p = form.save(commit=False)
        p.organisation = o
        p.save()
        messages.success(request, f'Pièce versée au dossier {p.dossier}.')
        return redirect('partenaire:client', pk=pk)
    return render(request, 'partenaire/client.html', {'o': o, 'form': form, 'score': services.score_preparation(o), 'formats': FORMATS,
                                                      'pieces': o.pieces.all(), 'exercices': o.exercices.all(),
                                                      'attestations': o.attestations.filter(attestateur=request.user.organisation)})


@role_requis('partenaire')
@require_POST
def attester(request, pk):
    o = _client(request, pk)
    org = request.user.organisation
    portee = request.POST.get('portee', '').strip() or 'Conformité à l’original et cohérence avec la liasse'
    cible = request.POST.get('cible', '')
    if cible == 'identite':
        o.profil_pme.identite_verifiee = True
        o.profil_pme.beneficiaires_identifies = True
        o.profil_pme.save(update_fields=['identite_verifiee', 'beneficiaires_identifies'])
        Attestation.objects.create(organisation=o, attestateur=org, portee='Identité des dirigeants et bénéficiaires effectifs vérifiés')
    elif cible.startswith('p'):
        piece = get_object_or_404(Piece, pk=cible[1:], organisation=o)
        Attestation.objects.create(organisation=o, attestateur=org, piece=piece, portee=portee, niveau_avant=piece.niveau_preuve)
        piece.niveau_preuve = 'certifie'
        piece.save(update_fields=['niveau_preuve'])
    elif cible.startswith('e'):
        ex = get_object_or_404(ExerciceFinancier, pk=cible[1:], organisation=o)
        Attestation.objects.create(organisation=o, attestateur=org, exercice=ex, portee=portee, niveau_avant=ex.niveau_preuve)
        ex.niveau_preuve = 'certifie'
        ex.save(update_fields=['niveau_preuve'])
    messages.success(request, 'Attestation enregistrée à votre nom, datée et révocable.')
    return redirect('partenaire:client', pk=pk)


@role_requis('partenaire')
@require_POST
def revoquer(request, pk, att):
    o = _client(request, pk)
    a = get_object_or_404(Attestation, pk=att, organisation=o, attestateur=request.user.organisation, revoquee_le__isnull=True)
    a.revoquee_le = timezone.now()
    a.save(update_fields=['revoquee_le'])
    for cible in (a.piece, a.exercice):
        if cible is not None:
            cible.niveau_preuve = a.niveau_avant or 'declaratif'
            cible.save(update_fields=['niveau_preuve'])
    messages.info(request, 'Attestation révoquée : le niveau de preuve est revenu à son état antérieur.')
    return redirect('partenaire:client', pk=pk)


@role_requis('partenaire')
def export(request, pk, fmt):
    """Un seul travail comptable (le gabarit pivot), puis l’export au format de chaque financeur."""
    o = _client(request, pk)
    ex = sorted(o.exercices.all(), key=lambda e: e.annee)
    p = o.profil_pme
    r = HttpResponse(content_type='text/csv; charset=utf-8')
    r['Content-Disposition'] = f'attachment; filename="ankadez-{fmt}-{o.slug}.csv"'
    w = csv.writer(r, delimiter=';')
    w.writerow([f'AnkadeZ · export {dict(FORMATS).get(fmt, fmt)}', o.nom, 'FICTIF' if o.est_demo else '', timezone.now().date().isoformat()])
    annees = [e.annee for e in ex]
    if fmt in ('pivot', 'banque', 'capital', 'api', 'bvmac'):
        lignes = LIGNES if fmt in ('pivot', 'api', 'bvmac') else [l for l in LIGNES if l[0] in (
            'chiffre_affaires', 'ebitda', 'resultat_net', 'caf', 'capitaux_propres', 'dettes_financieres', 'total_bilan', 'dette_nette', 'service_dette')] if fmt == 'banque' else [
            l for l in LIGNES if l[0] in ('chiffre_affaires', 'marge_brute', 'ebitda', 'resultat_net', 'flux_exploitation', 'capitaux_propres')]
        sel = ex[-3:] if fmt == 'capital' else ex[-2:] if fmt == 'pivot' else ex
        w.writerow(['Ligne'] + [e.annee for e in sel] + ['Niveau de preuve'])
        for champ, lab in lignes:
            w.writerow([lab] + [getattr(e, champ) if getattr(e, champ) is not None else '' for e in sel] + [sel[-1].get_niveau_preuve_display() if sel else ''])
        if fmt == 'banque' and ex:
            w.writerow(['Couverture du service de la dette', ex[-1].dscr or ''])
            w.writerow(['Plan de financement (usage des fonds)'] + [f'{u[0]} : {u[1]}' for u in (p.usage_fonds or [])])
    if fmt == 'ptf':
        w.writerow(['Indicateur', 'Valeur'])
        for lab, val in [('Emplois', p.effectif), ('Femmes', p.emplois_femmes), ('Jeunes', p.emplois_jeunes), ('Salariés CNPS', p.salaries_cnps),
                         ('Dirigée par une femme', 'oui' if p.dirigeante else 'non'), ('Zone rurale', 'oui' if p.zone_rurale else 'non'),
                         ('Part export (%)', p.part_export), ('Financement PTF', p.financement_ptf), ('Privé mobilisé', p.financement_prive)]:
            w.writerow([lab, val if val is not None else ''])
    w.writerow([])
    w.writerow(['Attestations'] + [f'{a.attestateur.nom} ({a.created_at.date()}) : {a.portee}' for a in o.attestations.filter(revoquee_le__isnull=True)])
    if not annees:
        w.writerow(['Aucun exercice déclaré'])
    return r


@role_requis('partenaire')
@require_POST
def repondre(request, q):
    obj = get_object_or_404(QuestionAccompagnateur, pk=q, structure=request.user.organisation)
    obj.reponse = request.POST.get('reponse', '').strip()[:2000]
    obj.signaler_pme = request.POST.get('signaler') == '1'
    obj.repondu_le = timezone.now()
    obj.save()
    messages.success(request, 'Réponse envoyée. La PME voit l’échange.')
    return redirect('partenaire:tableau')
