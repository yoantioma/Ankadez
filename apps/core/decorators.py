from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_requis(role):
    """Réserve une vue à un rôle ; renvoie vers l’onboarding si l’organisation n’est pas encore créée."""
    def deco(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            u = request.user
            if u.role != role and not u.is_superuser:
                return redirect('core:espace')
            if u.organisation is None and not u.is_superuser:
                return redirect('accounts:onboarding', role=role)
            return view(request, *args, **kwargs)
        return wrapper
    return deco


def est_partiel(request):
    """Requête faite par le script de chargement (fetch) : on renvoie seulement le fragment HTML."""
    return request.headers.get('X-Requested-With') == 'fetch' or request.GET.get('partiel') == '1'
