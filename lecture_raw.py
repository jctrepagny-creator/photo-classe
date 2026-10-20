"""Décodage des fichiers RAW, quelle que soit la marque de l'appareil."""
import numpy as np

# Formats RAW reconnus (extensions en minuscules)
EXT_RAW = {'.cr2', '.cr3', '.crw', '.nef', '.nrw', '.arw', '.srf', '.sr2', '.dng', '.orf',
           '.rw2', '.raf', '.pef', '.srw', '.iiq', '.3fr', '.erf', '.kdc', '.mrw', '.x3f',
           '.rwl', '.mef', '.mos', '.dcr'}

# Images retouchées acceptées comme « après »
EXT_IMAGES = {'.jpg', '.jpeg', '.tif', '.tiff', '.png'}


def charger_raw(chemin) -> np.ndarray:
    """Retourne une image RGB (uint16) décodée depuis un fichier RAW."""
    import rawpy
    with rawpy.imread(str(chemin)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=True,
            output_bps=16,
        )
    return rgb
