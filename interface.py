'''Fenêtre principale (PySide6).'''
import threading
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton, QSlider,
                               QSpinBox, QVBoxLayout, QWidget)

import parametres
import ui_maj
from entrainement import entrainer_depuis_exemples
from i18n import t
from ia_style import StyleIA
from pipeline import traiter_lot
from traitement_image import vers_uint8, appliquer_cadrage, appliquer_reglages

# réglage : (minimum, maximum, échelle du curseur, libellé)
CURSEURS = {
    'ev': (-200, 200, 100, 'exposition'),
    'da': (-300, 300, 10, 'vert_magenta'),
    'db': (-300, 300, 10, 'bleu_jaune'),
    'nettete': (0, 200, 100, 'nettete'),
}


def vers_pixmap(f, largeur=420):
    img = np.ascontiguousarray(vers_uint8(f))
    h, w, _ = img.shape
    qimg = QImage(img.data, w, h, 3 * w, QImage.Format_RGB888).copy()
    return QPixmap.fromImage(qimg).scaledToWidth(largeur, Qt.SmoothTransformation)


class DialogueValidation(QDialog):
    '''Aperçu avant/après avec ajustement manuel d'une photo.'''

    def __init__(self, mini, reglages, langue, parent=None):
        super().__init__(parent)
        self.mini, self.r, self.resultat = mini, dict(reglages), None
        lay = QVBoxLayout(self)
        images = QHBoxLayout()
        self.lbl_avant, self.lbl_apres = QLabel(), QLabel()
        for titre, lbl in ((t('avant', langue), self.lbl_avant),
                           (t('apres', langue), self.lbl_apres)):
            col = QVBoxLayout()
            col.addWidget(QLabel(titre))
            col.addWidget(lbl)
            images.addLayout(col)
        lay.addLayout(images)
        self.curseurs = {}
        for cle, (lo, hi, echelle, libelle) in CURSEURS.items():
            s = QSlider(Qt.Horizontal)
            s.setRange(lo, hi)
            s.setValue(int(self.r[cle] * echelle))
            s.valueChanged.connect(self._maj)
            self.curseurs[cle] = s
            ligne = QHBoxLayout()
            ligne.addWidget(QLabel(t(libelle, langue)))
            ligne.addWidget(s)
            lay.addLayout(ligne)
        boutons = QHBoxLayout()
        for cle, action in (('accepter', self._accepter), ('ignorer', self._ignorer),
                            ('arret_lot', self._stop)):
            b = QPushButton(t(cle, langue))
            b.clicked.connect(action)
            boutons.addWidget(b)
        lay.addLayout(boutons)
        self._maj()

    def _maj(self):
        for cle, (lo, hi, echelle, _) in CURSEURS.items():
            self.r[cle] = self.curseurs[cle].value() / echelle
        zone = appliquer_cadrage(self.mini, self.r['cadre'])
        apres = appliquer_reglages(zone, self.r['ev'], self.r['da'], self.r['db'],
                                   self.r['nettete'])
        self.lbl_avant.setPixmap(vers_pixmap(zone))
        self.lbl_apres.setPixmap(vers_pixmap(apres))

    def _accepter(self):
        self.resultat = self.r
        self.accept()

    def _ignorer(self):
        self.resultat = None
        self.reject()

    def _stop(self):
        self.resultat = 'STOP'
        self.reject()


class TravailEntrainement(QThread):
    message = Signal(str)
    fini = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            entrainer_depuis_exemples(self.config.dossier_exemples, self.config.modele_ia,
                                      self.message.emit)
            self.fini.emit('ok')
        except Exception as e:
            self.fini.emit(f'Erreur : {e}')


