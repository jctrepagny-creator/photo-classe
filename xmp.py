'''Fichier XMP à côté du RAW d'origine : Lightroom / Camera Raw appliquent le RECADRAGE sans toucher
au RAW. (Exposition et couleurs ne sont pas écrites : elles ne sont pas comparables au rendu de Lightroom.)'''
from pathlib import Path

from lecture_raw import _orientation


def vers_repere_capteur(cadre, o):
    '''Convertit un cadre (x0, y0, x1, y1), exprimé en fractions de la photo REDRESSÉE (celle que
    voit l'application), vers l'image telle qu'elle est enregistrée dans le fichier (non tournée).
    Lightroom lit les valeurs Crop* du XMP dans ce repère-là : sans cette conversion, une photo
    prise en portrait (orientation EXIF 6 ou 8) est recadrée au mauvais endroit.
    o = orientation EXIF (1 à 8), mêmes conventions que lecture_raw._redresser.'''
    x0, y0, x1, y1 = cadre
    if o == 2:
        pts = [(1 - x0, y0), (1 - x1, y1)]
    elif o == 3:
        pts = [(1 - x0, 1 - y0), (1 - x1, 1 - y1)]
    elif o == 4:
        pts = [(x0, 1 - y0), (x1, 1 - y1)]
    elif o == 5:
        pts = [(y0, x0), (y1, x1)]
    elif o == 6:                                   # photo tournée de 90° vers la droite
        pts = [(y0, 1 - x0), (y1, 1 - x1)]
    elif o == 7:
        pts = [(1 - y0, 1 - x0), (1 - y1, 1 - x1)]
    elif o == 8:                                   # photo tournée de 90° vers la gauche (Nikon Z8...)
        pts = [(1 - y0, x0), (1 - y1, x1)]
    else:
        return x0, y0, x1, y1
    (ua, va), (ub, vb) = pts
    return min(ua, ub), min(va, vb), max(ua, ub), max(va, vb)


def contenu(r, orientation=1):
    x0, y0, x1, y1 = vers_repere_capteur(
        [min(max(float(v), 0.0), 1.0) for v in r['cadre']], orientation)
    return f'''<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
    crs:Version="15.0"
    crs:ProcessVersion="11.0"
    crs:HasSettings="True"
    crs:AlreadyApplied="False"
    crs:HasCrop="True"
    crs:CropConstrainToWarp="0"
    crs:CropLeft="{x0:.6f}"
    crs:CropTop="{y0:.6f}"
    crs:CropRight="{x1:.6f}"
    crs:CropBottom="{y1:.6f}"
    crs:CropAngle="0"
    crs:CropConstrainToUnitSquare="1"/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
'''


def ecrire(raw_copie, r):
    '''Écrit nom_du_raw.xmp à côté de la copie du RAW. Retourne le chemin.'''
    chemin = Path(raw_copie).with_suffix('.xmp')
    chemin.write_text(contenu(r, _orientation(raw_copie)), encoding='utf-8')
    return chemin
