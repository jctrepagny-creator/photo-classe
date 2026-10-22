'''Chaîne complète : RAW -> analyse -> IA -> retouche -> export.

Les photos viennent d'une file d'attente : une liste de (fichier, racine) où `racine` est le
dossier déposé (None pour un fichier déposé seul). Le classement en sortie reprend cette
organisation : sortie / <dossier déposé> / <sous-dossiers>.'''
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

import cv2

from detection_visages import axe_du_visage, detecter_visages, haut_de_tete
from entrainement import ErreurApp
from ia_style import extraire_caracteristiques
from lecture_raw import EXT_IGNOREES, EXT_TOUT, charger_raw
from traitement_image import (vers_float, vers_uint8, vers_uint16, miniature,
                              appliquer_cadrage, appliquer_reglages)

FICHIER_SUIVI = '.traitees.jsonl'   # une ligne par photo terminée (reprise après coupure)
FICHIER_ERREURS = 'journal.txt'
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


def _noter(sortie, src, taille, resultat):
    try:
        with open(Path(sortie) / FICHIER_SUIVI, 'a', encoding='utf-8') as f:
            f.write(json.dumps({'src': str(src), 'taille': taille, 'sortie': str(resultat),
                                'date': datetime.now().isoformat(timespec='seconds')},
                               ensure_ascii=False) + '\n')
    except OSError:
        pass          # un journal illisible ne doit jamais interrompre le lot


def _noter_erreur(sortie, raw, message):
    try:
        with open(Path(sortie) / FICHIER_ERREURS, 'a', encoding='utf-8') as j:
            j.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {raw} | {message}\n")
    except OSError:
        pass


# --- Traitement ----------------------------------------------------------------
def recentrer(cadre, axe):
    '''Décale le cadre (sans changer sa taille) pour que `axe` soit au milieu.'''
    x0, y0, x1, y1 = cadre
    nl = x1 - x0
    nx0 = min(max(axe - nl / 2, 0.0), 1.0 - nl)
    return (nx0, y0, nx0 + nl, y1)


def recadrer_sur_cheveux(cadre, visage, sommet, marge, dims, axe=None):
    '''Place le haut du cadre à une distance constante au-dessus des cheveux
    (marge = fraction de la hauteur de la tête) en gardant le format du cadre prévu.'''
    h, w = dims[:2]
    x0, y0, x1, y1 = cadre
    haut_tete = visage[3] - sommet                    # sommet des cheveux -> menton
    if haut_tete < 0.02:
        return cadre
    ny0 = max(0.0, sommet - marge * haut_tete)
    if y1 - ny0 < 0.2:
        return cadre
    format_px = ((x1 - x0) * w) / max((y1 - y0) * h, 1)
    nl = min(1.0, format_px * (y1 - ny0) * h / w)
    cx = axe if axe is not None else (x0 + x1) / 2
    nx0 = min(max(cx - nl / 2, 0.0), 1.0 - nl)
    return (nx0, ny0, nx0 + nl, y1)


def analyser(f, ia, marge_haut=0.6, marge_cheveux=18, centrer=True):
    '''Réglages propres à CETTE photo (jamais un réglage global pour le lot).'''
    mini = vers_uint8(miniature(f, 768))
    visages = detecter_visages(mini)
    r = ia.predire(extraire_caracteristiques(miniature(f, 256), visages), marge_haut)
    if len(visages) == 1:
        axe = axe_du_visage(mini, visages[0]) if centrer else None
        sommet = haut_de_tete(mini, visages) if marge_cheveux >= 0 else None
        if sommet is not None:
            r['cadre'] = recadrer_sur_cheveux(r['cadre'], visages[0], sommet,
                                              marge_cheveux / 100.0, f.shape, axe)
            r['sommet'] = sommet
        elif axe is not None:
            r['cadre'] = recentrer(r['cadre'], axe)
        r['axe'] = axe
    return r


def rendu(f, r):
    zone = appliquer_cadrage(f, r['cadre'])
    return appliquer_reglages(zone, r['ev'], r['da'], r['db'], r['nettete'])


def exporter(img, base, config):
    '''Écrit le fichier final. base = chemin sans extension. Retourne le chemin écrit.'''
    if config.format_sortie == 'TIFF':
        ext, data, params = '.tif', vers_uint16(img), []
    else:
        ext, data = '.jpg', vers_uint8(img)
        params = [cv2.IMWRITE_JPEG_QUALITY, int(config.qualite_jpeg)]
    ok, tampon = cv2.imencode(ext, cv2.cvtColor(data, cv2.COLOR_RGB2BGR), params)
    if not ok:
        raise RuntimeError('Encodage impossible')
    chemin = Path(str(base) + ext)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    tampon.tofile(str(chemin))
    return chemin


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
    ext = '.tif' if config.format_sortie == 'TIFF' else '.jpg'
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
        if deja and deja.get('taille') == taille and Path(deja['sortie']).exists():
            rappel(i, n, 'saute', raw.name, deja['sortie'])
            continue
        rappel(i - 1, n, 'debut', raw.name, '')
        try:
            f = vers_float(charger_raw(raw))
            r = analyser(f, ia, config.marge_haut / 100.0, config.marge_cheveux,
                         config.centrer_visage)
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
            base = base_libre(dossier_cible(sortie, raw, racine) / nom, ext)
            cree = exporter(rendu(f, r), base, config)
            del f
            if config.conserver_raw:
                if racine is None:
                    dest = sortie / DOSSIER_RAW / raw.name
                else:
                    dest = sortie / DOSSIER_RAW / _nom_dossier(racine) / raw.relative_to(racine)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if not dest.exists():
                    shutil.copy2(raw, dest)
            _noter(sortie, raw, taille, cree)
            rappel(i, n, 'ok', raw.name, str(cree))
        except Exception as e:
            message = str(e) or type(e).__name__
            _noter_erreur(sortie, raw, message)
            rappel(i, n, 'erreur', raw.name, message)
