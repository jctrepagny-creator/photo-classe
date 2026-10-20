'''Gestionnaire de mises à jour (en arrière-plan) utilisé par la fenêtre et les réglages.'''
from PySide6.QtCore import QObject, Signal

import mise_a_jour
from taches import Tache


class GestionnaireMaj(QObject):
    disponible = Signal(str, str)     # version, url
    a_jour = Signal()
    echec = Signal()
    progression = Signal(int)
    lancee = Signal()                 # l'installateur est démarré : fermer l'application
    erreur_install = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._taches = []
        self.version_dispo = None
        self.url = None

    def _lancer(self, tache):
        self._taches.append(tache)
        tache.finished.connect(lambda: self._taches.remove(tache) if tache in self._taches else None)
        tache.start()

    def verifier(self):
        tache = Tache(mise_a_jour.verifier, parent=self)
        tache.fini.connect(self._resultat)
        tache.echec.connect(lambda _m: self.echec.emit())
        self._lancer(tache)

    def _resultat(self, r):
        if r and r[0] == 'maj':
            self.version_dispo, self.url = r[1], r[2]
            self.disponible.emit(r[1], r[2])
        elif r and r[0] == 'a_jour':
            self.a_jour.emit()
        else:
            self.echec.emit()

    def installer(self):
        if not self.url:
            return
        tache = Tache(mise_a_jour.telecharger_et_installer, self.url, self.progression.emit, parent=self)
        tache.fini.connect(lambda _r: self.lancee.emit())
        tache.echec.connect(self.erreur_install.emit)
        self._lancer(tache)
