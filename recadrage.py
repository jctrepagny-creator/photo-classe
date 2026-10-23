'''Recadrage manuel d'une photo déjà traitée : on repart de l'ORIGINAL (RAW/JPEG)
avec les mêmes réglages de couleur, et on remplace le fichier produit.'''
import os
from pathlib import Path

from entrainement import ErreurApp
from ia_style import StyleIA
from lecture_raw import charger_raw
from pipeline import _noter, analyser, ecrire_image, lire_suivi, rendu
from traitement_image import appliquer_reglages, miniature, vers_float, vers_uint8

CLES = ('ev', 'da', 'db', 'nettete')


def trouver_enregistrement(sortie, chemin):
    '''Retrouve (original, réglages) d'une photo produite grâce au suivi. None si inconnue.'''
    cible = os.path.normcase(str(Path(chemin)))
    trouve = None
    for r in lire_suivi(sortie).values():
        if os.path.normcase(str(Path(r['sortie']))) == cible:
            trouve = r                      # le plus récent l'emporte (le suivi garde le dernier)
    return trouve


def preparer(config, source, reglages):
    '''Charge l'original et prépare un aperçu en couleurs (grande miniature).
    `reglages` peut être None (anciens fichiers) : l'IA les recalcule.'''
    if not Path(source).exists():
        raise ErreurApp('err_original_introuvable', fichier=str(source))
    f = vers_float(charger_raw(source))
    if reglages is None:
        ia = StyleIA.charger(config.modele_ia)
        reglages = analyser(f, ia, config.marge_haut / 100.0, config.marge_haut_photo, config.centrer_visage)
    r = {k: float(reglages[k]) for k in CLES}
    r['cadre'] = tuple(float(v) for v in reglages['cadre'])
    apercu = vers_uint8(appliquer_reglages(miniature(f, 1400), r['ev'], r['da'], r['db'], 0.0))
    return {'apercu': apercu, 'reglages': r, 'dims': f.shape[:2]}


def enregistrer(config, source, reglages, cadre, chemin):
    '''Refait le rendu complet avec le nouveau cadre et remplace le fichier produit.'''
    f = vers_float(charger_raw(source))
    r = dict(reglages)
    r['cadre'] = tuple(float(v) for v in cadre)
    ecrire_image(rendu(f, r), chemin, config.qualite_jpeg)
    _noter(config.dossier_sortie, source, Path(source).stat().st_size, chemin, r)
    return str(chemin)
