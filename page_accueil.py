'''Tableau de bord : chiffres clés, étapes pour commencer, dernières photos.'''
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel

import bilan
import chemins
from entrainement import MIN_PAIRES, info_modele, lister_paires
from i18n import t
from widgets import Carte, CarteStat, PageBase, bouton, texte_discret


class PageAccueil(PageBase):
    def __init__(self, ctx):
        super().__init__(t('page_accueil'), t('accueil_sous'))
        self.ctx = ctx

        grille = QGridLayout()
        grille.setSpacing(14)
        self.s_traitees = CarteStat(t('stat_traitees'), 'orange')
        self.s_paires = CarteStat(t('stat_paires'), 'bleu')
        self.s_modele = CarteStat(t('stat_modele'), 'vert')
        self.s_erreurs = CarteStat(t('stat_erreurs'), 'jaune')
        for i, s in enumerate((self.s_traitees, self.s_paires, self.s_modele, self.s_erreurs)):
            grille.addWidget(s, 0, i)
            grille.setColumnStretch(i, 1)
        self.corps.addLayout(grille)

        self.carte_etapes = Carte(t('etapes_titre'))
        self._lignes = []
        cibles = ('exemples', 'exemples', 'traitement')
        for i, cible in enumerate(cibles, 1):
            rang = QHBoxLayout()
            rond = QLabel(str(i))
            rond.setFixedSize(30, 30)
            rond.setAlignment(Qt.AlignmentFlag.AlignCenter)
            texte = QLabel(t(f'etape_{i}'))
            texte.setWordWrap(True)
            b = bouton(t('aller'), lien=True)
            b.clicked.connect(lambda _=False, c=cible: self.ctx.aller(c))
            rang.addWidget(rond)
            rang.addWidget(texte, 1)
            rang.addWidget(b)
            self.carte_etapes.ajouter_layout(rang)
            self._lignes.append((rond, texte))
        self.corps.addWidget(self.carte_etapes)

        self.carte_recents = Carte(t('recents_titre'))
        self.liste = QLabel()
        self.liste.setTextFormat(Qt.TextFormat.PlainText)
        self.carte_recents.ajouter(self.liste)
        b = bouton(t('voir_resultats'), lien=True)
        b.clicked.connect(lambda: self.ctx.aller('resultats'))
        self.carte_recents.ajouter(b, alignment=Qt.AlignmentFlag.AlignLeft)
        self.corps.addWidget(self.carte_recents)
        self.corps.addStretch(1)

    def rafraichir(self):
        cfg = self.ctx.config
        paires, _, _ = lister_paires(chemins.dossier_exemples())
        info = info_modele(cfg.modele_ia)
        n_ok = bilan.nb_traitees(cfg.dossier_sortie)
        n_err = bilan.nb_erreurs(cfg.dossier_sortie)

        self.s_traitees.maj(n_ok, t('stat_traitees_sous'))
        self.s_paires.maj(len(paires), t('stat_paires_sous', minimum=MIN_PAIRES))
        if info:
            date = bilan.format_date(info.get('date', ''))
            self.s_modele.maj(t('modele_pret'), t('modele_info', date=date, n=info.get('paires') or '?'))
        else:
            self.s_modele.maj(t('modele_absent'), t('modele_absent_sous'))
        self.s_erreurs.maj(n_err, t('stat_erreurs_sous') if n_err else t('aucune_erreur'))

        faits = (len(paires) >= MIN_PAIRES, info is not None, n_ok > 0)
        for (rond, texte), fait in zip(self._lignes, faits):
            if fait:
                rond.setText('✓')
                rond.setStyleSheet('background:#2E8B57;color:white;border-radius:15px;font-weight:700;')
            else:
                rond.setStyleSheet('background:#E4D9C6;border-radius:15px;font-weight:700;')
            font = texte.font()
            font.setStrikeOut(bool(fait))
            texte.setFont(font)
        if not faits[0]:
            self._lignes[0][0].setText('1')
        if not faits[1]:
            self._lignes[1][0].setText('2')
        if not faits[2]:
            self._lignes[2][0].setText('3')

        recents = bilan.lister_sorties(cfg.dossier_sortie)[:6]
        if recents:
            lignes = []
            for p in recents:
                d = bilan.date_fichier(p)
                lignes.append(f"{p.name}    {d:%d/%m/%Y %H:%M}" if d else p.name)
            self.liste.setText('\n'.join(lignes))
        else:
            self.liste.setText(t('aucun_resultat'))
