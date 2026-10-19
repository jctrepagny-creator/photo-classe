'''Point d'entrée : python main.py'''
import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from interface import FenetrePrincipale

if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    fenetre = FenetrePrincipale()
    fenetre.resize(780, 700)
    fenetre.show()
    sys.exit(app.exec())
