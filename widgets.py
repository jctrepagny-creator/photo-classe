'''Éléments d'interface réutilisables : icônes dessinées, menu, cartes, zone de dépôt...'''
from pathlib import Path

from PySide6.QtCore import Qt, QPointF, QRectF, QSize, Signal
from PySide6.QtGui import (QBrush, QColor, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF)
from PySide6.QtWidgets import (QAbstractButton, QButtonGroup, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QPushButton, QScrollArea, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

import theme
from i18n import t


# --- Icônes (dessinées sur une grille de 24 x 24, aucun fichier image) ------------------
def _lignes(p, *points):
    chemin = QPainterPath()
    chemin.moveTo(QPointF(*points[0]))
    for pt in points[1:]:
        chemin.lineTo(QPointF(*pt))
    p.drawPath(chemin)


def _dessiner(p, nom):
    R = QRectF
    if nom == 'accueil':
        _lignes(p, (3, 11), (12, 3), (21, 11))
        _lignes(p, (5, 10), (5, 21), (19, 21), (19, 10))
        _lignes(p, (10, 21), (10, 15), (14, 15), (14, 21))
    elif nom == 'traitement':                       # appareil photo
        p.drawRoundedRect(R(3, 7, 18, 13), 2.5, 2.5)
        p.drawEllipse(QPointF(12, 13.5), 3.6, 3.6)
        _lignes(p, (8, 7), (9.5, 4), (14.5, 4), (16, 7))
    elif nom == 'exemples':                         # avant -> après
        p.drawRoundedRect(R(2.5, 6, 7.5, 12), 1.5, 1.5)
        p.drawRoundedRect(R(14, 6, 7.5, 12), 1.5, 1.5)
        _lignes(p, (10.8, 12), (13.2, 12))
    elif nom == 'resultats':                        # grille
        for x, y in ((3, 3), (13, 3), (3, 13), (13, 13)):
            p.drawRoundedRect(R(x, y, 8, 8), 1.8, 1.8)
    elif nom == 'reglages':                         # curseurs
        _lignes(p, (4, 6), (6.6, 6)); _lignes(p, (11.4, 6), (20, 6))
        p.drawEllipse(QPointF(9, 6), 2.4, 2.4)
        _lignes(p, (4, 12), (12.6, 12)); _lignes(p, (17.4, 12), (20, 12))
        p.drawEllipse(QPointF(15, 12), 2.4, 2.4)
        _lignes(p, (4, 18), (5.6, 18)); _lignes(p, (10.4, 18), (20, 18))
        p.drawEllipse(QPointF(8, 18), 2.4, 2.4)
    elif nom == 'dossier':
        _lignes(p, (3, 6), (9, 6), (11, 9), (21, 9), (21, 19), (3, 19), (3, 6))
    elif nom == 'telecharger':
        _lignes(p, (12, 4), (12, 15))
        _lignes(p, (7, 10.5), (12, 15.5), (17, 10.5))
        _lignes(p, (4, 20), (20, 20))
    elif nom == 'coche':
        _lignes(p, (4.5, 12.5), (9.5, 17.5), (19.5, 6.5))
    elif nom == 'croix':
        _lignes(p, (6, 6), (18, 18)); _lignes(p, (18, 6), (6, 18))
    elif nom == 'poubelle':
        _lignes(p, (4, 7), (20, 7))
        _lignes(p, (9, 7), (9, 4), (15, 4), (15, 7))
        _lignes(p, (6, 7), (7, 20), (17, 20), (18, 7))
    elif nom == 'fleche':
        _lignes(p, (5, 12), (19, 12))
        _lignes(p, (13, 6), (19, 12), (13, 18))
    elif nom == 'copie':
        p.drawRoundedRect(R(8, 8, 12, 12), 2, 2)
        _lignes(p, (16, 8), (16, 5), (4, 5), (4, 16), (8, 16))
    elif nom == 'zip':
        p.drawRoundedRect(R(3, 4, 18, 5), 1.5, 1.5)
        _lignes(p, (5, 9), (5, 20), (19, 20), (19, 9))
        _lignes(p, (10, 13), (14, 13))
    elif nom == 'actualiser':
        p.drawArc(R(4, 4, 16, 16), 40 * 16, 280 * 16)
        _lignes(p, (17.5, 2.5), (18.5, 7), (14, 7.5))


def pixmap_icone(nom, couleur, taille=24):
    echelle = 2
    pm = QPixmap(taille * echelle, taille * echelle)
    pm.fill(Qt.GlobalColor.transparent)
    pm.setDevicePixelRatio(echelle)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.scale(taille / 24.0, taille / 24.0)
    stylo = QPen(QColor(couleur), 1.9)
    stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
    stylo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(stylo)
    p.setBrush(Qt.BrushStyle.NoBrush)
    _dessiner(p, nom)
    p.end()
    return pm


def icone(nom, couleur, couleur_active=None, taille=24):
    ic = QIcon()
    ic.addPixmap(pixmap_icone(nom, couleur, taille), QIcon.Mode.Normal, QIcon.State.Off)
    if couleur_active:
        pm = pixmap_icone(nom, couleur_active, taille)
        ic.addPixmap(pm, QIcon.Mode.Normal, QIcon.State.On)
        ic.addPixmap(pm, QIcon.Mode.Active, QIcon.State.On)
    return ic


def icone_application():
    pm = QPixmap(128, 128)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(theme.ORANGE))
    p.drawRoundedRect(QRectF(4, 4, 120, 120), 28, 28)
    p.scale(128 / 24.0 * 0.62, 128 / 24.0 * 0.62)
    p.translate(24 * 0.31 / 0.62 * 0.0 + 7.3, 7.3)
    stylo = QPen(QColor('white'), 1.9)
    stylo.setCapStyle(Qt.PenCapStyle.RoundCap)
    stylo.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(stylo)
    p.setBrush(Qt.BrushStyle.NoBrush)
    _dessiner(p, 'traitement')
    p.end()
    return QIcon(pm)


