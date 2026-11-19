from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from apps.annuaire.models import Organisation

from . import contenu, vitrine
from .services import accueil_investisseur


# Diagnostic express de l’accueil : six pièces que tout financeur demande, pondérées sur 100.
DIAGNOSTIC = [
    ('Vos états financiers SYSCOHADA des deux derniers exercices sont établis.', 25),
    ('Votre DSF est déposée et vous avez une attestation de non-redevance.', 20),
    ('Statuts, RCCM et NIU sont à jour.', 15),
    ('Votre besoin est chiffré, avec l’usage prévu des fonds.', 15),
    ('Vous avez un contrat, une lettre d’intention ou 24 mois de ventes suivies.', 15),
    ('La répartition du capital entre associés est documentée.', 10),
]


def landing(request):
    """Accueil : le Cameroun en chiffres et le diagnostic (style tableau de bord), puis le récit et les appareils (style site v2)."""
    m = accueil_investisseur()
    return render(request, 'core/accueil.html', {'m': m, 'v': vitrine.composants(m), 'diagnostic': DIAGNOSTIC})


def landing_vitrine(request):
    """Version précédente de la vitrine (conservée pour comparaison)."""
    m = accueil_investisseur()
    return render(request, 'core/vitrine.html', {'m': m, 'v': vitrine.composants(m)})


def landing_simple(request):
    """Ancienne landing (conservée pour comparaison)."""
    m = accueil_investisseur()
    return render(request, 'core/landing.html', {
        'm': m, 'indicateurs': contenu.INDICATEURS_PAYS, 'atouts': contenu.ATOUTS, 'acteurs': contenu.ACTEURS,
        'chaines': contenu.CHAINES, 'outils': contenu.OUTILS,
        'structures': Organisation.objects.accompagnement().filter(pays='Cameroun').exclude(description='').select_related('secteur').order_by('-completude')[:6],
    })


APERCU_JS = ('<script>document.addEventListener("click",function(e){var a=e.target.closest("a,button,summary,label");if(a){e.preventDefault();e.stopImmediatePropagation();}},true);'
             'document.addEventListener("submit",function(e){e.preventDefault();e.stopImmediatePropagation();},true);</script>'
             '<style>#rm-loader,#rm-bar,.toasts{display:none!important}</style>')


@xframe_options_sameorigin
def apercu(request, vue):
    """Vrais écrans de l’application, en lecture seule, affichés dans l’ordinateur de la vitrine.
    Ils utilisent les données de démonstration (Savane Agro SA, Fonds Baobab Croissance)."""
    from apps.accounts.models import User
    from apps.investissement import views as inv
    from apps.pme import views as pme

    if vue not in ('pme', 'entreprises', 'fiche', 'pipeline'):
        raise Http404
    sav = Organisation.objects.filter(est_demo=True, nom='Savane Agro SA').first()
    fonds = Organisation.objects.filter(est_demo=True, kind='investisseur').first()
    if not sav or not fonds:
        return HttpResponse('<p style="font:16px system-ui;padding:40px">Aperçu indisponible : lancez <code>python manage.py seed_demo</code>.</p>')
    if vue == 'pme':
        request.user = User.objects.filter(email='pme@demo.cm').first() or User(email='apercu@demo.cm', first_name='Awa', role='pme', organisation=sav)
        reponse = pme.tableau.__wrapped__.__wrapped__(request)
    else:
        request.user = User.objects.filter(email='investisseur@demo.cm').first() or User(email='apercu-inv@demo.cm', first_name='Analyste', role='investisseur', organisation=fonds)
        if vue == 'entreprises':
            reponse = inv.marketplace.__wrapped__.__wrapped__(request)
        elif vue == 'pipeline':
            reponse = inv.pipeline.__wrapped__.__wrapped__(request)
        else:
            reponse = inv.fiche.__wrapped__.__wrapped__(request, sav.slug)
    contenu = reponse.content.decode('utf-8').replace('</body>', APERCU_JS + '</body>', 1)
    r = HttpResponse(contenu)
    r['X-Robots-Tag'] = 'noindex'
    return r


def espace(request):
    """Après connexion : chacun vers son espace (ou la fin de son onboarding)."""
    u = request.user
    if not u.is_authenticated:
        return redirect('core:landing')
    if u.is_superuser and not u.organisation:
        return redirect('admin:index')
    if u.organisation is None and u.role in ('pme', 'investisseur'):
        return redirect('accounts:onboarding', role=u.role)
    return redirect({'pme': 'pme:tableau', 'investisseur': 'investissement:cameroun'}.get(u.role, 'core:landing'))


def erreur_404(request, exception):
    return render(request, '404.html', status=404)
