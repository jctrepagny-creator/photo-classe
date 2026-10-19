'''IA de style locale : apprend, à partir des exemples avant/après, les réglages
et le cadrage à appliquer à chaque photo.'''
import cv2
import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor

from detection_visages import boite_groupe

NOMS_SORTIES = ['ev', 'da', 'db', 'nettete', 'x0', 'y0', 'x1', 'y1']


def extraire_caracteristiques(mini, visages):
    '''mini : petite image float32 RGB (0-1). Retourne un vecteur de mesures.'''
    lab = cv2.cvtColor(mini, cv2.COLOR_RGB2LAB)
    h, w = lab.shape[:2]
    lum = lab[..., 0]
    centre = lab[h // 4: 3 * h // 4, w // 4: 3 * w // 4]
    boite = boite_groupe(visages) or (0.0, 0.0, 1.0, 1.0)
    return np.array([
        lum.mean(), lab[..., 1].mean(), lab[..., 2].mean(), lum.std(),
        np.percentile(lum, 5), np.percentile(lum, 50), np.percentile(lum, 95),
        centre[..., 0].mean(), centre[..., 1].mean(), centre[..., 2].mean(),
        len(visages), *boite], dtype=np.float32)


class StyleIA:
    def __init__(self):
        self.modele = ExtraTreesRegressor(n_estimators=400, min_samples_leaf=2,
                                          n_jobs=-1, random_state=0)
        self.entraine = False

    def entrainer(self, X, Y):
        self.modele.fit(np.array(X), np.array(Y))
        self.entraine = True

    def predire(self, carac):
        v = self.modele.predict(carac.reshape(1, -1))[0]
        r = dict(zip(NOMS_SORTIES, map(float, v)))
        r['ev'] = float(np.clip(r['ev'], -2.0, 2.0))
        r['da'] = float(np.clip(r['da'], -30.0, 30.0))
        r['db'] = float(np.clip(r['db'], -30.0, 30.0))
        r['nettete'] = float(np.clip(r['nettete'], 0.0, 2.0))
        x0, y0, x1, y1 = (min(max(r[k], 0.0), 1.0) for k in ('x0', 'y0', 'x1', 'y1'))
        if x1 - x0 < 0.3 or y1 - y0 < 0.3:
            x0, y0, x1, y1 = 0.0, 0.0, 1.0, 1.0
        r['cadre'] = (x0, y0, x1, y1)
        return r

    def sauver(self, chemin):
        joblib.dump(self.modele, chemin)

    @staticmethod
    def charger(chemin):
        ia = StyleIA()
        ia.modele = joblib.load(chemin)
        ia.entraine = True
        return ia