# --- Menu latéral --------------------------------------------------------------------
class BoutonMenu(QToolButton):
    def __init__(self, cle_icone, texte, parent=None):
        super().__init__(parent)
        self.setObjectName('Menu')
        self.setCheckable(True)
        self.setAutoExclusive(False)
        self.setIcon(icone(cle_icone, theme.MENU_TEXTE, 'white', 26))
        self.setIconSize(QSize(26, 26))
        self.setText(texte)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.setFixedSize(92, 74)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class BandeSecurite(QWidget):
    '''Bandeau jaune et noir en haut de la fenêtre (comme sur un chantier).'''

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(8)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(theme.JAUNE))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.ENCRE))
        h, pas = self.height(), 22
        x = -h
        while x < self.width():
            p.drawPolygon(QPolygonF([QPointF(x, h), QPointF(x + 11, h),
                                     QPointF(x + 11 + h, 0), QPointF(x + h, 0)]))
            x += pas
        p.end()


# --- Cartes ---------------------------------------------------------------------------
class Carte(QFrame):
    def __init__(self, titre='', alerte=False, parent=None):
        super().__init__(parent)
        self.setObjectName('CarteAlerte' if alerte else 'Carte')
        self.mise = QVBoxLayout(self)
        self.mise.setContentsMargins(20, 16, 20, 18)
        self.mise.setSpacing(10)
        self.titre = None
        if titre:
            self.titre = QLabel(titre)
            self.titre.setObjectName('TitreSection')
            self.mise.addWidget(self.titre)

    def ajouter(self, widget, **options):
        self.mise.addWidget(widget, **options)
        return widget

    def ajouter_layout(self, layout):
        self.mise.addLayout(layout)
        return layout


