"""Әр сұраққа жеке сурет. Әр функция Svg қайтарады.

Ереже: сурет сұрақтағы жағдайды көрсетеді, бірақ дұрыс жауапты ашып бермейді.
«СІЗ» — сұрақтағы жүргізушінің көлігі (қызыл), сары үзік көрсеткі — оның ниеті.
"""
from lib import *  # noqa: F401,F403

SCENES = {}


def scene(qid, label):
    def deco(fn):
        SCENES[qid] = (fn, label)
        return fn
    return deco


# ----------------------------------------------------------------------
#  Ортақ көмекшілер
# ----------------------------------------------------------------------

def street(svg, p, kind='day', env='city', n_our=1, n_opp=1, lw=3.5, center='dashed', far=320, walk=3.2,
           ground_kind=None, seed=3, edge=False, road_color='#5a6069'):
    """Перспективадағы көше. Біздің жолақ ортасы u=0."""
    u_r = lw / 2
    u_c = u_r - n_our * lw
    u_l = u_c - n_opp * lw
    out = sky('night' if kind == 'night' else ('fog' if kind == 'fog' else ('overcast' if kind in ('rain', 'overcast') else ('winter' if kind == 'winter' else 'day'))), p.hz)
    if env == 'city':
        out += p_city(p, seed, '#8798a8' if kind != 'night' else '#132033', .7 if kind != 'night' else 1)
    else:
        out += p_hills(p, seed, '#8fb3a1' if kind not in ('night', 'winter') else ('#142019' if kind == 'night' else '#c9d6df'), .7)
    gk = ground_kind or {'night': 'night', 'fog': 'fog', 'winter': 'winter', 'rain': 'overcast', 'overcast': 'overcast'}.get(kind, 'day')
    out += p_ground(p, gk)
    if walk:
        wc = '#cfc8b6' if kind not in ('night',) else '#2a3036'
        if kind == 'winter':
            wc = '#e9eef2'
        out += f'<polygon points="{pts(p.quad(u_r, u_r + walk, 1.2, far, steps=30))}" fill="{wc}"/>'
        out += f'<polygon points="{pts(p.quad(u_l - walk, u_l, 1.2, far, steps=30))}" fill="{wc}"/>'
        out += f'<polygon points="{pts(p.quad(u_r, u_r + .2, 1.2, far, steps=30))}" fill="#9d9788"/>'
        out += f'<polygon points="{pts(p.quad(u_l - .2, u_l, 1.2, far, steps=30))}" fill="#9d9788"/>'
    rc = road_color if kind != 'night' else '#22272d'
    if kind == 'rain':
        rc = '#4a5059'
    if kind == 'winter':
        rc = '#7d858e'
    out += f'<polygon points="{pts(p.quad(u_l, u_r, 1.2, far, steps=40))}" fill="{rc}"/>'
    mk = MARK if kind != 'night' else '#c9ccc8'
    op = 1 if kind not in ('winter',) else .7
    if center == 'dashed':
        out += p_line(p, u_c, 1.2, far, .14, (3, 6), mk, op)
    elif center == 'solid':
        out += p_line(p, u_c, 1.2, far, .14, None, mk, op)
    elif center == 'double':
        out += p_line(p, u_c - .12, 1.2, far, .12, None, mk, op) + p_line(p, u_c + .12, 1.2, far, .12, None, mk, op)
    for i in range(1, n_our):
        out += p_line(p, u_r - i * lw, 1.2, far, .13, (3, 6), mk, op)
    for i in range(1, n_opp):
        out += p_line(p, u_c - i * lw, 1.2, far, .13, (3, 6), mk, op)
    if edge:
        out += p_line(p, u_r - .25, 1.2, far, .12, None, mk, op) + p_line(p, u_l + .25, 1.2, far, .12, None, mk, op)
    return out, (u_l, u_c, u_r)


def puddles(p, seed=1, n=9, u0=-3.0, u1=1.6, z0=7, z1=40):
    """Ылғал жолдағы шалшықтар мен шағылысулар."""
    rnd = random.Random(seed)
    out = ''
    for _ in range(n):
        u, z = rnd.uniform(u0, u1), rnd.uniform(z0, z1)
        x, y = p.pt(u, z)
        sc = p.scale(z)
        out += f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(sc * rnd.uniform(.6, 1.4))}" ry="{f(sc * rnd.uniform(.08, .16))}" fill="#a9bccd" opacity=".45"/>'
    return out


def caption(t, x=480, y=516, size=18):
    w = len(t) * size * .56 + 34
    return (f'<rect x="{f(x - w / 2)}" y="{f(y - size - 8)}" width="{f(w)}" height="{f(size + 18)}" rx="{f((size + 18) / 2)}" fill="#0f1b27" opacity=".78"/>'
            + text(x, y + 1, t, size, '#fff', 800))


def tl_card(svg, x, y, state, s=.62):
    """Бағдаршам суреті бар ақ карточка (жоғарыдан көрінетін сахналар үшін)."""
    w, h = 54 * s + 46, 150 * s + 40
    return card(x, y, w, h) + traffic_light(svg, x + w / 2, y + 20, s, state, pole=False)


def sign_card(x, y, kind, s=70, **kw):
    w, h = s + 34, s + 34
    if kind == 'lanes':
        w = s * 1.2 + 34
    return card(x, y, w, h) + f'<g transform="translate({f(x + w / 2)} {f(y + h / 2)})">{sign(kind, s, **kw)}</g>'


def city4(svg, arms='NSEW', **kw):
    """Стандарт қиылыс (бір жолақ әр бағытта)."""
    return crossroads(svg, 480, 270, arms, **kw)


# Жоғарыдан көріністегі стандарт координаттар (cx=480, cy=270, жолақ=58)
# Тік жол: оңтүстіктен солтүстікке жүретін жолақ x=509, қарсы жолақ x=451.
# Көлденең жол: шығысқа x→ жолақ y=299, батысқа жолақ y=241.
NB, SB, EB, WB = 509, 451, 299, 241


def p_xroad(p, z0, z1, ul, ur, kind='day', walk=2.6, center=True):
    rc = '#5a6069' if kind != 'night' else '#22272d'
    if kind == 'winter':
        rc = '#7d858e'
    wc = {'night': '#2a3036', 'winter': '#e9eef2'}.get(kind, '#cfc8b6')
    out = p_band(p, -90, 90, z0, z1, rc)
    out += p_band(p, -90, ul, z1, z1 + walk, wc) + p_band(p, ur, 90, z1, z1 + walk, wc)
    out += p_band(p, -90, ul - .0, z0 - walk, z0, wc) + p_band(p, ur, 90, z0 - walk, z0, wc)
    if center:
        zm = (z0 + z1) / 2
        u = -90
        while u < 90:
            if u + 3 < ul - .5 or u > ur + .5:
                out += p_band(p, u, u + 3, zm - .3, zm + .3, MARK)
            u += 6
    return out


def p_stopline(p, u0, u1, z):
    return p_band(p, u0, u1, z, z + .45, MARK)


def p_cross_car(svg, p, z, u, color='blue', facing='right'):
    x, yb = p.pt(u, z, 0)
    return car_side(svg, x, yb, 4.4 * p.scale(z), color, facing)


def p_car_ahead(svg, p, u, z, color='blue', **kw):
    x, yb = p.pt(u, z, 0)
    return car_rear(svg, x, yb, 1.8 * p.scale(z), color, **kw)


def p_car_oncoming(svg, p, u, z, color='white', **kw):
    x, yb = p.pt(u, z, 0)
    return car_front(svg, x, yb, 1.8 * p.scale(z), color, **kw)


def p_person(p, u, z, coat='#3b82c4', pose='walk', facing=1):
    x, yb = p.pt(u, z, 0)
    return person(x, yb, 1.72 * p.scale(z), coat, pose=pose, facing=facing)


def house(p, u, za, zb, h, color, side=1, night=False, wide=9.0):
    """Жол бойындағы үй: бүйір беті (жолға қараған) + алдыңғы беті."""
    out = ''
    sideface = [p.pt(u, za, 0), p.pt(u, zb, 0), p.pt(u, zb, h), p.pt(u, za, h)]
    front = [p.pt(u, za, 0), p.pt(u + side * wide, za, 0), p.pt(u + side * wide, za, h), p.pt(u, za, h)]
    out += f'<polygon points="{pts(front)}" fill="{color}"/><polygon points="{pts(front)}" fill="#000" opacity=".10"/>'
    out += f'<polygon points="{pts(sideface)}" fill="{color}"/>'
    win = '#ffe39a' if night else '#8ea6ba'
    rows = max(1, int(h // 3.3))
    # бүйір бетіндегі терезелер
    n = max(1, int((zb - za) // 3.2))
    for r in range(rows):
        h0, h1 = 1.2 + r * 3.3, 2.6 + r * 3.3
        if h1 > h - .5:
            break
        for i in range(n):
            z0 = za + (zb - za) * (i + .25) / n
            z1 = za + (zb - za) * (i + .75) / n
            q = [p.pt(u, z0, h0), p.pt(u, z1, h0), p.pt(u, z1, h1), p.pt(u, z0, h1)]
            out += f'<polygon points="{pts(q)}" fill="{win}" opacity="{.9 if night and (i + r) % 3 else .8}"/>'
        for i in range(3):
            uu0 = u + side * wide * (i + .25) / 3
            uu1 = u + side * wide * (i + .7) / 3
            q = [p.pt(uu0, za, h0), p.pt(uu1, za, h0), p.pt(uu1, za, h1), p.pt(uu0, za, h1)]
            out += f'<polygon points="{pts(q)}" fill="{win}" opacity=".7"/>'
    top = [p.pt(u, za, h), p.pt(u, zb, h)]
    out += f'<path d="M{f(top[0][0])} {f(top[0][1])} L{f(top[1][0])} {f(top[1][1])}" stroke="#000" stroke-opacity=".15" stroke-width="2"/>'
    return out


def facades(p, u, z0, z1, side=None, seed=1, night=False):
    """Көше бойындағы үйлер қатары (алыстан жақынға қарай салынады)."""
    rnd = random.Random(seed)
    side = side if side is not None else (1 if u > 0 else -1)
    cols = ['#d8cbb8', '#c3ccd4', '#dcc3ad', '#c9d2c0', '#d6cfdc', '#e2d6c2'] if not night else ['#1c2633', '#222d3b', '#1a2430']
    segs = []
    z = z0
    while z < z1:
        d = rnd.uniform(10, 18)
        segs.append((z, min(z + d, z1), rnd.uniform(8, 19), rnd.choice(cols)))
        z += d + rnd.uniform(3, 6)
    out = ''
    for za, zb, h, c in reversed(segs):
        out += house(p, u, za, zb, h, c, side, night)
    return out

def my_car(svg, p, z=5.0, u=0.0, color='red', label=True, **kw):
    """Біздің көлік (артынан, алдыңғы планда)."""
    x, yb = p.pt(u, z, 0)
    w = 1.8 * p.scale(z)
    out = car_rear(svg, x, yb, w, color, **kw)
    if label:
        out += you(x + w * .62, yb - w * .62)
    return out


# ======================================================================
#  БАҒДАРШАМ ЖӘНЕ РЕТТЕУШІ
# ======================================================================

@scene('g001', 'Қиылыс алдындағы қызыл бағдаршам және тоқтау сызығы')
def g001():
    s = Svg('Қиылыс алдындағы қызыл бағдаршам')
    p = P()
    base, (ul, uc, ur) = street(s, p, walk=4)
    s.add(base, facades(p, ur + 4.5, 26, 140, seed=2), facades(p, ul - 4.5, 26, 140, seed=5))
    s.add(p_xroad(p, 15.5, 24, ul, ur))
    s.add(p_tree(p, ur + 2.6, 30, 6, seed=3), p_tree(p, ul - 2.6, 34, 6, seed=4))
    s.add(p_cross_car(s, p, 22, -10, 'grey', 'left'), p_cross_car(s, p, 17.6, 6.5, 'yellow', 'right'))
    s.add(p_zebra(p, ul, ur, 13, 15.5), p_stopline(p, uc, ur, 11.6))
    s.add(p_person(p, ur + 1.5, 14.2, '#d9534f', 'stand', -1))
    s.add(p_tlight(s, p, ur + 1.1, 12.0, 'red', 1.85))
    s.add(my_car(s, p))
    return s

@scene('g002', 'Жасыл сигнал, бірақ қиылыстан кейін кептеліс')
def g002():
    s = Svg('Жасыл сигнал, бірақ қиылыстың арғы жағында кептеліс')
    s.add(city4(s, blocks='city'))
    for y, c in ((-40, 'grey'), (68, 'white'), (166, 'blue')):
        s.add(car(s, NB, y, 0, c, brake=True))
    s.add(car(s, SB, 120, 180, 'silver'), car(s, 120, WB, 270, 'orange'), car(s, 860, EB, 90, 'teal'))
    s.add(path_arrow(s, f'M{NB} 400 L{NB} 236'), qmark(NB + 52, 238))
    s.add(car(s, NB, 448, 0, 'red', label=you(NB + 62, 448)))
    s.add(tl_card(s, 846, 18, 'green'))
    return s


@scene('g003', 'Сары сигнал жанып тұрған бағдаршам')
def g003():
    s = Svg('Бағдаршамның сары сигналы')
    p = P()
    base, (ul, uc, ur) = street(s, p, n_our=2, n_opp=2, walk=4)
    s.add(base, facades(p, ur + 4.5, 27, 140, seed=7), facades(p, ul - 4.5, 27, 140, seed=8))
    s.add(p_xroad(p, 16, 25, ul, ur))
    s.add(p_tree(p, ur + 2.6, 32, 6, seed=5), p_tree(p, ul - 2.6, 30, 6, seed=6))
    s.add(p_cross_car(s, p, 23, -12, 'white', 'left'))
    s.add(p_zebra(p, ul, ur, 13.4, 16), p_stopline(p, uc, ur, 12))
    s.add(p_car_ahead(s, p, -3.5, 12.8, 'silver'))
    s.add(p_tlight(s, p, ur + 1.1, 12.4, 'yellow', 1.85))
    s.add(my_car(s, p))
    return s

@scene('g004', 'Жыпылықтап тұрған сары бағдаршам')
def g004():
    s = Svg('Жыпылықтаған сары бағдаршам')
    p = P()
    base, (ul, uc, ur) = street(s, p, walk=4)
    s.add(base, facades(p, ur + 4.5, 26, 140, seed=9), facades(p, ul - 4.5, 26, 140, seed=10))
    s.add(p_xroad(p, 15.5, 24, ul, ur))
    s.add(p_tree(p, ur + 2.6, 30, 6, seed=7), p_tree(p, ul - 2.6, 33, 6, seed=8))
    s.add(p_cross_car(s, p, 22, -16, 'white', 'left'), p_cross_car(s, p, 17.8, 7.5, 'blue', 'right'))
    s.add(p_zebra(p, ul, ur, 13, 15.5))
    s.add(p_tlight(s, p, ur + 1.1, 12.0, 'yellow-flash', 1.85))
    s.add(my_car(s, p))
    return s

@scene('g005', 'Реттеуші мен бағдаршам қатар тұрған қиылыс')
def g005():
    s = Svg('Қиылыс ортасында реттеуші, бағдаршам жасыл')
    p = P()
    base, (ul, uc, ur) = street(s, p, n_our=2, n_opp=2, walk=4)
    s.add(base, facades(p, ur + 4.5, 28, 140, seed=11), facades(p, ul - 4.5, 28, 140, seed=12))
    s.add(p_xroad(p, 15, 27, ul, ur))
    s.add(p_cross_car(s, p, 24.5, -14, 'teal', 'left'))
    x, yb = p.pt(-1.6, 17, 0)
    sc = p.scale(17)
    s.add(f'<ellipse cx="{f(x)}" cy="{f(yb)}" rx="{f(sc * 1.1)}" ry="{f(sc * .3)}" fill="#ececec" stroke="#c9c9c9"/>')
    s.add(officer_front(x, yb, 2.2 * sc))
    s.add(p_zebra(p, ul, ur, 12.6, 15), p_stopline(p, uc, ur, 11.4))
    s.add(p_tlight(s, p, ur + 1.1, 11.8, 'green', 1.85))
    s.add(my_car(s, p))
    return s

@scene('g006', 'STOP белгісі, тоқтау сызығы және басты жол')
def g006():
    s = Svg('STOP белгісі тұрған қиылыс')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.6)
    s.add(base)
    s.add(p_tree(p, ur + 9, 44, 7, seed=1), p_tree(p, ul - 8, 48, 8, seed=2), p_tree(p, ur + 14, 60, 6, 'pine'))
    s.add(p_xroad(p, 14.5, 22, ul, ur, walk=1.4))
    s.add(p_cross_car(s, p, 20.6, -11, 'white', 'left'), p_cross_car(s, p, 16.4, 9, 'blue', 'right'))
    s.add(p_stopline(p, uc, ur, 13))
    s.add(p_sign(p, ur + 1.3, 8.2, 'stop', 1.1))
    s.add(my_car(s, p))
    return s

@scene('g007', '«Жол беріңіз» белгісі, алда басты жол')
def g007():
    s = Svg('«Жол беріңіз» белгісі, алда көліктер жүретін басты жол')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.6)
    s.add(base)
    s.add(p_tree(p, ur + 9, 40, 7, seed=4), p_tree(p, ul - 8, 44, 6, seed=5), p_tree(p, ur + 14, 60, 7, 'pine'))
    s.add(p_xroad(p, 14.5, 22, ul, ur, walk=1.4))
    s.add(p_cross_car(s, p, 20.4, -7, 'orange', 'left'), p_cross_car(s, p, 16.4, 9.5, 'silver', 'right'))
    for k in range(int((ur - uc) / .9)):
        s.add(p_band(p, uc + .15 + k * .9, uc + .6 + k * .9, 13.1, 13.6, MARK))
    s.add(p_sign(p, ur + 1.3, 8.2, 'yield', 1.1))
    s.add(my_car(s, p))
    return s

@scene('g008', '«Кіруге тыйым салынады» белгісі бар көшенің кіреберісі')
def g008():
    s = Svg('«Кіруге тыйым салынады» белгілері тұрған көше')
    p = P()
    base, (ul, uc, ur) = street(s, p, n_our=1, n_opp=1, center=None, walk=3)
    s.add(base, facades(p, ur + 3.5, 13, 140, seed=13), facades(p, ul - 3.5, 13, 140, seed=14))
    s.add(p_car_oncoming(s, p, -1.6, 36, 'grey', lights=None), p_car_oncoming(s, p, 1.0, 24, 'yellow', lights=None))
    s.add(p_sign(p, ur + .9, 11.5, 'no_entry', 1.1), p_sign(p, ul - .7, 11.5, 'no_entry', 1.1))
    s.add(my_car(s, p, z=5.4))
    return s

@scene('g009', '«Бас жол» белгісі, оң жақтан жанама жол қосылады')
def g009():
    s = Svg('«Бас жол» белгісі және жанама жолдағы көлік')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.5, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 10, 36, 7, seed=6), p_tree(p, ul - 9, 26, 7, seed=7), p_tree(p, ur + 6, 52, 6, 'pine'))
    s.add(p_band(p, -60, ul, 30, 35, '#5a6069'), p_band(p, ur, 60, 17, 23, '#5a6069'))
    s.add(p_car_oncoming(s, p, -3.5, 46, 'white', lights=None))
    x, yb = p.pt(ur + 4.2, 19.2, 0)
    s.add(car_side(s, x, yb, 4.4 * p.scale(19.2), 'blue', 'left'))
    s.add(p_sign(p, ur + 1.2, 8.2, 'main', 1.1))
    s.add(my_car(s, p))
    return s

