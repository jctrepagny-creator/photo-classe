'''Correction manuelle d'une photo déjà traitée : on repart de l'ORIGINAL (RAW/JPEG),
on peut changer cadre, exposition, teinte et netteté, et on remplace le fichier produit.
La correction est mémorisée (proposition de l'IA + décision) pour réentraîner l'IA.'''
import os
from pathlib import Path

import corrections
import dng
import xmp
from detection_visages import detecter_visages
from entrainement import ErreurApp
from ia_style import StyleIA, extraire_caracteristiques
from lecture_raw import charger_raw
from pipeline import DOSSIER_RAW, _noter, analyser, ecrire_image, lire_suivi, rendu
from traitement_image import miniature, vers_float, vers_uint8

CLES = ('ev', 'da', 'db', 'nettete')


def trouver_enregistrement(sortie, chemin):
    '''Retrouve (original, réglages) d'une photo produite grâce au suivi. None si inconnue.'''
    cible = os.path.normcase(str(Path(chemin)))
    trouve = None
    for r in lire_suivi(sortie).values():
        if os.path.normcase(str(Path(r['sortie']))) == cible:
            trouve = r                      # le plus récent l'emporte (le suivi garde le dernier)
    return trouve


def _propre(r):
    out = {k: float(r[k]) for k in CLES}
    out['cadre'] = tuple(float(v) for v in r['cadre'])
    return out


def preparer(config, source, reglages):
    '''Charge l'original : grande miniature (pour l'aperçu en direct), réglages proposés par
    l'IA et mesures de la photo. `reglages` peut être None (anciens fichiers).'''
    if not Path(source).exists():
        raise ErreurApp('err_original_introuvable', fichier=str(source))
    f = vers_float(charger_raw(source))
    visages = detecter_visages(vers_uint8(miniature(f, 768)))
    carac = [float(v) for v in extraire_caracteristiques(miniature(f, 256), visages)]
    if reglages is None:
        ia = StyleIA.charger(config.modele_ia)
        reglages = analyser(f, ia, config.marge_haut / 100.0, config.marge_haut_photo, config.centrer_visage)
    return {'mini': miniature(f, 1100), 'reglages': _propre(reglages), 'dims': f.shape[:2],
            'carac': carac}


def enregistrer(config, source, propose, decide, chemin, carac, apprendre=True):
    '''Refait le rendu complet avec la décision et remplace le fichier produit.
    Si quelque chose a changé, la correction est mémorisée pour l'apprentissage.'''
    decide = _propre(decide)
    f = vers_float(charger_raw(source))
    img = rendu(f, decide)
    chemin = Path(chemin)
    ecrire_image(img, chemin, config.qualite_jpeg)
    if chemin.with_suffix('.dng').exists():
        dng.ecrire(img, chemin.with_suffix('.dng'))
    for ext in ('.jpg', '.tif'):                         # autres formats produits pour cette photo
        autre = chemin.with_suffix(ext)
        if autre != chemin and autre.exists():
            ecrire_image(img, autre, config.qualite_jpeg)
    if config.sortie_xmp:                                # met aussi à jour le XMP de Lightroom
        copie = next(iter((Path(config.dossier_sortie) / DOSSIER_RAW).rglob(Path(source).name)), None)
        if copie is not None:
            xmp.ecrire(copie, decide)
    _noter(config.dossier_sortie, source, Path(source).stat().st_size, chemin, decide)
    propose = _propre(propose)
    change = any(abs(decide[k] - propose[k]) > 1e-3 for k in CLES) or any(
        abs(a - b) > 5e-3 for a, b in zip(decide['cadre'], propose['cadre']))
    if change:
        corrections.enregistrer(source, carac, propose, decide, apprendre)
    return str(chemin)
