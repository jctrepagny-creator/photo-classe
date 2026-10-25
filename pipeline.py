'''Chaîne complète : RAW -> analyse -> IA -> retouche -> export.

Les photos viennent d'une file d'attente : une liste de (fichier, racine) où `racine` est le
dossier déposé (None pour un fichier déposé seul). Le classement en sortie reprend cette
organisation : sortie / <dossier déposé> / <sous-dossiers>.'''
import corrections
import detection_visages
import json
import dng
import xmp
import re
import shutil
from datetime import datetime
from pathlib import Path

import cv2

from detection_visages import axe_du_visage, boite_groupe, detecter_visages, haut_de_tete
from entrainement import ErreurApp
from ia_style import extraire_caracteristiques
import lecture_raw
from lecture_raw import EXT_IGNOREES, EXT_TOUT, charger_raw
import numpy as np
from traitement_image import (vers_float, vers_uint8, vers_uint16, miniature,
                              appliquer_cadrage, appliquer_reglages)

FICHIER_SUIVI = '.traitees.jsonl'   # une ligne par photo terminée (reprise après coupure)
FICHIER_ERREURS = 'journal.txt'
FICHIER_REGLAGES = 'reglages.csv'
DOSSIER_RAW = 'originaux_raw'


# --- Constitution de la file d'attente ---------------------------------------
def collecter(chemins, extensions):
    '''Parcourt fichiers et dossiers (sous-dossiers compris). Retourne [(fichier, racine)].'''
    elements, vus = [], set()
    for c in map(Path, chemins):
        try:
            if c.is_dir():
                for f in sorted(c.rglob('*')):
                    if (f.is_file() and f.suffix.lower() in extensions
                            and not f.name.startswith(('.', '._')) and f not in vus):
                        vus.add(f)
                        elements.append((f, c))
            elif (c.is_file() and c not in vus and not c.name.startswith('.')
                  and (c.suffix.lower() in extensions or c.suffix.lower() not in EXT_IGNOREES)):
                # un fichier déposé à la main est tenté même si son extension est inconnue
                vus.add(c)
                elements.append((c, None))
        except OSError:
            continue
    return elements


def collecter_photos(chemins):
    return collecter(chemins, EXT_TOUT)


collecter_raw = collecter_photos


# --- Noms de fichiers ---------------------------------------------------------
def formater_nom(modele, index, original):
    '''Applique le modèle de nom ({index}, {original}). En cas de modèle invalide,
    garde le nom d'origine. Les caractères interdits par Windows sont remplacés.'''
    try:
        nom = modele.format(index=index, original=original)
    except (KeyError, IndexError, ValueError, AttributeError):
        nom = original
    nom = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', nom).strip(' .')
    return nom or original


def modele_valide(modele):
    try:
        modele.format(index=1, original='IMG')
        return True
    except (KeyError, IndexError, ValueError, AttributeError):
        return False


def _nom_dossier(racine):
    return racine.name or racine.drive.replace(':', '') or 'dossier'


def dossier_cible(sortie, fichier, racine):
    if racine is None:
        return Path(sortie)
    return Path(sortie) / _nom_dossier(racine) / fichier.parent.relative_to(racine)


def base_libre(base, ext):
    '''Évite d'écraser un fichier existant : IMG, IMG_2, IMG_3...'''
    base = Path(base)
    candidat, k = base, 2
    while Path(str(candidat) + ext).exists():
        candidat = base.with_name(f'{base.name}_{k}')
        k += 1
    return candidat


# --- Suivi des photos traitées (reprise) --------------------------------------
def lire_suivi(sortie):
    suivi = {}
    chemin = Path(sortie) / FICHIER_SUIVI
    if not chemin.exists():
        return suivi
    try:
        with open(chemin, encoding='utf-8') as f:
            for ligne in f:
                try:
                    r = json.loads(ligne)
                    suivi[r['src']] = r
                except Exception:
                    continue
    except OSError:
        pass
    return suivi