@scene('g010', '«60» жылдамдық шектеу белгісі')
def g010():
    s = Svg('Жылдамдықты 60 км/сағ-қа шектейтін белгі')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 10, 50, 8, seed=9), p_tree(p, ul - 6, 40, 7, 'pine'), p_tree(p, ur + 6, 30, 7, seed=8), p_tree(p, ul - 10, 24, 8, seed=10))
    s.add(p_car_oncoming(s, p, -3.5, 62, 'silver', lights=None), p_car_ahead(s, p, 0, 34, 'blue'))
    s.add(p_sign(p, ur + 1.2, 8.0, 'speed', 1.1, n='60'))
    s.add(my_car(s, p))
    return s

@scene('g011', '«Жаяу жүргіншілер өткелі» белгісі мен зебра')
def g011():
    s = Svg('Жаяу жүргіншілер өткелі')
    p = P()
    base, (ul, uc, ur) = street(s, p, walk=4)
    s.add(base, facades(p, ur + 4.5, 20, 140, seed=15), facades(p, ul - 4.5, 20, 140, seed=16))
    s.add(p_tree(p, ur + 2.6, 24, 6, seed=11), p_tree(p, ul - 2.6, 28, 6, seed=12))
    s.add(p_zebra(p, ul, ur, 11.5, 14.5))
    s.add(p_sign(p, ul - 1.0, 15, 'crosswalk', 1.0))
    s.add(p_person(p, ul - 1.2, 13.6, '#f0a030', 'walk', 1))
    s.add(p_person(p, ur + 1.0, 12.6, '#2f9e6b', 'walk', -1))
    s.add(p_sign(p, ur + 1.0, 11.0, 'crosswalk', 1.0))
    s.add(my_car(s, p))
    return s

def roundabout(s, cx=480, cy=270, r_in=96, r_out=176, hw=58):
    out = f'<rect width="{W}" height="{H}" fill="{WALK}"/><rect width="{W}" height="{H}" fill="url(#tiles)"/>'
    s.define('tiles', '<pattern id="tiles" width="26" height="26" patternUnits="userSpaceOnUse"><path d="M0 0H26V26" fill="none" stroke="#c9c3b5" stroke-width="1.2"/></pattern>')
    a = 'fill="url(#asph)"'
    for k, (x, y, w, h) in enumerate(((-60, -60, cx - hw - 24 + 60, cy - hw - 24 + 60), (cx + hw + 24, -60, W, cy - hw - 24 + 60),
                                      (-60, cy + hw + 24, cx - hw - 24 + 60, H), (cx + hw + 24, cy + hw + 24, W, H))):
        out += block_fill(x, y, w, h, 30, 'grass', 40 + k)
    out += f'<circle cx="{cx}" cy="{cy}" r="{r_out + 24}" fill="{WALK}"/>'
    out += f'<rect x="{cx - hw}" y="-5" width="{2 * hw}" height="{H + 10}" {a}/><rect x="-5" y="{cy - hw}" width="{W + 10}" height="{2 * hw}" {a}/>'
    out += f'<circle cx="{cx}" cy="{cy}" r="{r_out}" {a}/>'
    for ang in (0, 90, 180, 270):
        out += (f'<g transform="translate({cx} {cy}) rotate({ang})">'
                f'<path d="M0 {r_out + 34} V460" stroke="{MARK}" stroke-width="4" stroke-dasharray="26 22"/>'
                f'<rect x="4" y="{r_out + 10}" width="{hw - 8}" height="5" fill="{MARK}"/>'
                f'<path d="M{-hw} {r_out - 2} V460 M{hw} {r_out - 2} V460" stroke="{CURB}" stroke-width="3"/></g>')
    out += f'<circle cx="{cx}" cy="{cy}" r="{(r_in + r_out) / 2}" fill="none" stroke="{MARK}" stroke-width="3" stroke-dasharray="20 22" opacity=".8"/>'
    out += f'<circle cx="{cx}" cy="{cy}" r="{r_in}" fill="#a8d08f" stroke="{CURB}" stroke-width="6"/>'
    out += f'<circle cx="{cx}" cy="{cy}" r="{r_in - 16}" fill="#93c57a"/>'
    out += tree_top(cx - 20, cy - 14, 30) + tree_top(cx + 30, cy + 22, 22) + f'<circle cx="{cx + 34}" cy="{cy - 34}" r="12" fill="#e9b949"/>'
    return out


@scene('g012', 'Айналма қозғалысы бар қиылыс және 4.3 белгісі')
def g012():
    s = Svg('Айналма қозғалыс белгісі тұрған қиылыс')
    s.add(roundabout(s))
    # айналмадағы көліктер (сағат тіліне қарсы)
    for ang, c in ((200, 'blue'), (320, 'yellow'), (20, 'white')):
        rr = 136
        x = 480 + rr * math.cos(math.radians(ang))
        y = 270 + rr * math.sin(math.radians(ang))
        s.add(car(s, x, y, ang + 180, c, scale=.9))
    s.add(car(s, 509, 500, 0, 'red', label=you(570, 500)))
    s.add(post_sign(590, 470, 'roundabout', 62))
    s.add(sign_card(838, 16, 'roundabout', 84))
    return s


@scene('g013', 'Тұтас сызықпен бөлінген жол, алда баяу трактор')
def g013():
    s = Svg('Қарсы бағыттағы жолақтарды бөлетін тұтас сызық')
    s.add(straight_road(s, 'v', 480, 58, (1, 1), 'solid', 'grass', 21))
    s.add(car(s, 509, 210, 0, 'green', 'tractor'), car(s, 451, 40, 180, 'silver'))
    s.add(path_arrow(s, 'M509 400 C509 340 451 340 451 280 L451 200'), qmark(400, 300))
    s.add(car(s, 509, 440, 0, 'red', label=you(572, 440)))
    return s


@scene('g014', 'Жолақтарды бөлетін үзік сызықтар')
def g014():
    s = Svg('Бір бағыттағы жолақтарды бөлетін үзік сызықтар')
    s.add(straight_road(s, 'v', 480, 116, (2, 2), 'double', 'city', 22))
    s.add(car(s, 567, 120, 0, 'blue'), car(s, 509, 30, 0, 'white'), car(s, 393, 160, 180, 'grey'), car(s, 451, 380, 180, 'yellow'))
    s.add(path_arrow(s, 'M567 410 C567 350 509 340 509 270'), qmark(450, 300))
    s.add(car(s, 567, 452, 0, 'red', signal='left', label=you(630, 452)))
    return s


@scene('g015', '«Тұраққа қоюға тыйым» және «Тоқтауға тыйым» белгілері')
def g015():
    s = Svg('Екі түрлі белгі: тұраққа қоюға тыйым және тоқтауға тыйым')
    p = P()
    base, (ul, uc, ur) = street(s, p)
    s.add(base, facades(p, ur + 3.2, 14, 120, seed=17), facades(p, ul - 3.2, 14, 120, seed=18))
    s.add(p_car_ahead(s, p, 0, 26, 'silver'))
    s.add(f'<rect width="{W}" height="{H}" fill="#0f1b27" opacity=".28"/>')
    s.add(card(250, 120, 200, 236) + f'<g transform="translate(350 220)">{sign("no_parking", 150)}</g>')
    s.add(card(510, 120, 200, 236) + f'<g transform="translate(610 220)">{sign("no_stopping", 150)}</g>')
    s.add(text(480, 252, '=', 54, '#fff', 900), qmark(480, 180, 22))
    s.add(text(350, 340, '3.28', 20, '#5b6b7b', 800), text(610, 340, '3.27', 20, '#5b6b7b', 800))
    return s


# ======================================================================
#  БАСЫМДЫҚ, ҚИЫЛЫСТАР
# ======================================================================

@scene('g016', 'Белгісіз тең дәрежелі қиылыс: оңнан және төменнен келе жатқан көліктер')
def g016():
    s = Svg('Басымдық белгілері жоқ тең дәрежелі қиылыс')
    s.add(city4(s, zebra='', stop='', center={a: 'dashed' for a in 'NSEW'}))
    s.add(path_arrow(s, f'M{NB} 380 L{NB} 120'), path_arrow(s, f'M720 {WB} L230 {WB}', '#ffffff'))
    s.add(car(s, NB, 430, 0, 'red', label=you(NB + 62, 430)), car(s, 790, WB, 270, 'blue'))
    return s


@scene('g017', 'Жанама жолдан басты жолға шығу (T тәрізді қиылыс)')
def g017():
    s = Svg('Екінші дәрежелі жолдан басты жолға шығу')
    s.add(crossroads(s, 480, 230, 'SEW', zebra='', stop='S', center={'E': 'solid', 'W': 'solid', 'S': 'dashed'}, blocks='grass'))
    s.add(car(s, 140, 259, 90, 'blue'), car(s, 800, 201, 270, 'white'))
    s.add(path_arrow(s, 'M509 380 L509 300 Q509 201 420 201 L300 201'), qmark(380, 150))
    s.add(car(s, 509, 430, 0, 'red', signal='left', label=you(572, 430)))
    s.add(post_sign(574, 345, 'yield', 66))
    return s


