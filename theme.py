'''Couleurs et feuille de style (QSS) de l'application.'''

FOND = '#EFE6D8'
CARTE = '#FFFDF8'
ENCRE = '#1C1A17'
ORANGE = '#F26522'
ORANGE_FONCE = '#D9541A'
ORANGE_CLAIR = '#FDE9DC'
JAUNE = '#F2B705'
BLEU = '#2F5D7C'
VERT = '#2E8B57'
ROUGE = '#C0392B'
BORD = '#E2D6C2'
BORD_FORT = '#CDBFA6'
DISCRET = '#7A6F60'
MENU_TEXTE = '#CFC6B8'

_MODELE = '''
QWidget { font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif; font-size: 14px; color: @ENCRE; }
QMainWindow, QDialog { background: @FOND; }
QWidget#Page { background: @FOND; }
QScrollArea { background: @FOND; border: none; }
QLabel { background: transparent; }
QToolTip { background: @ENCRE; color: white; border: none; padding: 6px; }

QFrame#Sidebar { background: @ENCRE; }
QLabel#Logo { color: white; font-size: 15px; font-weight: 800; }
QLabel#LogoSous { color: @MENU_TEXTE; font-size: 11px; }
QLabel#VersionMenu { color: #8F8576; font-size: 11px; }
QToolButton#Menu { color: @MENU_TEXTE; background: transparent; border: none; border-radius: 12px;
                   padding: 8px 4px; font-size: 12px; font-weight: 600; }
QToolButton#Menu:hover { background: #2B2823; }
QToolButton#Menu:checked { background: @ORANGE; color: white; }

QFrame#BandeMaj { background: @JAUNE; }
QFrame#BandeMaj QLabel { font-weight: 700; color: @ENCRE; }

QLabel#TitrePage { font-size: 28px; font-weight: 800; }
QLabel#SousTitre { color: @DISCRET; font-size: 14px; }
QLabel#TitreSection { font-size: 16px; font-weight: 700; }
QLabel#Discret { color: @DISCRET; }
QLabel#Erreur { color: @ROUGE; font-weight: 600; }
QLabel#Succes { color: @VERT; font-weight: 600; }
QLabel#Avertissement { color: #9A6B00; font-weight: 600; }

QFrame#Carte { background: @CARTE; border: 1px solid @BORD; border-radius: 14px; }
QFrame#CarteAlerte { background: #FFF4D6; border: 1px solid @JAUNE; border-radius: 14px; }

QFrame#CarteStat { background: @ENCRE; border-radius: 14px; border-left: 6px solid @ORANGE; }
QFrame#CarteStat[accent="bleu"] { border-left-color: #5B8FB4; }
QFrame#CarteStat[accent="vert"] { border-left-color: #4FBF85; }
QFrame#CarteStat[accent="jaune"] { border-left-color: @JAUNE; }
QFrame#CarteStat[accent="rouge"] { border-left-color: #E4695B; }
QLabel#StatTitre { color: @MENU_TEXTE; font-size: 12px; font-weight: 600; }
QLabel#StatValeur { color: white; font-size: 30px; font-weight: 800; }
QLabel#StatSous { color: #9C9284; font-size: 12px; }

QFrame#ZoneDepot { background: @CARTE; border: 2px dashed @BORD_FORT; border-radius: 16px; }
QFrame#ZoneDepot[survol="true"] { border-color: @ORANGE; background: @ORANGE_CLAIR; }
QFrame#ZoneDepot[actif="false"] { background: #F3ECDF; }
QLabel#ZoneTitre { font-size: 16px; font-weight: 700; }

QPushButton { background: @CARTE; border: 1px solid @BORD_FORT; border-radius: 10px; padding: 8px 16px; font-weight: 600; }
QPushButton:hover { background: #F7F0E4; }
QPushButton:pressed { background: #EDE3D2; }
QPushButton:disabled { color: #A89E8E; background: #F1EADD; border-color: @BORD; }
QPushButton#Principal { background: @ORANGE; color: white; border: none; padding: 12px 26px; font-size: 15px; }
QPushButton#Principal:hover { background: @ORANGE_FONCE; }
QPushButton#Principal:disabled { background: #E3BEA9; color: white; }
QPushButton#Danger { color: @ROUGE; }
QPushButton#Lien { border: none; background: transparent; color: @ORANGE_FONCE; padding: 4px 6px; }
QPushButton#Lien:hover { text-decoration: underline; background: transparent; }
QPushButton#Lien:disabled { color: #A89E8E; background: transparent; }
QPushButton#MajBtn { background: @ENCRE; color: white; border: none; }
QPushButton#MajBtn:hover { background: #3A352E; }

QFrame#Segment { background: #E4D9C6; border-radius: 10px; }
QPushButton#SegBtn { border: none; background: transparent; padding: 7px 16px; border-radius: 8px; font-weight: 600; }
QPushButton#SegBtn:hover { background: #EDE3D2; }
QPushButton#SegBtn:checked { background: @ORANGE; color: white; }
QPushButton#SegBtn:disabled { color: #A89E8E; }
QPushButton#SegBtn:checked:disabled { background: #E3BEA9; color: white; }

QLineEdit, QComboBox, QSpinBox { background: @CARTE; border: 1px solid @BORD_FORT; border-radius: 8px; padding: 6px 10px; }
QLineEdit:focus, QComboBox:focus { border-color: @ORANGE; }
QComboBox QAbstractItemView { background: @CARTE; selection-background-color: @ORANGE_CLAIR; selection-color: @ENCRE; }

QProgressBar { border: 1px solid @BORD_FORT; border-radius: 9px; background: @CARTE; text-align: center; min-height: 18px; max-height: 18px; }
QProgressBar::chunk { background: @ORANGE; border-radius: 8px; }

QSlider::groove:horizontal { height: 6px; background: @BORD_FORT; border-radius: 3px; }
QSlider::sub-page:horizontal { background: @ORANGE; border-radius: 3px; }
QSlider::handle:horizontal { background: white; border: 2px solid @ORANGE; width: 14px; height: 14px; margin: -6px 0; border-radius: 9px; }

QListWidget, QPlainTextEdit, QTableWidget { background: @CARTE; border: 1px solid @BORD; border-radius: 10px; }
QListWidget::item { padding: 6px; }
QListWidget::item:selected { background: @ORANGE_CLAIR; color: @ENCRE; }
QListWidget#Vignettes { border-radius: 12px; }
QListWidget#Vignettes::item { border-radius: 10px; padding: 4px; }
QListWidget#Vignettes::item:selected { background: @ORANGE_CLAIR; border: 2px solid @ORANGE; }
QPlainTextEdit { font-family: "Cascadia Mono", "Consolas", monospace; font-size: 12px; }
QTableWidget { gridline-color: @BORD; selection-background-color: @ORANGE_CLAIR; selection-color: @ENCRE; }
QHeaderView::section { background: @FOND; border: none; border-bottom: 1px solid @BORD_FORT; padding: 6px; font-weight: 700; }

QScrollBar:vertical { background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: @BORD_FORT; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: @BORD_FORT; border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

QMessageBox { background: @FOND; }
'''


def feuille_style():
    texte = _MODELE
    for nom in sorted(globals(), key=len, reverse=True):      # les plus longs d'abord (ORANGE_FONCE avant ORANGE)
        valeur = globals()[nom]
        if nom.isupper() and isinstance(valeur, str) and valeur.startswith('#'):
            texte = texte.replace('@' + nom, valeur)
    return texte
