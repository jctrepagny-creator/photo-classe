'''Paramètres par défaut de l'application, modifiables depuis la page Réglages.'''
from dataclasses import dataclass
from pathlib import Path

from chemins import dossier_donnees

_images = Path.home() / 'Pictures' / 'PhotosClasse'


@dataclass
class AppConfig:
    dossier_sortie: Path = _images / 'sortie'
    format_sortie: str = 'JPEG'          # 'JPEG' ou 'TIFF'
    qualite_jpeg: int = 95               # 1-100
    conserver_raw: bool = True
    renommer_fichiers: bool = True
    modele_renommage: str = 'classe_{index:04d}'
    mode_automatique: bool = True        # False = validation photo par photo
    modele_ia: Path = dossier_donnees() / 'modele' / 'style.pt'
    langue: str = 'fr'
    maj_auto: bool = True                # chercher les mises à jour au lancement
    dernier_dossier: Path = Path.home() / 'Pictures'