def verifier_sortie(sortie):
    '''Vérifie qu'on peut écrire dans le dossier de sortie (sinon erreur claire).'''
    sortie = Path(sortie)
    try:
        sortie.mkdir(parents=True, exist_ok=True)
        test = sortie / '.test_ecriture'
        test.write_text('ok')
        test.unlink()
    except OSError:
        raise ErreurApp('err_sortie_inaccessible', dossier=str(sortie))


def _noter(sortie, src, taille, resultat, reglages=None):
    try:
        with open(Path(sortie) / FICHIER_SUIVI, 'a', encoding='utf-8') as f:
            ligne = {'src': str(src), 'taille': taille, 'sortie': str(resultat),
                     'date': datetime.now().isoformat(timespec='seconds')}
            if reglages is not None:
                ligne['reglages'] = {k: (list(reglages[k]) if k == 'cadre' else float(reglages[k]))
                                     for k in ('ev', 'da', 'db', 'nettete', 'cadre')}
            f.write(json.dumps(ligne, ensure_ascii=False) + '\n')
    except OSError:
        pass          # un journal illisible ne doit jamais interrompre le lot


def _noter_erreur(sortie, raw, message):
    try:
        with open(Path(sortie) / FICHIER_ERREURS, 'a', encoding='utf-8') as j:
            j.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {raw} | {message}\n")
    except OSError:
        pass


# --- Traitement ----------------------------------------------------------------
def limiter_surexposition(f, cadre, ev, plafond=0.97):
    '''Empêche de « brûler » les blancs : l'exposition est réduite si les hautes lumières
    (97e centile) dépasseraient `plafond` après correction.'''
    zone = appliquer_cadrage(miniature(f, 256), cadre)
    lum = 0.2126 * zone[..., 0] + 0.7152 * zone[..., 1] + 0.0722 * zone[..., 2]
    haute = float(np.percentile(lum, 97)) ** 2.2
    if haute < 1e-4:
        return ev, False
    maxi = float(np.log2(plafond ** 2.2 / haute))
    return (maxi, True) if ev > maxi else (ev, False)


def _noter_reglages(sortie, nom, r):
    '''Une ligne par photo dans reglages.csv : sert à comprendre / corriger les résultats.'''
    chemin = Path(sortie) / FICHIER_REGLAGES
    try:
        nouveau = not chemin.exists()
        with open(chemin, 'a', encoding='utf-8') as f:
            if nouveau:
                f.write('fichier;source;ev;da;db;nettete;x0;y0;x1;y1;sommet;axe;ev_limite;visages;detection\n')
            c = r['cadre']
            f.write(';'.join(str(v) for v in (
                nom, lecture_raw.derniere_source, f"{r['ev']:.2f}", f"{r['da']:.1f}", f"{r['db']:.1f}",
                f"{r['nettete']:.2f}", *(f'{v:.3f}' for v in c), f"{r.get('sommet', -1):.3f}",
                f"{r.get('axe') if r.get('axe') is not None else -1:.3f}", int(r.get('ev_limite', False)), r.get('nb_visages', 0), detection_visages.diagnostic['methode'])) + '\n')
    except OSError:
        pass


def recentrer(cadre, axe):
    '''Décale le cadre (sans changer sa taille) pour que `axe` soit au milieu.'''
    x0, y0, x1, y1 = cadre
    nl = x1 - x0
    nx0 = min(max(axe - nl / 2, 0.0), 1.0 - nl)
    return (nx0, y0, nx0 + nl, y1)


