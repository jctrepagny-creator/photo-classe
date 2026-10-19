'''Apprentissage à partir des paires avant (RAW) / après (image retouchée).

Organisation attendue du dossier d'exemples :
    exemples/avant/IMG_0001.CR2   (le RAW d'origine)
    exemples/apres/IMG_0001.jpg   (la même photo retouchée par vous, même nom)
'''
from pathlib import Path

import cv2
import numpy as np

from detection_visages import detecter_visages
from ia_style import StyleIA, extraire_caracteristiques
from lecture_raw import charger_raw
from traitement_image import (vers_float, vers_uint8, miniature, appliquer_cadrage,
                              luminance_lineaire, lab_moyen, nettete_mesure)

EXT_APRES = ('.jpg', '.jpeg', '.tif', '.tiff', '.png')


def lire_image(chemin):
    '''Lecture compatible avec les chemins Windows contenant des accents.'''
    data = np.fromfile(str(chemin), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR | cv2.IMREAD_ANYDEPTH)
    if img is None:
        raise ValueError(f'Image illisible : {chemin}')
    return vers_float(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def trouver_cadre(avant, apres):
    '''Retrouve où se situe l'image retouchée dans le RAW (points SIFT + similitude).
    Retourne (x0, y0, x1, y1) entre 0 et 1, ou None si le repérage échoue.'''
    ga = cv2.cvtColor(vers_uint8(miniature(avant, 1400)), cv2.COLOR_RGB2GRAY)
    gb = cv2.cvtColor(vers_uint8(miniature(apres, 1000)), cv2.COLOR_RGB2GRAY)
    sift = cv2.SIFT_create()
    ka, desc_a = sift.detectAndCompute(ga, None)
    kb, desc_b = sift.detectAndCompute(gb, None)
    if desc_a is None or desc_b is None or len(ka) < 20 or len(kb) < 20:
        return None
    paires = cv2.BFMatcher().knnMatch(desc_b, desc_a, k=2)
    bons = [p[0] for p in paires if len(p) == 2 and p[0].distance < 0.75 * p[1].distance]
    if len(bons) < 15:
        return None
    src = np.float32([kb[m.queryIdx].pt for m in bons]).reshape(-1, 1, 2)
    dst = np.float32([ka[m.trainIdx].pt for m in bons]).reshape(-1, 1, 2)
    M, masque = cv2.estimateAffinePartial2D(src, dst, method=cv2.RANSAC,
                                            ransacReprojThreshold=4.0)
    if M is None or int(masque.sum()) < 15:
        return None
    hb, wb = gb.shape
    coins = np.float32([[0, 0], [wb, 0], [wb, hb], [0, hb]]).reshape(-1, 1, 2)
    pts = cv2.transform(coins, M).reshape(-1, 2)
    ha, wa = ga.shape
    x0, y0 = np.clip(pts.min(axis=0) / [wa, ha], 0, 1)
    x1, y1 = np.clip(pts.max(axis=0) / [wa, ha], 0, 1)
    if x1 - x0 < 0.2 or y1 - y0 < 0.2:
        return None
    return float(x0), float(y0), float(x1), float(y1)


def reglages_cibles(avant, apres, cadre):
    '''Différences mesurées entre le RAW recadré et l'image retouchée.'''
    zone = miniature(appliquer_cadrage(avant, cadre), 512)
    cible = cv2.resize(apres, (zone.shape[1], zone.shape[0]), interpolation=cv2.INTER_AREA)
    ev = float(np.log2((luminance_lineaire(cible) + 1e-6) / (luminance_lineaire(zone) + 1e-6)))
    _, a_av, b_av = lab_moyen(zone)
    _, a_ap, b_ap = lab_moyen(cible)
    rapport = (nettete_mesure(cible) + 1e-6) / (nettete_mesure(zone) + 1e-6)
    nettete = float(np.clip((rapport - 1.0) * 0.5, 0.0, 2.0))
    return [ev, a_ap - a_av, b_ap - b_av, nettete]


def entrainer_depuis_exemples(dossier_exemples, chemin_modele, progression=print):
    dossier = Path(dossier_exemples)
    index = {p.stem: p for p in (dossier / 'apres').iterdir()
             if p.suffix.lower() in EXT_APRES}
    raws = sorted(p for p in (dossier / 'avant').iterdir() if p.is_file())
    X, Y = [], []
    for i, raw in enumerate(raws, 1):
        retouche = index.get(raw.stem)
        if retouche is None:
            continue
        try:
            f_avant = vers_float(charger_raw(raw))
            f_apres = lire_image(retouche)
            cadre = trouver_cadre(f_avant, f_apres)
            if cadre is None:
                progression(f'Paire ignorée (cadrage introuvable) : {raw.name}')
                continue
            cibles = reglages_cibles(f_avant, f_apres, cadre)
            visages = detecter_visages(vers_uint8(miniature(f_avant, 768)))
            X.append(extraire_caracteristiques(miniature(f_avant, 256), visages))
            Y.append(cibles + list(cadre))
            progression(f'Exemple appris {i}/{len(raws)} : {raw.name}')
        except Exception as e:
            progression(f'Paire ignorée ({e}) : {raw.name}')
    if len(X) < 5:
        raise RuntimeError(f'Seulement {len(X)} paires exploitables : il en faut au moins 5 '
                           '(idéalement 50 ou plus).')
    ia = StyleIA()
    ia.entrainer(X, Y)
    Path(chemin_modele).parent.mkdir(parents=True, exist_ok=True)
    ia.sauver(chemin_modele)
    progression(f'Entraînement terminé avec {len(X)} paires.')
    return len(X)