@scene('g018', 'Жасыл сигналда солға бұрылу, қарсыдан көлік тура келеді')
def g018():
    s = Svg('Солға бұрылу кезінде қарсы бағыттан келе жатқан көлік')
    s.add(city4(s, blocks='city'))
    s.add(path_arrow(s, f'M{NB} 320 Q{NB} {WB} 380 {WB} L240 {WB}'), path_arrow(s, f'M{SB} 120 L{SB} 330', '#ffffff'))
    s.add(car(s, SB, 70, 180, 'blue'))
    s.add(car(s, NB, 372, 0, 'red', signal='left', label=you(NB + 62, 395)))
    s.add(tl_card(s, 846, 18, 'green'))
    return s


@scene('g019', 'Жұмыс істемей тұрған бағдаршам')
def g019():
    s = Svg('Сигналдары сөніп тұрған бағдаршам')
    p = P()
    base, (ul, uc, ur) = street(s, p, walk=4)
    s.add(base, facades(p, ur + 4.5, 26, 140, seed=19), facades(p, ul - 4.5, 26, 140, seed=20))
    s.add(p_xroad(p, 15.5, 24, ul, ur))
    s.add(p_tree(p, ur + 2.6, 30, 6, seed=9), p_tree(p, ul - 2.6, 33, 6, seed=10))
    s.add(p_cross_car(s, p, 22, -9, 'white', 'left'), p_cross_car(s, p, 17.6, 6.5, 'orange', 'right'))
    s.add(p_zebra(p, ul, ur, 13, 15.5), p_stopline(p, uc, ur, 11.6))
    s.add(p_tlight(s, p, ur + 1.1, 12.0, 'off', 1.85))
    s.add(my_car(s, p))
    return s


# ======================================================================
#  ҚИЫЛЫС, ЖАЯУ ЖҮРГІНШІ, ТЕМІРЖОЛ
# ======================================================================

@scene('g020', 'Жасыл сигнал, алдыңғы көлік қиылыс ортасында тоқтап қалған')
def g020():
    s = Svg('Қиылыс ортасында тоқтап қалған көлік')
    s.add(city4(s, blocks='city', seed=8))
    s.add(car(s, NB, 90, 0, 'grey', brake=True), car(s, NB, 262, 0, 'white', brake=True, hazard=True))
    s.add(car(s, 130, WB, 270, 'blue'), car(s, 820, EB, 90, 'yellow'))
    s.add(path_arrow(s, f'M{NB} 400 L{NB} 336'), qmark(NB + 50, 360))
    s.add(car(s, NB, 452, 0, 'red', label=you(NB + 62, 452)))
    s.add(tl_card(s, 846, 18, 'green'))
    return s


@scene('g021', 'Реттелмейтін өткелге жаяу жүргінші шығып келеді')
def g021():
    s = Svg('Реттелмейтін жаяу жүргіншілер өткеліне адам шығып жатыр')
    p = P()
    base, (ul, uc, ur) = street(s, p, walk=4)
    s.add(base, facades(p, ur + 4.5, 20, 140, seed=21), facades(p, ul - 4.5, 20, 140, seed=22))
    s.add(p_tree(p, ur + 2.6, 24, 6, seed=13), p_tree(p, ul - 2.6, 28, 6, seed=14))
    s.add(p_zebra(p, ul, ur, 11.5, 14.5))
    s.add(p_sign(p, ul - 1.0, 15, 'crosswalk', 1.0))
    s.add(p_person(p, ur - .4, 12.8, '#7d5bd6', 'walk', -1))
    s.add(p_sign(p, ur + 1.0, 11.0, 'crosswalk', 1.0))
    s.add(my_car(s, p))
    return s


@scene('g022', 'Оңға бұрылу кезінде жаяу жүргінші жолды кесіп өтіп барады')
def g022():
    s = Svg('Оңға бұрылатын жолда жаяу жүргінші өтіп барады')
    s.add(city4(s, blocks='city', seed=12))
    s.add(path_arrow(s, f'M{NB} 352 Q{NB} {EB} 560 {EB} L720 {EB}'), qmark(640, 360))
    s.add(person_top(570, 306, 0, '#f08a24'), person_top(572, 236, 0, '#2f6fd6'))
    s.add(car(s, SB, 110, 180, 'silver'), car(s, 140, WB, 270, 'teal'))
    s.add(car(s, NB, 404, 0, 'red', signal='right', label=you(NB - 64, 430)))
    s.add(tl_card(s, 846, 18, 'green'))
    return s


@scene('g023', 'Көрші жолақтағы көлік өткел алдында тоқтап тұр')
def g023():
    s = Svg('Көрші жолақта өткел алдында тоқтаған көлік, оның алдында жаяу жүргінші')
    s.add(straight_road(s, 'v', 480, 87, (2, 1), 'solid', 'city', 23))
    s.add(zebra_v(393, 567, 176))
    s.add(post_sign(612, 176, 'crosswalk', 56), post_sign(352, 228, 'crosswalk', 56))
    s.add(car(s, 480, 286, 0, 'blue', brake=True))
    s.add(person_top(500, 200, 90, '#e2463b'), car(s, 422, 60, 180, 'white'))
    s.add(path_arrow(s, 'M538 380 L538 210'), qmark(590, 280))
    s.add(car(s, 538, 432, 0, 'red', label=you(600, 432)))
    return s


def p_rails(p, z, ul=-30, ur=30):
    """Теміржол жолы (бір жол): шпалдар + екі рельс."""
    out = p_band(p, ul, ur, z - 1.6, z + 1.6, '#8f8577')
    u = ul
    while u < ur:
        out += p_band(p, u, u + .3, z - 1.25, z + 1.25, '#6d5a47')
        u += .8
    for dz in (-.75, .75):
        out += p_band(p, ul, ur, z + dz - .06, z + dz + .06, '#d6d9dc')
    return out


def p_barrier(p, u_post, z, length=6.0, ang=35, side=-1, h=1.1):
    """Шлагбаум: тірек u_post-та, жебе side бағытында ang бұрышпен."""
    x0, y0 = p.pt(u_post, z, h)
    a = math.radians(ang)
    x1, y1 = p.pt(u_post + side * length * math.cos(a), z, h + length * math.sin(a))
    sc = p.scale(z)
    return (p_post(p, u_post, z, h + .25, '#e9e9e9') +
            f'<rect x="{f(x0 - sc * .18)}" y="{f(y0 - sc * .12)}" width="{f(sc * .36)}" height="{f(sc * .3)}" rx="3" fill="#d23"/>' +
            barrier_stripes(x0, y0, x1, y1, max(sc * .12, 4), 10))


@scene('g024', 'Шлагбаумы жабылып жатқан теміржол өткелі')
def g024():
    s = Svg('Теміржол өткелі: шлагбаум түсіп жатыр, қызыл шамдар жанып тұр')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.2)
    s.add(base)
    s.add(p_tree(p, ur + 9, 45, 7, 'pine'), p_tree(p, ul - 10, 50, 8, 'pine'), p_tree(p, ur + 14, 30, 7, seed=3))
    s.add(p_rails(p, 22.5), p_rails(p, 18))
    s.add(p_barrier(p, ul - .8, 23.5, 6.2, 16, 1))
    x, y = p.pt(ur + 1.5, 15.2, 3.0)
    s.add(p_post(p, ur + 1.5, 15.2, 3.0, '#ececec'), rail_lights(s, x, y, p.scale(15.2) * .011, 'left'))
    s.add(p_barrier(p, ur + .8, 15.2, 5.4, 22, -1))
    s.add(p_sign(p, ur + 1.3, 8.6, 'rail_barrier', 1.0))
    s.add(my_car(s, p))
    return s


@scene('g025', 'Шлагбаумсыз өткел: қызыл шам жыпылықтайды, поезд көрінбейді')
def g025():
    s = Svg('Шлагбаумсыз теміржол өткелі, қызыл шам жыпылықтап тұр')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.2)
    s.add(base)
    s.add(p_tree(p, ur + 9, 45, 7, 'pine'), p_tree(p, ul - 10, 50, 8, 'pine'), p_tree(p, ul - 8, 26, 7, seed=4))
    s.add(p_rails(p, 16.5))
    s.add(p_stopline(p, uc, ur, 12.2))
    x, y = p.pt(ur + 1.4, 11.6, 3.3)
    s.add(p_post(p, ur + 1.4, 11.6, 3.3, '#ececec'))
    sc = p.scale(11.6)
    s.add(f'<g transform="translate({f(x)} {f(y - sc * .25)})">{sign_st_andrew(sc * 1.2)}</g>')
    s.add(rail_lights(s, x, y + sc * .5, sc * .013, 'left'))
    s.add(my_car(s, p))
    return s

def rails_h(y, x0=-10, x1=970):
    out = f'<rect x="{x0}" y="{y - 34}" width="{x1 - x0}" height="68" fill="#9a8f80"/>'
    for x in range(x0, x1, 22):
        out += f'<rect x="{x}" y="{y - 26}" width="11" height="52" rx="2" fill="#6d5a47"/>'
    out += f'<rect x="{x0}" y="{y - 17}" width="{x1 - x0}" height="6" fill="#c9cdd1"/><rect x="{x0}" y="{y + 11}" width="{x1 - x0}" height="6" fill="#c9cdd1"/>'
    return out


def train_top(x, y, n=3, ang=90):
    out = f'<g transform="translate({f(x)} {f(y)}) rotate({ang})">'
    for k in range(n):
        yy = k * 168
        out += (f'<rect x="-27" y="{yy - 2}" width="58" height="164" rx="10" fill="#0b1520" opacity=".3"/>'
                f'<rect x="-30" y="{yy - 6}" width="60" height="160" rx="{14 if k == 0 else 6}" fill="{"#2e7d32" if k == 0 else "#3d8b40"}"/>'
                f'<rect x="-22" y="{yy + 20}" width="44" height="110" rx="5" fill="#cfd8d0" opacity=".55"/>')
    out += '<rect x="-24" y="-4" width="48" height="16" rx="6" fill="url(#glass)"/>'
    return out + '</g>'


@scene('g026', 'Көлік теміржол өткелінде тоқтап қалды, алыстан поезд келеді')
def g026():
    s = Svg('Теміржол өткелінде тоқтап қалған көлік')
    s.add(straight_road(s, 'v', 480, 58, (1, 1), 'solid', 'grass', 26))
    s.add(rails_h(250))
    s.add(f'<rect x="422" y="216" width="116" height="68" fill="#6c727a"/>')
    s.add(f'<rect x="422" y="231" width="116" height="6" fill="#c9cdd1"/><rect x="422" y="261" width="116" height="6" fill="#c9cdd1"/>')
    s.add(barrier_stripes(560, 330, 560, 400, 9, 6), barrier_stripes(400, 170, 400, 100, 9, 6))
    s.add(f'<circle cx="560" cy="330" r="8" fill="#d23"/><circle cx="400" cy="170" r="8" fill="#d23"/>')
    s.add(train_top(250, 250, 3, 90))
    s.add(car(s, 509, 262, 0, 'red', hazard=True, label=you(572, 300)))
    s.add(person_top(600, 210, 90, '#2f6fd6'))
    return s


@scene('g027', 'Сол жақ жолаққа ауысу: көрші жолақпен көлік келе жатыр')
def g027():
    s = Svg('Жолақ ауыстыру: сол жақ жолақта көлік келе жатыр')
    s.add(straight_road(s, 'v', 480, 87, (2, 1), 'solid', 'city', 27))
    s.add(car(s, 480, 420, 0, 'blue'), car(s, 422, 120, 180, 'white'), car(s, 538, 60, 0, 'grey'))
    s.add(path_arrow(s, 'M480 360 L480 210', '#ffffff'))
    s.add(path_arrow(s, 'M538 260 C538 200 480 200 480 140'), qmark(430, 210))
    s.add(car(s, 538, 312, 0, 'red', signal='left', label=you(600, 312)))
    return s


@scene('g028', 'Бұрылыс көрсеткішін қосып, жиектен шығу')
def g028():
    s = Svg('Жол жиегінен шығу: бұрылыс көрсеткіші қосулы, жолақта көлік келе жатыр')
    s.add(straight_road(s, 'v', 480, 87, (2, 1), 'solid', 'city', 28))
    s.add(car(s, 538, 120, 0, 'silver'), car(s, 538, 470, 0, 'white'))
    s.add(car(s, 480, 452, 0, 'blue'), car(s, 422, 80, 180, 'grey'))
    s.add(path_arrow(s, 'M480 392 L480 250', '#ffffff'))
    s.add(path_arrow(s, 'M538 240 C538 200 480 194 480 140'), qmark(600, 200))
    s.add(car(s, 538, 294, 0, 'red', signal='left', label=you(612, 294)))
    return s

@scene('g029', 'Тұрақтан кері жүріспен шығу, артта адам мен көлік')
def g029():
    s = Svg('Тұрақтан кері жүріспен шығу')
    s.add(f'<rect width="{W}" height="{H}" fill="#5f656d"/>')
    for i in range(9):
        x = 60 + i * 100
        s.add(f'<path d="M{x} 0V150M{x} 390V540" stroke="{MARK}" stroke-width="4"/>')
    s.add(f'<rect x="0" y="150" width="{W}" height="240" fill="#555b63"/>')
    s.add(f'<path d="M0 270H{W}" stroke="{MARK}" stroke-width="3" stroke-dasharray="24 20" opacity=".6"/>')
    for i, c in enumerate(['white', 'blue', None, 'grey', 'yellow', 'silver', 'teal', 'black']):
        if c:
            s.add(car(s, 110 + i * 100, 82, 180, c, scale=.92))
    for i, c in enumerate(['silver', 'grey', 'white', None, 'blue', 'orange', 'white', 'grey']):
        if c and i != 3:
            s.add(car(s, 110 + i * 100, 462, 0, c, scale=.92))
    s.add(glow(s, 410, 118, 30, '#ffffff'))
    s.add(car(s, 410, 66, 180, 'red', scale=.92, label=you(410, 18)))
    s.add(f'<rect x="398" y="106" width="8" height="5" fill="#fff"/><rect x="414" y="106" width="8" height="5" fill="#fff"/>')
    s.add(path_arrow(s, 'M410 130 L410 205'), qmark(468, 196))
    s.add(person_top(330, 214, 90, '#d9534f'))
    s.add(car(s, 700, 300, 270, 'blue'))
    return s


