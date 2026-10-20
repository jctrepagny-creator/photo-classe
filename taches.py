'''Travaux longs exécutés en arrière-plan (l'interface reste fluide).'''
import shutil
import threading
import zipfile
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

import chemins
import pipeline
from entrainement import ErreurApp, entrainer_depuis_exemples
from i18n import t
from ia_style import StyleIA
from veille import autoriser_veille, empecher_veille


def message_erreur(e):
    if isinstance(e, ErreurApp):
        return t(e.cle, **e.params)
    return str(e) or type(e).__name__


class Tache(QThread):
    '''Exécute une fonction quelconque en arrière-plan.'''
    fini = Signal(object)
    echec = Signal(str)

    def __init__(self, fonction, *args, parent=None):
        super().__init__(parent)
        self._fonction, self._args = fonction, args

    def run(self):
        try:
            self.fini.emit(self._fonction(*self._args))
        except Exception as e:
            self.echec.emit(message_erreur(e))


class TravailLot(QThread):
    progression = Signal(int, int, str, str, str)
    demande_validation = Signal(object, object)
    termine = Signal(bool)          # True si arrêté avant la fin
    echec = Signal(str)

    def __init__(self, config, elements, parent=None):
        super().__init__(parent)
        self.config, self.elements = config, elements
        self._arret = threading.Event()
        self._evt = threading.Event()
        self._reponse = None
        self._stoppe = False

    def arreter(self):
        self._arret.set()
        self._evt.set()

    def repondre(self, reponse):
        self._reponse = reponse
        self._evt.set()

    def _valider(self, mini, reglages):
        self._reponse = None
        self._evt.clear()
        self.demande_validation.emit(mini, reglages)
        while not self._evt.wait(0.3):
            if self._arret.is_set():
                break
        if self._arret.is_set():
            return 'STOP'
        return self._reponse

    def _rappel(self, i, n, statut, nom, detail):
        if statut == 'stop':
            self._stoppe = True
        self.progression.emit(i, n, statut, nom, detail)

    def run(self):
        empecher_veille()
        try:
            ia = StyleIA.charger(self.config.modele_ia)
            pipeline.traiter_lot(self.config, ia, self.elements, self._rappel,
                                 valider=self._valider, arret=self._arret)
            self.termine.emit(self._stoppe)
        except Exception as e:
            self.echec.emit(message_erreur(e))
        finally:
            autoriser_veille()


class TravailEntrainement(QThread):
    progression = Signal(int, int, str, str, str)
    termine = Signal(int)
    echec = Signal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

    def run(self):
        empecher_veille()
        try:
            n = entrainer_depuis_exemples(
                chemins.dossier_exemples(), self.config.modele_ia,
                lambda *a: self.progression.emit(*a))
            self.termine.emit(n)
        except Exception as e:
            self.echec.emit(message_erreur(e))
        finally:
            autoriser_veille()


def charger_vignette(chemin, taille=220):
    '''Petite image (QImage) d'une photo produite, ou None.'''
    try:
        data = np.fromfile(str(chemin), dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_REDUCED_COLOR_4)
        if img is None:
            return None
        h, w = img.shape[:2]
        k = taille / max(h, w)
        if k < 1:
            img = cv2.resize(img, (max(1, int(w * k)), max(1, int(h * k))),
                             interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        h, w = img.shape[:2]
        return QImage(img.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
    except Exception:
        return None


class TravailVignettes(QThread):
    prete = Signal(str, object)

    def __init__(self, fichiers, parent=None):
        super().__init__(parent)
        self.fichiers = [str(f) for f in fichiers]
        self._annule = False

    def annuler(self):
        self._annule = True

    def run(self):
        for f in self.fichiers:
            if self._annule:
                return
            img = charger_vignette(f)
            if img is not None and not self._annule:
                self.prete.emit(f, img)


# --- Fonctions simples lancées via Tache ----------------------------------------------
def copier_vers(fichiers, destination, extensions):
    '''Copie fichiers et dossiers (récursif) vers `destination`. Retourne (copiés, ignorés).'''
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    trouves = {f for f, _ in pipeline.collecter(fichiers, extensions)}
    ignores = 0
    for c in map(Path, fichiers):
        if c.is_file() and c not in trouves:
            ignores += 1
    copies = 0
    for f in sorted(trouves):
        shutil.copy2(f, destination / f.name)
        copies += 1
    return copies, ignores


def creer_zip(fichiers, racine, cible):
    '''ZIP sans recompression (les JPEG sont déjà compressés). Retourne le nombre de fichiers.'''
    racine = Path(racine)
    with zipfile.ZipFile(cible, 'w', zipfile.ZIP_STORED) as z:
        for f in map(Path, fichiers):
            try:
                nom = f.relative_to(racine)
            except ValueError:
                nom = Path(f.name)
            z.write(f, str(nom))
    return len(fichiers)
