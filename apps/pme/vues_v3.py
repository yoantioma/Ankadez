"""Écrans PME du cahier des charges v3 : passeport transmissible (6.3), reprise (7.2), radar de clauses (v2 maintenu),
divulgation spontanée (6.2), accompagnement à chaque étape (8.1, 8.3) et académie (10.1)."""
import hashlib
import json

from django import forms
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.annuaire.models import Organisation
from apps.core.decorators import role_requis
from apps.offres import services as offres

from . import services, v3
from .models import EntrepriseProfile, FicheCession, Partage, Signalement

# « Un passeport, plusieurs lunettes » : chaque institution ne reçoit que ce dont elle a besoin (périmètre proposé, modifiable)
PERIMETRES = {'apme': ['profil', 'scores', 'accompagnement'], 'api': ['profil', 'grade', 'scores', 'pieces', 'usage', 'accompagnement'],
              'bvmac': ['profil', 'grade', 'scores', 'pieces', 'finances', 'accompagnement', 'impact'],
              'investisseur': ['profil', 'grade', 'scores', 'pieces'], 'accompagnateur': ['profil', 'grade', 'scores']}
INSTITUTIONS = {'apme': 'APME', 'api': 'Agence de Promotion des Investissements', 'bvmac': 'BVMAC'}


def _org(request):
    return request.user.organisation


def _empreinte(piece):
    """Empreinte numérique (SHA-256) : du fichier quand il existe, sinon de l’intitulé et de la date de dépôt."""
    h = hashlib.sha256()
    if piece.fichier:
        try:
            for bloc in piece.fichier.chunks():
                h.update(bloc)
            return h.hexdigest()[:16]
        except (OSError, ValueError):
            pass
    h.update(f'{piece.titre}|{piece.created_at.isoformat()}'.encode())
    return h.hexdigest()[:16]


def contenu_passeport(org, perimetre=None):
    """Le dossier numérique unique : profil, grade, stade, confiance, scores, pièces et empreintes, attestations, consentements."""
    perimetre = perimetre or [c for c, _ in Partage.SECTIONS]
    s = services.score_preparation(org)
    p = getattr(org, 'profil_pme', None)
    d = {'passeport': 'AnkadeZ', 'version': '3.0', 'emis_le': timezone.now().isoformat(timespec='seconds'), 'entreprise': org.nom,
         'fictif': org.est_demo, 'avertissement': 'Atteste la préparation d’un dossier. Ni agrément, ni recommandation d’investir, ni appel public à l’épargne.'}
    if 'profil' in perimetre:
        d['profil'] = {'secteur': str(org.secteur or ''), 'region': org.region, 'ville': org.ville, 'forme': p.forme_juridique if p else '',
                       'rccm': bool(p and p.rccm), 'effectif': p.effectif if p else None, 'montant_recherche': p.ticket_recherche if p else None}
    if 'grade' in perimetre:
        d['grade'] = {'palier': s.palier, 'score': s.total, 'stade': s.stade_libelle, 'confiance': s.confiance, 'points_rouges': s.points_rouges}
    if 'scores' in perimetre:
        d['scores'] = {lab: f'{v}/{mx}' for _, lab, v, mx in s.dims} | {'lecture_banque': s.dette, 'lecture_fonds': s.fonds_propres}
    if 'pieces' in perimetre:
        d['pieces'] = [{'dossier': pc.dossier, 'titre': pc.titre, 'niveau': pc.niveau_preuve, 'empreinte_sha256': _empreinte(pc),
                        'deposee_le': pc.created_at.date().isoformat()} for pc in org.pieces.all()]
    if 'finances' in perimetre:
        d['finances'] = [{'annee': e.annee, 'chiffre_affaires': e.chiffre_affaires, 'ebitda': e.ebitda, 'resultat_net': e.resultat_net,
                          'niveau': e.niveau_preuve} for e in org.exercices.all()]
    if 'usage' in perimetre:
        d['usage_des_fonds'] = p.usage_fonds if p else []
    if 'accompagnement' in perimetre:
        d['attestations'] = [{'par': a.attestateur.nom, 'portee': a.portee, 'le': a.created_at.date().isoformat()}
                             for a in org.attestations.filter(revoquee_le__isnull=True).select_related('attestateur')]
        d['accompagnateur'] = p.accompagnateur.nom if p and p.accompagnateur else None
    if 'impact' in perimetre and p:
        d['impact'] = {'emplois': p.effectif, 'femmes': p.emplois_femmes, 'jeunes': p.emplois_jeunes, 'cnps': p.salaries_cnps,
                       'dirigeante': p.dirigeante, 'part_export': p.part_export}
    d['consentements'] = [{'destinataire': x.get_destinataire_type_display(), 'perimetre': x.perimetre, 'le': x.created_at.date().isoformat(),
                           'revoque_le': x.revoque_le.date().isoformat() if x.revoque_le else None} for x in org.partages.all()]
    brut = json.dumps(d, ensure_ascii=False, sort_keys=True)
    d['signature_sha256'] = hashlib.sha256(brut.encode()).hexdigest()
    return d