class CarteStat(QFrame):
    def __init__(self, titre, accent='orange', parent=None):
        super().__init__(parent)
        self.setObjectName('CarteStat')
        self.setProperty('accent', accent)
        mise = QVBoxLayout(self)
        mise.setContentsMargins(18, 14, 16, 14)
        mise.setSpacing(2)
        self.l_titre = QLabel(titre)
        self.l_titre.setObjectName('StatTitre')
        self.l_valeur = QLabel('-')
        self.l_valeur.setObjectName('StatValeur')
        self.l_sous = QLabel('')
        self.l_sous.setObjectName('StatSous')
        self.l_sous.setWordWrap(True)
        for w in (self.l_titre, self.l_valeur, self.l_sous):
            mise.addWidget(w)
        self.setMinimumHeight(112)

    def maj(self, valeur, sous=''):
        self.l_valeur.setText(str(valeur))
        self.l_sous.setText(sous)


def titre_section(texte):
    lab = QLabel(texte)
    lab.setObjectName('TitreSection')
    return lab


def texte_discret(texte, mot_a_mot=True):
    lab = QLabel(texte)
    lab.setObjectName('Discret')
    lab.setWordWrap(mot_a_mot)
    return lab


def bouton(texte, nom_icone=None, principal=False, danger=False, lien=False):
    b = QPushButton(texte)
    if principal:
        b.setObjectName('Principal')
    elif danger:
        b.setObjectName('Danger')
    elif lien:
        b.setObjectName('Lien')
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if nom_icone:
        couleur = 'white' if principal else (theme.ROUGE if danger else theme.ENCRE)
        b.setIcon(icone(nom_icone, couleur, None, 18))
        b.setIconSize(QSize(18, 18))
    return b


# --- Zone de glisser-déposer ----------------------------------------------------------
class ZoneDepot(QFrame):
    '''Rectangle où l'on dépose des fichiers ou des dossiers (ou que l'on remplit avec les boutons).'''
    deposes = Signal(list)           # liste de chemins (str)
    dossier_utilise = Signal(str)    # dernier dossier consulté

    def __init__(self, titre, sous_titre, filtre='', avec_dossier=True, parent=None):
        super().__init__(parent)
        self.setObjectName('ZoneDepot')
        self.setProperty('survol', False)
        self.setProperty('actif', True)
        self.setAcceptDrops(True)
        self.setMinimumHeight(170)
        self.filtre = filtre
        self.dossier_depart = str(Path.home())

        mise = QVBoxLayout(self)
        mise.setContentsMargins(20, 18, 20, 18)
        mise.setSpacing(6)
        mise.addStretch(1)
        self.l_icone = QLabel()
        self.l_icone.setPixmap(pixmap_icone('telecharger', theme.ORANGE, 40))
        self.l_icone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.l_titre = QLabel(titre)
        self.l_titre.setObjectName('ZoneTitre')
        self.l_titre.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.l_titre.setWordWrap(True)
        self.l_sous = QLabel(sous_titre)
        self.l_sous.setObjectName('Discret')
        self.l_sous.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.l_sous.setWordWrap(True)
        mise.addWidget(self.l_icone)
        mise.addWidget(self.l_titre)
        mise.addWidget(self.l_sous)

        rang = QHBoxLayout()
        rang.setSpacing(10)
        rang.addStretch(1)
        self.b_fichiers = bouton(t('choisir_fichiers'), None)
        self.b_fichiers.clicked.connect(self._choisir_fichiers)
        rang.addWidget(self.b_fichiers)
        self.b_dossier = None
        if avec_dossier:
            self.b_dossier = bouton(t('choisir_dossier'), 'dossier')
            self.b_dossier.clicked.connect(self._choisir_dossier)
            rang.addWidget(self.b_dossier)
        rang.addStretch(1)
        mise.addLayout(rang)
        mise.addStretch(1)

    # -- apparence
    def _survol(self, etat):
        self.setProperty('survol', etat)
        self.style().unpolish(self)
        self.style().polish(self)

    def setEnabled(self, etat):
        super().setEnabled(etat)
        self.setProperty('actif', bool(etat))
        self.style().unpolish(self)
        self.style().polish(self)

    # -- glisser-déposer
    def dragEnterEvent(self, e):
        if self.isEnabled() and e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._survol(True)
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if self.isEnabled() and e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dragLeaveEvent(self, e):
        self._survol(False)

    def dropEvent(self, e):
        self._survol(False)
        chemins = [u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile()]
        if chemins:
            e.acceptProposedAction()
            self.dossier_utilise.emit(str(Path(chemins[0]).parent))
            self.deposes.emit(chemins)

    # -- boutons
    def _choisir_fichiers(self):
        chemins, _ = QFileDialog.getOpenFileNames(self, t('choisir_fichiers'),
                                                  self.dossier_depart, self.filtre)
        if chemins:
            self.dossier_utilise.emit(str(Path(chemins[0]).parent))
            self.deposes.emit(chemins)

    def _choisir_dossier(self):
        d = QFileDialog.getExistingDirectory(self, t('choisir_dossier'), self.dossier_depart)
        if d:
            self.dossier_utilise.emit(str(Path(d).parent))
            self.deposes.emit([d])