@scene('g030', 'Қауіпті бұрылыс алдындағы белгі')
def g030():
    s = Svg('Қауіпті бұрылыс белгісі және алда оңға бұрылатын жол')
    p = P(bend=-.0055)
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.2, edge=True, far=120)
    s.add(base)
    for z in range(16, 60, 4):
        x0, y0 = p.pt(ul - 1.0, z, 0)
        x1, y1 = p.pt(ul - 1.0, z, .8)
        s.add(f'<path d="M{f(x0)} {f(y0)}V{f(y1)}" stroke="#9aa3ab" stroke-width="{f(max(p.scale(z) * .1, 1.5))}"/>')
    s.add(f'<polyline points="{pts([p.pt(ul - 1.0, z, .75) for z in range(16, 61, 2)])}" fill="none" stroke="#c9d0d6" stroke-width="5"/>')
    s.add(p_tree(p, ur + 6, 40, 8, 'pine'), p_tree(p, ur + 4, 26, 7, 'pine'), p_tree(p, ul - 6, 22, 7, seed=5))
    s.add(p_sign(p, ur + 1.2, 8.2, 'curve_right', 1.1))
    s.add(my_car(s, p))
    return s


@scene('g031', 'Басып озуды бастамас бұрын: алда жүк көлігі, қарсыдан көлік')
def g031():
    s = Svg('Басып озу алдындағы жағдай')
    s.add(straight_road(s, 'v', 480, 58, (1, 1), 'dashed', 'grass', 31))
    s.add(car(s, 509, 230, 0, '#e9edf1', 'truck'), car(s, 451, 40, 180, 'white'))
    s.add(path_arrow(s, 'M509 400 C509 350 451 350 451 290 L451 160 C451 110 509 110 509 70'), qmark(400, 260))
    s.add(car(s, 509, 448, 0, 'red', label=you(572, 448)))
    return s


@scene('g032', 'Жаяу жүргіншілер өткелінде басып озу')
def g032():
    s = Svg('Жаяу жүргіншілер өткелі алдында басып озуға ниет')
    s.add(straight_road(s, 'v', 480, 58, (1, 1), 'dashed', 'city', 32))
    s.add(zebra_v(422, 538, 170))
    s.add(post_sign(572, 170, 'crosswalk', 56), post_sign(388, 224, 'crosswalk', 56))
    s.add(person_top(380, 178, 90, '#f08a24', stride=False))
    s.add(car(s, 509, 300, 0, 'blue', brake=True))
    s.add(path_arrow(s, 'M509 420 C509 380 451 380 451 330 L451 150'), qmark(400, 300))
    s.add(car(s, 509, 466, 0, 'red', label=you(572, 466)))
    return s


@scene('g033', 'Көріну шектеулі бұрылыста басып озу')
def g033():
    s = Svg('Орман ішіндегі бұрылыс: алдағы көрініс жабық')
    cx, cy, R = 120, 548, 380
    s.add(f'<rect width="{W}" height="{H}" fill="{GRASS}"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{R + 64}" fill="#c9c2b0"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{R + 58}" fill="#555b63"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{R - 58}" fill="#c9c2b0"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{R - 64}" fill="#7fb36b"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{MARK}" stroke-width="4" stroke-dasharray="26 22"/>')
    rnd = random.Random(33)
    for _ in range(70):
        a = math.radians(rnd.uniform(-100, 5))
        rr = rnd.uniform(40, R - 90)
        s.add(tree_top(cx + rr * math.cos(a), cy + rr * math.sin(a), rnd.uniform(22, 34)))
    for _ in range(26):
        a = math.radians(rnd.uniform(-95, 5))
        rr = rnd.uniform(R + 100, R + 400)
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        if 0 < x < W and 0 < y < H:
            s.add(tree_top(x, y, rnd.uniform(18, 28)))

    def at(th, rad):
        t = math.radians(th)
        return cx + rad * math.cos(t), cy + rad * math.sin(t)
    x, y = at(-30, R + 29)
    s.add(car(s, x, y, -30, 'green', 'tractor'))
    x, y = at(-74, R - 29)
    s.add(car(s, x, y, -74 + 180, 'blue'))
    p0, p1, p2 = at(-12, R + 29), at(-26, R - 29), at(-48, R - 29)
    s.add(path_arrow(s, f'M{f(p0[0])} {f(p0[1])} Q{f(at(-19, R - 10)[0])} {f(at(-19, R - 10)[1])} {f(p1[0])} {f(p1[1])} A{R - 29} {R - 29} 0 0 0 {f(p2[0])} {f(p2[1])}'))
    q = at(-40, R - 130)
    s.add(qmark(q[0], q[1]))
    x, y = at(-4, R + 29)
    s.add(car(s, x, y, -4, 'red', label=you(x + 70, y)))
    return s


@scene('g034', 'Басып озудан кейін өз жолағына қайту')
def g034():
    s = Svg('Басып озып болған соң өз жолағына оралу')
    s.add(straight_road(s, 'v', 480, 58, (1, 1), 'dashed', 'grass', 34))
    s.add(car(s, 509, 380, 0, '#e9edf1', 'truck'), car(s, 451, 30, 180, 'silver'))
    s.add(path_arrow(s, 'M451 210 L451 180 C451 140 509 140 509 100'), qmark(560, 180))
    s.add(car(s, 451, 262, 0, 'red', signal='right', label=you(390, 262)))
    return s


def mirror_cones(svg, x, y, ang=0, reach=240, color='#4aa3ff'):
    """Айна арқылы көрінетін аймақтар (көлік центрі x,y, жоғары қарап тұр)."""
    out = f'<g transform="translate({f(x)} {f(y)}) rotate({f(ang)})" opacity=".26">'
    out += f'<polygon points="{pts([(-27, -16), (-27 - reach * .55, reach), (-27 - reach * .18, reach)])}" fill="{color}"/>'
    out += f'<polygon points="{pts([(27, -16), (27 + reach * .55, reach), (27 + reach * .18, reach)])}" fill="{color}"/>'
    out += f'<polygon points="{pts([(0, 0), (-reach * .14, reach * 1.1), (reach * .14, reach * 1.1)])}" fill="{color}"/>'
    return out + '</g>'


def blind_zones(x, y, ang=0, color='#ff3b30', size=1.0):
    out = f'<g transform="translate({f(x)} {f(y)}) rotate({f(ang)}) scale({f(size)})" opacity=".32">'
    out += f'<polygon points="{pts([(-27, 0), (-27, 120), (-27 - 66, 110), (-27 - 40, 10)])}" fill="{color}"/>'
    out += f'<polygon points="{pts([(27, 0), (27, 120), (27 + 66, 110), (27 + 40, 10)])}" fill="{color}"/>'
    return out + '</g>'


@scene('g035', 'Жолақ ауыстыру алдында: айна және көрсеткіш')
def g035():
    s = Svg('Жолақ ауыстыру алдында айналарды тексеру')
    s.add(straight_road(s, 'v', 480, 87, (3, 0), None, 'city', 35))
    s.add(mirror_cones(s, 480, 300, 0, 230))
    s.add(car(s, 422, 470, 0, 'blue'), car(s, 538, 90, 0, 'white'), car(s, 480, 70, 0, 'grey'))
    s.add(path_arrow(s, 'M480 240 C480 200 422 196 422 150'), qmark(370, 230))
    s.add(car(s, 480, 300, 0, 'red', label=you(545, 300)))
    return s


@scene('g036', 'Кері бұрылу (U-бұрылыс) алдындағы жағдай')
def g036():
    s = Svg('Жолда кері бұрылуға дайындық')
    s.add(straight_road(s, 'v', 480, 116, (2, 2), 'double', 'grass', 36))
    s.add(f'<rect x="470" y="150" width="20" height="150" fill="url(#asph)"/>')
    s.add(f'<path d="M480 150V300" stroke="{MARK}" stroke-width="3" stroke-dasharray="14 12"/>')
    s.add(car(s, 393, 70, 180, 'white'), car(s, 451, 20, 180, 'grey'), car(s, 567, 470, 0, 'blue'))
    s.add(path_arrow(s, 'M509 340 L509 250 C509 170 422 170 422 250 L422 330'), qmark(560, 200))
    s.add(car(s, 509, 392, 0, 'red', signal='left', label=you(572, 392)))
    return s


@scene('g037', 'Жаңбырда алдыңғы көлікке дейінгі арақашықтық')
def g037():
    s = Svg('Жаңбырлы күні алдыңғы көлікпен арақашықтық')
    p = P()
    base, (ul, uc, ur) = street(s, p, kind='rain', env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 7, 40, 7, seed=37), p_tree(p, ul - 8, 34, 7, 'pine'))
    s.add(puddles(p, 37))
    s.add(p_band(p, -.9, .9, 7.2, 14.2, '#ffd23f', .28))
    x0, y0 = p.pt(-1.05, 7.2)
    x1, y1 = p.pt(-1.05, 14.2)
    s.add(f'<path d="M{f(x0)} {f(y0)} L{f(x1)} {f(y1)}" stroke="#ffd23f" stroke-width="5"/>')
    s.add(p_car_ahead(s, p, 0, 15, 'blue', brake=True))
    s.add(qmark(*p.pt(-1.9, 10.3)))
    s.add(p_car_oncoming(s, p, -3.5, 40, 'white', lights='low'))
    s.add(my_car(s, p), rain(37))
    return s


@scene('g038', 'Жаңбыр кезінде жылдамдықты таңдау')
def g038():
    s = Svg('Жаңбырлы жол, жүргізуші орнынан көрініс')
    p = P(horizon=200, cam_h=1.4, focal=760)
    base, (ul, uc, ur) = street(s, p, kind='rain', env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 7, 40, 7, seed=38), p_tree(p, ul - 8, 34, 7, 'pine'), p_tree(p, ur + 9, 60, 8, seed=39))
    s.add(puddles(p, 38))
    s.add(p_car_ahead(s, p, 0, 26, 'grey', night=True))
    s.add(p_car_oncoming(s, p, -3.5, 46, 'white', lights='low'))
    s.add(drops(38, 70), windshield())
    s.add('<path d="M150 452 Q300 400 470 388" stroke="#11161c" stroke-width="6" stroke-linecap="round"/><path d="M520 444 Q660 405 820 396" stroke="#11161c" stroke-width="6" stroke-linecap="round"/>')
    cx, cy = 480, 520
    s.add(f'<circle cx="{cx}" cy="{cy}" r="64" fill="#0d1218" stroke="#3a4450" stroke-width="4"/>')
    for k in range(9):
        a = math.radians(200 + k * 17.5)
        s.add(f'<path d="M{f(cx + 52 * math.cos(a))} {f(cy + 52 * math.sin(a))} L{f(cx + 60 * math.cos(a))} {f(cy + 60 * math.sin(a))}" stroke="#cfd8e0" stroke-width="3"/>')
    s.add(text(cx, cy - 18, 'км/сағ', 11, '#9fb0c0', 700), qmark(cx, cy + 2, 17))
    return s


# ======================================================================
#  ҚАУІПСІЗДІК БЕЛДІГІ, АУА РАЙЫ, ТҮН
# ======================================================================

def interior_base(s):
    out = '<rect width="960" height="540" fill="#dfe8ef"/>'
    out += '<path d="M0 420 H960 V540 H0Z" fill="#c9d3dc"/>'
    # көліктің бүйір пішіні (кесінді)
    out += ('<path d="M60 470 L60 300 Q70 250 120 236 L250 110 Q270 96 300 96 L600 96 Q640 96 670 120 L800 250 Q900 270 910 330 L910 470 Z" '
            'fill="#f4f7fa" stroke="#9fb0c0" stroke-width="6"/>')
    out += '<path d="M270 120 L600 120 Q630 120 650 140 L760 250 L270 250 Z" fill="#cfe4f3" opacity=".7"/>'
    out += '<path d="M120 250 L240 128 L240 250 Z" fill="#cfe4f3" opacity=".7"/>'
    out += '<path d="M440 120 V250" stroke="#9fb0c0" stroke-width="10"/>'
    out += '<rect x="60" y="440" width="850" height="30" fill="#7f8c99"/>'
    out += wheel(210, 480, 52, '#b6c0ca') + wheel(760, 480, 52, '#b6c0ca')
    return out


def seated(x, y, s=1.0, coat='#2f6fd6', skin='#e0b18f', hair='#3a2a20', child=False):
    """Отырған адам (бүйірден, оңға қарайды). (x,y) — жамбас."""
    k = s
    return (f'<g transform="translate({f(x)} {f(y)}) scale({f(k)})">'
            f'<path d="M0 0 L120 -6" stroke="#2b3440" stroke-width="44" stroke-linecap="round"/>'
            f'<path d="M120 -6 L150 100" stroke="#2b3440" stroke-width="36" stroke-linecap="round"/>'
            f'<path d="M140 104 H182" stroke="#222" stroke-width="16" stroke-linecap="round"/>'
            f'<path d="M-6 -6 L-22 -130" stroke="{coat}" stroke-width="62" stroke-linecap="round"/>'
            f'<circle cx="-14" cy="-180" r="34" fill="{skin}"/>'
            f'<path d="M-48 -186 Q-46 -222 -10 -218 Q22 -218 20 -192 Q2 -204 -20 -200 Q-38 -198 -48 -186Z" fill="{hair}"/>'
            f'<circle cx="12" cy="-180" r="4" fill="#333"/>'
            + ('' if child else f'<path d="M-16 -116 L40 -62 L112 -96" stroke="{coat}" stroke-width="22" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
               f'<circle cx="116" cy="-98" r="12" fill="{skin}"/>')
            + '</g>')


