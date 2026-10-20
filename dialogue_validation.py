'''Fenêtre de validation photo par photo (mode manuel).'''
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel, QSlider, QVBoxLayout)

from i18n import t
from pipeline import rendu
from traitement_image import vers_uint8
from widgets import bouton


class DialogueValidation(QDialog):
    '''Après exec() : `resultat` = réglages (valider), None (ignorer) ou 'STOP' (arrêter le lot).'''
    CURSEURS = (('ev', 'reg_exposition', -2.0, 3.0), ('da', 'reg_magenta', -20.0, 20.0),
                ('db', 'reg_cyan', -20.0, 20.0), ('nettete', 'reg_nettete', 0.0, 2.0))

    def __init__(self, mini, reglages, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('valid_titre'))
        self.resize(900, 720)
        self.mini = mini
        self.reglages = dict(reglages)
        self.resultat = 'STOP'

        mise = QVBoxLayout(self)
        mise.setContentsMargins(20, 18, 20, 18)
        mise.setSpacing(12)
        self.apercu = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.apercu.setMinimumSize(640, 420)
        mise.addWidget(self.apercu, 1)

        grille = QGridLayout()
        grille.setHorizontalSpacing(12)
        self._curseurs = {}
        self._valeurs = {}
        for ligne, (cle, texte, mini_v, maxi_v) in enumerate(self.CURSEURS):
            lab = QLabel(t(texte))
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(int(mini_v * 100), int(maxi_v * 100))
            s.setValue(int(round(float(self.reglages[cle]) * 100)))
            val = QLabel()
            val.setMinimumWidth(50)
            s.valueChanged.connect(self._maj)
            grille.addWidget(lab, ligne, 0)
            grille.addWidget(s, ligne, 1)
            grille.addWidget(val, ligne, 2)
            self._curseurs[cle], self._valeurs[cle] = s, val
        mise.addLayout(grille)

        rang = QHBoxLayout()
        b_stop = bouton(t('valid_arreter'), danger=True)
        b_skip = bouton(t('valid_ignorer'))
        b_ok = bouton(t('valid_valider'), principal=True)
        b_stop.clicked.connect(lambda: self._fin('STOP'))
        b_skip.clicked.connect(lambda: self._fin(None))
        b_ok.clicked.connect(lambda: self._fin('OK'))
        rang.addWidget(b_stop)
        rang.addStretch(1)
        rang.addWidget(b_skip)
        rang.addWidget(b_ok)
        mise.addLayout(rang)
        self._maj()

    def _lire(self):
        r = dict(self.reglages)
        for cle, s in self._curseurs.items():
            r[cle] = s.value() / 100.0
        return r

    def _maj(self, *_):
        r = self._lire()
        for cle, val in self._valeurs.items():
            val.setText(f'{r[cle]:+.2f}')
        try:
            img = vers_uint8(rendu(self.mini, r))
            h, w = img.shape[:2]
            qi = QImage(img.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
            pm = QPixmap.fromImage(qi).scaled(self.apercu.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)
            self.apercu.setPixmap(pm)
        except Exception:
            self.apercu.setText('...')

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._maj()

    def _fin(self, choix):
        self.resultat = self._lire() if choix == 'OK' else choix
        self.accept()

    def reject(self):
        self.resultat = 'STOP'
        super().reject()
