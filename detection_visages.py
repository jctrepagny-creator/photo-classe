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