@scene('g041', 'Жүргізуші қауіпсіздік белдігін тағып отыр')
def g041():
    s = Svg('Қауіпсіздік белдігі тағылған жүргізуші')
    s.add(interior_base(s))
    s.add('<path d="M330 420 L300 170 Q298 150 318 148 L352 146 Q370 146 372 166 L400 400 Z" fill="#3b4652"/>')
    s.add('<rect x="300" y="110" width="66" height="44" rx="16" fill="#3b4652"/>')
    s.add('<path d="M320 420 L560 420 Q580 420 580 400 L578 386 L330 380 Z" fill="#46525f"/>')
    s.add(seated(420, 368, 1.0, '#2f6fd6'))
    s.add('<path d="M650 250 L720 330" stroke="#2b313a" stroke-width="16" stroke-linecap="round"/>')
    s.add('<ellipse cx="640" cy="248" rx="14" ry="62" transform="rotate(-25 640 248)" fill="none" stroke="#1d232a" stroke-width="12"/>')
    s.add('<path d="M700 300 Q780 290 820 330 L820 380 L700 380Z" fill="#3a4450"/>')
    s.add('<path d="M372 196 L404 228 L470 330 L480 360" stroke="#ffd23f" stroke-width="22" stroke-linecap="round" fill="none" opacity=".45"/>')
    s.add('<path d="M372 196 L404 228 L470 330 L480 360" stroke="#1f2933" stroke-width="10" stroke-linecap="round" fill="none"/>')
    s.add('<path d="M378 362 L480 362" stroke="#1f2933" stroke-width="10" stroke-linecap="round"/>')
    s.add('<rect x="470" y="352" width="26" height="20" rx="4" fill="#9aa4ae" stroke="#5c6670" stroke-width="2"/>')
    s.add('<rect x="364" y="186" width="16" height="22" rx="4" fill="#7f8a95"/>')
    s.add(qmark(560, 200, 22))
    return s


@scene('g042', 'Артқы орындықтағы жас бала')
def g042():
    s = Svg('Автокөліктің артқы орындығындағы бала')
    s.add(interior_base(s))
    # артқы орындық
    s.add('<path d="M150 420 L130 190 Q130 170 150 168 L196 166 Q214 166 216 186 L240 410 Z" fill="#3b4652"/>')
    s.add('<path d="M150 420 L420 420 Q440 420 440 402 L438 388 L170 384 Z" fill="#46525f"/>')
    # бала орындығы
    s.add('<path d="M226 388 L206 236 Q204 212 228 208 L280 204 Q300 204 304 222 L318 300 L396 300 Q414 300 416 318 L418 388 Z" fill="#e2463b"/>')
    s.add('<path d="M232 380 L216 246 Q216 228 232 226 L274 224 Q288 224 290 238 L302 310 L392 312 L394 380 Z" fill="#2b313a"/>')
    s.add(seated(300, 330, .62, '#f2c230', child=True))
    s.add('<path d="M290 262 L322 312 M262 262 L322 312" stroke="#11161c" stroke-width="7" stroke-linecap="round"/>')
    s.add('<rect x="314" y="304" width="16" height="16" rx="3" fill="#9aa4ae"/>')
    # алдыңғы орындық
    s.add('<path d="M560 420 L536 190 Q534 170 554 168 L590 166 Q608 166 610 186 L636 400 Z" fill="#3b4652"/>')
    s.add('<rect x="534" y="122" width="62" height="42" rx="16" fill="#3b4652"/>')
    s.add('<path d="M560 420 L780 420 Q800 420 800 400 L798 386 L566 380 Z" fill="#46525f"/>')
    s.add(qmark(370, 190, 22))
    return s


@scene('g045', 'Ылғал, тайғақ жолда алдыңғы көлік кенет тежеді')
def g045():
    s = Svg('Ылғал жолда алдағы көлік тежеп жатыр')
    p = P()
    base, (ul, uc, ur) = street(s, p, kind='rain', env='country', walk=1.4, edge=True)
    s.add(base, puddles(p, 45, 14, -3.2, 1.6, 6.5, 30))
    s.add(p_tree(p, ur + 7, 36, 7, seed=45), p_tree(p, ul - 8, 42, 8, 'pine'))
    for dz in (0, .9):
        x0, y0 = p.pt(-.6, 12.2 + dz)
        x1, y1 = p.pt(-.6, 17 + dz)
        x2, y2 = p.pt(.6, 12.2 + dz)
        x3, y3 = p.pt(.6, 17 + dz)
    s.add(p_car_ahead(s, p, 0, 13.6, 'silver', brake=True))
    for sx in (-1, 1):
        x, y = p.pt(sx * .75, 13.6)
        sc = p.scale(13.6)
        s.add(f'<path d="M{f(x)} {f(y)} q{f(sx * sc * .5)} {f(-sc * .4)} {f(sx * sc * 1.0)} {f(-sc * .1)}" stroke="#e1edf7" stroke-width="{f(sc * .12)}" fill="none" opacity=".7" stroke-linecap="round"/>')
    s.add(qmark(*p.pt(-1.9, 9.6)))
    s.add(my_car(s, p), rain(45, 140))
    return s


@scene('g049', 'Қалың тұман')
def g049():
    s = Svg('Қалың тұмандағы жол')
    p = P()
    base, (ul, uc, ur) = street(s, p, kind='fog', env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 6, 26, 7, seed=49), p_tree(p, ul - 6, 32, 8, 'pine'), p_tree(p, ur + 5, 14, 7, 'bare'))
    s.add(p_car_ahead(s, p, 0, 22, 'grey', night=True))
    s.add(p_car_oncoming(s, p, -3.5, 30, 'white', lights='low'))
    s.add(fog_layer(p, .9))
    s.add(my_car(s, p, night=True))
    s.add(f'<rect width="{W}" height="{H}" fill="#e6eaed" opacity=".18"/>')
    return s


@scene('g050', 'Түнде алыс жарықпен келе жатқанда қарсы көлік шықты')
def g050():
    s = Svg('Түнгі жол: алыс жарық қосулы, қарсыдан көлік келе жатыр')
    p = P()
    base, (ul, uc, ur) = street(s, p, kind='night', env='country', walk=1.2, edge=True)
    s.add(base)
    rnd = random.Random(50)
    for _ in range(40):
        s.add(f'<circle cx="{f(rnd.uniform(0, W))}" cy="{f(rnd.uniform(0, p.hz - 20))}" r="{f(rnd.uniform(.8, 2))}" fill="#fff" opacity=".8"/>')
    s.add('<circle cx="800" cy="60" r="24" fill="#f4f1d8"/><circle cx="790" cy="54" r="22" fill="#0e1a2c"/>')
    s.add(f'<polygon points="{pts([p.pt(-1.4, 5.5), p.pt(1.4, 5.5), p.pt(3.2, 70), p.pt(-4.8, 70)])}" fill="#fff6cc" opacity=".22"/>')
    s.add(f'<polygon points="{pts([p.pt(-1.0, 5.5), p.pt(1.0, 5.5), p.pt(2.0, 40), p.pt(-3.0, 40)])}" fill="#fff6cc" opacity=".22"/>')
    s.add(p_car_oncoming(s, p, -3.5, 34, 'white', lights='high'))
    s.add(my_car(s, p, night=True))
    return s


@scene('g051', 'Артта жарқылдақ маягі қосулы жедел жәрдем келе жатыр')
def g051():
    s = Svg('Жедел жәрдем көлігі арттан жақындап келеді')
    s.add(straight_road(s, 'v', 480, 87, (2, 1), 'solid', 'city', 51))
    s.add(car(s, 422, 60, 180, 'white'), car(s, 538, 90, 0, 'grey'))
    s.add(car(s, 480, 440, 0, 'white', 'ambulance', flash=True))
    for r in (40, 64, 88):
        s.add(f'<path d="M{480 - r} {380 - r * .35} Q480 {380 - r * 1.05} {480 + r} {380 - r * .35}" fill="none" stroke="#2f7bff" stroke-width="4" opacity=".7"/>')
    s.add(qmark(410, 230))
    s.add(car(s, 480, 232, 0, 'red', label=you(545, 232)))
    return s


@scene('g052', 'Айнада көк маягі жанған полиция көлігі көрінеді')
def g052():
    s = Svg('Артқы көрініс айнасында полиция көлігі')
    p = P(horizon=210, cam_h=1.4, focal=760)
    base, (ul, uc, ur) = street(s, p, n_our=2, n_opp=1, walk=3, edge=False)
    s.add(base, facades(p, ur + 4, 16, 140, seed=52), facades(p, ul - 4, 16, 140, seed=53))
    s.add(p_car_ahead(s, p, -3.5, 22, 'blue'), p_car_ahead(s, p, 0, 34, 'white'))
    s.add(windshield())
    # үлкен айна
    s.add('<rect x="330" y="22" width="300" height="104" rx="22" fill="#11161c"/>')
    s.add('<clipPath id="mir"><rect x="340" y="30" width="280" height="88" rx="16"/></clipPath>')
    s.add('<g clip-path="url(#mir)"><rect x="340" y="30" width="280" height="88" fill="#a9c4d8"/>'
          '<rect x="340" y="74" width="280" height="44" fill="#6c737c"/>'
          '<polygon points="430,118 530,118 492,74 468,74" fill="#5a6069"/>')
    s.add(car_front(s, 480, 112, 70, 'white', lights='low'))
    s.add('<rect x="458" y="56" width="44" height="8" rx="3" fill="#1d2a38"/><rect x="460" y="57" width="20" height="6" fill="#2f7bff"/><rect x="480" y="57" width="20" height="6" fill="#ff3b30"/>')
    s.add(glow(s, 466, 60, 34, '#2f7bff'), glow(s, 496, 60, 26, '#ff3b30'))
    s.add('<rect x="340" y="30" width="280" height="22" fill="#fff" opacity=".18"/></g>')
    s.add(qmark(660, 76, 20))
    return s


@scene('g053', 'Жол нашар көрінеді: боран')
def g053():
    s = Svg('Қатты боран, алдағы жол әрең көрінеді')
    p = P(horizon=200, cam_h=1.4, focal=760)
    base, (ul, uc, ur) = street(s, p, kind='winter', env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 6, 30, 7, 'pine'), p_tree(p, ul - 6, 24, 7, 'pine'))
    s.add(p_car_ahead(s, p, 0, 30, 'grey', night=True))
    s.add(fog_layer(p, .92, '#f2f5f7'), snow(53, 320, .95))
    s.add('<g stroke="#fff" stroke-width="3" opacity=".6">' + ''.join(f'<path d="M{x} {y} l60 14"/>' for x, y in ((100, 80), (300, 160), (620, 120), (760, 220), (200, 300), (540, 280))) + '</g>')
    s.add(windshield())
    s.add('<path d="M150 452 Q300 400 470 388" stroke="#11161c" stroke-width="6" stroke-linecap="round"/><path d="M520 444 Q660 405 820 396" stroke="#11161c" stroke-width="6" stroke-linecap="round"/>')
    return s


@scene('g054', 'Көше жиегіне тұраққа қою алдындағы жағдай')
def g054():
    s = Svg('Көше жиегінде тұраққа қоятын орын іздеу')
    s.add(straight_road(s, 'h', 300, 87, (2, 1), 'solid', 'city', 54))
    # гараж қақпасы
    s.add('<rect x="430" y="387" width="110" height="60" fill="#c3ccd4"/><rect x="440" y="400" width="90" height="50" fill="#8e99a6"/>'
          + ''.join(f'<path d="M440 {408 + k * 9}H530" stroke="#6c7682"/>' for k in range(5)))
    s.add('<rect x="430" y="380" width="110" height="8" fill="#9d9788"/>')
    for x, c in ((120, 'silver'), (250, 'blue'), (680, 'white'), (810, 'grey')):
        s.add(car(s, x, 358, 90, c, scale=.95))
    s.add(path_arrow(s, 'M320 300 C380 300 420 358 470 358'), qmark(486, 300))
    s.add(car(s, 250, 300, 90, 'red', signal='right', label=you(250, 250)))
    s.add(car(s, 700, 242, 90, 'teal'), car(s, 120, 184, 270, 'yellow'))
    return s


@scene('g055', 'Кептелісте жаяу жүргіншілер өткелінің үстінде тоқтау')
def g055():
    s = Svg('Кептеліс: алдағы бос орын өткелдің дәл үстінде')
    s.add(straight_road(s, 'v', 480, 58, (1, 1), 'dashed', 'city', 55))
    s.add(zebra_v(422, 538, 250))
    s.add(post_sign(572, 250, 'crosswalk', 56), post_sign(388, 300, 'crosswalk', 56))
    s.add(car(s, 509, 180, 0, 'blue', brake=True), car(s, 509, 60, 0, 'grey', brake=True))
    s.add(path_arrow(s, 'M509 380 L509 300'), qmark(560, 285))
    s.add(car(s, 509, 430, 0, 'red', label=you(572, 430)))
    s.add(person_top(380, 262, 90, '#2f9e6b', stride=False))
    return s


@scene('g058', 'Уақытша және тұрақты белгілер бір-біріне қайшы')
def g058():
    s = Svg('Жол жұмыстары: тұрақты 60 белгісі мен уақытша 40 белгісі')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 9, 40, 7, seed=58), p_tree(p, ul - 8, 34, 7, 'pine'))
    for z in range(16, 40, 3):
        x, y = p.pt(-.6, z)
        s.add(cone(x, y, p.scale(z) * .8))
    s.add(p_sign(p, ul - 1.0, 12.5, 'road_works', .95))
    s.add(p_sign(p, ur + 1.2, 16, 'speed', 1.0, n='60'))
    s.add(p_sign(p, ur + 1.2, 8.4, 'temp_speed', 1.05, n='40'))
    s.add(my_car(s, p))
    return s


@scene('g059', 'Қиылыста оңға бұрылар алдында: оң жақта велосипедші')
def g059():
    s = Svg('Оңға бұрылу алдында, оң жақта велосипедші келе жатыр')
    s.add(city4(s, blocks='city', seed=59))
    s.add(path_arrow(s, f'M{NB} 400 Q{NB} {EB} 570 {EB} L720 {EB}'), qmark(620, 370))
    s.add(car(s, 532, 448, 0, '#2f9e6b', 'bike', scale=1.3))
    s.add(path_arrow(s, 'M532 410 L532 180', '#ffffff', 5))
    s.add(person_top(580, 360, -90, '#d9534f'))
    s.add(car(s, SB, 120, 180, 'silver'), car(s, 160, WB, 270, 'blue'))
    s.add(car(s, NB - 8, 470, 0, 'red', label=you(NB - 75, 470)))
    s.add(tl_card(s, 846, 18, 'green'))
    return s


