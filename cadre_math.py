'''Calculs géométriques du cadre de recadrage manuel (sans interface : testable).
Un rectangle = (x0, y0, x1, y1) ; `lim` = rectangle de l'image à l'écran.'''


def poignee_sous(pt, rect, tol=14):
    '''Que touche-t-on ? 'hg', 'hd', 'bg', 'bd' (coins), 'milieu' (déplacer) ou None.'''
    x, y = pt
    x0, y0, x1, y1 = rect
    for nom, (cx, cy) in (('hg', (x0, y0)), ('hd', (x1, y0)), ('bg', (x0, y1)), ('bd', (x1, y1))):
        if abs(x - cx) <= tol and abs(y - cy) <= tol:
            return nom
    if x0 < x < x1 and y0 < y < y1:
        return 'milieu'
    return None


def deplacer(rect, dx, dy, lim):
    '''Déplace le cadre sans changer sa taille ni sortir de l'image.'''
    x0, y0, x1, y1 = rect
    w, h = x1 - x0, y1 - y0
    nx = min(max(x0 + dx, lim[0]), lim[2] - w)
    ny = min(max(y0 + dy, lim[1]), lim[3] - h)
    return (nx, ny, nx + w, ny + h)


def redimensionner(rect, coin, pt, lim, ratio=None, mini=40.0):
    '''Tire sur un coin ; le coin opposé reste fixe. `ratio` (largeur / hauteur) verrouille le format.'''
    x0, y0, x1, y1 = rect
    ax = x1 if coin in ('hg', 'bg') else x0
    ay = y1 if coin in ('hg', 'hd') else y0
    sx = -1 if coin in ('hg', 'bg') else 1
    sy = -1 if coin in ('hg', 'hd') else 1
    maxw = (lim[2] - ax) if sx > 0 else (ax - lim[0])
    maxh = (lim[3] - ay) if sy > 0 else (ay - lim[1])
    w = min(max((pt[0] - ax) * sx, mini), maxw)
    h = min(max((pt[1] - ay) * sy, mini), maxh)
    if ratio:
        if w / h > ratio:
            w = h * ratio
        else:
            h = w / ratio
        k = min(1.0, maxw / w, maxh / h)
        w, h = w * k, h * k
    nx, ny = ax + sx * w, ay + sy * h
    return (min(ax, nx), min(ay, ny), max(ax, nx), max(ay, ny))


def vers_pixels(cadre, cible):
    '''Fractions (0-1) -> pixels écran. `cible` = (x, y, largeur, hauteur) de l'image affichée.'''
    cx, cy, cw, ch = cible
    return (cx + cadre[0] * cw, cy + cadre[1] * ch, cx + cadre[2] * cw, cy + cadre[3] * ch)


def vers_fractions(rect, cible):
    cx, cy, cw, ch = cible
    return ((rect[0] - cx) / cw, (rect[1] - cy) / ch, (rect[2] - cx) / cw, (rect[3] - cy) / ch)