def recadrer_sur_cheveux(cadre, sommet, marge, dims, axe=None):
    '''Place le haut du cadre pour que l'espace au-dessus des cheveux soit TOUJOURS le même
    fraction `marge` de la hauteur de la photo finale. Le format du cadre prévu est conservé.'''
    h, w = dims[:2]
    x0, y0, x1, y1 = cadre
    marge = min(max(marge, 0.0), 0.4)
    ny0 = max(0.0, (sommet - marge * y1) / (1.0 - marge))      # sommet - ny0 = marge * (y1 - ny0)
    if y1 - ny0 < 0.2 or sommet <= ny0 - 1e-9:
        return cadre
    format_px = ((x1 - x0) * w) / max((y1 - y0) * h, 1)
    nl = min(1.0, format_px * (y1 - ny0) * h / w)
    cx = axe if axe is not None else (x0 + x1) / 2
    nx0 = min(max(cx - nl / 2, 0.0), 1.0 - nl)
    return (nx0, ny0, nx0 + nl, y1)


def analyser(f, ia, marge_haut=0.6, marge_photo=6, centrer=True):
    '''Réglages propres à CETTE photo (jamais un réglage global pour le lot).'''
    mini = vers_uint8(miniature(f, 768))
    visages = detecter_visages(mini)
    nb_visages = len(visages)
    r = ia.predire(extraire_caracteristiques(miniature(f, 256), visages), marge_haut)
    if visages:
        if not centrer:
            axe = None
        elif len(visages) == 1:
            axe = axe_du_visage(mini, visages[0])
        else:
            b = boite_groupe(visages)               # plusieurs enfants : milieu du groupe
            axe = (b[0] + b[2]) / 2
        sommet = haut_de_tete(mini, visages) if marge_photo >= 0 else None
        if sommet is not None:
            r['cadre'] = recadrer_sur_cheveux(r['cadre'], sommet, marge_photo / 100.0, f.shape, axe)
            r['sommet'] = sommet
        elif axe is not None:
            r['cadre'] = recentrer(r['cadre'], axe)
        r['axe'] = axe
    r['nb_visages'] = nb_visages
    r['ev'], r['ev_limite'] = limiter_surexposition(f, r['cadre'], r['ev'])
    return r


def appliquer_mode_couleur(r, mode):
    '''1 : aucune correction · 2 : exposition seulement · 3 : exposition, teinte et netteté (IA).'''
    r = dict(r)
    if mode <= 1:
        r.update(ev=0.0, da=0.0, db=0.0, nettete=0.0)
        r['ev_limite'] = False
    elif mode == 2:
        r.update(da=0.0, db=0.0)
    return r


def rendu(f, r):
    zone = appliquer_cadrage(f, r['cadre'])
    return appliquer_reglages(zone, r['ev'], r['da'], r['db'], r['nettete'])


def ecrire_image(img, chemin, qualite=95):
    '''Écrit `img` (float RGB) au chemin exact ; le format suit l'extension (.tif = 16 bits).'''
    chemin = Path(chemin)
    if chemin.suffix.lower() in ('.tif', '.tiff'):
        data, params = vers_uint16(img), []
    else:
        data, params = vers_uint8(img), [cv2.IMWRITE_JPEG_QUALITY, int(qualite)]
    ok, tampon = cv2.imencode(chemin.suffix.lower(), cv2.cvtColor(data, cv2.COLOR_RGB2BGR), params)
    if not ok:
        raise RuntimeError('Encodage impossible')
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tampon.tofile(str(chemin))
    return chemin


def extensions_images(config):
    ext = []
    if config.sortie_jpeg:
        ext.append('.jpg')
    if config.sortie_tiff:
        ext.append('.tif')
    return ext


def exporter(img, base, config):
    '''Écrit les fichiers images cochés (JPEG et/ou TIFF). base = chemin sans extension.
    Retourne le chemin principal (le premier format coché).'''
    exts = extensions_images(config)
    principal = None
    if config.sortie_dng:
        principal = dng.ecrire(img, Path(str(base) + '.dng'))
    if not exts:
        exts = ['.jpg']                      # aperçu pour la galerie
    apercu = None
    for ext in exts:
        chemin = ecrire_image(img, Path(str(base) + ext), config.qualite_jpeg)
        apercu = apercu or chemin
    return apercu


