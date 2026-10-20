'''Fenêtre principale : menu latéral à gauche, pages à droite.'''
import os

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFrame, QHBoxLayout, QLabel,
                               QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget)

import parametres
from i18n import t
from page_accueil import PageAccueil
from page_exemples import PageExemples
from page_reglages import PageReglages
from page_resultats import PageResultats
from page_traitement import PageTraitement
from ui_maj import GestionnaireMaj
from version import VERSION
from widgets import BandeSecurite, BoutonMenu, bouton, icone_application


class FenetrePrincipale(QMainWindow):
    occupation_changee = Signal(object)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.occupation = None            # None, 'lot' ou 'entrainement'
        self.setWindowTitle('Photo Classe')
        self.setWindowIcon(icone_application())
        self.resize(1200, 800)
        self.setMinimumSize(1000, 660)
        self.maj = GestionnaireMaj(self)

        racine = QWidget()
        self.setCentralWidget(racine)
        ligne = QHBoxLayout(racine)
        ligne.setContentsMargins(0, 0, 0, 0)
        ligne.setSpacing(0)

        # --- menu latéral
        self.menu = QFrame()
        self.menu.setObjectName('Sidebar')
        self.menu.setFixedWidth(108)
        col = QVBoxLayout(self.menu)
        col.setContentsMargins(8, 16, 8, 12)
        col.setSpacing(6)
        logo = QLabel('Photo\nClasse')
        logo.setObjectName('Logo')
        col.addWidget(logo)
        col.addSpacing(14)

        self.pages = {}
        self.boutons = {}
        self.pile = QStackedWidget()
        self._groupe = QButtonGroup(self)
        self._groupe.setExclusive(True)
        definitions = (('accueil', 'accueil', PageAccueil), ('traitement', 'traitement', PageTraitement),
                       ('exemples', 'exemples', PageExemples), ('resultats', 'resultats', PageResultats),
                       ('reglages', 'reglages', PageReglages))
        for cle, icone, classe in definitions:
            b = BoutonMenu(icone, t('menu_' + cle))
            self._groupe.addButton(b)
            self.boutons[cle] = b
            self.pages[cle] = classe(self)
            self.pile.addWidget(self.pages[cle])
            b.clicked.connect(lambda _=False, c=cle: self.aller(c))
            if cle == 'reglages':
                col.addStretch(1)
            col.addWidget(b)
        v = QLabel(t('version', v=VERSION))
        v.setObjectName('VersionMenu')
        col.addWidget(v)
        ligne.addWidget(self.menu)

        # --- contenu
        droite = QVBoxLayout()
        droite.setSpacing(0)
        droite.addWidget(BandeSecurite())
        self.bandeau = QFrame()
        self.bandeau.setObjectName('BandeMaj')
        rb = QHBoxLayout(self.bandeau)
        rb.setContentsMargins(24, 8, 24, 8)
        self.l_bandeau = QLabel('')
        self.b_bandeau = bouton(t('maj_installer'))
        self.b_bandeau.setObjectName('MajBtn')
        self.b_bandeau.clicked.connect(self._installer_maj)
        rb.addWidget(self.l_bandeau, 1)
        rb.addWidget(self.b_bandeau)
        self.bandeau.hide()
        droite.addWidget(self.bandeau)
        droite.addWidget(self.pile, 1)
        ligne.addLayout(droite, 1)

        self.maj.disponible.connect(self._maj_disponible)
        self.maj.progression.connect(lambda p: self.l_bandeau.setText(t('maj_telechargement', p=p)))
        self.maj.lancee.connect(self._maj_lancee)
        self.maj.erreur_install.connect(self._maj_erreur)

        for p in self.pages.values():
            p.rafraichir()
        self.aller('accueil')
        if config.maj_auto:
            QTimer.singleShot(1500, self.maj.verifier)

    # -- API utilisée par les pages
    def sauver_config(self):
        parametres.sauver(self.config)

    def aller(self, cle):
        if cle not in self.pages:
            return
        self.boutons[cle].setChecked(True)
        self.pile.setCurrentWidget(self.pages[cle])
        self.pages[cle].rafraichir()

    def definir_occupation(self, occupation):
        self.occupation = occupation
        for p in self.pages.values():
            p.occupation_changee(occupation)
        if occupation is None:
            self.pages['accueil'].rafraichir()

    # -- mises à jour
    def _maj_disponible(self, version, url):
        self.l_bandeau.setText(t('maj_bandeau', v=version))
        self.b_bandeau.setEnabled(True)
        self.bandeau.show()

    def _installer_maj(self):
        if self.occupation:
            QMessageBox.information(self, t('maj_titre'), t('maj_occupe'))
            return
        rep = QMessageBox.question(self, t('maj_titre'), t('maj_confirmer'))
        if rep == QMessageBox.StandardButton.Yes:
            self.b_bandeau.setEnabled(False)
            self.l_bandeau.setText(t('maj_telechargement', p=0))
            self.maj.installer()

    def _maj_lancee(self):
        self.sauver_config()
        QApplication.instance().quit()

    def _maj_erreur(self, message):
        self.b_bandeau.setEnabled(True)
        self.l_bandeau.setText(t('maj_echec_install'))
        QMessageBox.warning(self, t('erreur'), message)

    # -- fermeture
    def closeEvent(self, e):
        if self.occupation:
            rep = QMessageBox.question(self, t('quitter_titre'), t('quitter_occupe'))
            if rep != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
            ok = self.pages['traitement'].attendre_fin() and self.pages['exemples'].attendre_fin()
            if not ok:                   # travail trop long à interrompre : on repart de zéro au prochain lancement
                self.sauver_config()
                os._exit(0)
        self.pages['resultats'].attendre_fin()
        self.sauver_config()
        e.accept()
