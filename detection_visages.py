'''Détection des visages (MediaPipe si disponible, sinon OpenCV).
Une erreur de détection ne doit jamais interrompre un lot : on renvoie alors « aucun visage ».'''
import cv2
import numpy as np

_detecteur = None
_cascade = None


def _mediapipe():
    global _detecteur
    if _detecteur is None:
        import mediapipe as mp
        _detecteur = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.4)
    return _detecteur


def _haar(rgb8):
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gris = cv2.cvtColor(rgb8, cv2.COLOR_RGB2GRAY)
    h, w = gris.shape
    faces = _cascade.detectMultiScale(gris, 1.1, 5, minSize=(24, 24))
    return [(x / w, y / h, (x + fw) / w, (y + fh) / h) for (x, y, fw, fh) in faces]


def detecter_visages(rgb8):
    '''rgb8 : image uint8 RGB. Retourne une liste de boîtes (x0, y0, x1, y1) entre 0 et 1.'''
    try:
        res = _mediapipe().process(rgb8)
        boites = []
        for d in (res.detections or []):
            b = d.location_data.relative_bounding_box
            boites.append((max(0.0, b.xmin), max(0.0, b.ymin),
                           min(1.0, b.xmin + b.width), min(1.0, b.ymin + b.height)))
        return boites
    except Exception:
        pass
    try:
        return _haar(rgb8)
    except Exception:
        return []


def boite_groupe(visages):
    '''Boîte englobant tous les visages, ou None s'il n'y en a aucun.'''
    if not visages:
        return None
    a = np.array(visages, dtype=np.float32)
    return (float(a[:, 0].min()), float(a[:, 1].min()),
            float(a[:, 2].max()), float(a[:, 3].max()))


# --- Sommet de la tête (cheveux compris) -----------------------------------------------
_segmenteur = None


def _masque_mediapipe(rgb8):
    '''Masque « personne » (0-1) par segmentation MediaPipe.'''
    global _segmenteur
    if _segmenteur is None:
        import mediapipe as mp
        _segmenteur = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=0)
    m = _segmenteur.process(rgb8).segmentation_mask
    if m.shape[:2] != rgb8.shape[:2]:
        m = cv2.resize(m, (rgb8.shape[1], rgb8.shape[0]))
    return m


def _masque_grabcut(rgb8, boite):
    '''Plan B sans MediaPipe : GrabCut autour du visage (fond de studio uni).'''
    h0, w0 = rgb8.shape[:2]
    k = 400.0 / w0 if w0 > 400 else 1.0
    img = cv2.cvtColor(cv2.resize(rgb8, (int(w0 * k), int(h0 * k))) if k < 1 else rgb8, cv2.COLOR_RGB2BGR)
    h, w = img.shape[:2]
    x0, y0, x1, y1 = boite
    fw, fh = x1 - x0, y1 - y0
    masque = np.full((h, w), cv2.GC_BGD, np.uint8)
    xa, xb = int(max(0, x0 - 0.7 * fw) * w), int(min(1, x1 + 0.7 * fw) * w)
    ya = int(max(0, y0 - 1.0 * fh) * h)
    masque[ya:h, xa:xb] = cv2.GC_PR_FGD
    masque[int((y0 + 0.25 * fh) * h):int((y1 - 0.1 * fh) * h),
           int((x0 + 0.2 * fw) * w):int((x1 - 0.2 * fw) * w)] = cv2.GC_FGD
    masque[:, :int(0.04 * w)] = cv2.GC_BGD
    masque[:, int(0.96 * w):] = cv2.GC_BGD
    fond, premier = np.zeros((1, 65)), np.zeros((1, 65))
    cv2.grabCut(img, masque, None, fond, premier, 3, cv2.GC_INIT_WITH_MASK)
    return np.isin(masque, (cv2.GC_FGD, cv2.GC_PR_FGD)).astype(np.float32)


def _sommet(masque, boite):
    '''On remonte depuis le visage tant que la colonne centrale contient la personne.'''
    h, w = masque.shape[:2]
    x0, y0, x1, y1 = boite
    fw = x1 - x0
    a, b = int(max(0, x0 - 0.15 * fw) * w), max(int(min(1, x1 + 0.15 * fw) * w), 1)
    b = max(b, a + 1)
    y = int((y0 + 0.2 * (y1 - y0)) * h)
    if masque[y, a:b].mean() < 0.4:
        return None                      # le masque ne couvre pas le visage : on n'y croit pas
    haut, trous = y, 0
    while y > 0 and trous < max(3, h // 100):
        y -= 1
        if masque[y, a:b].mean() >= 0.15:
            haut, trous = y, 0
        else:
            trous += 1
    return haut / h


def haut_de_tete(rgb8, visages):
    '''Position (0 = haut de l'image, 1 = bas) du sommet de la tête, cheveux compris,
    ou None si on n'y arrive pas. Fonctionne pour une seule personne.'''
    boite = boite_groupe(visages)
    if boite is None:
        return None
    for fabrique in (lambda: _masque_mediapipe(rgb8), lambda: _masque_grabcut(rgb8, boite)):
        try:
            masque = fabrique()
            sommet = _sommet(masque > 0.5, boite)
            if sommet is not None and sommet < boite[1]:
                return float(sommet)
        except Exception:
            continue
    return None


def axe_du_visage(rgb8, boite):
    '''Position horizontale (0-1) de l'axe du visage : moyenne du milieu des yeux, du nez et
    de la bouche (MediaPipe). Sans MediaPipe : centre de la boîte du visage.'''
    centre = (boite[0] + boite[2]) / 2
    try:
        meilleur, ecart = None, 1.0
        for d in (_mediapipe().process(rgb8).detections or []):
            b = d.location_data.relative_bounding_box
            c = b.xmin + b.width / 2
            if abs(c - centre) < ecart and len(d.location_data.relative_keypoints) >= 4:
                kp = d.location_data.relative_keypoints
                meilleur, ecart = (((kp[0].x + kp[1].x) / 2) + kp[2].x + kp[3].x) / 3, abs(c - centre)
        if meilleur is not None and ecart < 0.1:
            return float(min(max(meilleur, 0.0), 1.0))
    except Exception:
        pass
    return float(centre)
