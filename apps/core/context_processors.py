from django.urls import reverse


def navigation(request):
    """Menu de la barre du haut, selon le rôle de la personne connectée."""
    u = request.user
    if not u.is_authenticated:
        items = [('Le Cameroun', reverse('core:landing') + '#cameroun'), ('La plateforme', reverse('core:landing') + '#plateforme'),
                 ('Écosystème', reverse('annuaire:ecosysteme')), ('Outils PME', reverse('core:landing') + '#outils')]
    elif u.role == 'pme':
        items = [('Accueil', reverse('pme:tableau')), ('Data room', reverse('pme:dossier')), ('Finances', reverse('pme:finances')),
                 ('Profil', reverse('pme:profil')), ('Investisseurs', reverse('pme:investisseurs')), ('Écosystème', reverse('annuaire:ecosysteme'))]
    elif u.role == 'investisseur':
        items = [('Le Cameroun', reverse('core:landing')), ('Entreprises', reverse('investissement:marketplace')),
                 ('Pipeline', reverse('investissement:pipeline')), ('Ma thèse', reverse('investissement:these')), ('Écosystème', reverse('annuaire:ecosysteme'))]
    else:
        items = [('Accueil', reverse('core:landing')), ('Écosystème', reverse('annuaire:ecosysteme'))]
    path = request.path
    nav = [(lab, url, url.split('#')[0] == path and '#' not in url) for lab, url in items]
    return {'rm_nav': nav}