@scene('g060', 'Қиылыс алдындағы бағыттар бойынша жолақтар')
def g060():
    s = Svg('Әр жолақтың қозғалыс бағыты белгіленген қиылыс')
    s.add(crossroads(s, 480, 200, 'NSEW', v_hw=116, lanes={'S': (3, 1), 'N': (1, 3)}, center={'S': 'solid', 'N': 'solid'},
                     zebra='NSEW', stop='S', arrows={'S': ['L', 'S', 'R']}, blocks='city', seed=60))
    s.add(path_arrow(s, 'M509 440 C509 400 567 400 567 372'), qmark(620, 440))
    s.add(car(s, 509, 488, 0, 'red', label=you(445, 488)))
    s.add(car(s, 451, 120, 180, 'grey'), car(s, 150, 171, 270, 'blue'))
    s.add(sign_card(820, 380, 'lanes', 76, arrows=('L', 'S', 'R')))
    return s


@scene('g061', 'Жолдағы мұз басқан бөлік')
def g061():
    s = Svg('Қысқы жол, алда мұз басқан тайғақ бөлік')
    p = P()
    base, (ul, uc, ur) = street(s, p, kind='winter', env='country', walk=1.6, edge=True)
    s.add(base)
    s.add(p_band(p, ur + .2, ur + 1.6, 1.2, 300, '#ffffff', .9), p_band(p, ul - 1.6, ul - .2, 1.2, 300, '#ffffff', .9))
    s.add(f'<polygon points="{pts([p.pt(-1.6, 11), p.pt(1.6, 11.5), p.pt(1.4, 19), p.pt(-2.4, 18)])}" fill="#d9f0ff" opacity=".85"/>')
    s.add(f'<polygon points="{pts([p.pt(-1.0, 12), p.pt(.4, 12.3), p.pt(-.2, 15)])}" fill="#fff" opacity=".8"/>')
    s.add(p_tree(p, ur + 6, 26, 7, 'pine'), p_tree(p, ul - 6, 34, 8, 'pine'), p_tree(p, ur + 9, 46, 7, 'bare'))
    s.add(snow(61, 80, .7))
    s.add(p_sign(p, ur + 1.2, 8.4, 'slippery', 1.05))
    s.add(my_car(s, p))
    return s


@scene('g063', 'Көк төртбұрышта ақ «P» белгісі')
def g063():
    s = Svg('«Тұрақ орны» белгісі')
    p = P()
    base, (ul, uc, ur) = street(s, p, walk=2)
    s.add(base, facades(p, ul - 3, 12, 140, seed=63))
    s.add(p_band(p, ur + 2, 40, 9, 40, '#6c737c'))
    for k in range(6):
        z = 12 + k * 4.5
        s.add(p_band(p, ur + 2.4, 20, z - .06, z + .06, MARK))
    s.add(facades(p, ur + 20, 10, 140, seed=64))
    for k, c in enumerate(['white', 'blue', None, 'grey', 'yellow']):
        if c:
            x, yb = p.pt(ur + 6, 14.2 + k * 4.5)
            s.add(car_side(s, x, yb, 4.4 * p.scale(14.2 + k * 4.5), c, 'left'))
    s.add(p_sign(p, ur + 1.2, 8.2, 'parking', 1.05))
    s.add(my_car(s, p))
    return s


@scene('g064', '«Жол жұмыстары» ескерту белгісі және алдағы жұмыс аймағы')
def g064():
    s = Svg('«Жол жұмыстары» белгісі')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(p_tree(p, ur + 8, 44, 7, seed=64), p_tree(p, ul - 8, 36, 7, 'pine'))
    for z in range(14, 34, 3):
        x, y = p.pt(-.3 + (z - 14) * .02, z)
        s.add(cone(x, y, p.scale(z) * .8))
    s.add(p_person(p, 1.0, 24, '#ff7a2f', 'stand'))
    x0, y0 = p.pt(.2, 18, .9)
    x1, y1 = p.pt(1.7, 18, .9)
    s.add(barrier_stripes(x0, y0, x1, y1, p.scale(18) * .2, 6))
    s.add(p_sign(p, ur + 1.2, 8.4, 'road_works', 1.1))
    s.add(my_car(s, p))
    return s


@scene('g069', 'Жасыл сигнал жанды, бірақ өткелде жаяу жүргінші қалып қойды')
def g069():
    s = Svg('Өткелдің ортасында қалып қойған жаяу жүргінші')
    s.add(city4(s, blocks='city', seed=69))
    s.add(person_top(500, 361, -90, '#7d5bd6'))
    s.add(path_arrow(s, f'M{NB} 400 L{NB} 300'), qmark(NB + 52, 312))
    s.add(car(s, NB, 452, 0, 'red', label=you(NB + 62, 452)))
    s.add(car(s, SB, 120, 180, 'grey'), car(s, 160, WB, 270, 'yellow', brake=True))
    s.add(tl_card(s, 846, 18, 'green'))
    return s


@scene('g070', 'Қалада айналарды тексеру: жанында велосипедші мен мотоцикл')
def g070():
    s = Svg('Айналар арқылы көрші жолақтарды бақылау')
    s.add(straight_road(s, 'v', 480, 116, (3, 1), 'solid', 'city', 70))
    s.add(f'<rect x="580" y="0" width="16" height="540" fill="#5a8f5a" opacity=".0"/>')
    s.add(mirror_cones(s, 509, 230, 0, 260))
    s.add(car(s, 509, 230, 0, 'red', label=you(509, 158)))
    s.add(car(s, 574, 330, 0, '#2f9e6b', 'bike', scale=1.3), car(s, 451, 360, 0, 'black', 'moto', scale=1.3))
    s.add(car(s, 393, 90, 180, 'white'), car(s, 567, 60, 0, 'grey'))
    s.add(qmark(640, 250))
    return s


@scene('g071', 'Қараңғы жол, жарық жеткен жерде адам')
def g071():
    s = Svg('Түнгі жарықсыз жол')
    p = P()
    base, (ul, uc, ur) = street(s, p, kind='night', env='country', walk=1.2, edge=True)
    s.add(base)
    s.add(f'<polygon points="{pts([p.pt(-1.2, 5.5), p.pt(1.2, 5.5), p.pt(2.4, 24), p.pt(-3.0, 24)])}" fill="#fff6cc" opacity=".25"/>')
    s.add(f'<polygon points="{pts([p.pt(-1.0, 5.5), p.pt(1.0, 5.5), p.pt(1.8, 17), p.pt(-2.2, 17)])}" fill="#fff6cc" opacity=".2"/>')
    s.add(f'<rect width="{W}" height="{H}" fill="#020812" opacity=".18"/>')
    s.add(p_person(p, 1.0, 19, '#56606b', 'walk', -1))
    s.add(my_car(s, p, night=True))
    return s


@scene('g073', 'Реттелмейтін қиылыс: трамвай және автомобиль')
def g073():
    s = Svg('Реттелмейтін қиылыста трамвай мен автомобиль')
    s.add(crossroads(s, 480, 270, 'NSEW', h_hw=87, lanes={'E': (1, 1), 'W': (1, 1)}, zebra='', stop='', center={'E': None, 'W': None}, blocks='city', seed=73))
    for y in (246, 294):
        s.add(f'<path d="M0 {y - 9}H960M0 {y + 9}H960" stroke="#c9cdd1" stroke-width="4"/>')
    s.add(car(s, 210, 294, 90, 'red', 'tram'))
    s.add(path_arrow(s, 'M370 294 L640 294', '#ffffff'))
    s.add(path_arrow(s, f'M{NB} 400 L{NB} 140'), qmark(NB + 52, 400))
    s.add(car(s, NB, 452, 0, '#e2463b', label=you(NB + 62, 452)))
    return s


@scene('g075', 'Басып озуға кірісерде арттағы көлік те озуды бастады')
def g075():
    s = Svg('Арттағы көлік басып озуды бастап қойған')
    s.add(straight_road(s, 'v', 480, 58, (1, 1), 'dashed', 'grass', 75))
    s.add(car(s, 509, 140, 0, '#e9edf1', 'truck'))
    s.add(car(s, 451, 420, 0, 'blue', signal='left'))
    s.add(path_arrow(s, 'M451 360 L451 200', '#ffffff'))
    s.add(path_arrow(s, 'M509 250 C509 220 470 220 466 190'), qmark(560, 230))
    s.add(car(s, 509, 300, 0, 'red', signal='left', label=you(572, 300)))
    return s


@scene('g077', 'Айналарда көрінбейтін аймақтар')
def g077():
    s = Svg('Айналар көрсетпейтін соқыр аймақтар')
    s.add(straight_road(s, 'v', 480, 116, (2, 2), 'double', 'grass', 77))
    s.add(mirror_cones(s, 538, 230, 0, 280))
    s.add(blind_zones(538, 230, 0, '#ff3b30', 1.2))
    s.add(car(s, 538, 230, 0, 'red', label=you(538, 160)))
    s.add(car(s, 480, 330, 0, 'black', 'moto', scale=1.3))
    s.add(car(s, 422, 80, 180, 'white'))
    s.add(qmark(440, 268), qmark(640, 268))
    return s


@scene('g078', 'Қалада жылдамдықпен шұғыл жолақ ауыстыру')
def g078():
    s = Svg('Көп жолақты көшеде шұғыл жолақ ауыстыру')
    s.add(straight_road(s, 'v', 480, 174, (3, 3), 'double', 'city', 78))
    for x, y, c in ((538, 90, 'white'), (596, 300, 'blue'), (654, 30, 'grey'), (538, 360, 'yellow')):
        s.add(car(s, x, y, 0, c))
    for x, y, c in ((422, 120, 'silver'), (364, 380, 'teal')):
        s.add(car(s, x, y, 180, c))
    s.add(path_arrow(s, 'M654 380 C654 330 538 320 538 260 C538 210 654 210 654 150'), qmark(720, 260))
    s.add('<g stroke="#fff" stroke-width="4" stroke-linecap="round" opacity=".85"><path d="M640 500V530M654 505V540M668 500V530"/></g>')
    s.add(car(s, 654, 440, 0, 'red', label=you(720, 440)))
    return s


# ======================================================================
#  ЖҮК КӨЛІКТЕРІ ЖӘНЕ ЖҮК
# ======================================================================

YG = 470  # бүйірден көріністегі жер деңгейі


def side_bg(s, kind='day', city=False, seed=1, road=True):
    out = sky('day' if kind == 'day' else kind, 330)
    rnd = random.Random(seed)
    if city:
        out += '<g fill="#a9b8c6" opacity=".75">'
        x = -10
        while x < W:
            w = rnd.uniform(50, 110)
            h = rnd.uniform(60, 170)
            out += f'<rect x="{f(x)}" y="{f(330 - h)}" width="{f(w)}" height="{f(h + 2)}"/>'
            x += w + rnd.uniform(4, 14)
        out += '</g>'
    else:
        path = 'M-20 332 '
        for x in range(-20, W + 80, 80):
            path += f'L{x} {f(330 - rnd.uniform(20, 70))} '
        out += f'<path d="{path} L{W + 20} 332Z" fill="#9cbcaa" opacity=".7"/>'
    out += '<rect y="330" width="960" height="210" fill="#a9cf8f"/>'
    if road:
        out += f'<rect y="{YG - 46}" width="960" height="76" fill="#5a6069"/>'
        out += f'<rect y="{YG - 50}" width="960" height="6" fill="#c9c2b0"/><rect y="{YG + 30}" width="960" height="6" fill="#c9c2b0"/>'
        out += f'<path d="M0 {YG + 12}H960" stroke="{MARK}" stroke-width="4" stroke-dasharray="40 30"/>'
    return out


@scene('c001', 'Рұқсат етілген ең жоғары массасы 3 500 кг ГАЗель')
def c001():
    s = Svg('Жүк ГАЗелі, рұқсат етілген ең жоғары массасы 3 500 кг')
    s.add(side_bg(s, seed=1))
    s.add(gazelle_side(80, YG, 1.12, '#f4f6f8', 'tent'))
    s.add(spec_card(600, 24, 'Рұқсат етілген ең жоғары масса', '3 500 кг', 336, 'техпаспорт бойынша'))
    return s


@scene('c002', 'Рұқсат етілген ең жоғары массасы 3 500–7 500 кг жүк көлігі')
def c002():
    s = Svg('Орташа жүк көлігі, масса 3 500 – 7 500 кг')
    s.add(side_bg(s, seed=2))
    s.add(heavy_truck_side(110, YG, .9, '#2f9e6b', '#eef1f4', 'box', 2))
    s.add(spec_card(600, 24, 'Рұқсат етілген ең жоғары масса', '7 200 кг', 336, '3 500-ден көп, 7 500-ден аз'))
    return s


@scene('c003', 'Ауыр жүк көлігі: массасы 3 500 кг-нан асады')
def c003():
    s = Svg('Ауыр жүк көлігі')
    s.add(side_bg(s, seed=3))
    s.add(heavy_truck_side(60, YG, .98, '#2f6fd6', '#eef1f4', 'box', 3))
    s.add(spec_card(600, 24, 'Рұқсат етілген ең жоғары масса', '18 000 кг', 336, 'жүк көлігі, автобус емес'))
    return s


def flat_load(rows=((10, 4), (70, 4)), w=80, h=58, x0=12, base=-104, c='#c9965a'):
    """Жүк ГАЗелінің кузовындағы жәшіктер (gazelle_side координаттарымен)."""
    out = ''
    for row, (_, n) in enumerate(rows):
        for i in range(n):
            out += box_crate(x0 + i * (w + 6), base - (row + 1) * h, w, h, c)
    return out


@scene('c005', 'Жүк тиелген соң: бекіту белдіктері')
def c005():
    s = Svg('Бортты ГАЗельдегі белдікпен бекітілген жүк')
    s.add(side_bg(s, city=True, seed=5))
    load = flat_load(((0, 4), (0, 3)), 82, 62)
    straps = strap(30, -104, 150, -228) + strap(150, -228, 270, -104) + strap(200, -104, 300, -166) + strap(30, -166, 330, -166)
    s.add(gazelle_side(170, YG, 1.1, '#f4f6f8', 'flatbed'))
    s.add(f'<g transform="translate(170 {YG}) scale(1.1)">{load}{straps}</g>')
    s.add(person(100, YG + 8, 190, '#ff7a2f', 'stand'))
    s.add(qmark(330, 160, 24))
    return s


