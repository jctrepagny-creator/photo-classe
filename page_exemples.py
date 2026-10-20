'''Page « Exemples » : on dépose les photos d'origine (RAW) et leurs versions retouchées.'''
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
                               QPlainTextEdit, QProgressBar, QTableWidget, QTableWidgetItem)

import chemins
import bilan
from entrainement import MIN_PAIRES, info_modele, lister_paires
from i18n import t
from lecture_raw import EXT_IMAGES, EXT_RAW
from taches import Tache, TravailEntrainement, copier_vers
from widgets import Carte, PageBase, ZoneDepot, bouton, texte_discret

FILTRE_RAW = 'RAW (' + ' '.join('*' + e for e in sorted(EXT_RAW)) + ')'
FILTRE_IMG = 'Images (' + ' '.join('*' + e for e in sorted(EXT_IMAGES)) + ')'


class PageExemples(PageBase):
    def __init__(self, ctx):
        super().__init__(t('page_exemples'), t('exemples_sous'))
        self.ctx = ctx
        self.travail = None
        self._taches = []
        self._lignes = []     # [(nom, fichier_avant|None, fichier_apres|None)]

        zones = QHBoxLayout()
        zones.setSpacing(16)
        self.z_avant = ZoneDepot(t('depot_avant_titre'), t('depot_avant_sous'), FILTRE_RAW + ';;*')
        self.z_apres = ZoneDepot(t('depot_apres_titre'), t('depot_apres_sous'), FILTRE_IMG + ';;*')
        self.z_avant.deposes.connect(lambda c: self._deposer(c, 'avant', EXT_RAW))
        self.z_apres.deposes.connect(lambda c: self._deposer(c, 'apres', EXT_IMAGES))
        zones.addWidget(self.z_avant, 1)
        zones.addWidget(self.z_apres, 1)
        self.corps.addLayout(zones)
        self.l_info = QLabel('')
        self.l_info.setObjectName('Avertissement')
        self.l_info.setWordWrap(True)
        self.l_info.hide()
        self.corps.addWidget(self.l_info)

        carte = Carte(t('paires_titre'))
        self.l_compte = QLabel('')
        carte.ajouter(self.l_compte)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([t('col_nom'), t('col_original'), t('col_retouchee')])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setMinimumHeight(200)
        self.table.setMaximumHeight(320)
        carte.ajouter(self.table)
        rang = QHBoxLayout()
        self.b_retirer = bouton(t('retirer_selection'), 'croix')
        self.b_vider = bouton(t('tout_supprimer'), 'poubelle', danger=True)
        self.b_retirer.clicked.connect(self.retirer)
        self.b_vider.clicked.connect(self.tout_supprimer)
        rang.addWidget(self.b_retirer)
        rang.addWidget(self.b_vider)
        rang.addStretch(1)
        carte.ajouter_layout(rang)
        carte.ajouter(texte_discret(t('copie_info')))
        self.corps.addWidget(carte)

        carte = Carte(t('entrainement_titre'))
        self.l_modele = QLabel('')
        carte.ajouter(self.l_modele)
        self.l_aide = texte_discret('')
        carte.ajouter(self.l_aide)
        self.b_entrainer = bouton(t('entrainer'), 'traitement', principal=True)
        self.b_entrainer.clicked.connect(self.entrainer)
        carte.ajouter(self.b_entrainer, alignment=Qt.AlignmentFlag.AlignLeft)
        self.barre = QProgressBar()
        self.barre.hide()
        carte.ajouter(self.barre)
        self.l_etat = QLabel('')
        self.l_etat.setWordWrap(True)
        carte.ajouter(self.l_etat)
        self.journal = QPlainTextEdit()
        self.journal.setReadOnly(True)
        self.journal.setMaximumBlockCount(1000)
        self.journal.setMinimumHeight(110)
        self.journal.hide()
        carte.ajouter(self.journal)
        self.corps.addWidget(carte)
        self.corps.addStretch(1)

    # -- dépôt
    def _deposer(self, fichiers, sous, extensions):
        if self.ctx.occupation:
            return
        dest = chemins.dossier_exemples() / sous
        tache = Tache(copier_vers, fichiers, dest, extensions, parent=self)
        self._taches.append(tache)
        self.setCursor(Qt.CursorShape.BusyCursor)
        tache.fini.connect(self._copie_finie)
        tache.echec.connect(self._copie_echec)
        tache.finished.connect(lambda: self._taches.remove(tache) if tache in self._taches else None)
        tache.start()

    def _copie_finie(self, res):
        self.unsetCursor()
        copies, ignores = res
        if copies == 0:
            self.l_info.setText(t('rien_trouve_exemples'))
            self.l_info.show()
        else:
            self.l_info.hide()
        self.rafraichir()

    def _copie_echec(self, message):
        self.unsetCursor()
        QMessageBox.warning(self.window(), t('erreur'), message)
        self.rafraichir()

    # -- liste des paires
    def rafraichir(self):
        paires, sans_apres, sans_avant = lister_paires(chemins.dossier_exemples())
        lignes = [(a.stem, a, b) for a, b in paires]
        lignes += [(a.stem, a, None) for a in sans_apres]
        lignes += [(b.stem, None, b) for b in sans_avant]
        lignes.sort(key=lambda x: x[0].lower())
        self._lignes = lignes
        self.table.setRowCount(len(lignes))
        for r, (nom, a, b) in enumerate(lignes):
            complet = a is not None and b is not None
            valeurs = (nom, '✓' if a else '✗', '✓' if b else '✗')
            for c, v in enumerate(valeurs):
                it = QTableWidgetItem(v)
                if c:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if not complet and c:
                    it.setForeground(QColor('#C0392B' if v == '✗' else '#2E8B57'))
                elif c:
                    it.setForeground(QColor('#2E8B57'))
                self.table.setItem(r, c, it)
        n = len(paires)
        self.l_compte.setText(t('paires_compte', n=n, sans_apres=len(sans_apres), sans_avant=len(sans_avant)))

        info = info_modele(self.ctx.config.modele_ia)
        if info:
            self.l_modele.setText(t('modele_etat_ok', date=bilan.format_date(info.get('date', '')),
                                    n=info.get('paires') or '?'))
        else:
            self.l_modele.setText(t('modele_absent'))
        if n < MIN_PAIRES:
            self.l_aide.setText(t('aide_min_paires', n=n, minimum=MIN_PAIRES))
        else:
            self.l_aide.setText(t('aide_pret', n=n))
        self._etat_boutons()

    def occupation_changee(self, occupation):
        self._etat_boutons()

    def _etat_boutons(self):
        libre = self.ctx.occupation is None
        self.z_avant.setEnabled(libre)
        self.z_apres.setEnabled(libre)
        self.b_retirer.setEnabled(libre)
        self.b_vider.setEnabled(libre)
        paires, _, _ = lister_paires(chemins.dossier_exemples())
        self.b_entrainer.setEnabled(libre and len(paires) >= MIN_PAIRES)
        self.b_entrainer.setVisible(self.ctx.occupation != 'entrainement')

    # -- suppression (uniquement les COPIES gardées par l'application)
    def retirer(self):
        lignes = {i.row() for i in self.table.selectedItems()}
        for r in lignes:
            _, a, b = self._lignes[r]
            for f in (a, b):
                if f:
                    try:
                        Path(f).unlink()
                    except OSError:
                        pass
        self.rafraichir()

    def tout_supprimer(self):
        rep = QMessageBox.question(self.window(), t('confirmer'), t('tout_supprimer_confirm'))
        if rep != QMessageBox.StandardButton.Yes:
            return
        for sous in ('avant', 'apres'):
            for f in (chemins.dossier_exemples() / sous).glob('*'):
                try:
                    if f.is_file():
                        f.unlink()
                except OSError:
                    pass
        self.rafraichir()

    # -- entraînement
    def entrainer(self):
        if self.ctx.occupation:
            return
        self.journal.clear()
        self.journal.show()
        self.barre.setValue(0)
        self.barre.setMaximum(1)
        self.barre.setFormat('%v / %m')
        self.barre.show()
        self.l_etat.setText(t('entrainement_en_cours'))
        self.travail = TravailEntrainement(self.ctx.config, self)
        self.travail.progression.connect(self._progression)
        self.travail.termine.connect(self._termine)
        self.travail.echec.connect(self._echec)
        self.ctx.definir_occupation('entrainement')
        self.travail.start()

    def attendre_fin(self, delai_ms=20000):
        if self.travail and self.travail.isRunning():
            return self.travail.wait(delai_ms)
        return True

    def _progression(self, i, n, statut, nom, detail):
        self.barre.setMaximum(max(n, 1))
        self.barre.setValue(i)
        if statut == 'ok':
            self.journal.appendPlainText(f'✓ {nom}')
        elif statut == 'ignore':
            raison = t('raison_cadrage') if detail == 'cadrage' else detail
            self.journal.appendPlainText(f'✗ {nom} : {raison}')
        elif statut == 'fin':
            self.l_etat.setText(t('apprentissage_fin'))

    def _fin_commune(self):
        self.ctx.definir_occupation(None)
        self.travail = None
        self.rafraichir()

    def _termine(self, n):
        self._fin_commune()
        self.l_etat.setText(t('entrainement_ok', n=n))
        self.l_etat.setObjectName('Succes')
        self.l_etat.setStyleSheet('color:#2E8B57;font-weight:600;')

    def _echec(self, message):
        self._fin_commune()
        self.l_etat.setText(message)
        self.l_etat.setStyleSheet('color:#C0392B;font-weight:600;')
        self.journal.appendPlainText(message)
