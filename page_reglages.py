'''Page « Réglages » : toutes les options, enregistrées automatiquement.'''
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMessageBox, QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QSlider)

import chemins
import pipeline
from i18n import t
from entrainement import ErreurApp
from version import VERSION
from widgets import Carte, Interrupteur, PageBase, Segment, bouton, texte_discret


def _ligne(libelle, widget, aide=''):
    rang = QHBoxLayout()
    rang.setSpacing(12)
    col = QLabel(libelle)
    col.setMinimumWidth(210)
    rang.addWidget(col)
    rang.addWidget(widget)
    rang.addStretch(1)
    return rang


class PageReglages(PageBase):
    def __init__(self, ctx):
        super().__init__(t('page_reglages'), t('reglages_sous'))
        self.ctx = ctx
        cfg = ctx.config
        self._chargement = True

        # --- Sortie
        c = Carte(t('reg_sortie'))
        self.sw_jpeg = Interrupteur()
        self.sw_tiff = Interrupteur()
        self.sw_dng = Interrupteur()
        self.sw_xmp = Interrupteur()
        self.sw_dng.toggled.connect(lambda v: self._format('sortie_dng', v))
        self.sw_jpeg.toggled.connect(lambda v: self._format('sortie_jpeg', v))
        self.sw_tiff.toggled.connect(lambda v: self._format('sortie_tiff', v))
        self.sw_xmp.toggled.connect(lambda v: self._format('sortie_xmp', v))
        c.ajouter_layout(_ligne(t('reg_format_jpeg'), self.sw_jpeg))
        c.ajouter_layout(_ligne(t('reg_format_tiff'), self.sw_tiff))
        c.ajouter_layout(_ligne(t('reg_format_dng'), self.sw_dng))
        c.ajouter_layout(_ligne(t('reg_format_xmp'), self.sw_xmp))
        c.ajouter(texte_discret(t('reg_format_aide')))
        rang = QHBoxLayout()
        rang.setSpacing(12)
        rang.addWidget(QLabel(t('reg_qualite')))
        self.qualite = QSlider(Qt.Orientation.Horizontal)
        self.qualite.setRange(70, 100)
        self.qualite.setFixedWidth(240)
        self.qualite.valueChanged.connect(self._qualite)
        self.l_qualite = QLabel('')
        rang.addWidget(self.qualite)
        rang.addWidget(self.l_qualite)
        rang.addStretch(1)
        c.ajouter_layout(rang)
        self.l_dossier = QLabel('')
        self.l_dossier.setObjectName('Discret')
        self.l_dossier.setWordWrap(True)
        b1 = bouton(t('changer'), 'dossier')
        b1.clicked.connect(self._changer_dossier)
        b2 = bouton(t('ouvrir'), lien=True)
        b2.clicked.connect(lambda: chemins.ouvrir_dossier(self.ctx.config.dossier_sortie))
        r = QHBoxLayout()
        r.addWidget(QLabel(t('dossier_sortie')))
        r.addWidget(self.l_dossier, 1)
        r.addWidget(b1)
        r.addWidget(b2)
        c.ajouter_layout(r)
        self.corps.addWidget(c)

        # --- Fichiers
        c = Carte(t('reg_fichiers'))
        self.sw_raw = Interrupteur()
        self.sw_raw.toggled.connect(self._raw)
        c.ajouter_layout(_ligne(t('reg_conserver_raw'), self.sw_raw))
        c.ajouter(texte_discret(t('reg_conserver_raw_aide')))
        self.sw_apercu = Interrupteur()
        self.sw_apercu.toggled.connect(self._apercu_raw)
        c.ajouter_layout(_ligne(t('reg_apercu'), self.sw_apercu))
        c.ajouter(texte_discret(t('reg_apercu_aide')))
        self.sw_retraiter = Interrupteur()
        self.sw_retraiter.toggled.connect(self._retraiter)
        c.ajouter_layout(_ligne(t('reg_retraiter'), self.sw_retraiter))
        c.ajouter(texte_discret(t('reg_retraiter_aide')))
        self.couleur = Segment([t('couleur_1'), t('couleur_2'), t('couleur_3')])
        self.couleur.change.connect(self._couleur)
        c.ajouter_layout(_ligne(t('reg_couleur'), self.couleur))
        c.ajouter(texte_discret(t('reg_couleur_aide')))
        self.sw_ren = Interrupteur()
        self.sw_ren.toggled.connect(self._renommer)
        c.ajouter_layout(_ligne(t('reg_renommer'), self.sw_ren))
        self.modele = QLineEdit()
        self.modele.setMinimumWidth(240)
        self.modele.textChanged.connect(self._modele)
        c.ajouter_layout(_ligne(t('reg_modele'), self.modele))
        self.l_apercu = QLabel('')
        self.l_apercu.setObjectName('Discret')
        c.ajouter(self.l_apercu)
        self.corps.addWidget(c)

        # --- Traitement
        c = Carte(t('reg_traitement'))
        self.mode = Segment([t('mode_auto'), t('mode_manuel')])
        self.mode.change.connect(self._mode)
        c.ajouter_layout(_ligne(t('reg_mode_defaut'), self.mode))
        rang = QHBoxLayout()
        rang.setSpacing(12)
        etiquette = QLabel(t('reg_marge_haut'))
        etiquette.setMinimumWidth(210)
        rang.addWidget(etiquette)
        self.marge = QSlider(Qt.Orientation.Horizontal)
        self.marge.setRange(0, 25)
        self.marge.setSingleStep(5)
        self.marge.setFixedWidth(240)
        self.marge.valueChanged.connect(self._marge)
        self.l_marge = QLabel('')
        rang.addWidget(self.marge)
        rang.addWidget(self.l_marge)
        rang.addStretch(1)
        c.ajouter_layout(rang)
        c.ajouter(texte_discret(t('reg_marge_haut_aide')))
        self.sw_centrer = Interrupteur()
        self.sw_centrer.toggled.connect(self._centrer)
        c.ajouter_layout(_ligne(t('reg_centrer'), self.sw_centrer))
        c.ajouter(texte_discret(t('reg_centrer_aide')))
        self.corps.addWidget(c)

        # --- Application
        c = Carte(t('reg_application'))
        self.langue = QComboBox()
        self.langue.addItem('Français', 'fr')
        self.langue.addItem('English', 'en')
        self.langue.currentIndexChanged.connect(self._langue)
        c.ajouter_layout(_ligne(t('reg_langue'), self.langue))
        self.l_langue = texte_discret('')
        c.ajouter(self.l_langue)
        self.sw_maj = Interrupteur()
        self.sw_maj.toggled.connect(self._maj_auto)
        c.ajouter_layout(_ligne(t('reg_maj_auto'), self.sw_maj))
        self.b_maj = bouton(t('reg_chercher_maj'))
        self.b_maj.clicked.connect(self._chercher_maj)
        self.l_maj = QLabel(t('version', v=VERSION))
        r = QHBoxLayout()
        r.addWidget(self.b_maj)
        r.addWidget(self.l_maj, 1)
        c.ajouter_layout(r)
        r = QHBoxLayout()
        b = bouton(t('reg_ouvrir_donnees'), 'dossier')
        b.clicked.connect(lambda: chemins.ouvrir_dossier(chemins.dossier_donnees()))
        r.addWidget(b)
        r.addStretch(1)
        c.ajouter_layout(r)
        self.corps.addWidget(c)
        self.corps.addStretch(1)

        ctx.maj.disponible.connect(lambda v, u: self._etat_maj(t('maj_dispo', v=v), 'Avertissement'))
        ctx.maj.a_jour.connect(lambda: self._etat_maj(t('maj_a_jour'), 'Succes'))
        ctx.maj.echec.connect(lambda: self._etat_maj(t('maj_echec'), 'Erreur'))
        self._chargement = False

    # -- affichage
    def rafraichir(self):
        cfg = self.ctx.config
        self._chargement = True
        self.sw_jpeg.setChecked(cfg.sortie_jpeg)
        self.sw_tiff.setChecked(cfg.sortie_tiff)
        self.sw_dng.setChecked(cfg.sortie_dng)
        self.sw_xmp.setChecked(cfg.sortie_xmp)
        self.sw_retraiter.setChecked(cfg.retraiter)
        self.sw_apercu.setChecked(cfg.lecture_apercu)
        self.couleur.set_index(max(0, min(2, int(cfg.mode_couleur) - 1)))
        self.qualite.setValue(int(cfg.qualite_jpeg))
        self.l_qualite.setText(str(int(cfg.qualite_jpeg)))
        self.qualite.setEnabled(cfg.sortie_jpeg)
        self.l_dossier.setText(str(cfg.dossier_sortie))
        self.sw_raw.setChecked(cfg.conserver_raw)
        self.sw_ren.setChecked(cfg.renommer_fichiers)
        self.modele.setText(cfg.modele_renommage)
        self.modele.setEnabled(cfg.renommer_fichiers)
        self.mode.set_index(0 if cfg.mode_automatique else 1)
        self.sw_centrer.setChecked(cfg.centrer_visage)
        self.marge.setValue(int(cfg.marge_haut_photo))
        self.l_marge.setText(f'{int(cfg.marge_haut_photo)} %')
        self.langue.setCurrentIndex(max(0, self.langue.findData(cfg.langue)))
        self.sw_maj.setChecked(cfg.maj_auto)
        self._chargement = False
        self._apercu()

    def occupation_changee(self, occupation):
        pass

    def _etat_maj(self, texte, nom):
        self.l_maj.setText(texte)
        self.l_maj.setObjectName(nom)
        self.l_maj.style().unpolish(self.l_maj)
        self.l_maj.style().polish(self.l_maj)
        self.b_maj.setEnabled(True)

    def _apercu(self):
        cfg = self.ctx.config
        if not cfg.renommer_fichiers:
            self.l_apercu.setText(t('apercu_original'))
            self.l_apercu.setObjectName('Discret')
        elif pipeline.modele_valide(cfg.modele_renommage):
            nom = pipeline.formater_nom(cfg.modele_renommage, 1, 'IMG_1234')
            self.l_apercu.setText(t('apercu_nom', nom=nom, ext='.jpg' if cfg.sortie_jpeg or not cfg.sortie_tiff else '.tif'))
            self.l_apercu.setObjectName('Discret')
        else:
            self.l_apercu.setText(t('modele_invalide'))
            self.l_apercu.setObjectName('Erreur')
        self.l_apercu.style().unpolish(self.l_apercu)
        self.l_apercu.style().polish(self.l_apercu)

    # -- modifications (enregistrées immédiatement)
    def _enregistrer(self):
        if not self._chargement:
            self.ctx.sauver_config()
            self._apercu()

    def _format(self, champ, v):
        if self._chargement:
            return
        setattr(self.ctx.config, champ, bool(v))
        self.qualite.setEnabled(self.ctx.config.sortie_jpeg)
        self._enregistrer()

    def _couleur(self, i):
        self.ctx.config.mode_couleur = int(i) + 1
        self._enregistrer()

    def _apercu_raw(self, v):
        self.ctx.config.lecture_apercu = bool(v)
        self._enregistrer()

    def _retraiter(self, v):
        self.ctx.config.retraiter = bool(v)
        self._enregistrer()

    def _qualite(self, v):
        self.l_qualite.setText(str(v))
        self.ctx.config.qualite_jpeg = int(v)
        self._enregistrer()

    def _changer_dossier(self):
        d = QFileDialog.getExistingDirectory(self, t('dossier_sortie'), str(self.ctx.config.dossier_sortie))
        if d:
            try:
                pipeline.verifier_sortie(d)
            except ErreurApp as e:
                QMessageBox.warning(self.window(), t('erreur'), t(e.cle, **e.params))
                return
            self.ctx.config.dossier_sortie = Path(d)
            self.l_dossier.setText(d)
            self._enregistrer()

    def _raw(self, v):
        self.ctx.config.conserver_raw = bool(v)
        self._enregistrer()

    def _renommer(self, v):
        self.ctx.config.renommer_fichiers = bool(v)
        self.modele.setEnabled(bool(v))
        self._enregistrer()

    def _modele(self, texte):
        if texte.strip():
            self.ctx.config.modele_renommage = texte
        self._enregistrer()

    def _mode(self, i):
        self.ctx.config.mode_automatique = (i == 0)
        self._enregistrer()

    def _centrer(self, v):
        self.ctx.config.centrer_visage = bool(v)
        self._enregistrer()

    def _marge(self, v):
        self.l_marge.setText(f'{v} %')
        self.ctx.config.marge_haut_photo = int(v)
        self._enregistrer()

    def _langue(self, _i):
        if self._chargement:
            return
        nouvelle = self.langue.currentData()
        if nouvelle != self.ctx.config.langue:
            self.ctx.config.langue = nouvelle
            self.l_langue.setText(t('reg_langue_redemarrer'))
            self._enregistrer()

    def _maj_auto(self, v):
        self.ctx.config.maj_auto = bool(v)
        self._enregistrer()

    def _chercher_maj(self):
        self.b_maj.setEnabled(False)
        self.l_maj.setText(t('maj_recherche'))
        self.ctx.maj.verifier()
