'''Fenêtre de recadrage manuel : on voit l'original en entier, on déplace / redimensionne le cadre.'''
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QVBoxLayout, QWidget

import cadre_math as M
import recadrage
import theme
from i18n import t
from taches import Tache
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
        self.dims = (1, 1)

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
        rang.addStretch(1)
        self.b_retablir = bouton(t('retablir'))
        self.b_annuler = bouton(t('annuler'))
        self.b_ok = bouton(t('enregistrer'), principal=True)
        self.b_retablir.clicked.connect(self.zone.retablir)
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
        self.reglages, self.dims = res['reglages'], res['dims']
        img = res['apercu']
        h, w = img.shape[:2]
        qi = QImage(img.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()
        c = self.reglages['cadre']
        H, W = self.dims
        ratio = ((c[2] - c[0]) * W) / max((c[3] - c[1]) * H, 1)
        self.zone.definir(qi, c, ratio)
        self.l_etat.setText(t('recadrage_pret'))
        for b in (self.b_retablir, self.b_ok):
            b.setEnabled(True)
        self._maj_taille()

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
        tache = Tache(recadrage.enregistrer, self.config, self.enreg['src'], self.reglages,
                      self.zone.cadre, self.chemin)
        tache.fini.connect(lambda _r: self.accept())
        tache.echec.connect(self._echec_enreg)
        _lancer(tache)

    def _echec_enreg(self, message):
        for b in (self.b_retablir, self.b_ok, self.b_annuler):
            b.setEnabled(True)
        QMessageBox.warning(self, t('erreur'), message)