class TravailLot(QThread):
    progression = Signal(int, int, str)
    validation_demandee = Signal(object, object)
    fini = Signal(str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.arret = threading.Event()
        self._attente = threading.Event()
        self._reponse = None

    def repondre(self, reponse):
        self._reponse = reponse
        self._attente.set()

    def _valider(self, mini, reglages):
        self._attente.clear()
        self.validation_demandee.emit(mini, reglages)
        self._attente.wait()
        return self._reponse

    def run(self):
        try:
            ia = StyleIA.charger(self.config.modele_ia)
            traiter_lot(self.config, ia, lambda i, n, m: self.progression.emit(i, n, m),
                        self._valider, self.arret)
            self.fini.emit('ok')
        except Exception as e:
            self.fini.emit(f'Erreur : {e}')


class FenetrePrincipale(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = parametres.charger()
        L = self.cfg.langue
        self.travail = None
        self.setWindowTitle(t('titre', L))
        centre = QWidget()
        self.setCentralWidget(centre)
        lay = QVBoxLayout(centre)
        form = QFormLayout()
        lay.addLayout(form)

        self.champs = {}
        for cle in ('dossier_entree', 'dossier_sortie', 'dossier_exemples'):
            champ = QLineEdit(str(getattr(self.cfg, cle)))
            bouton = QPushButton(t('parcourir', L))
            bouton.clicked.connect(lambda _=False, c=champ: self._choisir(c))
            ligne = QHBoxLayout()
            ligne.addWidget(champ)
            ligne.addWidget(bouton)
            form.addRow(t(cle, L), ligne)
            self.champs[cle] = champ

        self.format = QComboBox()
        self.format.addItems(['JPEG', 'TIFF'])
        self.format.setCurrentText(self.cfg.format_sortie)
        self.qualite = QSpinBox()
        self.qualite.setRange(1, 100)
        self.qualite.setValue(self.cfg.qualite_jpeg)
        self.chk_raw = QCheckBox(t('conserver_raw', L))
        self.chk_raw.setChecked(self.cfg.conserver_raw)
        self.chk_nom = QCheckBox(t('renommer', L))
        self.chk_nom.setChecked(self.cfg.renommer_fichiers)
        self.modele_nom = QLineEdit(self.cfg.modele_renommage)
        self.mode = QComboBox()
        self.mode.addItems([t('mode_auto', L), t('mode_manuel', L)])
        self.mode.setCurrentIndex(0 if self.cfg.mode_automatique else 1)
        self.langue = QComboBox()
        self.langue.addItems(['fr', 'en'])
        self.langue.setCurrentText(L)
        form.addRow(t('format', L), self.format)
        form.addRow(t('qualite', L), self.qualite)
        form.addRow(self.chk_raw)
        form.addRow(self.chk_nom)
        form.addRow(t('modele_renommage', L), self.modele_nom)
        form.addRow(t('mode', L), self.mode)
        form.addRow(t('langue', L), self.langue)

        boutons = QHBoxLayout()
        self.btn_entrainer = QPushButton(t('entrainer', L))
        self.btn_lancer = QPushButton(t('lancer', L))
        self.btn_arreter = QPushButton(t('arreter', L))
        self.btn_arreter.setEnabled(False)
        self.btn_entrainer.clicked.connect(self._entrainer)
        self.btn_lancer.clicked.connect(self._lancer)
        self.btn_arreter.clicked.connect(self._arreter)
        for b in (self.btn_entrainer, self.btn_lancer, self.btn_arreter):
            boutons.addWidget(b)
        lay.addLayout(boutons)
        self.barre = QProgressBar()
        self.journal = QPlainTextEdit()
        self.journal.setReadOnly(True)
        lay.addWidget(self.barre)
        lay.addWidget(self.journal)
        self.maj = ui_maj.GestionMaj(self, lay)

    # --- utilitaires -------------------------------------------------
    def _choisir(self, champ):
        dossier = QFileDialog.getExistingDirectory(self, '', champ.text())
        if dossier:
            champ.setText(dossier)

    def _lire_config(self):
        c = self.cfg
        c.dossier_entree = Path(self.champs['dossier_entree'].text())
        c.dossier_sortie = Path(self.champs['dossier_sortie'].text())
        c.dossier_exemples = Path(self.champs['dossier_exemples'].text())
        c.format_sortie = self.format.currentText()
        c.qualite_jpeg = self.qualite.value()
        c.conserver_raw = self.chk_raw.isChecked()
        c.renommer_fichiers = self.chk_nom.isChecked()
        c.modele_renommage = self.modele_nom.text() or 'classe_{index:04d}'
        c.mode_automatique = self.mode.currentIndex() == 0
        c.langue = self.langue.currentText()
        parametres.sauver(c)
        return c

    def _occupe(self, oui):
        self.btn_entrainer.setEnabled(not oui)
        self.btn_lancer.setEnabled(not oui)
        self.btn_arreter.setEnabled(oui)

    def _log(self, texte):
        self.journal.appendPlainText(texte)

    # --- entraînement ------------------------------------------------
    def _entrainer(self):
        cfg = self._lire_config()
        self._occupe(True)
        self.travail = TravailEntrainement(cfg)
        self.travail.message.connect(self._log)
        self.travail.fini.connect(self._fin)
        self.travail.start()

    # --- traitement --------------------------------------------------
    def _lancer(self):
        cfg = self._lire_config()
        if not Path(cfg.modele_ia).exists():
            QMessageBox.warning(self, '', t('pas_de_modele', cfg.langue))
            return
        self._occupe(True)
        self.travail = TravailLot(cfg)
        self.travail.progression.connect(self._progression)
        self.travail.validation_demandee.connect(self._validation)
        self.travail.fini.connect(self._fin)
        self.travail.start()

    def _progression(self, i, n, message):
        self.barre.setMaximum(max(n, 1))
        self.barre.setValue(i)
        self._log(message)

    def _validation(self, mini, reglages):
        dlg = DialogueValidation(mini, reglages, self.cfg.langue, self)
        dlg.exec()
        self.travail.repondre(dlg.resultat)

    def _arreter(self):
        if isinstance(self.travail, TravailLot):
            self.travail.arret.set()

    def _fin(self, etat):
        self._occupe(False)
        self._log('Terminé.' if etat == 'ok' else etat)
