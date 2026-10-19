'''Opérations d'image : conversions, recadrage, retouche couleur, netteté.'''
import cv2
import numpy as np


def vers_float(img):
    '''Convertit une image uint8 ou uint16 en float32 entre 0 et 1.'''
    if img.dtype == np.uint16:
        return img.astype(np.float32) / 65535.0
    return img.astype(np.float32) / 255.0


def vers_uint8(f):
    return (np.clip(f, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def vers_uint16(f):
    return (np.clip(f, 0.0, 1.0) * 65535.0 + 0.5).astype(np.uint16)


def miniature(f, largeur):
    h, w = f.shape[:2]
    if w <= largeur:
        return f
    return cv2.resize(f, (largeur, max(1, round(h * largeur / w))),
                      interpolation=cv2.INTER_AREA)


def appliquer_cadrage(f, cadre):
    '''cadre = (x0, y0, x1, y1) entre 0 et 1.'''
    h, w = f.shape[:2]
    x0, y0, x1, y1 = cadre
    xa, xb = int(round(x0 * w)), int(round(x1 * w))
    ya, yb = int(round(y0 * h)), int(round(y1 * h))
    return np.ascontiguousarray(f[ya:yb, xa:xb])


def luminance_lineaire(f):
    lin = np.power(np.clip(f, 0.0, 1.0), 2.2)
    return float((0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]).mean())


def lab_moyen(f):
    lab = cv2.cvtColor(np.ascontiguousarray(f, dtype=np.float32), cv2.COLOR_RGB2LAB)
    return tuple(float(v) for v in lab.reshape(-1, 3).mean(axis=0))


def nettete_mesure(f):
    gris = cv2.cvtColor(np.ascontiguousarray(f, dtype=np.float32), cv2.COLOR_RGB2GRAY)
    return float(cv2.Laplacian(gris, cv2.CV_32F).var())


def appliquer_reglages(f, ev, da, db, nettete):
    '''Exposition (en EV, en lumière linéaire), décalage des canaux a et b de
    l'espace Lab (a : vert-magenta, b : bleu-jaune), puis netteté par masque flou.'''
    lin = np.power(np.clip(f, 0.0, 1.0), 2.2) * (2.0 ** ev)
    img = np.power(np.clip(lin, 0.0, 1.0), 1 / 2.2).astype(np.float32)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    lab[..., 1] += da
    lab[..., 2] += db
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    if nettete > 0.01:
        flou = cv2.GaussianBlur(img, (0, 0), 1.5)
        img = cv2.addWeighted(img, 1.0 + nettete, flou, -nettete, 0)
    return np.clip(img, 0.0, 1.0)
