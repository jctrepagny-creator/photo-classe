'''Emplacements des fichiers : données de l'utilisateur et ressources livrées.'''
import os
import sys
from pathlib import Path


def dossier_donnees():
    '''Réglages et modèle d'IA : ils survivent aux mises à jour.'''
    base = Path(os.environ.get('APPDATA', str(Path.home()))) / 'PhotoClasse'
    base.mkdir(parents=True, exist_ok=True)
    return base


def dossier_ressources():
    '''Fichiers livrés avec l'application.'''
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent
