"""Indice de compatibilité : 6 critères, 100 points, une raison écrite par critère.
Ce n’est jamais une probabilité de closing."""

SEUIL_AFFICHAGE = 55


def compatibilite(these, org):
    profil = getattr(org, 'profil_pme', None)
    lignes = []

    secteurs = set(these.secteurs.values_list('id', flat=True)) if these else set()
    if not secteurs:
        lignes.append(('Secteur', 15, 25, 'Thèse ouverte à tous les secteurs'))
    elif org.secteur_id in secteurs:
        lignes.append(('Secteur', 25, 25, f'{org.secteur} fait partie de votre thèse'))
    else:
        lignes.append(('Secteur', 0, 25, 'Secteur hors de votre thèse'))

    ticket = profil.ticket_recherche if profil else None
    if not ticket or not these or (not these.ticket_min and not these.ticket_max):
        lignes.append(('Ticket', 10, 20, 'Montant ou fourchette non renseigné'))
    else:
        lo, hi = these.ticket_min or 0, these.ticket_max or ticket
        if lo <= ticket <= hi:
            lignes.append(('Ticket', 20, 20, 'Montant dans votre fourchette'))
        elif ticket < lo * 0.8 or ticket > hi * 1.25:
            lignes.append(('Ticket', 0, 20, 'Montant loin de votre fourchette'))
        else:
            lignes.append(('Ticket', 12, 20, 'Montant proche de votre fourchette'))

    zones = [z.lower() for z in (these.zones if these else [])]
    if not zones:
        lignes.append(('Zone', 10, 15, 'Zone non précisée'))
    elif org.region.lower() in zones or org.pays.lower() in zones or 'cemac' in zones:
        lignes.append(('Zone', 15, 15, f'{org.region or org.pays} dans votre zone'))
    else:
        lignes.append(('Zone', 0, 15, 'Hors de votre zone'))

    stades = these.stades if these else []
    stade = profil.stade if profil else ''
    if not stades or not stade:
        lignes.append(('Stade', 8, 15, 'Stade non renseigné'))
    else:
        lignes.append(('Stade', 15, 15, 'Stade compatible') if stade in stades else ('Stade', 0, 15, 'Stade hors thèse'))

    instruments = these.instruments if these else []
    instr = profil.instrument_souhaite if profil else ''
    if not instruments or not instr:
        lignes.append(('Instrument', 8, 15, 'Instrument non renseigné'))
    elif instr in instruments or instr == 'mixte' or 'mixte' in instruments:
        lignes.append(('Instrument', 15, 15, 'Instrument compatible'))
    else:
        lignes.append(('Instrument', 0, 15, 'Instrument différent'))

    esg = org.pieces.filter(dossier='09').exists()
    if these and these.exigence_esg:
        lignes.append(('ESG', 10 if esg else 3, 10, 'Politique ESG fournie' if esg else 'Politique ESG à fournir'))
    else:
        lignes.append(('ESG', 10 if esg else 6, 10, 'Pas d’exigence ESG' if not esg else 'Politique ESG fournie'))

    total = sum(l[1] for l in lignes)
    return {'total': total, 'lignes': lignes, 'visible': total >= SEUIL_AFFICHAGE}