@scene('c006', 'Жүк кабинадан биік тиелген, көрініс жабылған')
def c006():
    s = Svg('Кабинадан биік тиелген жүк артқы көріністі жауып тұр')
    s.add(side_bg(s, seed=6))
    load = flat_load(((0, 4), (0, 4), (0, 3), (0, 2)), 82, 60)
    s.add(gazelle_side(110, YG, 1.0, '#f4f6f8', 'flatbed'))
    s.add(f'<g transform="translate(110 {YG})">{load}</g>')
    s.add(f'<g transform="translate(110 {YG})"><rect x="350" y="-188" width="40" height="80" rx="6" fill="#c9965a" stroke="#8a5a2b" stroke-width="2"/></g>')
    s.add(f'<path d="M546 {YG - 175} L60 {YG - 140}" stroke="#ffd23f" stroke-width="5" stroke-dasharray="14 10"/>')
    s.add(f'<circle cx="548" cy="{YG - 175}" r="9" fill="#ffd23f" stroke="#fff" stroke-width="3"/>')
    s.add(qmark(300, 150, 24))
    return s


@scene('c007', 'Артынан шығып тұрған жүк нөмір мен шамдарды жауып тұр')
def c007():
    s = Svg('Ұзын жүк артқы нөмір мен шамдарды жауып тұр')
    s.add(side_bg(s, city=True, seed=7, road=False))
    s.add('<rect y="330" width="960" height="210" fill="#6c737c"/><path d="M480 540 L480 330" stroke="#f5f5ef" stroke-width="6" stroke-dasharray="30 30"/>')
    boards = ''.join(f'<rect x="-150" y="{-150 + k * 16}" width="300" height="15" rx="2" fill="{["#d8a25e", "#c9914f", "#b88445"][k % 3]}" stroke="#7b5226" stroke-width="1.5"/>' for k in range(6))
    boards += '<rect x="-150" y="-150" width="300" height="96" fill="#000" opacity=".06"/>' + ''.join(f'<circle cx="{x}" cy="{-140 + k * 16}" r="4" fill="#7b5226"/>' for k in range(6) for x in (-120, 0, 120))
    s.add(rear_truck(480, 500, 1.2, '#f4f6f8', 'flatbed', load=f'<g transform="translate(0 50)">{boards}</g>'))
    s.add(qmark(700, 300, 24))
    return s


@scene('c008', 'Жүк жолға шашылып қалды, артта көліктер келеді')
def c008():
    s = Svg('Жүк көлігінен жолға құлаған жәшіктер')
    s.add(straight_road(s, 'v', 480, 87, (2, 1), 'solid', 'grass', 81))
    s.add(car(s, 538, 120, 0, 'white', 'van', cargo='flatbed-load'))
    for x, y, a in ((520, 236, 20), (548, 262, -15), (500, 300, 40), (556, 318, 5)):
        s.add(f'<g transform="translate({x} {y}) rotate({a})"><rect x="-13" y="-13" width="26" height="26" rx="3" fill="#c9965a" stroke="#8a5a2b" stroke-width="2"/><rect x="-3" y="-13" width="6" height="26" fill="#e7d3a8"/></g>')
    s.add(car(s, 538, 470, 0, 'blue'), car(s, 480, 420, 0, 'grey'), car(s, 422, 60, 180, 'silver'))
    s.add(qmark(620, 280))
    return s


@scene('c009', 'Нормадан артық тиелген жүк көлігі')
def c009():
    s = Svg('Артық тиелген, серіппелері басылған ГАЗель')
    s.add(side_bg(s, seed=9))
    load = flat_load(((0, 4), (0, 4), (0, 4)), 82, 56)
    s.add(gazelle_side(110, YG, 1.0, '#f4f6f8', 'flatbed', sag=14))
    s.add(f'<g transform="translate(110 {YG + 14})">{load}</g>')
    s.add(f'<g transform="translate(110 {YG})"><ellipse cx="92" cy="-6" rx="34" ry="8" fill="#1b1f24"/><ellipse cx="452" cy="-6" rx="34" ry="8" fill="#1b1f24"/>'
          '<path d="M60 -60 l10 8 l-10 8 l10 8 M120 -60 l-10 8 l10 8 l-10 8" stroke="#e2463b" stroke-width="3" fill="none"/></g>')
    s.add(qmark(470, 120, 24))
    return s


@scene('c010', 'Бос және жүкті көліктің тежелу жолы')
def c010():
    s = Svg('Бос және ауыр жүкті көліктердің тежелуін салыстыру')
    s.add(sky('day', 120) + '<rect y="120" width="960" height="420" fill="#a9cf8f"/>')
    for yg, loaded in ((250, False), (470, True)):
        s.add(f'<rect y="{yg - 40}" width="960" height="70" fill="#5a6069"/><path d="M0 {yg + 12}H960" stroke="{MARK}" stroke-width="3" stroke-dasharray="40 30"/>')
        s.add(gazelle_side(20, yg, .62, '#f4f6f8', 'flatbed', sag=8 if loaded else 0))
        if loaded:
            s.add(f'<g transform="translate(20 {yg + 5}) scale(.62)">{flat_load(((0, 4), (0, 4), (0, 3)), 82, 56)}</g>')
        x0 = 20 + 540 * .62
        s.add(f'<path d="M{f(x0)} {yg - 4}H{f(x0 + 60)}" stroke="#2b313a" stroke-width="5" opacity=".5"/>')
        s.add(f'<rect x="{f(x0 + 20)}" y="{yg - 30}" width="{f(560 - x0 + 300)}" height="20" fill="#ffd23f" opacity=".25"/>')
        s.add(text(x0 + 30, yg - 50, 'бос' if not loaded else 'жүкті', 30, '#111c27', 900, 'start'))
        s.add(qmark(880, yg - 20, 22))
    return s


@scene('c011', 'Тік бұрылысқа жақындаған ауыр жүк көлігі')
def c011():
    s = Svg('Таудағы тік бұрылыс, ауыр жүк көлігі')
    p = P(bend=.0065)
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.2, edge=True, far=110)
    s.add(base)
    s.add(p_hills(p, 11, '#7c9a8a', .9, 90))
    for z in range(18, 60, 4):
        x0, y0 = p.pt(ur + 1.0, z, 0)
        x1, y1 = p.pt(ur + 1.0, z, .8)
        s.add(f'<path d="M{f(x0)} {f(y0)}V{f(y1)}" stroke="#9aa3ab" stroke-width="{f(max(p.scale(z) * .1, 1.5))}"/>')
    s.add(f'<polyline points="{pts([p.pt(ur + 1.0, z, .75) for z in range(18, 61, 2)])}" fill="none" stroke="#c9d0d6" stroke-width="5"/>')
    s.add(p_tree(p, ul - 5, 30, 8, 'pine'), p_tree(p, ul - 9, 22, 7, 'pine'))
    x, y = p.pt(ur + 1.2, 9.0, 2.6)
    s.add(p_post(p, ur + 1.2, 9.0, 2.8))
    s.add(f'<g transform="translate({f(x)} {f(y)}) scale(-1 1)">{sign_curve_right(p.scale(9) * 1.05)}</g>')
    x, yb = p.pt(0, 6.4)
    s.add(car_rear(s, x, yb, 2.4 * p.scale(6.4), '#e9edf1', truck=True), you(x - 190, yb - 300))
    return s


def p_my_truck(s, p, z=6.6, color='#e9edf1'):
    x, yb = p.pt(0, z)
    w = 2.45 * p.scale(z)
    return car_rear(s, x, yb, w, color, truck=True) + you(x - w * .56, yb - w * 1.2)


@scene('c012', 'Биіктік шектеу белгісі бар көпір асты')
def c012():
    s = Svg('Көпір астындағы биіктік шектеу белгісі')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='city', walk=2.5)
    s.add(base, facades(p, ur + 3.5, 30, 140, seed=12), facades(p, ul - 3.5, 30, 140, seed=13))
    z = 17
    a, b = p.pt(-30, z, 4.0), p.pt(30, z, 6.0)
    s.add(f'<rect x="-10" y="{f(b[1])}" width="980" height="{f(a[1] - b[1])}" fill="#8e99a6"/>')
    s.add(f'<rect x="-10" y="{f(b[1])}" width="980" height="{f((a[1] - b[1]) * .25)}" fill="#a9b4bf"/>')
    for u in (ul - 2.5, ur + 2.5):
        x0, y0 = p.pt(u - .6, z, 0)
        x1, y1 = p.pt(u + .6, z, 4)
        s.add(f'<rect x="{f(x0)}" y="{f(y1)}" width="{f(x1 - x0)}" height="{f(y0 - y1)}" fill="#7f8a95"/>')
    x, y = p.pt(0, z, 3.55)
    s.add(f'<g transform="translate({f(x)} {f(y)})">{sign_height(p.scale(z) * 1.0, "3,5")}</g>')
    s.add(p_sign(p, ur + 1.2, 9, 'height', .95, val='3,5'))
    s.add(p_my_truck(s, p))
    return s


@scene('c013', 'Көпір алдындағы массаны шектейтін белгі')
def c013():
    s = Svg('Көпір алдындағы масса шектеуі')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.2, edge=True)
    s.add(base)
    s.add(p_band(p, -80, 80, 16, 30, '#5d9fc9'))
    s.add(p_band(p, ul - .2, ur + .2, 15, 31, '#5a6069'))
    for u in (ul - .3, ur + .3):
        s.add(f'<polyline points="{pts([p.pt(u, z, 1.0) for z in (15, 18, 22, 26, 31)])}" fill="none" stroke="#c9d0d6" stroke-width="5"/>')
        for zz in (15, 19, 23, 27, 31):
            x0, y0 = p.pt(u, zz, 0)
            x1, y1 = p.pt(u, zz, 1.0)
            s.add(f'<path d="M{f(x0)} {f(y0)}V{f(y1)}" stroke="#9aa3ab" stroke-width="3"/>')
    s.add(p_tree(p, ur + 8, 40, 8, seed=13), p_tree(p, ul - 8, 44, 8, 'pine'))
    s.add(p_sign(p, ur + 1.2, 10.5, 'weight', 1.05, val='10т'))
    s.add(p_my_truck(s, p))
    return s


