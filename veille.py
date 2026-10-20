'''Empêche Windows de se mettre en veille pendant un long traitement (ex. : une nuit).'''
import sys

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _appel(drapeaux):
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(drapeaux)
    except Exception:
        pass


def empecher_veille():
    '''À appeler depuis le fil de traitement lui-même.'''
    _appel(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def autoriser_veille():
    _appel(ES_CONTINUOUS)
