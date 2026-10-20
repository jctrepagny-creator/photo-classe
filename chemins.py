'''Emplacements des fichiers : données de l'utilisateur et ressources livrées.'''
import os
import subprocess
import sys
from pathlib import Path


def dossier_donnees():
    '''Réglages, modèle d'IA et exemples : ils survivent aux mises à jour.'''
    base = Path(os.environ.get('APPDATA', str(Path.home()))) / 'PhotoClasse'
    base.mkdir(parents=True, exist_ok=True)
    return base


def dossier_exemples():
    '''Dossier des paires avant/après (créé s'il n'existe pas).'''
    base = dossier_donnees() / 'exemples'
    (base / 'avant').mkdir(parents=True, exist_ok=True)
    (base / 'apres').mkdir(parents=True, exist_ok=True)
    return base


def dossier_ressources():
    '''Fichiers livrés avec l'application.'''
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


def ouvrir_dossier(chemin):
    '''Ouvre un dossier dans l'Explorateur Windows.'''
    chemin = Path(chemin)
    chemin.mkdir(parents=True, exist_ok=True)
    if sys.platform == 'win32':
        os.startfile(str(chemin))
    else:
        subprocess.Popen(['xdg-open', str(chemin)])


def afficher_dans_dossier(fichier):
    '''Ouvre l'Explorateur en sélectionnant le fichier.'''
    fichier = Path(fichier)
    if sys.platform == 'win32':
        subprocess.Popen(['explorer', '/select,', str(fichier)])
    else:
        ouvrir_dossier(fichier.parent)