@scene('c014', 'Жүк кузовтың бір жағына ғана үйіліп тиелген')
def c014():
    s = Svg('Жүк бір жаққа үйілген, көлік қисайған')
    s.add(side_bg(s, city=True, seed=14, road=False))
    s.add('<rect y="330" width="960" height="210" fill="#6c737c"/>')
    boxes = ''.join(box_crate(-146 + 0 * 78 + (k % 2) * 76, -230 - (k // 2) * 60 + 80, 72, 58) for k in range(6))
    s.add(rear_truck(480, 500, 1.15, '#f4f6f8', 'flatbed', load=boxes, tilt=-4))
    s.add('<circle cx="380" cy="300" r="14" fill="#fff" stroke="#e2463b" stroke-width="4"/><path d="M380 286V314M366 300H394" stroke="#e2463b" stroke-width="3"/>')
    s.add('<path d="M480 520 V200" stroke="#ffd23f" stroke-width="3" stroke-dasharray="10 8"/>')
    s.add(qmark(640, 220, 24))
    return s


@scene('c015', 'Ашық кузовтағы бос бекітілген жүк')
def c015():
    s = Svg('Ашық кузовтағы бекітілмеген жүк желмен ұшып барады')
    s.add(side_bg(s, seed=15))
    load = flat_load(((0, 4), (0, 2)), 82, 56)
    s.add(gazelle_side(330, YG, 1.0, '#f4f6f8', 'flatbed'))
    s.add(f'<g transform="translate(330 {YG})">{load}</g>')
    s.add(f'<path d="M340 {YG - 216} Q300 {YG - 250} 250 {YG - 230} Q210 {YG - 214} 180 {YG - 240} L200 {YG - 200} Q240 {YG - 190} 280 {YG - 200} Q310 {YG - 210} 340 {YG - 160}Z" fill="#3f7fb8" opacity=".9"/>')
    s.add(f'<g transform="translate(150 {YG - 120}) rotate(-25)"><rect x="-26" y="-26" width="52" height="52" rx="3" fill="#c9965a" stroke="#8a5a2b" stroke-width="2"/></g>')
    s.add(f'<g transform="translate(70 {YG - 30}) rotate(30)"><rect x="-20" y="-20" width="40" height="40" rx="3" fill="#c9965a" stroke="#8a5a2b" stroke-width="2"/></g>')
    s.add(wind_lines(40, 120, 4, 130, '#ffffff'))
    s.add(qmark(560, 140, 24))
    return s


@scene('c017', 'Төмен көпір алдындағы жүк көлігі')
def c017():
    s = Svg('Төмен темір жол көпіріне жақындаған жүк көлігі')
    s.add(side_bg(s, seed=17))
    s.add(f'<rect x="640" y="150" width="320" height="56" fill="#7f8a95"/><rect x="640" y="140" width="320" height="14" fill="#5d6873"/>')
    s.add(f'<rect x="900" y="200" width="60" height="{YG - 200 + 30}" fill="#8e99a6"/>')
    s.add(f'<g transform="translate(790 206)">{sign_height(64, "3,8")}</g>')
    s.add(dim_arrow(700, 210, 700, YG, '3,8 м', lx=744, ly=330))
    load = flat_load(((0, 4), (0, 4), (0, 3)), 82, 58)
    s.add(gazelle_side(40, YG, .95, '#f4f6f8', 'flatbed'))
    s.add(f'<g transform="translate(40 {YG}) scale(.95)">{load}</g>')
    s.add(dim_arrow(620, YG - 4, 620, YG - 274 * .95 - 10, ''), qmark(620, 190, 20))
    return s


@scene('c018', 'Жүк көлігінің соқыр аймағында жеңіл көлік тұр')
def c018():
    s = Svg('Жүк көлігінің оң жағындағы соқыр аймақта жеңіл көлік')
    s.add(straight_road(s, 'v', 480, 116, (2, 2), 'double', 'city', 18))
    s.add(blind_zones(509, 110, 0, '#ff3b30', 1.9))
    s.add(f'<g opacity=".3"><rect x="470" y="50" width="78" height="44" fill="#ff3b30"/></g>')
    s.add(car(s, 509, 200, 0, '#2f6fd6', 'truck', signal='right', cargo='#eef1f4', label=you(430, 200)))
    s.add(car(s, 567, 196, 0, 'yellow'))
    s.add(path_arrow(s, 'M509 90 C509 60 567 50 567 10'), qmark(640, 300))
    s.add(car(s, 393, 120, 180, 'white'))
    return s


@scene('c019', 'Тар ауламен жүк көлігі артқа жүріп барады')
def c019():
    s = Svg('Тар жерде артқа жүріп келе жатқан жүк көлігі')
    s.add(f'<rect width="{W}" height="{H}" fill="#9a9a94"/>')
    s.add(roof(-20, -20, 360, 580, '#b8a58c', False), roof(620, -20, 360, 580, '#a9b4bf', False))
    s.add(f'<rect x="340" y="0" width="280" height="540" fill="#6c737c"/>')
    s.add(f'<rect x="352" y="420" width="70" height="40" rx="4" fill="#2f7a3f"/><rect x="556" y="380" width="54" height="54" rx="6" fill="#8e5d3b"/>')
    s.add(f'<g opacity=".3"><rect x="430" y="300" width="100" height="200" fill="#ff3b30"/></g>')
    s.add(car(s, 480, 160, 0, '#e2463b', 'truck', cargo='#eef1f4', label=you(480, 40)))
    s.add(glow(s, 458, 266, 22, '#ffffff'), glow(s, 502, 266, 22, '#ffffff'))
    s.add(path_arrow(s, 'M480 290 L480 420'))
    s.add(person_top(470, 470, -90, '#f2c230'))
    s.add(qmark(570, 300))
    return s


@scene('c020', 'Ұзын еңіспен түсіп келе жатқан ауыр жүк көлігі')
def c020():
    s = Svg('Ұзақ еңіс: ауыр жүк көлігі төмен түсіп келеді')
    s.add(sky('day', 540))
    s.add('<path d="M-20 330 L200 250 L420 290 L640 210 L980 280 V540 H-20Z" fill="#9cbcaa" opacity=".7"/>')
    s.add('<path d="M-20 170 L980 470 V540 H-20Z" fill="#a9cf8f"/>')
    s.add('<path d="M-20 196 L980 496 L980 520 L-20 220Z" fill="#5a6069"/>')
    s.add('<path d="M-20 208 L980 508" stroke="#f5f5ef" stroke-width="4" stroke-dasharray="40 30"/>')
    s.add(f'<g transform="translate(200 254) rotate(16.7)">' + heavy_truck_side(0, 0, .7, '#2f6fd6', '#d98b2b', 'tipper', 3) + '</g>')
    s.add(post_sign(820, 410, 'steep_down', 96, pole=120, pct='10%'))
    s.add(qmark(560, 120, 24))
    return s


@scene('c022', 'Ауыр жүк көлігі жеңіл көліктің артынан келеді')
def c022():
    s = Svg('Ауыр жүк көлігі мен алдыңғы жеңіл көлік арасындағы қашықтық')
    s.add(straight_road(s, 'v', 480, 116, (2, 2), 'double', 'grass', 22))
    s.add(car(s, 509, 90, 0, 'blue', brake=True))
    s.add(f'<rect x="490" y="150" width="38" height="170" fill="#ffd23f" opacity=".3"/>')
    s.add(dim_arrow(560, 150, 560, 318, ''), qmark(610, 236))
    s.add(car(s, 509, 430, 0, '#2f6fd6', 'truck', cargo='#d98b2b', label=you(430, 430)))
    s.add(car(s, 451, 300, 180, 'white'), car(s, 393, 60, 180, 'grey'))
    return s


@scene('c023', 'ГАЗельге жүк тиеу: рұқсат етілген ең жоғары масса')
def c023():
    s = Svg('ГАЗельге жүк тиеу')
    s.add(side_bg(s, city=True, seed=23))
    load = flat_load(((0, 4), (0, 3)), 82, 58)
    s.add(gazelle_side(60, YG, 1.0, '#f4f6f8', 'flatbed'))
    s.add(f'<g transform="translate(60 {YG})">{load}</g>')
    s.add(f'<g transform="translate(60 {YG})">{box_crate(250, -280, 82, 58)}</g>')
    s.add(person(40, YG + 6, 180, '#2f9e6b', 'stand'))
    s.add(spec_card(640, 26, 'Рұқсат етілген ең жоғары масса', '3 500 кг', 290))
    s.add(card(640, 136, 290, 70) + text(660, 180, 'Тиелген жүк:', 20, '#5b6b7b', 800, 'start') + text(880, 182, '?', 32, '#f59e0b', 900))
    return s


@scene('c024', 'Ашық жолда бүйірден қатты жел соғып тұр')
def c024():
    s = Svg('Бүйірден соққан қатты жел, биік кузовты жүк көлігі')
    p = P()
    base, (ul, uc, ur) = street(s, p, env='country', walk=1.0, edge=True)
    s.add(base)
    x0, y0 = p.pt(ur + 1.6, 12, 0)
    x1, y1 = p.pt(ur + 1.6, 12, 4)
    s.add(f'<path d="M{f(x0)} {f(y0)}V{f(y1)}" stroke="#8c98a4" stroke-width="5"/>')
    s.add(f'<path d="M{f(x1)} {f(y1)} l60 8 l-4 26 l-56 -8z" fill="#ff7a2f"/><path d="M{f(x1 + 20)} {f(y1 + 3)} l0 26 M{f(x1 + 40)} {f(y1 + 6)} l0 25" stroke="#fff" stroke-width="5"/>')
    s.add(p_sign(p, ur + 1.3, 10, 'crosswind', 1.05))
    s.add(wind_lines(30, 210, 4, 150, '#ffffff'))
    x, yb = p.pt(0, 6.6)
    w = 2.45 * p.scale(6.6)
    s.add(f'<g transform="rotate(3 {f(x)} {f(yb)})">{car_rear(s, x, yb, w, "#e9edf1", truck=True)}</g>', you(x - w * .56, yb - w * 1.2))
    s.add(qmark(150, 400, 24))
    return s


@scene('c025', 'Биік тиелген көлік бұрылыста')
def c025():
    s = Svg('Биік жүк тиелген көлік бұрылыста қисаяды')
    s.add(side_bg(s, city=False, seed=25, road=False))
    s.add('<rect y="330" width="960" height="210" fill="#6c737c"/>')
    boxes = ''.join(box_crate(-146 + (k % 4) * 74, -210 - (k // 4) * 60, 70, 58) for k in range(16))
    s.add(rear_truck(480, 500, 1.0, '#f4f6f8', 'flatbed', load=boxes, tilt=6))
    s.add('<circle cx="500" cy="190" r="14" fill="#fff" stroke="#e2463b" stroke-width="4"/><path d="M500 176V204M486 190H514" stroke="#e2463b" stroke-width="3"/>')
    s.add('<path d="M240 160 Q180 300 260 420" stroke="#ffd23f" stroke-width="7" fill="none" stroke-dasharray="14 10"/><polygon points="252,428 278,408 248,400" fill="#ffd23f"/>')
    s.add(qmark(760, 200, 24))
    return s


@scene('c026', 'Түнде жол жиегінде тоқтаған жүк көлігі')
def c026():
    s = Svg('Түнде жол шетінде тоқтап тұрған жүк көлігі')
    p = P()
    base, (ul, uc, ur) = street(s, p, kind='night', env='country', walk=1.4, edge=True)
    s.add(base)
    s.add(f'<polygon points="{pts([p.pt(-1.2, 5.5), p.pt(1.2, 5.5), p.pt(3.0, 40), p.pt(-3.4, 40)])}" fill="#fff6cc" opacity=".18"/>')
    x, yb = p.pt(ur + .4, 19)
    s.add(car_rear(s, x, yb, 2.45 * p.scale(19), '#3b4450', truck=True, plate=True))
    s.add(f'<rect width="{W}" height="{H}" fill="#020812" opacity=".12"/>')
    s.add(qmark(x + 120, yb - 170, 22))
    s.add(my_car(s, p, night=True, label=False))
    return s


@scene('c028', 'Жүк көлігі оңға бұрылады: алдыңғы және артқы доңғалақ іздері')
def c028():
    s = Svg('Бұрылыста артқы доңғалақтар ішкерірек жүреді')
    s.add(crossroads(s, 480, 230, 'NSEW', h_hw=58, v_hw=58, blocks='city', seed=28, zebra='', stop=''))
    s.add(f'<path d="M538 540 L538 330 Q538 288 600 288 L960 288" fill="none" stroke="#ffd23f" stroke-width="5" stroke-dasharray="14 10"/>')
    s.add(f'<path d="M530 540 L530 380 Q530 300 600 300" fill="none" stroke="#ff3b30" stroke-width="5" stroke-dasharray="14 10"/>')
    s.add(car(s, 640, 259, 72, '#2f6fd6', 'truck', signal='right', cargo='#eef1f4', scale=.8))
    s.add(qmark(590, 380))
    s.add(card(24, 410, 360, 112) + '<path d="M50 448 H112" stroke="#ffd23f" stroke-width="8" stroke-dasharray="14 9"/>' + text(126, 456, 'алдыңғы доңғалақ', 23, '#111c27', 900, 'start')
          + '<path d="M50 492 H112" stroke="#ff3b30" stroke-width="8" stroke-dasharray="14 9"/>' + text(126, 500, 'артқы доңғалақ', 23, '#111c27', 900, 'start'))
    return s


@scene('c029', 'Тар қиылыста жүк көлігі оңға бұрылады, ішкі жақта велосипедші')
def c029():
    s = Svg('Тар қиылыста оңға бұрылатын жүк көлігі және оң жақтағы велосипедші')
    s.add(city4(s, blocks='city', seed=29))
    s.add(car(s, NB, 400, 0, '#2f6fd6', 'truck', signal='right', cargo='#eef1f4', label=you(440, 470)))
    s.add(path_arrow(s, f'M{NB} 290 Q{NB} {EB} 590 {EB} L760 {EB}'))
    s.add(car(s, 548, 380, 0, '#2f9e6b', 'bike', scale=1.3), person_top(570, 344, -90, '#d9534f'))
    s.add(qmark(620, 410))
    return s


@scene('c030', 'Жүк қорабының есігі бекітілмеген')
def c030():
    s = Svg('Есігі ашық тұрған жүк қорабы')
    s.add(side_bg(s, city=True, seed=30, road=False))
    s.add('<rect y="330" width="960" height="210" fill="#6c737c"/>')
    s.add(rear_truck(480, 500, 1.15, '#f4f6f8', 'box', plate=True))
    inner = ''.join(box_crate(x, y, 64, 54) for x, y in ((310, 250), (380, 250), (310, 194), (380, 194), (450, 250)))
    s.add('<rect x="308" y="125" width="172" height="280" fill="#3a4450"/>' + inner)
    s.add('<path d="M308 124 L200 150 L200 420 L308 405 Z" fill="#dfe5ea" stroke="#b4bec8" stroke-width="3"/>')
    s.add('<path d="M215 250 L290 246" stroke="#8e99a6" stroke-width="5"/>')
    s.add('<path d="M170 180 q-20 30 0 60 M150 170 q-30 40 0 80" stroke="#ffd23f" stroke-width="5" fill="none"/>')
    s.add(qmark(720, 200, 24))
    return s


@scene('c031', 'Жүк көлігінің кабинасы алдында адам тұр')
def c031():
    s = Svg('Кабинаның дәл алдындағы көрінбейтін аймақ')
    s.add(side_bg(s, city=True, seed=31))
    s.add(heavy_truck_side(-300, YG, 1.0, '#2f6fd6', '#eef1f4', 'box', 3))
    s.add(f'<polygon points="{pts([(466, YG - 248), (960, YG + 40), (474, YG + 40)])}" fill="#ff3b30" opacity=".16"/>')
    s.add(f'<path d="M440 {YG - 252} L960 {YG + 20}" stroke="#ffd23f" stroke-width="4" stroke-dasharray="14 10"/>')
    s.add(f'<circle cx="440" cy="{YG - 252}" r="9" fill="#ffd23f" stroke="#fff" stroke-width="3"/>')
    s.add(person(560, YG + 8, 120, '#f2c230', 'stand', -1))
    s.add(qmark(640, 200, 24))
    return s


@scene('c032', 'Кенет тежегенде бекітілмеген жүк')
def c032():
    s = Svg('Кенет тежеу: бекітілмеген жәшіктер алға жылжиды')
    s.add(side_bg(s, seed=32))
    s.add(f'<path d="M80 {YG + 2} H360 M90 {YG + 8} H340" stroke="#22272d" stroke-width="5" opacity=".6"/>')
    s.add(gazelle_side(140, YG, 1.0, '#f4f6f8', 'flatbed', tilt=-1.2))
    for i, (x, y, a) in enumerate(((330, -165, 8), (250, -165, 4), (300, -230, 14), (190, -165, 0))):
        s.add(f'<g transform="translate({140 + x} {YG + y}) rotate({a})">{box_crate(0, 0, 80, 58)}</g>')
    s.add('<g stroke="#ffffff" stroke-width="5" stroke-linecap="round"><path d="M300 270 h-50 M310 300 h-70 M300 330 h-40"/></g>')
    s.add(text(620, 120, 'ТЕЖЕУ', 34, '#e2463b', 900))
    s.add(qmark(760, 110, 24))
    return s


@scene('c033', 'Ауыр жүкті көлік бұрылысқа жақындап келеді')
def c033():
    s = Svg('Қатты жүктелген көлік бұрылыс алдында')
    s.add(crossroads(s, 480, 210, 'NSEW', blocks='city', seed=33))
    s.add(path_arrow(s, f'M{NB} 352 Q{NB} 181 400 181 L200 181'), qmark(380, 320))
    s.add(car(s, NB, 440, 0, '#2f6fd6', 'dump', signal='left', label=you(440, 470)))
    s.add('<g stroke="#ffffff" stroke-width="4" stroke-linecap="round" opacity=".9"><path d="M494 530V548M509 524V548M524 530V548"/></g>')
    s.add(car(s, SB, 60, 180, 'white'))
    return s


@scene('c034', 'Жүк тіркеу нөмірін жауып тұр')
def c034():
    s = Svg('Артқы бортқа байланған жүк нөмірді жауып тұр')
    s.add(side_bg(s, city=True, seed=34, road=False))
    s.add('<rect y="330" width="960" height="210" fill="#6c737c"/>')
    load = (box_crate(-140, -228, 90, 78) + box_crate(-40, -228, 90, 78) + box_crate(56, -228, 84, 78)
            + '<g transform="translate(0 0)">' + box_crate(-70, -84, 140, 70, '#b98a52') + '</g>'
            + '<path d="M-90 -90 L-60 -20 M90 -90 L60 -20" stroke="#f2a516" stroke-width="6"/>')
    s.add(rear_truck(480, 500, 1.2, '#f4f6f8', 'flatbed', load=load))
    s.add(qmark(700, 300, 24))
    return s
