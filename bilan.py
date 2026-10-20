'''Chiffres affichés sur le tableau de bord et liste des photos produites.'''
import os
from datetime import datetime
from pathlib import Path

from pipeline import DOSSIER_RAW, FICHIER_ERREURS, lire_suivi

EXT_SORTIE = {'.jpg', '.jpeg', '.tif', '.tiff'}


def lister_sorties(sortie):
    '''Toutes les photos produites, de la plus récente à la plus ancienne.'''
    sortie = Path(sortie)
    trouvees = []
    if not sortie.is_dir():
        return []
    for racine, dossiers, fichiers in os.walk(sortie):
        dossiers[:] = [d for d in dossiers if d != DOSSIER_RAW]
        for nom in fichiers:
            if nom.startswith('.') or Path(nom).suffix.lower() not in EXT_SORTIE:
                continue
            p = Path(racine) / nom
            try:
                trouvees.append((p.stat().st_mtime, p))
            except OSError:
                continue
    trouvees.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in trouvees]


def nb_traitees(sortie):
    return len(lire_suivi(sortie))


def nb_erreurs(sortie):
    chemin = Path(sortie) / FICHIER_ERREURS
    try:
        with open(chemin, encoding='utf-8') as f:
            return sum(1 for ligne in f if ligne.strip())
    except OSError:
        return 0


def date_fichier(chemin):
    try:
        return datetime.fromtimestamp(Path(chemin).stat().st_mtime)
    except OSError:
        return None


def format_duree(secondes):
    '''« 2 h 15 min », « 12 min », « 40 s ».'''
    secondes = int(max(0, secondes))
    h, reste = divmod(secondes, 3600)
    m, s = divmod(reste, 60)
    if h:
        return f'{h} h {m:02d} min'
    if m:
        return f'{m} min'
    return f'{s} s'


def format_date(iso):
    '''Date ISO -> « 19/10/2026 à 08:34 ».'''
    try:
        d = datetime.fromisoformat(iso)
        return f'{d:%d/%m/%Y} {d:%H:%M}'
    except Exception:
        return ''