def copier_raw(sortie, raw, racine):
    dest = (sortie / DOSSIER_RAW / raw.name if racine is None
            else sortie / DOSSIER_RAW / _nom_dossier(racine) / raw.relative_to(racine))
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(raw, dest)
    return dest


def ecrire_xmp(sortie, raw, racine, reglages):
    '''RAW d'origine copié + fichier XMP à côté (Lightroom / Camera Raw).'''
    return xmp.ecrire(copier_raw(Path(sortie), Path(raw), racine), reglages)


def traiter_lot(config, ia, elements, rappel, valider=None, arret=None):
    '''elements : [(fichier, racine)].
    rappel(i, n, statut, nom, detail) avec statut parmi :
      'debut', 'ok' (detail = fichier créé), 'saute' (déjà traitée), 'ignore' (écartée
      en mode manuel), 'erreur' (detail = message), 'stop'.
    valider(mini, reglages) -> réglages modifiés, None (ignorer) ou 'STOP'.
    Les photos déjà traitées sont sautées : on peut relancer après une coupure.
    Les fichiers d'origine ne sont jamais modifiés ni supprimés.'''
    sortie = Path(config.dossier_sortie)
    verifier_sortie(sortie)
    suivi = lire_suivi(sortie)
    n = len(elements)
    exts = extensions_images(config) + (['.dng'] if config.sortie_dng else [])
    exts = exts or ['.jpg']
    for i, (raw, racine) in enumerate(elements, 1):
        if arret is not None and arret.is_set():
            rappel(i - 1, n, 'stop', '', '')
            return
        try:
            taille = raw.stat().st_size
        except OSError as e:
            _noter_erreur(sortie, raw, str(e))
            rappel(i, n, 'erreur', raw.name, str(e))
            continue
        deja = suivi.get(str(raw))
        if (deja and not config.retraiter and deja.get('taille') == taille
                and Path(deja['sortie']).exists()):
            rappel(i, n, 'saute', raw.name, deja['sortie'])
            continue
        rappel(i - 1, n, 'debut', raw.name, '')
        try:
            f = vers_float(charger_raw(raw))
            r = analyser(f, ia, config.marge_haut / 100.0, config.marge_haut_photo,
                         config.centrer_visage)
            r = appliquer_mode_couleur(r, config.mode_couleur)
            decision = corrections.decision_pour(raw)      # déjà corrigée par vous : on garde votre choix
            if decision is not None:
                r = dict(r, **decision)
            _noter_reglages(sortie, raw.name, r)
            if not config.mode_automatique and valider is not None:
                rep = valider(miniature(f, 900), r)
                if isinstance(rep, str) and rep == 'STOP':
                    rappel(i - 1, n, 'stop', '', '')
                    return
                if rep is None:
                    rappel(i, n, 'ignore', raw.name, '')
                    continue
                r = rep
            nom = (formater_nom(config.modele_renommage, i, raw.stem)
                   if config.renommer_fichiers else raw.stem)
            dossier = dossier_cible(sortie, raw, racine)
            base = dossier / nom
            k = 2
            while any(Path(str(base) + e).exists() for e in exts):
                base = dossier / f'{nom}_{k}'
                k += 1
            cree = exporter(rendu(f, r), base, config)
            del f
            if config.sortie_xmp:
                ecrire_xmp(sortie, raw, racine, r)
            elif config.conserver_raw:
                copier_raw(sortie, raw, racine)
            _noter(sortie, raw, taille, cree, r)
            rappel(i, n, 'ok', raw.name, str(cree))
        except Exception as e:
            message = str(e) or type(e).__name__
            _noter_erreur(sortie, raw, message)
            rappel(i, n, 'erreur', raw.name, message)
