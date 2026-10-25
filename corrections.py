'''Mémoire des corrections manuelles : pour chaque photo corrigée, on garde
ce que l'IA avait PROPOSÉ et ce que vous avez DÉCIDÉ. Elles servent ensuite à réentraîner l'IA.'''
import json
from datetime import datetime
from pathlib import Path

from chemins import dossier_donnees

SEUIL_PROPOSITION = 10       # on propose de mettre l'IA à jour à partir de ce nombre de corrections


def _fichier():
    return dossier_donnees() / 'corrections.jsonl'


def enregistrer(src, carac, propose, decide, apprendre=True):
    '''Ajoute une correction. `carac` : mesures de la photo (celles que l'IA utilise).'''
    def nettoyer(r):
        return {'ev': float(r['ev']), 'da': float(r['da']), 'db': float(r['db']),
                'nettete': float(r['nettete']), 'cadre': [float(v) for v in r['cadre']]}
    try:
        taille = Path(src).stat().st_size
    except OSError:
        taille = None
    ligne = {'src': str(src), 'taille': taille, 'date': datetime.now().isoformat(timespec='seconds'),
             'carac': [float(v) for v in carac], 'propose': nettoyer(propose),
             'decide': nettoyer(decide), 'apprendre': bool(apprendre)}
    try:
        with open(_fichier(), 'a', encoding='utf-8') as f:
            f.write(json.dumps(ligne, ensure_ascii=False) + '\n')
    except OSError:
        pass
    return ligne


def lire():
    '''Corrections à apprendre : une par photo (la plus récente), sans celles écartées.'''
    derniere = {}
    try:
        with open(_fichier(), encoding='utf-8') as f:
            for texte in f:
                try:
                    r = json.loads(texte)
                    derniere[r['src']] = r
                except Exception:
                    continue
    except OSError:
        return {}
    return {k: r for k, r in derniere.items() if r.get('apprendre', True)}


def decision_pour(src):
    '''Réglages que VOUS avez décidés pour cette photo (ou None), même si le RAW a été copié ou
    déplacé : on reconnaît le fichier à son chemin, sinon à son nom ET sa taille.'''
    src = Path(src)
    toutes = lire()
    r = toutes.get(str(src))
    if r is None:
        try:
            taille = src.stat().st_size
        except OSError:
            return None
        meilleur = None
        for x in toutes.values():
            if x.get('taille') == taille and Path(x['src']).name.lower() == src.name.lower():
                if meilleur is None or x['date'] > meilleur['date']:
                    meilleur = x
        r = meilleur
    return None if r is None else r['decide']


def en_attente(date_modele):
    '''Nombre de corrections plus récentes que le dernier entraînement.'''
    toutes = lire().values()
    if not date_modele:
        return len(toutes)
    return sum(1 for r in toutes if r['date'] > date_modele)


def vers_exemple(r):
    '''(X, Y) d'entraînement : les réglages décidés et le cadre RELATIF au visage.'''
    x = r['carac']
    b0, b1, b2, b3 = x[11:15]
    lw, lh = max(b2 - b0, 1e-3), max(b3 - b1, 1e-3)
    c = r['decide']['cadre']
    rel = [(c[0] - b0) / lw, (c[1] - b1) / lh, (c[2] - b0) / lw, (c[3] - b1) / lh]
    d = r['decide']
    return x, [d['ev'], d['da'], d['db'], d['nettete']] + rel