# --- Choix à deux ou trois positions ---------------------------------------------------
class Segment(QFrame):
    change = Signal(int)

    def __init__(self, libelles, parent=None):
        super().__init__(parent)
        self.setObjectName('Segment')
        mise = QHBoxLayout(self)
        mise.setContentsMargins(3, 3, 3, 3)
        mise.setSpacing(2)
        self._groupe = QButtonGroup(self)
        self._groupe.setExclusive(True)
        self._boutons = []
        for i, texte in enumerate(libelles):
            b = QPushButton(texte)
            b.setObjectName('SegBtn')
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self._groupe.addButton(b, i)
            mise.addWidget(b)
            self._boutons.append(b)
        self._boutons[0].setChecked(True)
        self._groupe.idClicked.connect(self.change.emit)

    def index(self):
        return max(0, self._groupe.checkedId())

    def set_index(self, i):
        if 0 <= i < len(self._boutons):
            self._boutons[i].setChecked(True)


class Interrupteur(QAbstractButton):
    '''Bouton à bascule (comme sur un téléphone).'''

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def sizeHint(self):
        return QSize(46, 26)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(Qt.PenStyle.NoPen)
        actif = self.isChecked()
        couleur = QColor(theme.ORANGE if actif else theme.BORD_FORT)
        if not self.isEnabled():
            couleur.setAlpha(110)
        p.setBrush(QBrush(couleur))
        p.drawRoundedRect(QRectF(1, 1, 44, 24), 12, 12)
        p.setBrush(QColor('white'))
        x = 24 if actif else 4
        p.drawEllipse(QRectF(x, 4, 18, 18))
        p.end()


# --- Page type ------------------------------------------------------------------------
class PageBase(QWidget):
    '''Titre + sous-titre, puis `self.corps` (un QVBoxLayout) à remplir.'''

    def __init__(self, titre, sous_titre='', defilement=True, parent=None):
        super().__init__(parent)
        if defilement:
            externe = QVBoxLayout(self)
            externe.setContentsMargins(0, 0, 0, 0)
            zone = QScrollArea()
            zone.setWidgetResizable(True)
            zone.setFrameShape(QFrame.Shape.NoFrame)
            interieur = QWidget()
            zone.setWidget(interieur)
            externe.addWidget(zone)
        else:
            interieur = self
        interieur.setObjectName('Page')
        interieur.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.corps = QVBoxLayout(interieur)
        self.corps.setContentsMargins(32, 26, 32, 26)
        self.corps.setSpacing(16)
        self.l_titre = QLabel(titre)
        self.l_titre.setObjectName('TitrePage')
        self.l_sous = QLabel(sous_titre)
        self.l_sous.setObjectName('SousTitre')
        self.l_sous.setWordWrap(True)
        self.corps.addWidget(self.l_titre)
        if sous_titre:
            self.corps.addWidget(self.l_sous)
            self.corps.setSpacing(16)

    def rafraichir(self):
        '''Appelé chaque fois que la page devient visible.'''

    def occupation_changee(self, occupation):
        '''Appelé quand un traitement / un entraînement démarre ou se termine.'''
