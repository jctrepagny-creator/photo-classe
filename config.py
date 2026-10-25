'''Paramètres par défaut de l'application, modifiables depuis la page Réglages.'''
from dataclasses import dataclass
from pathlib import Path

from chemins import dossier_donnees

_images = Path.home() / 'Pictures' / 'PhotosClasse'


@dataclass
class AppConfig:
    dossier_sortie: Path = _images / 'sortie'
    lecture_apercu: bool = True          # lire l'aperçu intégré du RAW (couleurs cohérentes avec l'entraînement)
    sortie_jpeg: bool = True             # formats produits (cumulables)
    sortie_tiff: bool = False
    sortie_dng: bool = True              # RAW traité (DNG) : recadré et corrigé, à ouvrir dans Lightroom
    mode_couleur: int = 2                # 1 aucune correction, 2 exposition seulement, 3 complet (IA)
    migration_134: bool = True           # (interne) anciens réglages mis à jour une fois
    sortie_xmp: bool = True              # RAW d'origine + fichier XMP (Lightroom / Camera Raw)
    retraiter: bool = False              # retraiter aussi les photos déjà traitées
    qualite_jpeg: int = 95               # 1-100
    conserver_raw: bool = True
    renommer_fichiers: bool = False      # False : la photo garde le numéro de son RAW (_DSC8163.jpg)
    modele_renommage: str = 'classe_{index:04d}'
    centrer_visage: bool = True          # nez au milieu de la photo
    marge_haut_photo: int = 6            # espace au-dessus des cheveux, en % de la hauteur de la photo finale
    marge_haut: int = 60                 # marge minimale au-dessus de la tête, en % de la hauteur du visage
    mode_automatique: bool = True        # False = validation photo par photo
    modele_ia: Path = dossier_donnees() / 'modele' / 'style.pt'
    langue: str = 'fr'
    maj_auto: bool = True                # chercher les mises à jour au lancement
    dernier_dossier: Path = Path.home() / 'Pictures'
