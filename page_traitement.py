'''Page « Traitement » : on dépose des photos RAW (fichiers ou dossiers) puis on lance.'''
import time
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
                               QPlainTextEdit, QProgressBar, QFileDialog)

import bilan
import chemins
import pipeline
from dialogue_validation import DialogueValidation
from entrainement import ErreurApp
from i18n import t
from lecture_raw import EXT_TOUT
from taches import TravailLot
from widgets import Carte, PageBase, Segment, ZoneDepot, bouton, texte_discret

FILTRE_RAW = 'Photos (' + ' '.join('*' + e for e in sorted(EXT_TOUT)) + ')'


class PageTraitement(PageBase):
    def __init__(self, ctx):
        super().__init__(t('page_traitement'), t('traitement_sous'))
        self.ctx = ctx
        self.sources = []            # [{'chemin': Path, 'elements': [(fichier, racine)]}]
        self.travail = None

        self.zone = ZoneDepot(t('depot_raw_titre'), t('depot_raw_sous'), 'Tous les fichiers (*.*);;' + FILTRE_RAW)
        self.zone.deposes.connect(self.ajouter)
        self.zone.dossier_utilise.connect(self._memoriser_dossier)
        self.corps.addWidget(self.zone)
        self.l_info = QLabel('')
        self.l_info.setObjectName('Avertissement')
        self.l_info.setWordWrap(True)
        self.l_info.hide()
        self.corps.addWidget(self.l_info)

        # file d'attente
        self.carte_file = Carte(t('file_titre'))
        self.l_total = QLabel('')
        self.carte_file.ajouter(self.l_total)
        self.liste = QListWidget()
        self.liste.setMinimumHeight(110)
        self.liste.setMaximumHeight(190)
        self.liste.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.carte_file.ajouter(self.liste)
        rang = QHBoxLayout()
        self.b_retirer = bouton(t('retirer_selection'), 'croix')
        self.b_vider = bouton(t('tout_vider'), 'poubelle')
        self.b_retirer.clicked.connect(self.retirer)
        self.b_vider.clicked.connect(self.vider)
        rang.addWidget(self.b_retirer)
        rang.addWidget(self.b_vider)
        rang.addStretch(1)
        self.carte_file.ajouter_layout(rang)
        self.corps.addWidget(self.carte_file)

        # options
        carte = Carte(t('options_titre'))
        r1 = QHBoxLayout()
        r1.addWidget(QLabel(t('mode')))
        self.mode = Segment([t('mode_auto'), t('mode_manuel')])
        self.mode.change.connect(self._mode_change)
        r1.addWidget(self.mode)
        r1.addStretch(1)
        carte.ajouter_layout(r1)
        r2 = QHBoxLayout()
        r2.addWidget(QLabel(t('dossier_sortie')))
        self.l_sortie = QLabel('')
        self.l_sortie.setObjectName('Discret')
        self.l_sortie.setWordWrap(True)
        r2.addWidget(self.l_sortie, 1)
        self.b_changer = bouton(t('changer'), 'dossier')
        self.b_changer.clicked.connect(self.changer_sortie)
        b_ouvrir = bouton(t('ouvrir'), lien=True)
        b_ouvrir.clicked.connect(lambda: chemins.ouvrir_dossier(self.ctx.config.dossier_sortie))
        r2.addWidget(self.b_changer)
        r2.addWidget(b_ouvrir)
        carte.ajouter_layout(r2)
        self.corps.addWidget(carte)

        # alerte modèle absent
        self.alerte = Carte(t('pas_de_modele_titre'), alerte=True)
        self.alerte.ajouter(texte_discret(t('pas_de_modele_texte')))
        b = bouton(t('aller_exemples'))
        b.clicked.connect(lambda: self.ctx.aller('exemples'))
        self.alerte.ajouter(b, alignment=Qt.AlignmentFlag.AlignLeft)
        self.corps.addWidget(self.alerte)

        # lancement
        rang = QHBoxLayout()
        self.b_lancer = bouton(t('lancer'), 'traitement', principal=True)
        self.b_lancer.clicked.connect(self.lancer)
        self.b_arreter = bouton(t('arreter'), danger=True)
        self.b_arreter.clicked.connect(self.arreter)
        self.b_arreter.hide()
        rang.addWidget(self.b_lancer)
        rang.addWidget(self.b_arreter)
        rang.addStretch(1)
        self.corps.addLayout(rang)

        self.carte_suivi = Carte(t('suivi_titre'))
        self.barre = QProgressBar()
        self.carte_suivi.ajouter(self.barre)
        self.l_etat = QLabel('')
        self.carte_suivi.ajouter(self.l_etat)
        self.l_compteurs = QLabel('')
        self.l_compteurs.setObjectName('Discret')
        self.carte_suivi.ajouter(self.l_compteurs)
        self.journal = QPlainTextEdit()
        self.journal.setReadOnly(True)
        self.journal.setMaximumBlockCount(1500)
        self.journal.setMinimumHeight(140)
        self.carte_suivi.ajouter(self.journal)
        self.b_voir = bouton(t('voir_resultats'), 'resultats')
        self.b_voir.clicked.connect(lambda: self.ctx.aller('resultats'))
        self.b_voir.hide()
        self.carte_suivi.ajouter(self.b_voir, alignment=Qt.AlignmentFlag.AlignLeft)
        self.carte_suivi.hide()
        self.corps.addWidget(self.carte_suivi)
        self.corps.addStretch(1)

        self._maj_file()

    # -- file d'attente
    def _memoriser_dossier(self, d):
        self.ctx.config.dernier_dossier = Path(d)
        self.ctx.sauver_config()

    def _dejà_en_file(self):
        return {f for s in self.sources for f, _ in s['elements']}

    def ajouter(self, chemins_deposes):
        trouves = pipeline.collecter_photos(chemins_deposes)
        deja = self._dejà_en_file()
        ajout = False
        for c in map(Path, chemins_deposes):
            if c.is_dir():
                el = [(f, r) for f, r in trouves if r == c and f not in deja]
            else:
                el = [(f, r) for f, r in trouves if f == c and f not in deja]
            if el:
                self.sources.append({'chemin': c, 'elements': el})
                deja.update(f for f, _ in el)
                ajout = True
        if ajout:
            self.l_info.hide()
        else:
            self.l_info.setText(t('rien_trouve'))
            self.l_info.show()
        self._maj_file()

    def retirer(self):
        lignes = sorted({self.liste.row(i) for i in self.liste.selectedItems()}, reverse=True)
        for r in lignes:
            del self.sources[r]
        self._maj_file()

    def vider(self):
        self.sources.clear()
        self._maj_file()

    def _elements(self):
        return [e for s in self.sources for e in s['elements']]

    def _maj_file(self):
        self.liste.clear()
        for s in self.sources:
            n = len(s['elements'])
            icone = '📁' if s['chemin'].is_dir() else '📷'
            self.liste.addItem(QListWidgetItem(f"{icone}  {s['chemin'].name or s['chemin']}   -   {t('n_photos', n=n)}"))
        total = len(self._elements())
        self.l_total.setText(t('n_en_attente', n=total) if total else t('file_vide'))
        self.carte_file.setVisible(bool(self.sources))
        self._etat_boutons()

    # -- options
    def _mode_change(self, i):
        self.ctx.config.mode_automatique = (i == 0)
        self.ctx.sauver_config()

    def changer_sortie(self):
        d = QFileDialog.getExistingDirectory(self, t('dossier_sortie'), str(self.ctx.config.dossier_sortie))
        if d:
            try:
                pipeline.verifier_sortie(d)
            except ErreurApp as e:
                QMessageBox.warning(self.window(), t('erreur'), t(e.cle, **e.params))
                return
            self.ctx.config.dossier_sortie = Path(d)
            self.ctx.sauver_config()
            self.rafraichir()

    def rafraichir(self):
        cfg = self.ctx.config
        self.mode.set_index(0 if cfg.mode_automatique else 1)
        self.l_sortie.setText(str(cfg.dossier_sortie))
        self.zone.dossier_depart = str(cfg.dernier_dossier)
        self.alerte.setVisible(not cfg.modele_ia.exists())
        self._etat_boutons()

    def occupation_changee(self, occupation):
        self._etat_boutons()

    def _etat_boutons(self):
        occ = self.ctx.occupation
        libre = occ is None
        self.zone.setEnabled(libre)
        self.b_retirer.setEnabled(libre)
        self.b_vider.setEnabled(libre)
        self.mode.setEnabled(libre)
        self.b_changer.setEnabled(libre)
        self.b_lancer.setEnabled(libre and bool(self._elements()) and self.ctx.config.modele_ia.exists())
        self.b_lancer.setVisible(occ != 'lot')
        self.b_arreter.setVisible(occ == 'lot')

    # -- traitement
    def lancer(self):
        elements = self._elements()
        if not elements or self.ctx.occupation:
            return
        if not self.ctx.config.modele_ia.exists():
            self.rafraichir()
            return
        try:
            pipeline.verifier_sortie(self.ctx.config.dossier_sortie)
        except ErreurApp as e:
            QMessageBox.warning(self.window(), t('erreur'), t(e.cle, **e.params))
            return
        self.ctx.config.mode_automatique = (self.mode.index() == 0)
        self.ctx.sauver_config()
        self.compt = {'ok': 0, 'saute': 0, 'ignore': 0, 'erreur': 0}
        self.t0 = time.time()
        self.journal.clear()
        self.barre.setMaximum(len(elements))
        self.barre.setValue(0)
        self.barre.setFormat('%v / %m')
        self.l_etat.setText(t('demarrage'))
        self._compteurs()
        self.b_voir.hide()
        self.carte_suivi.show()
        self.travail = TravailLot(self.ctx.config, elements, self)
        self.travail.progression.connect(self._progression)
        self.travail.demande_validation.connect(self._validation)
        self.travail.termine.connect(self._termine)
        self.travail.echec.connect(self._echec)
        self.ctx.definir_occupation('lot')
        self.travail.start()

    def arreter(self):
        if self.travail:
            self.b_arreter.setEnabled(False)
            self.l_etat.setText(t('arret_en_cours'))
            self.travail.arreter()

    def attendre_fin(self, delai_ms=20000):
        if self.travail and self.travail.isRunning():
            self.travail.arreter()
            return self.travail.wait(delai_ms)
        return True

    def _compteurs(self):
        c = self.compt
        self.l_compteurs.setText(t('compteurs', ok=c['ok'], saute=c['saute'], erreur=c['erreur'], ignore=c['ignore']))

    def _progression(self, i, n, statut, nom, detail):
        if statut == 'debut':
            self.l_etat.setText(t('en_cours', nom=nom))
            return
        if statut in self.compt:
            self.compt[statut] += 1
        self.barre.setValue(min(i, n))
        fait = self.compt['ok'] + self.compt['erreur'] + self.compt['ignore']
        reste = n - i
        eta = ''
        if fait >= 2 and reste > 0:
            eta = '  -  ' + t('reste', duree=bilan.format_duree((time.time() - self.t0) / fait * reste))
        self.l_etat.setText(t('avancement', i=i, n=n) + eta)
        self._compteurs()
        if statut == 'ok':
            self.journal.appendPlainText(f'✓ {nom}')
        elif statut == 'saute':
            self.journal.appendPlainText(f'↷ {nom}  ({t("deja_fait")})')
        elif statut == 'ignore':
            self.journal.appendPlainText(f'- {nom}  ({t("ignoree")})')
        elif statut == 'erreur':
            self.journal.appendPlainText(f'✗ {nom} : {detail}')

    def _validation(self, mini, reglages):
        dlg = DialogueValidation(mini, reglages, self.window())
        dlg.exec()
        self.travail.repondre(dlg.resultat)

    def _fin_commune(self):
        self.ctx.definir_occupation(None)
        self.b_arreter.setEnabled(True)
        self.travail = None

    def _termine(self, arrete):
        c = self.compt
        self._fin_commune()
        duree = bilan.format_duree(time.time() - self.t0)
        if arrete:
            self.l_etat.setText(t('arrete_bilan', ok=c['ok'], duree=duree))
        else:
            self.l_etat.setText(t('termine_bilan', ok=c['ok'], erreur=c['erreur'], duree=duree))
            self.sources.clear()
            self._maj_file()
        self.b_voir.show()
        self.journal.appendPlainText(self.l_etat.text())
        if c['erreur']:
            self.journal.appendPlainText(t('voir_journal', fichier=str(Path(self.ctx.config.dossier_sortie) / pipeline.FICHIER_ERREURS)))

    def _echec(self, message):
        self._fin_commune()
        self.l_etat.setText(t('echec_lot'))
        self.journal.appendPlainText(message)
        QMessageBox.warning(self.window(), t('erreur'), message)
