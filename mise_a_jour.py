'''Vérification et installation des mises à jour via les versions (Releases) GitHub.'''
import subprocess
import tempfile
from pathlib import Path

import requests

from version import DEPOT, VERSION

API = 'https://api.github.com/repos/{depot}/releases/latest'


def _numero(texte):
    return tuple(int(x) for x in texte.lstrip('v').split('.') if x.isdigit())


def verifier():
    '''Retourne (version, url_du_fichier) si une version plus récente existe, sinon None.
    Toute erreur (pas d'internet, etc.) est silencieuse : l'application
    continue simplement de fonctionner.'''
    if not DEPOT:
        return None
    try:
        r = requests.get(API.format(depot=DEPOT), timeout=10, headers={
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'})
        if r.status_code != 200:
            return None
        info = r.json()
        if _numero(info['tag_name']) <= _numero(VERSION):
            return None
        for fichier in info.get('assets', []):
            if fichier['name'].endswith('_Setup.exe'):
                return info['tag_name'].lstrip('v'), fichier['browser_download_url']
    except Exception:
        return None
    return None


def telecharger_et_installer(url, progression=None):
    '''Télécharge le nouvel installateur et le lance. L'application doit ensuite se fermer.'''
    cible = Path(tempfile.gettempdir()) / 'PhotoClasse_Setup.exe'
    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get('Content-Length', 0))
        fait = 0
        with open(cible, 'wb') as f:
            for morceau in r.iter_content(1024 * 1024):
                f.write(morceau)
                fait += len(morceau)
                if progression and total:
                    progression(int(100 * fait / total))
    subprocess.Popen([str(cible), '/SILENT', '/CLOSEAPPLICATIONS'],
                     creationflags=subprocess.DETACHED_PROCESS, close_fds=True)
