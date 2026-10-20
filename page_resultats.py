'''Page « Résultats » : galerie des photos produites, glisser-déposer vers l'extérieur, ZIP, liens.'''
from pathlib import Path

from PySide6.QtCore import QMimeData, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QDrag, QIcon, QPixmap, QGuiApplication, QColor
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                               QListView, QListWidget, QListWidgetItem, QMenu, QMessageBox)

import bilan
import chemins
from i18n import t
from taches import Tache, TravailVignettes, creer_zip
from widgets import Carte, PageBase, bouton, texte_discret

ROLE_CHEMIN = Qt.ItemDataRole.UserRole
PAS = 400


class ListeVignettes(QListWidget):
    '''Galerie : on peut faire glisser les photos vers l'Explorateur, un mail, etc.'''

    def startDrag(self, actions):
        items = self.selectedItems()
        if not items:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(i.data(ROLE_CHEMIN)) for i in items])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(items[0].icon().pixmap(72, 72))
        drag.exec(Qt.DropAction.CopyAction)


class PageResultats(PageBase):
    def __init__(self, ctx):
        super().__init__(t('page_resultats'), t('resultats_sous'), defilement=False)
        self.ctx = ctx
        self.tous = []
        self.filtres = []
        self.limite = PAS
        self._items = {}
        self._vignettes = None
        self._anciens = []
        self._taches = []
        self._vide_pm = self._pixmap_vide()

        barre = QHBoxLayout()
        self.recherche = QLineEdit()
        self.recherche.setPlaceholderText(t('rechercher'))
        self.recherche.setClearButtonEnabled(True)
        self.recherche.textChanged.connect(self._filtrer)
        barre.addWidget(self.recherche, 1)
        self.b_actualiser = bouton(t('actualiser'), 'actualiser')
        self.b_actualiser.clicked.connect(self.rafraichir)
        self.b_dossier = bouton(t('ouvrir_dossier'), 'dossier')
        self.b_dossier.clicked.connect(lambda: chemins.ouvrir_dossier(self.ctx.config.dossier_sortie))
        barre.addWidget(self.b_actualiser)
        barre.addWidget(self.b_dossier)
        self.corps.addLayout(barre)

        actions = QHBoxLayout()
        self.l_compte = QLabel('')
        self.l_compte.setObjectName('Discret')
        actions.addWidget(self.l_compte, 1)
        self.b_chemins = bouton(t('copier_chemins'), 'copie')
        self.b_fichiers = bouton(t('copier_fichiers'), 'copie')
        self.b_zip = bouton(t('creer_zip'), 'zip')
        self.b_chemins.clicked.connect(self.copier_chemins)
        self.b_fichiers.clicked.connect(self.copier_fichiers)
        self.b_zip.clicked.connect(self.creer_zip)
        for b in (self.b_chemins, self.b_fichiers, self.b_zip):
            actions.addWidget(b)
        self.corps.addLayout(actions)

        self.liste = ListeVignettes()
        self.liste.setObjectName('Vignettes')
        self.liste.setViewMode(QListView.ViewMode.IconMode)
        self.liste.setResizeMode(QListView.ResizeMode.Adjust)
        self.liste.setMovement(QListView.Movement.Static)
        self.liste.setIconSize(QSize(170, 128))
        self.liste.setGridSize(QSize(196, 172))
        self.liste.setSpacing(4)
        self.liste.setUniformItemSizes(True)
        self.liste.setWordWrap(True)
        self.liste.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.liste.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.liste.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.liste.setDragEnabled(True)
        self.liste.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.liste.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.liste.customContextMenuRequested.connect(self._menu)
        self.liste.itemDoubleClicked.connect(lambda it: self._ouvrir(it.data(ROLE_CHEMIN)))
        self.corps.addWidget(self.liste, 1)

        self.b_plus = bouton(t('afficher_plus'))
        self.b_plus.clicked.connect(self._plus)
        self.corps.addWidget(self.b_plus, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.vide = Carte(t('resultats_vide_titre'))
        self.vide.ajouter(texte_discret(t('resultats_vide_texte')))
        b = bouton(t('aller_traitement'))
        b.clicked.connect(lambda: self.ctx.aller('traitement'))
        self.vide.ajouter(b, alignment=Qt.AlignmentFlag.AlignLeft)
        self.corps.addWidget(self.vide)

        self.l_astuce = texte_discret(t('astuce_glisser'))
        self.corps.addWidget(self.l_astuce)

    @staticmethod
    def _pixmap_vide():
        pm = QPixmap(170, 128)
        pm.fill(QColor('#E9DFCE'))
        return pm

    # -- chargement
    def rafraichir(self):
        self.tous = bilan.lister_sorties(self.ctx.config.dossier_sortie)
        self.limite = PAS
        self._filtrer()

    def _filtrer(self, *_):
        mot = self.recherche.text().strip().lower()
        self.filtres = [p for p in self.tous if mot in p.name.lower()] if mot else list(self.tous)
        self.limite = PAS
        self._afficher()

    def _plus(self):
        self.limite += PAS
        self._afficher()

    def _arreter_vignettes(self):
        v = self._vignettes
        if v is not None:
            v.annuler()
            try:
                v.prete.disconnect(self._vignette_prete)
            except (RuntimeError, TypeError):
                pass
            self._anciens.append(v)
            v.finished.connect(lambda v=v: self._anciens.remove(v) if v in self._anciens else None)
        self._vignettes = None

    def _afficher(self):
        self._arreter_vignettes()
        self.liste.clear()
        self._items = {}
        montres = self.filtres[:self.limite]
        icone_vide = QIcon(self._vide_pm)
        for p in montres:
            it = QListWidgetItem(icone_vide, p.name)
            it.setData(ROLE_CHEMIN, str(p))
            it.setToolTip(str(p))
            it.setSizeHint(QSize(190, 166))
            self.liste.addItem(it)
            self._items[str(p)] = it
        total, nb = len(self.tous), len(self.filtres)
        self.l_compte.setText(t('n_photos_affichees', n=len(montres), total=nb) if nb != total
                              else t('n_photos', n=total))
        vide = total == 0
        self.vide.setVisible(vide)
        self.liste.setVisible(not vide)
        self.l_astuce.setVisible(not vide)
        self.b_plus.setVisible(len(self.filtres) > self.limite)
        for b in (self.b_chemins, self.b_fichiers, self.b_zip):
            b.setEnabled(not vide)
        if montres:
            self._vignettes = TravailVignettes(montres, self)
            self._vignettes.prete.connect(self._vignette_prete)
            self._vignettes.start()

    def _vignette_prete(self, chemin, image):
        it = self._items.get(chemin)
        if it is not None:
            it.setIcon(QIcon(QPixmap.fromImage(image)))

    def attendre_fin(self, delai_ms=3000):
        self._arreter_vignettes()
        for v in list(self._anciens):
            v.wait(delai_ms)

    # -- actions
    def _cibles(self):
        '''Les photos sélectionnées, ou toutes celles du filtre si rien n'est sélectionné.'''
        sel = [Path(i.data(ROLE_CHEMIN)) for i in self.liste.selectedItems()]
        return sel or list(self.filtres)

    def copier_chemins(self):
        cibles = self._cibles()
        QGuiApplication.clipboard().setText('\n'.join(str(p) for p in cibles))
        self.l_compte.setText(t('chemins_copies', n=len(cibles)))

    def copier_fichiers(self):
        cibles = self._cibles()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(p)) for p in cibles])
        QGuiApplication.clipboard().setMimeData(mime)
        self.l_compte.setText(t('fichiers_copies', n=len(cibles)))

    def creer_zip(self):
        cibles = self._cibles()
        if not cibles:
            return
        defaut = str(Path(self.ctx.config.dossier_sortie).parent / 'photos_traitees.zip')
        cible, _ = QFileDialog.getSaveFileName(self, t('creer_zip'), defaut, 'ZIP (*.zip)')
        if not cible:
            return
        self.b_zip.setEnabled(False)
        self.l_compte.setText(t('zip_en_cours'))
        tache = Tache(creer_zip, cibles, self.ctx.config.dossier_sortie, cible, parent=self)
        self._taches.append(tache)
        tache.fini.connect(lambda n, c=cible: self._zip_fini(n, c))
        tache.echec.connect(self._zip_echec)
        tache.finished.connect(lambda: self._taches.remove(tache) if tache in self._taches else None)
        tache.start()

    def _zip_fini(self, n, cible):
        self.b_zip.setEnabled(True)
        self.l_compte.setText(t('zip_ok', n=n))
        chemins.afficher_dans_dossier(cible)

    def _zip_echec(self, message):
        self.b_zip.setEnabled(True)
        QMessageBox.warning(self.window(), t('erreur'), message)

    def _ouvrir(self, chemin):
        QDesktopServices.openUrl(QUrl.fromLocalFile(chemin))

    def _menu(self, pos):
        it = self.liste.itemAt(pos)
        if it is None:
            return
        chemin = it.data(ROLE_CHEMIN)
        menu = QMenu(self)
        a1 = menu.addAction(t('ouvrir_photo'))
        a2 = menu.addAction(t('afficher_dans_dossier'))
        a3 = menu.addAction(t('copier_chemin'))
        choix = menu.exec(self.liste.viewport().mapToGlobal(pos))
        if choix == a1:
            self._ouvrir(chemin)
        elif choix == a2:
            chemins.afficher_dans_dossier(chemin)
        elif choix == a3:
            QGuiApplication.clipboard().setText(chemin)
