"""Décodage des fichiers RAW, quelle que soit la marque de l'appareil."""
import rawpy
import numpy as np


def charger_raw(chemin) -> np.ndarray:
    """Retourne une image RGB (uint16) décodée depuis un fichier RAW."""
    with rawpy.imread(str(chemin)) as raw:
        rgb = raw.postprocess(
            use_camera_wb=True,
            no_auto_bright=True,
            output_bps=16,
        )
    return rgb
