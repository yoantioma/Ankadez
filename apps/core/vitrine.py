"""Composants dynamiques de la page vitrine (même balisage que le prototype validé), calculés sur la base."""
import math
from html import escape as e

from django.templatetags.static import static
from django.utils.safestring import mark_safe

from .templatetags.rm import ic

SEUIL_COMPAT = 55


def _fr(v, d=1):
    return f'{v:.{d}f}'.replace('.', ',')


def _md(fcfa):
    return _fr(fcfa / 1e9, 2)


def _m(fcfa):
    return f'{fcfa / 1e6:.0f} M'


def _photo(k):
    return static(f'img/photos/{k}.webp')


def hero(m):
    mb = m['potentiel']
    shades = ['#FFFFFF', 'rgba(255,255,255,.66)', 'rgba(255,255,255,.42)', 'rgba(255,255,255,.2)']
    top3 = [(nom, v) for nom, v, _ in m['top3']]
    rest = m['autres']
    parts = top3 + ([('Autres secteurs', rest)] if rest else [])
    split = ''.join(f'<i style="flex:{v};background:{shades[i]}"></i>' for i, (_, v) in enumerate(parts))
    splitl = ''.join(f'<span style="flex:{v}">{e(s if len(s) <= 14 else s.split()[0])} · {round(v / mb * 100) if mb else 0} %</span>' for s, v in top3)
    splitl += f'<span style="flex:{rest}"></span>' if rest else ''
    avs = ''.join(f'<span style="background-image:url(\'{_photo(k)}\')"></span>' for k in ('agro', 'port', 'solaire', 'couture'))
    t = m['tickets']
    if mb:
        bloc = (f'<b>{_md(mb)}<small>Md FCFA</small></b><span class="ex">{format(mb, ",").replace(",", " ")} FCFA par an, au Cameroun, sur {m["n_avec_marge"]} '
                f'entreprise{"s" if m["n_avec_marge"] > 1 else ""} aux comptes déclarés. Les 3 secteurs qui pèsent le plus :</span>'
                f'<div class="split" aria-hidden="true">{split}</div><div class="splitl">{splitl}</div>')
    else:
        bloc = '<b style="font-size:40px;white-space:normal">Aucune entreprise n’a encore déclaré ses comptes.</b>'
    tickets = (f'<div class="rng"><i style="left:0%"></i><i class="m" style="left:{t["pos"]}%"></i><i style="left:100%"></i></div>'
               f'<div class="rngl"><span><b>{_m(t["min"])}</b>minimum</span><span><b>{_m(t["med"])}</b>médiane</span><span><b>{_m(t["max"])}</b>maximum</span></div>'
               if t else '<span class="s">Aucun montant indiqué pour l’instant.</span>')
    return mark_safe(
        f'<section class="hero6" aria-label="Potentiel"><div class="bk"><span class="live"><i></i>Tous secteurs confondus</span>'
        f'<p class="k">L’argent à se faire : marge brute cumulée des entreprises inscrites</p>{bloc}</div>'
        f'<div class="pn6"><p class="k2">Effectif</p><div class="avs">{avs}</div><b>{m["n_entreprises"]}<small style="font-size:18px;margin-left:8px;letter-spacing:0">entreprises</small></b>'
        f'<span class="s">inscrites sur la plateforme, dans <b style="color:#15132B">{m["n_secteurs"]} secteurs</b> d’activité</span></div>'
        f'<div class="pn6"><p class="k2">Tickets · toutes entreprises</p>{tickets}</div></section>')


def _radial(p, big, sub, n=44):
    r, cx, cy, k = 76, 92, 92, round(p * n)
    dots = ''
    for i in range(n):
        a = math.radians(-90 + i * 360 / n)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        dots += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="var(--violet)" opacity="{.3 + .7 * i / max(1, k - 1):.2f}"/>' if i < k
                 else f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4" fill="var(--creux)"/>')
    return (f'<div class="rad"><svg width="184" height="184" viewBox="0 0 184 184" role="img" aria-label="{e(big)} {e(sub)}">'
            f'<circle cx="{cx}" cy="{cy}" r="58" fill="none" stroke="var(--vd)" stroke-width="12" opacity=".7"/>{dots}'
            f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" style="font:400 34px var(--f);fill:var(--encre);letter-spacing:-1px">{e(big)}</text>'
            f'<text x="{cx}" y="{cy + 24}" text-anchor="middle" style="font:500 11.5px var(--f);fill:var(--t3)">{e(sub)}</text></svg></div>')


def ck(m):
    n, comptes = m['n_entreprises'], m['avec_comptes']
    rows = [('var(--violet)', 'Avec états financiers', comptes), ('#8B78F0', 'Couverture de la dette calculée', len(m['dscr'])), ('#B8ABF7', 'Sortie écrite', m['sorties_ecrites'])]
    rws = '<div class="rws">' + ''.join(f'<div><i style="background:{c}"></i><span>{e(t)}</span><b>{v}</b></div>' for c, t, v in rows) + '</div>'
    return mark_safe(f'<section class="bx" style="grid-area:ck"><div class="bh"><div><p class="t1">{n} entreprises inscrites, tous secteurs</p><h3>Qualité des dossiers</h3></div></div>'
                     f'{_radial(comptes / n if n else 0, f"{comptes} / {n}", "avec comptes")}{rws}</section>')


