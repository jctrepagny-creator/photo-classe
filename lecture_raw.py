"""Lecture des photos : RAW de toutes marques (Canon, Nikon, Sony, Fuji, Olympus, Panasonic,
Pentax, Leica, Hasselblad, Phase One...) et images JPEG / TIFF / PNG."""
import struct
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


def _orientation_depuis(tete, debut):
    e = '<' if tete[debut:debut + 2] == b'II' else '>'
    if struct.unpack(e + 'H', tete[debut + 2:debut + 4])[0] != 42:
        return None
    pos = debut + struct.unpack(e + 'I', tete[debut + 4:debut + 8])[0]
    n = struct.unpack(e + 'H', tete[pos:pos + 2])[0]
    for i in range(min(n, 200)):
        ent = tete[pos + 2 + 12 * i: pos + 14 + 12 * i]
        if struct.unpack(e + 'H', ent[:2])[0] == 274:
            v = struct.unpack(e + 'H', ent[8:10])[0]
            return v if 1 <= v <= 8 else 1
    return None


def _orientation(chemin):
    """Sens de prise de vue (balise EXIF 274) : 1 = normal, 6 = portrait...
    NEF/ARW/DNG : en-tête TIFF au début du fichier. CR3 : bloc EXIF enfoui plus loin."""
    try:
        with open(chemin, 'rb') as f:
            tete = f.read(1 << 20)
        if tete[:2] in (b'II', b'MM'):
            v = _orientation_depuis(tete, 0)
            if v:
                return v
        for marque in (b'II*\x00', b'MM\x00*'):
            pos = tete.find(marque)
            while 0 <= pos < len(tete) - 16:
                try:
                    v = _orientation_depuis(tete, pos)
                except Exception:
                    v = None
                if v:
                    return v
                pos = tete.find(marque, pos + 4)
    except Exception:
        pass
    return 1


def _redresser(img, o):
    if o == 2:
        return np.fliplr(img)
    if o == 3:
        return np.rot90(img, 2)
    if o == 4:
        return np.flipud(img)
    if o == 5:
        return np.transpose(img, (1, 0, 2))
    if o == 6:
        return np.rot90(img, -1)
    if o == 7:
        return np.rot90(np.transpose(img, (1, 0, 2)), 2)
    if o == 8:
        return np.rot90(img, 1)
    return img


def _apercu_integre(chemin):
    """Plan B : la plupart des RAW (NEF, CR3, ARW...) contiennent un grand JPEG d'aperçu.
    On prend le plus grand JPEG lisible du fichier (utile pour les appareils dont le format
    n'est pas encore géré par le décodeur RAW, comme le NEF « haute efficacité » du Z 8)."""
    data = Path(chemin).read_bytes()
    meilleur, surface = None, 0
    debut, essais = 0, 0
    while essais < 12:
        pos = data.find(b'\xff\xd8\xff', debut)
        if pos < 0:
            break
        debut = pos + 3
        essais += 1
        img = cv2.imdecode(np.frombuffer(data[pos:], dtype=np.uint8),
                           cv2.IMREAD_COLOR | cv2.IMREAD_IGNORE_ORIENTATION)
        if img is not None and img.shape[0] * img.shape[1] > surface:
            meilleur, surface = img, img.shape[0] * img.shape[1]
    if meilleur is None or surface < 500_000:      # moins d'un demi-mégapixel : trop petit
        raise ValueError('aperçu intégré introuvable')
    rgb = cv2.cvtColor(meilleur, cv2.COLOR_BGR2RGB).astype(np.uint16) * 257
    return np.ascontiguousarray(_redresser(rgb, _orientation(chemin)))


def _texte_erreur(e):
    m = e.args[0] if e.args else str(e)
    return m.decode('utf-8', 'replace') if isinstance(m, bytes) else str(m)


derniere_source = ''      # 'raw', 'apercu' ou 'image' : sert au journal de diagnostic


def charger_raw(chemin) -> np.ndarray:
    """Retourne une image RGB (uint16) : RAW décodé, sinon aperçu intégré, ou image ordinaire."""
    global derniere_source
    if Path(chemin).suffix.lower() in EXT_IMAGES:
        derniere_source = 'image'
        return _lire_image(chemin)
    import rawpy
    try:
        with rawpy.imread(str(chemin)) as raw:
            img = raw.postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=16)
        derniere_source = 'raw'
        return img
    except Exception as erreur_raw:
        for plan_b in (_apercu_integre, _lire_image):  # aperçu du RAW, puis image déguisée
            try:
                img = plan_b(chemin)
                if img.shape[0] * img.shape[1] >= 500_000:   # évite une simple vignette
                    derniere_source = 'apercu' if plan_b is _apercu_integre else 'image'
                    return img
            except Exception:
                pass
        raise ValueError(f"{_texte_erreur(erreur_raw)} ({Path(chemin).name})")
