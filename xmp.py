'''Fichier de réglages XMP à côté du RAW d'origine : Lightroom / Camera Raw l'appliquent
(recadrage, exposition, teinte, netteté) sans toucher au RAW.'''
from pathlib import Path

ECHELLE_TEMPERATURE = 2.5      # écart bleu/jaune (b) -> IncrementalTemperature (approximation)
ECHELLE_TEINTE = 2.0           # écart vert/magenta (a) -> IncrementalTint (approximation)


def contenu(r):
    x0, y0, x1, y1 = (min(max(float(v), 0.0), 1.0) for v in r['cadre'])
    netteté = int(round(min(150, max(0, 40 + 40 * float(r['nettete'])))))
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
    crs:Exposure2012="{float(r['ev']):+.2f}"
    crs:IncrementalTemperature="{int(round(float(r['db']) * ECHELLE_TEMPERATURE))}"
    crs:IncrementalTint="{int(round(float(r['da']) * ECHELLE_TEINTE))}"
    crs:Sharpness="{netteté}"/>
 </rdf:RDF>
</x:xmpmeta>
<?xpacket end="w"?>
'''


def ecrire(raw_copie, r):
    '''Écrit nom_du_raw.xmp à côté de la copie du RAW. Retourne le chemin.'''
    chemin = Path(raw_copie).with_suffix('.xmp')
    chemin.write_text(contenu(r), encoding='utf-8')
    return chemin
