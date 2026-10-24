'''Apprentissage à partir des paires avant (RAW) / après (image retouchée).

Organisation du dossier d'exemples (gérée par l'application, page « Exemples ») :
    avant/IMG_0001.CR2   (le RAW d'origine)
    apres/IMG_0001.jpg   (la même photo retouchée par vous, même nom)
'''
import json
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

import corrections
from chemins import dossier_donnees
from detection_visages import boite_groupe, detecter_visages
from ia_style import StyleIA, extraire_caracteristiques
from lecture_raw import EXT_IMAGES, EXT_TOUT, charger_raw
from traitement_image import (vers_float, vers_uint8, miniature, appliquer_cadrage,
                              luminance_lineaire, lab_moyen, nettete_mesure)

MIN_PAIRES = 5
POIDS_CORRECTION = 5.0          # une correction manuelle compte 5 fois plus qu'une paire
VERSION_CACHE = 4


class ErreurApp(Exception):
    '''Erreur destinée à l'utilisateur : `cle` est une clé de traduction (i18n).'''

    def __init__(self, cle, **params):
        super().__init__(cle)
        self.cle = cle
        self.params = params


def lister_paires(dossier):
    '''Retourne (paires, sans_apres, sans_avant) d'après les noms de fichiers.
    paires : liste de (raw, retouchee) ; les autres : listes de fichiers sans correspondant.'''
    dossier = Path(dossier)

    def _lire(sous, extensions):
        d = dossier / sous
        if not d.is_dir():
            return {}
        return {p.stem.lower(): p for p in sorted(d.iterdir())
                if p.is_file() and p.suffix.lower() in extensions and not p.name.startswith('.')}

    avant, apres = _lire('avant', EXT_TOUT), _lire('apres', EXT_IMAGES)
    paires = [(avant[k], apres[k]) for k in sorted(avant) if k in apres]
    sans_apres = [avant[k] for k in sorted(avant) if k not in apres]
    sans_avant = [apres[k] for k in sorted(apres) if k not in avant]
    return paires, sans_apres, sans_avant


def _chemin_info(chemin_modele):
    return Path(chemin_modele).with_suffix('.json')


def info_modele(chemin_modele):
    '''Retourne {'date': ..., 'paires': ...} si un modèle existe, sinon None.'''
    chemin_modele = Path(chemin_modele)
    if not chemin_modele.exists():
        return None
    try:
        return json.loads(_chemin_info(chemin_modele).read_text(encoding='utf-8'))
    except Exception:
        date = datetime.fromtimestamp(chemin_modele.stat().st_mtime).isoformat(timespec='seconds')
        return {'date': date, 'paires': None}


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


def _fichier_cache():
    return dossier_donnees() / 'cache_exemples.json'


def _lire_cache():
    try:
        donnees = json.loads(_fichier_cache().read_text(encoding='utf-8'))
        return donnees['paires'] if donnees.get('version') == VERSION_CACHE else {}
    except Exception:
        return {}


def _cle(raw, retouche):
    a, b = Path(raw).stat(), Path(retouche).stat()
    return f'{raw}|{a.st_size}|{a.st_mtime_ns}|{retouche}|{b.st_size}|{b.st_mtime_ns}'


def chemin_precedent(chemin_modele):
    return Path(chemin_modele).with_suffix('.precedent.pt')


def restaurer_precedent(chemin_modele):
    '''Revient au modèle d'avant le dernier entraînement. Retourne True si c'est fait.'''
    chemin_modele = Path(chemin_modele)
    ancien = chemin_precedent(chemin_modele)
    if not ancien.exists():
        return False
    shutil.copy2(ancien, chemin_modele)
    info = ancien.with_suffix('.json')
    if info.exists():
        shutil.copy2(info, _chemin_info(chemin_modele))
    return True


def entrainer_depuis_exemples(dossier_exemples, chemin_modele, rappel=None):
    '''rappel(i, n, statut, nom, detail) avec statut 'ok', 'ignore' ou 'fin'.
    Utilise les paires avant/après ET les corrections manuelles enregistrées.
    Lève ErreurApp si les exemples sont insuffisants.'''
    def _rappel(*args):
        if rappel:
            rappel(*args)

    paires, _, _ = lister_paires(dossier_exemples)
    toutes_corrections = corrections.lire()
    if not paires and not toutes_corrections:
        raise ErreurApp('err_aucune_paire')
    n = len(paires)
    cache, nouveau_cache = _lire_cache(), {}
    X, Y, poids, ignorees = [], [], [], 0
    for i, (raw, retouche) in enumerate(paires, 1):
        try:
            cle = _cle(raw, retouche)
            if cle in cache:                               # déjà analysée : pas de nouveau décodage
                x, y = cache[cle]['x'], cache[cle]['y']
            else:
                f_avant = vers_float(charger_raw(raw))
                f_apres = lire_image(retouche)
                cadre = trouver_cadre(f_avant, f_apres)
                if cadre is None:
                    ignorees += 1
                    _rappel(i, n, 'ignore', raw.name, 'cadrage')
                    continue
                cibles = reglages_cibles(f_avant, f_apres, cadre)
                visages = detecter_visages(vers_uint8(miniature(f_avant, 768)))
                x = [float(v) for v in extraire_caracteristiques(miniature(f_avant, 256), visages)]
                b0, b1, b2, b3 = boite_groupe(visages) or (0.0, 0.0, 1.0, 1.0)
                lw, lh = max(b2 - b0, 1e-3), max(b3 - b1, 1e-3)
                relatif = [(cadre[0] - b0) / lw, (cadre[1] - b1) / lh,
                           (cadre[2] - b0) / lw, (cadre[3] - b1) / lh]
                y = [float(v) for v in cibles + relatif]
            nouveau_cache[cle] = {'x': x, 'y': y}
            X.append(x)
            Y.append(y)
            poids.append(1.0)
            _rappel(i, n, 'ok', raw.name, '')
        except Exception as e:
            ignorees += 1
            _rappel(i, n, 'ignore', raw.name, str(e))
    try:
        _fichier_cache().write_text(json.dumps({'version': VERSION_CACHE, 'paires': nouveau_cache}),
                                    encoding='utf-8')
    except OSError:
        pass
    n_paires = len(X)
    for rec in toutes_corrections.values():                # ce que vous avez décidé après coup
        x, y = corrections.vers_exemple(rec)
        X.append(x)
        Y.append(y)
        poids.append(POIDS_CORRECTION)
    if len(X) < MIN_PAIRES:
        raise ErreurApp('err_pas_assez_paires', n=len(X), minimum=MIN_PAIRES)
    ia = StyleIA()
    ia.entrainer(X, Y, poids)
    chemin_modele = Path(chemin_modele)
    chemin_modele.parent.mkdir(parents=True, exist_ok=True)
    if chemin_modele.exists():                             # on garde l'ancien modèle en secours
        shutil.copy2(chemin_modele, chemin_precedent(chemin_modele))
        if _chemin_info(chemin_modele).exists():
            shutil.copy2(_chemin_info(chemin_modele), chemin_precedent(chemin_modele).with_suffix('.json'))
    ia.sauver(chemin_modele)
    info = {'date': datetime.now().isoformat(timespec='seconds'), 'paires': n_paires,
            'corrections': len(toutes_corrections), 'ignorees': ignorees}
    _chemin_info(chemin_modele).write_text(json.dumps(info), encoding='utf-8')
    _rappel(n, n, 'fin', '', str(len(X)))
    return len(X)
