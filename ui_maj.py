'''Bouton « Mettre à jour » et vérification automatique au lancement.'''
from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton

import mise_a_jour
from i18n import t
from version import VERSION


class _Travail(QThread):
    trouvee = Signal(str, str)
    rien = Signal()
    progression = Signal(int)
    fini = Signal(str)

    def __init__(self, url=None):
        super().__init__()
        self.url = url

    def run(self):
        if self.url is None:
            res = mise_a_jour.verifier()
            if res:
                self.trouvee.emit(*res)
            else:
                self.rien.emit()
            return
        try:
            mise_a_jour.telecharger_et_installer(self.url, self.progression.emit)
            self.fini.emit('ok')
        except Exception as e:
            self.fini.emit(f'Erreur : {e}')


class GestionMaj(QObject):
    def __init__(self, fen, layout):
        super().__init__(fen)
        self.fen = fen
        self.langue = fen.cfg.langue
        self.silencieux = True
        self.travail = None
        fen.setWindowTitle(f'{fen.windowTitle()} - v{VERSION}')
        self.bouton = QPushButton(t('maj', self.langue))
        self.bouton.clicked.connect(self.verifier_manuel)
        layout.addWidget(self.bouton)
        QTimer.singleShot(2000, self.verifier_auto)

    def verifier_auto(self):
        self._chercher(True)

    def verifier_manuel(self, *_):
        self._chercher(False)

    def _chercher(self, silencieux):
        self.silencieux = silencieux
        self.travail = _Travail()
        self.travail.trouvee.connect(self._trouvee)
        self.travail.rien.connect(self._rien)
        self.travail.start()

    def _rien(self):
        if not self.silencieux:
            QMessageBox.information(self.fen, '', t('maj_a_jour', self.langue))

    def _trouvee(self, version, url):
        en_cours = getattr(self.fen, 'travail', None)
        if en_cours is not None and en_cours.isRunning():
            QMessageBox.information(self.fen, '', t('maj_occupe', self.langue))
            return
        rep = QMessageBox.question(self.fen, '',
                                   t('maj_dispo', self.langue).format(version=version))
        if rep != QMessageBox.Yes:
            return
        self.bouton.setEnabled(False)
        self.fen.barre.setMaximum(100)
        self.travail = _Travail(url)
        self.travail.progression.connect(self.fen.barre.setValue)
        self.travail.fini.connect(self._fini)
        self.travail.start()

    def _fini(self, resultat):
        if resultat == 'ok':
            QApplication.quit()
        else:
            self.bouton.setEnabled(True)
            QMessageBox.warning(self.fen, '', resultat)
