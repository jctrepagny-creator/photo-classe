'''Écriture d'un fichier DNG « LinearRaw » : l'image TRAITÉE (recadrée, couleurs corrigées) dans un
conteneur RAW (.dng) que Lightroom / Camera Raw ouvrent comme un RAW. Aucune dépendance externe.'''
import struct
from pathlib import Path

import numpy as np

# XYZ (D50-adapté ignoré : D65) -> sRGB linéaire inversé = matrice « couleur de l'appareil » (primaires sRGB)
_XYZ_VERS_SRGB = [3.2404542, -1.5371385, -0.4985314,
                  -0.9692660, 1.8760108, 0.0415560,
                  0.0556434, -0.2040259, 1.0572252]


def _linearise(img):
    c = np.clip(img, 0.0, 1.0)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def ecrire(img, chemin, modele='Photo Classe'):
    '''img : float RGB 0..1 (sRGB). Écrit un DNG 16 bits linéaire.'''
    lin = _linearise(img)
    h, w = lin.shape[:2]
    data = np.ascontiguousarray((lin * 65535.0 + 0.5).astype('<u2'))
    donnees = data.tobytes()
    modele_b = modele.encode('ascii', 'replace') + b'\0'
    make_b = b'Photo Classe\0'
    matrice = [(int(round(v * 10000)), 10000) for v in _XYZ_VERS_SRGB]

    # blocs de données hors-entrée, placés après la table
    tags = []            # (tag, type, count, valeur_ou_bytes)
    def court(t, v): tags.append((t, 3, 1, struct.pack('<HH', v, 0)))
    def long_(t, v): tags.append((t, 4, 1, struct.pack('<I', v)))
    def octets(t, v): tags.append((t, 1, len(v), bytes(v) + b'\0' * (4 - len(v)) if len(v) <= 4 else bytes(v)))
    def ascii_(t, b): tags.append((t, 2, len(b), b))
    long_(254, 0)
    long_(256, w)
    long_(257, h)
    tags.append((258, 3, 3, struct.pack('<HHH', 16, 16, 16)))
    court(259, 1)
    court(262, 34892)
    ascii_(271, make_b)
    ascii_(272, modele_b)
    tags.append((273, 4, 1, None))          # StripOffsets : rempli plus bas
    court(274, 1)
    court(277, 3)
    long_(278, h)
    long_(279, len(donnees))
    court(284, 1)
    octets(50706, [1, 4, 0, 0])
    octets(50707, [1, 1, 0, 0])
    ascii_(50708, modele_b)
    tags.append((50721, 10, 9, b''.join(struct.pack('<ii', n, d) for n, d in matrice)))
    tags.append((50728, 5, 3, b''.join(struct.pack('<II', 1, 1) for _ in range(3))))
    court(50778, 21)
    tags.sort(key=lambda x: x[0])

    n = len(tags)
    debut_extra = 8 + 2 + 12 * n + 4
    extra, entrees = b'', []
    # d'abord on calcule la taille des blocs hors-entrée pour connaître l'offset de l'image
    def taille_inline(tag):
        return len(tag[3]) if tag[3] is not None else 4
    taille_extra = sum((len(t[3]) + (len(t[3]) & 1)) for t in tags if t[3] is not None and len(t[3]) > 4)
    offset_image = debut_extra + taille_extra
    offset_image += offset_image & 1
    for tag, typ, cnt, val in tags:
        if tag == 273:
            val = struct.pack('<I', offset_image)
        if len(val) <= 4:
            entrees.append(struct.pack('<HHI', tag, typ, cnt) + val.ljust(4, b'\0'))
        else:
            entrees.append(struct.pack('<HHII', tag, typ, cnt, debut_extra + len(extra)))
            extra += val + (b'\0' if len(val) & 1 else b'')
    sortie = b'II*\0' + struct.pack('<I', 8) + struct.pack('<H', n) + b''.join(entrees) + struct.pack('<I', 0)
    sortie += extra
    sortie += b'\0' * (offset_image - len(sortie))
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(sortie + donnees)
    return chemin