@role_requis('pme')
def passeport(request):
    org = _org(request)
    if request.method == 'POST':
        if request.POST.get('action') == 'revoquer':
            x = get_object_or_404(Partage, pk=request.POST.get('pk'), organisation=org, revoque_le__isnull=True)
            x.revoque_le = timezone.now()
            x.save(update_fields=['revoque_le'])
            messages.info(request, f'Accès révoqué : {x.get_destinataire_type_display()}.')
        else:
            typ = request.POST.get('destinataire_type')
            perimetre = [c for c in request.POST.getlist('perimetre') if c in dict(Partage.SECTIONS)]
            if typ not in dict(Partage.DESTINATAIRES) or not perimetre:
                messages.error(request, 'Choisissez un destinataire et au moins une rubrique.')
            elif request.POST.get('consentement') != '1':
                messages.error(request, 'Le passeport n’est jamais envoyé sans votre accord explicite.')
            else:
                dest = Organisation.objects.filter(nom__icontains=INSTITUTIONS[typ]).first() if typ in INSTITUTIONS else None
                Partage.objects.create(organisation=org, destinataire_type=typ, destinataire=dest, perimetre=perimetre)
                messages.success(request, f'Passeport transmis : {dict(Partage.DESTINATAIRES)[typ]}. Vous pouvez révoquer cet envoi à tout moment.')
        return redirect('pme:passeport')
    s = services.score_preparation(org)
    return render(request, 'pme/passeport.html', {
        'org': org, 'score': s, 'contenu': contenu_passeport(org), 'partages': org.partages.select_related('destinataire'),
        'destinataires': Partage.DESTINATAIRES, 'sections': Partage.SECTIONS, 'perimetres': json.dumps(PERIMETRES),
        'fraicheur': v3.coefficient_fraicheur(org)[1], 'familles': v3.familles(org), 'portes': v3.portes(org)})


@role_requis('pme')
def passeport_json(request):
    d = contenu_passeport(_org(request))
    r = HttpResponse(json.dumps(d, ensure_ascii=False, indent=2), content_type='application/json; charset=utf-8')
    r['Content-Disposition'] = 'attachment; filename="passeport-ankadez.json"'
    return r


@role_requis('pme')
def passeport_imprimer(request):
    org = _org(request)
    return render(request, 'pme/passeport_imprimer.html', {'org': org, 'd': contenu_passeport(org), 'score': services.score_preparation(org)})


# ------------------------------------------------------------------ 7.2 Reprise d’entreprise
class CessionForm(forms.ModelForm):
    class Meta:
        model = FicheCession
        exclude = ['organisation', 'updated_at']
        widgets = {k: forms.Textarea(attrs={'rows': 2}) for k in ('actifs', 'dettes', 'contrats_cles')}


@role_requis('pme')
def reprise(request):
    org = _org(request)
    fiche = getattr(org, 'fiche_cession', None) or FicheCession(organisation=org)
    form = CessionForm(request.POST or None, instance=fiche)
    if request.method == 'POST' and form.is_valid():
        f = form.save(commit=False)
        f.organisation = org
        f.save()
        profil, _ = EntrepriseProfile.objects.get_or_create(organisation=org)
        profil.ouvert_reprise = True
        if f.operation not in profil.ouvertures:
            profil.ouvertures = profil.ouvertures + [f.operation]
        profil.save(update_fields=['ouvert_reprise', 'ouvertures'])
        messages.success(request, 'Fiche enregistrée. ' + ('La fiche anonyme est publiée.' if f.publiee else 'Elle reste confidentielle.'))
        return redirect('pme:reprise')
    from apps.offres.models import ProduitFinancier
    return render(request, 'pme/reprise.html', {
        'org': org, 'form': form, 'fiche': fiche if fiche.pk else None, 'score': services.score_preparation(org),
        'financements': ProduitFinancier.objects.filter(actif=True, type__in=['credit', 'ligne', 'garantie'])[:4],
        'conseils': [(lab, offres.recommander(s, 2)) for s, lab in [('comptabilite', 'Expert-comptable'), ('juridique', 'Avocat OHADA'), ('structuration', 'Évaluateur, conseil financier')]]})


