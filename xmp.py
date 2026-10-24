'''Fichier XMP à côté du RAW d'origine : Lightroom / Camera Raw appliquent le RECADRAGE sans toucher
au RAW. (Exposition et couleurs ne sont pas écrites : elles ne sont pas comparables au rendu de Lightroom.)'''
from pathlib import Path



def contenu(r):
    x0, y0, x1, y1 = (min(max(float(v), 0.0), 1.0) for v in r['cadre'])
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
    chemin.write_text(contenu(r), encoding='utf-8')
    return chemin
