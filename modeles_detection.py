'''Modèles de détection de visage, téléchargés une seule fois (GitHub) dans %APPDATA%\\PhotoClasse.
Si le téléchargement est impossible, on peut aussi poser le fichier à la main dans ce dossier.'''
import urllib.request
from pathlib import Path

from chemins import dossier_donnees

YUNET = ('face_detection_yunet_2023mar.onnx', (
    'https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx',
    'https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx'),
    100_000)
HAAR = ('haarcascade_frontalface_default.xml', (
    'https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/haarcascade_frontalface_default.xml',),
    50_000)

_echecs = {}


def dossier():
    d = dossier_donnees() / 'modeles_detection'
    d.mkdir(parents=True, exist_ok=True)
    return d


def obtenir(modele):
    '''Chemin du fichier (téléchargé si besoin) ou None. Une erreur n'est retentée qu'au prochain lancement.'''
    nom, urls, taille_mini = modele
    chemin = dossier() / nom
    if chemin.exists() and chemin.stat().st_size >= taille_mini:
        return chemin
    if nom in _echecs:
        return None
    erreurs = []
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'PhotoClasse'})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if len(data) < taille_mini:
                raise ValueError(f'fichier trop petit ({len(data)} octets)')
            tmp = chemin.with_suffix(chemin.suffix + '.part')
            tmp.write_bytes(data)
            tmp.replace(chemin)
            return chemin
        except Exception as e:
            erreurs.append(f'{url} : {e!r}'[:200])
    _echecs[nom] = ' | '.join(erreurs)
    return None


def derniere_erreur(modele):
    return _echecs.get(modele[0], '')
