'''Sauvegarde et rechargement des paramètres (fichier parametres.json).'''
import json
from dataclasses import asdict, fields
from pathlib import Path

from chemins import dossier_donnees
from config import AppConfig

FICHIER = dossier_donnees() / 'parametres.json'


def charger():
    cfg = AppConfig()
    if not FICHIER.exists():
        return cfg
    try:
        donnees = json.loads(FICHIER.read_text(encoding='utf-8'))
    except Exception:
        return cfg
    if donnees.get('format_sortie') == 'TIFF':       # ancien réglage
        donnees.setdefault('sortie_tiff', True)
        donnees.setdefault('sortie_jpeg', False)
    if not donnees.get('migration_134'):             # v1.3.4 : noms d'origine + XMP par défaut
        donnees['renommer_fichiers'] = False
        donnees['sortie_xmp'] = True
        donnees['migration_134'] = True
    for champ in fields(AppConfig):
        if champ.name not in donnees:
            continue
        defaut = getattr(cfg, champ.name)
        valeur = donnees[champ.name]
        if isinstance(defaut, Path):
            if isinstance(valeur, str) and valeur:
                setattr(cfg, champ.name, Path(valeur))
        elif isinstance(valeur, type(defaut)):
            setattr(cfg, champ.name, valeur)
    return cfg


def sauver(cfg):
    donnees = {k: (str(v) if isinstance(v, Path) else v) for k, v in asdict(cfg).items()}
    try:
        FICHIER.write_text(json.dumps(donnees, indent=2, ensure_ascii=False), encoding='utf-8')
    except OSError:
        pass
