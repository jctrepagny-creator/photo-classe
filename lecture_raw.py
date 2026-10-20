"""Lecture des photos : RAW de toutes marques (Canon, Nikon, Sony, Fuji, Olympus, Panasonic,
Pentax, Leica, Hasselblad, Phase One...) et images JPEG / TIFF / PNG."""
from pathlib import Path

import cv2
import numpy as np

# Formats RAW reconnus (extensions en minuscules)
EXT_RAW = {'.cr2', '.cr3', '.crw', '.nef', '.nrw', '.arw', '.srf', '.sr2', '.dng', '.orf',
           '.rw2', '.raf', '.pef', '.ptx', '.srw', '.iiq', '.3fr', '.fff', '.erf', '.kdc',
           '.dcr', '.dcs', '.drf', '.k25', '.mrw', '.x3f', '.rwl', '.rwz', '.mef', '.mos',
           '.raw', '.rw1', '.cap', '.bay', '.cs1', '.gpr', '.arq', '.pxn', '.ori', '.mdc'}

# Images ordinaires (JPEG, TIFF, PNG) : acceptées en entrée comme en « après »
EXT_IMAGES = {'.jpg', '.jpeg', '.jpe', '.tif', '.tiff', '.png', '.bmp'}

# Tout ce que l'application sait ouvrir comme photo
EXT_TOUT = EXT_RAW | EXT_IMAGES

# Fichiers déposés à la main qu'on n'essaie jamais d'ouvrir
EXT_IGNOREES = {'.txt', '.pdf', '.zip', '.rar', '.7z', '.doc', '.docx', '.xls', '.xlsx', '.exe',
                '.db', '.ini', '.xmp', '.json', '.csv', '.html', '.htm', '.py', '.lnk', '.log',
                '.thm', '.mov', '.mp4', '.avi', '.dll', '.tmp', '.ds_store'}


def _lire_image(chemin):
    data = np.fromfile(str(chemin), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR | cv2.IMREAD_ANYDEPTH)
    if img is None:
        raise ValueError('Fichier illisible : ' + Path(chemin).name)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return (img.astype(np.uint16) * 257) if img.dtype == np.uint8 else img.astype(np.uint16)


def charger_raw(chemin) -> np.ndarray:
    """Retourne une image RGB (uint16) : RAW décodé, ou image ordinaire."""
    if Path(chemin).suffix.lower() in EXT_IMAGES:
        return _lire_image(chemin)
    try:
        import rawpy
        with rawpy.imread(str(chemin)) as raw:
            return raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=16)
    except Exception as erreur_raw:
        try:                                  # extension inconnue mais c'est peut-être une image
            return _lire_image(chemin)
        except Exception:
            raise erreur_raw
