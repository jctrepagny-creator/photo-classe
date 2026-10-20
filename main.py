'''Point d'entrée de Photo Classe.'''
import multiprocessing
import sys
import threading
import traceback
from datetime import datetime


def _journal_erreurs():
    from chemins import dossier_donnees
    return dossier_donnees() / 'erreurs.log'


def _noter(texte):
    try:
        with open(_journal_erreurs(), 'a', encoding='utf-8') as f:
            f.write(f'--- {datetime.now():%Y-%m-%d %H:%M:%S}\n{texte}\n')
    except Exception:
        pass


def _hook(type_, valeur, tb):
    _noter(''.join(traceback.format_exception(type_, valeur, tb)))


def _hook_thread(args):
    _hook(args.exc_type, args.exc_value, args.exc_traceback)


def main():
    multiprocessing.freeze_support()
    sys.excepthook = _hook
    threading.excepthook = _hook_thread
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName('Photo Classe')
    try:
        import i18n
        import parametres
        import theme
        config = parametres.charger()
        i18n.definir_langue(config.langue)
        app.setStyleSheet(theme.feuille_style())
        from interface import FenetrePrincipale
        fenetre = FenetrePrincipale(config)
        fenetre.show()
    except Exception:
        detail = traceback.format_exc()
        _noter(detail)
        QMessageBox.critical(None, 'Photo Classe',
                             'Le démarrage a échoué.\n\nDétail enregistré dans :\n'
                             f'{_journal_erreurs()}\n\n{detail[-600:]}')
        return 1
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
