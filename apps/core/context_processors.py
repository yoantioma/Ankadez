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
        items = [('Le Cameroun', reverse('investissement:cameroun')), ('Entreprises', reverse('investissement:marketplace')),
                 ('Pipeline', reverse('investissement:pipeline')), ('Ma thèse', reverse('investissement:these')), ('Écosystème', reverse('annuaire:ecosysteme'))]
    else:
        items = [('Accueil', reverse('core:landing')), ('Écosystème', reverse('annuaire:ecosysteme'))]
    path = request.path
    nav = [(lab, url, url.split('#')[0] == path and '#' not in url) for lab, url in items]
    web = []
    if u.is_authenticated and u.role == 'investisseur':
        # Barre de l'espace web, comme dans les maquettes (sans « Accueil » : la page d'arrivée est la vue pays)
        liens = [('Le Cameroun', 'carte', reverse('investissement:cameroun'), ()),
                 ('Secteurs', 'boussole', reverse('investissement:secteurs'), ()),
                 ('Entreprises', 'liste', reverse('investissement:entreprises'), ()),
                 ('Fiche PME', 'jauge', reverse('investissement:fiche_courante'), ('/investisseur/entreprise/',)),
                 ('Marketplace', 'pile', reverse('investissement:marketplace'), ()),
                 ('Pipeline', 'cible', reverse('investissement:pipeline'), ()),
                 ('Reprises', 'sortie', reverse('investissement:reprises'), ()),
                 ('Impact', 'reseau', reverse('investissement:impact'), ())]
    elif u.is_authenticated and u.role == 'pme':
        # Barre de l'espace PME, comme dans les maquettes (la page « Compétitivité » viendra avec l'outil PESTEL)
        liens = [('Accueil', 'accueil', reverse('pme:tableau'), ()),
                 ('Data room', 'dossier', reverse('pme:dossier'), ()),
                 ('Financer', 'financer', reverse('pme:finances'), ()),
                 ('Passeport', 'bouclier', reverse('pme:passeport'), ()),
                 ('Investisseurs', 'invest', reverse('pme:investisseurs'), ()),
                 ('Deals', 'cible', reverse('pme:deals'), ()),
                 ('Niveau', 'jauge', reverse('pme:niveau'), ('/pme/reprise/', '/pme/radar-clauses/'))]
    elif u.is_authenticated and u.role == 'partenaire':
        liens = [('Mes PME', 'liste', reverse('partenaire:tableau'), ('/partenaire/',)), ('Programmes', 'livre', reverse('core:programmes'), ()),
                 ('Académie', 'jauge', reverse('core:academie'), ())]
    else:
        liens = []
    if liens:
        accueil = liens[0][2]
        for lab, icone, url, extra in liens:
            actif = path == url or (url != accueil and path.startswith(url)) or any(path.startswith(x) for x in extra)
            web.append((lab, icone, url, actif))
    return {'rm_nav': nav, 'rm_nav_web': web}