def ratios(m):
    n, tick = m['n_entreprises'], m['total_tickets']
    prof = m['profondeur_pct']
    r1 = (f'<section class="rt6"><div class="hd"><span class="ico">{ic("jauge", 16)}</span><p class="k">Profondeur</p></div><span class="v">{_fr(prof)} %</span>'
          f'<div class="sc6"><span class="tk"></span><span class="fl" style="width:{prof}%"></span><span class="lb" style="left:0">recherché {_md(tick)} Md</span>'
          f'<span class="lb" style="right:0">cible 11 Md</span></div><p>Montants recherchés par les entreprises inscrites, face au milieu de la cible de capital à 36 mois.</p>'
          '<p class="so">Le marché est encore étroit : peu de concurrence.</p></section>')
    pos = lambda v: max(0, min(100, (v - 1.0) / 0.5 * 100))
    vals = m['dscr']
    pts = ''.join(f'<span class="pt{" on" if i == 0 else (" lo" if v < 1.2 else "")}" style="left:{pos(v):.0f}%" tabindex="0"><span class="tipc">{_fr(v, 2)}</span></span>' for i, v in enumerate(vals))
    texte = (f'<b>{len(vals)} entreprises sur {n}</b> ont une couverture calculée ; la plus documentée affiche {_fr(vals[0], 2)} en année 1, indicatif, avant examen du comité.'
             if vals else 'Aucune couverture de la dette calculée pour l’instant.')
    r2 = (f'<section class="rt6"><div class="hd"><span class="ico">{ic("balance", 16)}</span><p class="k">Porte dette</p></div><span class="v">1,2<small>seuil d’entrée</small></span>'
          f'<div class="sc6"><span class="tk"></span><span class="thr" style="left:{pos(1.2):.0f}%"><span>1,2</span></span>{pts}<span class="lb" style="left:0">1,0</span><span class="lb" style="right:0">1,5</span></div>'
          f'<p>{texte}</p><p class="so">{m["dscr_sous_seuil"]} sous le seuil.</p></section>')
    t = sorted(m['tickets_liste'], reverse=True)
    cols = ['#5536E8', '#8B78F0', 'var(--creux)']
    segs = [t[0] if t else 0, t[1] if len(t) > 1 else 0, sum(t[2:])]
    acc, arcs = 0, ''
    for i, v in enumerate(segs):
        f = v / tick * 100 if tick else 0
        if f:
            arcs += (f'<circle cx="36" cy="36" r="27" fill="none" stroke="{cols[i]}" stroke-width="11" pathLength="100" stroke-dasharray="{max(f - 1, .5):.1f} 100" '
                     f'stroke-dashoffset="{-acc:.1f}" transform="rotate(-90 36 36)"/>')
        acc += f
    r3 = (f'<section class="rt6"><div class="hd"><span class="ico">{ic("pile", 16)}</span><p class="k">Concentration</p></div>'
          f'<div class="dn6"><svg width="72" height="72" viewBox="0 0 72 72" role="img" aria-label="Part des deux plus gros montants">{arcs}</svg>'
          f'<div><span class="v">{m["concentration_pct"]} %</span><ul style="margin-top:6px"><li><i style="background:{cols[0]}"></i>1er montant</li>'
          f'<li><i style="background:{cols[1]}"></i>2e montant</li><li><i style="background:{cols[2]}"></i>{max(len(t) - 2, 0)} autres</li></ul></div></div>'
          f'<p>Les deux plus gros montants : {_m(sum(t[:2]))} sur {_m(tick)}.</p><p class="so">Part des deux plus gros dossiers dans le total.</p></section>')
    r4 = (f'<section class="rt6"><div class="hd"><span class="ico">{ic("cible", 16)}</span><p class="k">Compatibilité</p></div><span class="v">≥ {SEUIL_COMPAT}</span>'
          f'<div class="sc6"><span class="tk"></span><span class="thr" style="left:{SEUIL_COMPAT}%"><span>{SEUIL_COMPAT}</span></span><span class="lb" style="left:0">0</span><span class="lb" style="right:0">100</span></div>'
          '<p>Calculée après votre inscription, selon votre thèse : secteur, ticket, zone, stade, instrument.</p><p class="so">Pas une probabilité de closing.</p></section>')
    r5 = (f'<section class="rt6"><div class="hd"><span class="ico">{ic("sortie", 16)}</span><p class="k">Suite</p></div><span class="v">{m["sorties_ecrites"]} / {n}</span>'
          f'<div class="ex6" aria-hidden="true">{"".join("<i>?</i>" for _ in range(min(n, 8)))}</div><p>entreprises avec une sortie écrite.</p>'
          '<p class="so">Pas de tour de table sans sortie écrite.</p></section>')
    return mark_safe(f'<div class="rat6">{r1}{r2}{r3}{r4}{r5}</div>')


def composants(m):
    return {'hero': hero(m), 'ck': ck(m), 'ratios': ratios(m)}
