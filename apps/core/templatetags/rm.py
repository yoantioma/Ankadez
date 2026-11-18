"""Filtres d’affichage des montants en FCFA, à la française."""
from django import template

register = template.Library()


def _fr(v, d=1):
    s = f'{v:,.{d}f}'.replace(',', ' ').replace('.', ',')
    return s[:-2] if d and s.endswith(',0') else s


@register.filter
def fcfa(v):
    """1 268 000 000 → « 1,27 Md » ; 500 000 000 → « 500 M » ; 750 000 → « 750 000 »."""
    if v in (None, ''):
        return '—'
    v = float(v)
    if abs(v) >= 1e9:
        return f'{_fr(v / 1e9, 2)} Md'
    if abs(v) >= 1e6:
        return f'{_fr(v / 1e6, 0 if v % 1e6 == 0 else 1)} M'
    return _fr(v, 0)


@register.filter
def entier(v):
    if v in (None, ''):
        return '—'
    return _fr(float(v), 0)


@register.filter
def virgule(v, d=1):
    if v in (None, ''):
        return '—'
    return _fr(float(v), int(d))


@register.filter
def pct_of(v, total):
    try:
        return round(float(v) / float(total) * 100, 1) if float(total) else 0
    except (TypeError, ValueError):
        return 0


@register.filter
def get(d, k):
    try:
        return d.get(k)
    except AttributeError:
        return None


import json  # noqa: E402
from pathlib import Path  # noqa: E402

from django.utils.safestring import mark_safe  # noqa: E402

_ICONES = json.loads((Path(__file__).resolve().parent.parent / 'icones.json').read_text(encoding='utf-8'))


@register.simple_tag
def ic(nom, taille=20):
    """Icône au trait (SVG en ligne), décorative."""
    corps = _ICONES.get(nom, '')
    return mark_safe(f'<svg class="ic" width="{taille}" height="{taille}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                     f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{corps}</svg>')