# ------------------------------------------------------------------ Radar de clauses (v2 maintenu) : on explique, on ne rédige pas
CLAUSES = [
    (r'liquidation|préférence de liquidation|liquidation preference', 'Préférence de liquidation',
     'En cas de vente, l’investisseur récupère sa mise (parfois plus) avant les autres associés. Vérifiez le multiple (1× est l’usage) et s’il est « participatif ».'),
    (r'anti-?dilution|ratchet', 'Clause anti-dilution',
     'Protège l’investisseur si une levée future se fait à un prix plus bas. La version « full ratchet » est très défavorable au dirigeant.'),
    (r'drag[- ]?along|sortie forcée|entraînement', 'Sortie forcée (drag-along)', 'Une majorité peut obliger les autres associés à vendre. Vérifiez le seuil et le prix plancher.'),
    (r'tag[- ]?along|sortie conjointe', 'Sortie conjointe (tag-along)', 'Les minoritaires peuvent vendre aux mêmes conditions que le majoritaire. Plutôt protecteur.'),
    (r'non[- ]?concurrence', 'Non-concurrence', 'Vous interdit une activité concurrente. Vérifiez la durée, la zone et la contrepartie.'),
    (r'exclusivit', 'Exclusivité', 'Vous empêche de discuter avec d’autres financeurs pendant une période. Limitez-la (60 à 90 jours).'),
    (r'changement de contr[ôo]le|change of control', 'Changement de contrôle', 'Un contrat peut tomber si le capital change de mains. À vérifier avant toute cession.'),
    (r'vesting|acquisition progressive', 'Acquisition progressive (vesting)', 'Les parts du dirigeant s’acquièrent dans le temps ; s’il part tôt, il en perd une partie.'),
    (r'good leaver|bad leaver|leaver', 'Bon et mauvais partant', 'Fixe le prix de rachat des parts d’un associé qui part. La définition du « mauvais partant » est clé.'),
    (r'droit de veto|décisions importantes|reserved matters', 'Droits de veto', 'Liste des décisions qui exigent l’accord de l’investisseur. Vérifiez qu’elle ne bloque pas la gestion courante.'),
    (r'préemption|pre-?emption', 'Droit de préemption', 'Les associés sont prioritaires pour racheter les parts mises en vente.'),
    (r'convertible|conversion', 'Prêt convertible', 'Le prêt devient du capital à un événement donné. Vérifiez la décote, le plafond de valorisation et la validité en droit OHADA.'),
    (r'information|reporting|droit d.information', 'Droits d’information', 'Ce que vous devrez transmettre (comptes mensuels, trimestriels, audit annuel). Prévoyez le coût.'),
]


@role_requis('pme')
def radar(request):
    import re
    texte = request.POST.get('texte', '') if request.method == 'POST' else ''
    trouvees = [(lab, expl) for motif, lab, expl in CLAUSES if re.search(motif, texte, re.I)] if texte else []
    return render(request, 'pme/radar.html', {'org': _org(request), 'texte': texte, 'trouvees': trouvees, 'analyse': bool(texte),
                                              'avocats': offres.recommander('juridique', 3)})


# ------------------------------------------------------------------ 6.2 Divulgation spontanée
@role_requis('pme')
@require_POST
def divulguer(request):
    org = _org(request)
    typ = request.POST.get('type')
    desc = request.POST.get('description', '').strip()
    if typ in dict(Signalement.TYPES) and desc:
        Signalement.objects.create(organisation=org, auteur=org, type=typ, description=desc[:255], divulgation_spontanee=True,
                                   majeur=request.POST.get('majeur') == '1')
        messages.success(request, 'Faiblesse déclarée avant tout contrôle : elle ne pénalise pas votre indice.')
    return redirect('pme:dossier')


# ------------------------------------------------------------------ 8.1 et 8.3 : accompagnateurs, consentement, journal
@role_requis('pme')
@require_POST
def choisir_accompagnateur(request):
    org = _org(request)
    profil, _ = EntrepriseProfile.objects.get_or_create(organisation=org)
    acc = Organisation.objects.accompagnement().filter(pk=request.POST.get('accompagnateur') or 0).first()
    cab = Organisation.objects.accompagnement().filter(pk=request.POST.get('cabinet') or 0).first()
    profil.accompagnateur = acc
    profil.cabinet = cab
    profil.accompagnateur_peut_repondre = request.POST.get('peut_repondre') == '1' and acc is not None
    profil.save(update_fields=['accompagnateur', 'cabinet', 'accompagnateur_peut_repondre'])
    messages.success(request, 'Accompagnement enregistré.')
    return redirect('pme:niveau')
