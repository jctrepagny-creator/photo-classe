'''Vérification et installation des mises à jour via les versions (Releases) GitHub.'''
import subprocess
import sys
import tempfile
from pathlib import Path

import requests

from version import DEPOT, VERSION

API = 'https://api.github.com/repos/{depot}/releases/latest'


def _numero(texte):
    return tuple(int(x) for x in texte.lstrip('v').split('.') if x.isdigit())


def verifier():
    '''Retourne ('maj', version, url) si une version plus récente existe,
    ('a_jour',) si on est à jour, ('erreur',) si la vérification est impossible.'''
    if not DEPOT:
        return ('erreur',)
    try:
        r = requests.get(API.format(depot=DEPOT), timeout=10, headers={
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'})
        if r.status_code != 200:
            return ('erreur',)
        info = r.json()
        if _numero(info['tag_name']) <= _numero(VERSION):
            return ('a_jour',)
        for fichier in info.get('assets', []):
            if fichier['name'].endswith('_Setup.exe'):
                return ('maj', info['tag_name'].lstrip('v'), fichier['browser_download_url'])
        return ('erreur',)
    except Exception:
        return ('erreur',)


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
    drapeaux = getattr(subprocess, 'DETACHED_PROCESS', 0) if sys.platform == 'win32' else 0
    subprocess.Popen([str(cible), '/SILENT', '/CLOSEAPPLICATIONS'],
                     creationflags=drapeaux, close_fds=True)
