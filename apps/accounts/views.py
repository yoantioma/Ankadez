from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.annuaire.models import Organisation
from apps.investissement.models import These
from apps.pme.models import EntrepriseProfile, ExerciceFinancier

from .forms import CompteForm, ConnexionForm, EntrepriseForm, FinancementForm, TheseForm
from .models import User

PARCOURS = {
    'pme': {'titre': 'Je dirige une PME', 'etapes': ['Votre compte', 'Votre entreprise', 'Votre financement'],
            'photo': 'F', 'accroche': 'Préparer votre dossier, calculer un montant juste, rencontrer les bons investisseurs.'},
    'investisseur': {'titre': 'J’investis', 'etapes': ['Votre compte', 'Votre thèse'], 'photo': 'L',
                     'accroche': 'Des PME au dossier vérifié, une compatibilité expliquée critère par critère.'},
}


def inscription(request):
    return render(request, 'accounts/inscription.html', {'parcours': PARCOURS})


def _ctx(role, etape, form, **extra):
    p = PARCOURS[role]
    return {'role': role, 'p': p, 'etape': etape, 'n_etapes': len(p['etapes']), 'titre_etape': p['etapes'][etape], 'form': form, **extra}


def inscription_compte(request, role):
    if role not in PARCOURS:
        return redirect('accounts:inscription')
    if request.user.is_authenticated:
        return redirect('accounts:onboarding', role=role)
    form = CompteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(role=role)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'Compte créé. Continuons.')
        return redirect('accounts:onboarding', role=role)
    return render(request, 'accounts/onboarding.html', _ctx(role, 0, form, submit='Créer mon compte'))


@login_required
def onboarding(request, role):
    user = request.user
    if role != user.role or role not in PARCOURS:
        return redirect('core:espace')
    if role == 'pme':
        return _onboarding_pme(request, user)
    return _onboarding_investisseur(request, user)


def _onboarding_pme(request, user):
    org = user.organisation
    if org is None:
        form = EntrepriseForm(request.POST or None)
        if request.method == 'POST' and form.is_valid():
            d = form.cleaned_data
            with transaction.atomic():
                org = Organisation.objects.create(kind=Organisation.Kind.PME, nom=d['nom'], secteur=d['secteur'], ville=d['ville'],
                                                  region=d['region'], description=d['description'], a_verifier=True, completude=40)
                EntrepriseProfile.objects.create(organisation=org, forme_juridique=d['forme_juridique'], annee_creation=d['annee_creation'],
                                                 effectif=d['effectif'])
                user.organisation = org
                user.save(update_fields=['organisation'])
            return redirect('accounts:onboarding', role='pme')
        return render(request, 'accounts/onboarding.html', _ctx('pme', 1, form, submit='Continuer'))
    form = FinancementForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            profil, _ = EntrepriseProfile.objects.get_or_create(organisation=org)
            for k in ('ticket_recherche', 'part_investissement', 'instrument_souhaite', 'stade'):
                setattr(profil, k, d[k] if d[k] not in ('', None) else getattr(profil, k))
            profil.save()
            if d.get('chiffre_affaires'):
                ExerciceFinancier.objects.update_or_create(organisation=org, annee=d['annee'], defaults={
                    'chiffre_affaires': d['chiffre_affaires'], 'marge_brute': d['marge_brute'], 'ebitda': d['ebitda']})
        messages.success(request, 'Votre espace est prêt. Voici votre premier score de préparation.')
        return redirect('pme:tableau')
    return render(request, 'accounts/onboarding.html', _ctx('pme', 2, form, submit='Voir mon score', passer=reverse('pme:tableau')))


def _onboarding_investisseur(request, user):
    form = TheseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            org = user.organisation or Organisation.objects.create(kind=Organisation.Kind.INVESTISSEUR, nom=d['nom'], ville=d['ville'], pays=d['pays'] or 'Cameroun')
            these, _ = These.objects.update_or_create(organisation=org, defaults={
                'ticket_min': d['ticket_min'], 'ticket_max': d['ticket_max'], 'zones': d['zones'], 'stades': d['stades'],
                'instruments': d['instruments'], 'exigence_esg': d['exigence_esg'], 'horizon_annees': d['horizon_annees']})
            these.secteurs.set(d['secteurs'])
            user.organisation = org
            user.save(update_fields=['organisation'])
        messages.success(request, 'Votre thèse est enregistrée. Voici les entreprises compatibles.')
        return redirect('investissement:marketplace')
    return render(request, 'accounts/onboarding.html', _ctx('investisseur', 1, form, submit='Voir les entreprises compatibles'))


class Connexion(LoginView):
    template_name = 'accounts/connexion.html'
    authentication_form = ConnexionForm
    redirect_authenticated_user = True


class Deconnexion(LogoutView):
    pass
