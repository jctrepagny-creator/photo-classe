'''Chaîne complète : RAW -> analyse -> IA -> retouche -> export.'''
import shutil
from pathlib import Path

import cv2

from detection_visages import detecter_visages
from ia_style import extraire_caracteristiques
from lecture_raw import charger_raw
from traitement_image import (vers_float, vers_uint8, vers_uint16, miniature,
                              appliquer_cadrage, appliquer_reglages)

EXT_RAW = {'.cr2', '.cr3', '.nef', '.nrw', '.arw', '.dng', '.orf', '.rw2', '.raf',
           '.pef', '.srw', '.iiq', '.3fr', '.erf', '.kdc', '.mrw', '.x3f'}


def lister_raw(dossier):
    return sorted(p for p in Path(dossier).rglob('*') if p.suffix.lower() in EXT_RAW)


def analyser(f, ia):
    '''Réglages propres à CETTE photo (jamais un réglage global pour le lot).'''
    visages = detecter_visages(vers_uint8(miniature(f, 768)))
    return ia.predire(extraire_caracteristiques(miniature(f, 256), visages))


def rendu(f, r):
    zone = appliquer_cadrage(f, r['cadre'])
    return appliquer_reglages(zone, r['ev'], r['da'], r['db'], r['nettete'])


def exporter(img, base, config):
    '''Écrit le fichier final. base = chemin sans extension.'''
    if config.format_sortie == 'TIFF':
        ext, data, params = '.tif', vers_uint16(img), []
    else:
        ext, data = '.jpg', vers_uint8(img)
        params = [cv2.IMWRITE_JPEG_QUALITY, int(config.qualite_jpeg)]
    ok, tampon = cv2.imencode(ext, cv2.cvtColor(data, cv2.COLOR_RGB2BGR), params)
    if not ok:
        raise RuntimeError('Encodage impossible')
    chemin = Path(str(base) + ext)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tampon.tofile(str(chemin))
    return chemin


def traiter_lot(config, ia, progression, valider=None, arret=None):
    '''progression(i, n, message).
    valider(mini, reglages) -> reglages modifiés, None (ignorer) ou 'STOP'.
    Les photos déjà traitées sont sautées : on peut relancer après une coupure.
    Les fichiers d'origine ne sont jamais supprimés.'''
    entree, sortie = Path(config.dossier_entree), Path(config.dossier_sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    journal = sortie / 'journal.txt'
    fichiers = lister_raw(entree)
    n = len(fichiers)
    ext = '.tif' if config.format_sortie == 'TIFF' else '.jpg'
    for i, raw in enumerate(fichiers, 1):
        if arret is not None and arret.is_set():
            progression(i - 1, n, 'Arrêt demandé')
            break
        relatif = raw.relative_to(entree)
        nom = (config.modele_renommage.format(index=i, original=raw.stem)
               if config.renommer_fichiers else raw.stem)
        base = sortie / relatif.parent / nom
        if Path(str(base) + ext).exists():
            progression(i, n, f'Déjà traité : {raw.name}')
            continue
        try:
            f = vers_float(charger_raw(raw))
            r = analyser(f, ia)
            if not config.mode_automatique and valider is not None:
                rep = valider(miniature(f, 900), r)
                if isinstance(rep, str) and rep == 'STOP':
                    progression(i - 1, n, 'Arrêt demandé')
                    break
                if rep is None:
                    progression(i, n, f'Ignorée : {raw.name}')
                    continue
                r = rep
            exporter(rendu(f, r), base, config)
            if config.conserver_raw:
                dest = sortie / 'originaux_raw' / relatif
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(raw, dest)
            progression(i, n, f'Terminé : {raw.name}')
        except Exception as e:
            with open(journal, 'a', encoding='utf-8') as j:
                j.write(f'{raw} : {e}\n')
            progression(i, n, f'Erreur sur {raw.name} : {e}')
