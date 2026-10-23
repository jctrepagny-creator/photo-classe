'''Fenêtre de recadrage manuel : on voit l'original en entier, on déplace / redimensionne le cadre.'''
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QSlider,
                               QVBoxLayout, QWidget)

import cadre_math as M
import recadrage
import theme
from i18n import t
from taches import Tache
from traitement_image import appliquer_reglages, vers_uint8
from widgets import Interrupteur, bouton

_en_cours = []        # les travaux en arrière-plan survivent à la fermeture de la fenêtre


def _lancer(tache):
    _en_cours.append(tache)
    tache.finished.connect(lambda: _en_cours.remove(tache) if tache in _en_cours else None)
    tache.start()


class ZoneCadre(QWidget):
    modifie = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 400)
        self.setMouseTracking(True)
        self._pm = None
        self.cadre = (0.0, 0.0, 1.0, 1.0)
        self.initial = self.cadre
        self.ratio_px = None            # largeur / hauteur du cadre d'origine
        self.verrou = True
        self._glisse = None

    def definir(self, image, cadre, ratio_px):
        self._pm = QPixmap.fromImage(image)
        self.cadre = self.initial = tuple(cadre)
        self.ratio_px = ratio_px
        self.update()

    def maj_image(self, image):
        self._pm = QPixmap.fromImage(image)
        self.update()

    def retablir(self):
        self.cadre = self.initial
        self.update()
        self.modifie.emit()

    def _cible(self):
        m = 12
        iw, ih = self._pm.width(), self._pm.height()
        k = min((self.width() - 2 * m) / iw, (self.height() - 2 * m) / ih)
        w, h = iw * k, ih * k
        return ((self.width() - w) / 2, (self.height() - h) / 2, w, h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.fillRect(self.rect(), QColor(theme.ENCRE))
        if self._pm is None:
            p.end()
            return
        cible = self._cible()
        p.drawPixmap(QRectF(*cible), self._pm, QRectF(self._pm.rect()))
        x0, y0, x1, y1 = M.vers_pixels(self.cadre, cible)
        ix, iy, iw, ih = cible
        voile = QColor(0, 0, 0, 140)
        for r in (QRectF(ix, iy, iw, y0 - iy), QRectF(ix, y1, iw, iy + ih - y1),
                  QRectF(ix, y0, x0 - ix, y1 - y0), QRectF(x1, y0, ix + iw - x1, y1 - y0)):
            p.fillRect(r, voile)
        fin = QPen(QColor(255, 255, 255, 110), 1)
        p.setPen(fin)
        for k in (1, 2):                                  # règle des tiers
            p.drawLine(QPointF(x0 + k * (x1 - x0) / 3, y0), QPointF(x0 + k * (x1 - x0) / 3, y1))
            p.drawLine(QPointF(x0, y0 + k * (y1 - y0) / 3), QPointF(x1, y0 + k * (y1 - y0) / 3))
        p.setPen(QPen(QColor(theme.ORANGE), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))
        p.setBrush(QColor('white'))
        for cx, cy in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            p.drawRect(QRectF(cx - 6, cy - 6, 12, 12))
        p.end()

    # -- souris
    def _rect(self):
        return M.vers_pixels(self.cadre, self._cible())

    def mousePressEvent(self, e):
        if self._pm is None or e.button() != Qt.MouseButton.LeftButton:
            return
        pt = (e.position().x(), e.position().y())
        rect = self._rect()
        quoi = M.poignee_sous(pt, rect)
        if quoi:
            self._glisse = (quoi, pt, rect)

    def mouseMoveEvent(self, e):
        if self._pm is None:
            return
        pt = (e.position().x(), e.position().y())
        cible = self._cible()
        if self._glisse is None:
            quoi = M.poignee_sous(pt, self._rect())
            forme = {'hg': Qt.CursorShape.SizeFDiagCursor, 'bd': Qt.CursorShape.SizeFDiagCursor,
                     'hd': Qt.CursorShape.SizeBDiagCursor, 'bg': Qt.CursorShape.SizeBDiagCursor,
                     'milieu': Qt.CursorShape.SizeAllCursor}.get(quoi, Qt.CursorShape.ArrowCursor)
            self.setCursor(forme)
            return
        quoi, depart, rect0 = self._glisse
        lim = (cible[0], cible[1], cible[0] + cible[2], cible[1] + cible[3])
        if quoi == 'milieu':
            nouveau = M.deplacer(rect0, pt[0] - depart[0], pt[1] - depart[1], lim)
        else:
            nouveau = M.redimensionner(rect0, quoi, pt, lim, self.ratio_px if self.verrou else None)
        self.cadre = M.vers_fractions(nouveau, cible)
        self.update()
        self.modifie.emit()

    def mouseReleaseEvent(self, e):
        self._glisse = None


class DialogueRecadrage(QDialog):
    def __init__(self, config, chemin, enreg, parent=None):
        super().__init__(parent)
        self.config, self.chemin, self.enreg = config, Path(chemin), enreg
        self.setWindowTitle(t('recadrage_titre'))
        self.resize(980, 780)
        self.reglages = None
        self.propose = None
        self.carac = None
        self.mini = None
        self.dims = (1, 1)
        self._chargement = True

        mise = QVBoxLayout(self)
        mise.setContentsMargins(20, 18, 20, 18)
        mise.setSpacing(10)
        titre = QLabel(self.chemin.name)
        titre.setObjectName('TitreSection')
        mise.addWidget(titre)
        self.l_etat = QLabel(t('recadrage_charge'))
        self.l_etat.setObjectName('Discret')
        self.l_etat.setWordWrap(True)
        mise.addWidget(self.l_etat)
        self.zone = ZoneCadre()
        self.zone.modifie.connect(self._maj_taille)
        mise.addWidget(self.zone, 1)

        grille = QGridLayout()
        grille.setHorizontalSpacing(12)
        self._curseurs, self._valeurs = {}, {}
        for ligne, (cle, texte, mini_v, maxi_v) in enumerate((
                ('ev', 'reg_exposition', -2.0, 3.0), ('da', 'reg_magenta', -20.0, 20.0),
                ('db', 'reg_cyan', -20.0, 20.0), ('nettete', 'reg_nettete', 0.0, 2.0))):
            s = QSlider(Qt.Orientation.Horizontal)
            s.setRange(int(mini_v * 100), int(maxi_v * 100))
            s.valueChanged.connect(self._curseur_change)
            val = QLabel('')
            val.setMinimumWidth(52)
            grille.addWidget(QLabel(t(texte)), ligne // 2, (ligne % 2) * 3)
            grille.addWidget(s, ligne // 2, (ligne % 2) * 3 + 1)
            grille.addWidget(val, ligne // 2, (ligne % 2) * 3 + 2)
            self._curseurs[cle], self._valeurs[cle] = s, val
        mise.addLayout(grille)
        self._minuteur = QTimer(self)
        self._minuteur.setSingleShot(True)
        self._minuteur.setInterval(70)
        self._minuteur.timeout.connect(self._rafraichir_apercu)

        rang = QHBoxLayout()
        self.sw = Interrupteur()
        self.sw.setChecked(True)
        self.sw.toggled.connect(lambda v: setattr(self.zone, 'verrou', bool(v)))
        rang.addWidget(self.sw)
        rang.addWidget(QLabel(t('garder_format')))
        rang.addSpacing(18)
        self.l_taille = QLabel('')
        self.l_taille.setObjectName('Discret')
        rang.addWidget(self.l_taille)
        rang.addSpacing(18)
        self.sw_apprendre = Interrupteur()
        self.sw_apprendre.setChecked(True)
        rang.addWidget(self.sw_apprendre)
        rang.addWidget(QLabel(t('apprendre_correction')))
        rang.addStretch(1)
        self.b_retablir = bouton(t('retablir'))
        self.b_annuler = bouton(t('annuler'))
        self.b_ok = bouton(t('enregistrer'), principal=True)
        self.b_retablir.clicked.connect(self._retablir)
        self.b_annuler.clicked.connect(self.reject)
        self.b_ok.clicked.connect(self._enregistrer)
        for b in (self.b_retablir, self.b_annuler, self.b_ok):
            rang.addWidget(b)
        mise.addLayout(rang)
        mise.addWidget(QLabel(t('recadrage_aide')))
        for b in (self.b_retablir, self.b_ok):
            b.setEnabled(False)

        tache = Tache(recadrage.preparer, config, enreg['src'], enreg.get('reglages'))
        tache.fini.connect(self._pret)
        tache.echec.connect(self._echec)
        _lancer(tache)

    def _pret(self, res):
        self.reglages, self.dims, self.carac = res['reglages'], res['dims'], res['carac']
        self.propose = dict(self.reglages)
        self.mini = res['mini']
        c = self.reglages['cadre']
        H, W = self.dims
        ratio = ((c[2] - c[0]) * W) / max((c[3] - c[1]) * H, 1)
        self._chargement = True
        for cle, s in self._curseurs.items():
            s.setValue(int(round(self.reglages[cle] * 100)))
        self._chargement = False
        self.zone.definir(self._qimage(), c, ratio)
        self._maj_valeurs()
        self.l_etat.setText(t('recadrage_pret'))
        for b in (self.b_retablir, self.b_ok):
            b.setEnabled(True)
        self._maj_taille()

    def _lire_curseurs(self):
        r = dict(self.reglages)
        for cle, s in self._curseurs.items():
            r[cle] = s.value() / 100.0
        return r

    def _qimage(self):
        r = self._lire_curseurs()
        img = vers_uint8(appliquer_reglages(self.mini, r['ev'], r['da'], r['db'], 0.0))
        h, w = img.shape[:2]
        return QImage(img.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()

    def _maj_valeurs(self):
        r = self._lire_curseurs()
        for cle, val in self._valeurs.items():
            val.setText(f'{r[cle]:+.2f}')

    def _curseur_change(self, *_):
        if self._chargement or self.mini is None:
            return
        self._maj_valeurs()
        self._minuteur.start()

    def _rafraichir_apercu(self):
        self.zone.maj_image(self._qimage())

    def _retablir(self):
        self.zone.retablir()
        self._chargement = True
        for cle, s in self._curseurs.items():
            s.setValue(int(round(self.propose[cle] * 100)))
        self._chargement = False
        self._maj_valeurs()
        self._rafraichir_apercu()

    def _echec(self, message):
        self.l_etat.setText(message)
        self.l_etat.setObjectName('Erreur')
        self.l_etat.style().unpolish(self.l_etat)
        self.l_etat.style().polish(self.l_etat)

    def _maj_taille(self):
        c, (H, W) = self.zone.cadre, self.dims
        self.l_taille.setText(t('taille_px', w=int((c[2] - c[0]) * W), h=int((c[3] - c[1]) * H)))

    def _enregistrer(self):
        for b in (self.b_retablir, self.b_ok, self.b_annuler):
            b.setEnabled(False)
        self.l_etat.setText(t('recadrage_enregistrement'))
        decide = self._lire_curseurs()
        decide['cadre'] = tuple(self.zone.cadre)
        tache = Tache(recadrage.enregistrer, self.config, self.enreg['src'], self.propose, decide,
                      self.chemin, self.carac, self.sw_apprendre.isChecked())
        tache.fini.connect(lambda _r: self.accept())
        tache.echec.connect(self._echec_enreg)
        _lancer(tache)

    def _echec_enreg(self, message):
        for b in (self.b_retablir, self.b_ok, self.b_annuler):
            b.setEnabled(True)
        QMessageBox.warning(self, t('erreur'), message)
