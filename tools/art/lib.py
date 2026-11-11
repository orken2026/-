"""QAZAQ PDD — суреттерге арналған SVG сызу кітапханасы (тек стандартты Python).

Үш түрлі көрініс:
  * жоғарыдан (top-down) — қиылыстар, жолақтар, маневрлер;
  * перспектива (жүргізуші көзімен) — белгілер, бағдаршамдар, ауа райы;
  * бүйірден / артынан — жүк көліктері, жүк, салон.
"""
import math
import random

W, H = 960, 540
FONT = "'Inter','Segoe UI',Roboto,Arial,sans-serif"


def f(v):
    """Санды қысқа форматта жазу."""
    if isinstance(v, float):
        s = f'{v:.1f}'
        return s[:-2] if s.endswith('.0') else s
    return str(v)


def pts(points):
    return ' '.join(f'{f(x)},{f(y)}' for x, y in points)


def esc(t):
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


class Svg:
    def __init__(self, label='Жол жағдайы'):
        self.parts = []
        self.defs = {}
        self.label = label
        self.markers = set()

    def add(self, *items):
        for s in items:
            if s:
                self.parts.append(s)
        return self

    def define(self, key, content):
        self.defs.setdefault(key, content)

    def marker(self, color):
        key = 'm' + color.replace('#', '')
        if key not in self.markers:
            self.markers.add(key)
            self.define(key, f'<marker id="{key}" viewBox="0 0 10 10" refX="5.5" refY="5" markerWidth="3.6" markerHeight="3.6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="{color}"/></marker>')
        return key

    def render(self):
        base_defs(self)
        defs = ''.join(self.defs.values())
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
                f'role="img" aria-label="{esc(self.label)}" font-family="{FONT}">'
                f'<defs>{defs}</defs>' + ''.join(self.parts) + '</svg>')


def radial(svg, key, color, inner=0.95, mid=0.45):
    svg.define(key, f'<radialGradient id="{key}"><stop offset="0" stop-color="{color}" stop-opacity="{inner}"/>'
                    f'<stop offset=".35" stop-color="{color}" stop-opacity="{mid}"/>'
                    f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
    return f'url(#{key})'


def base_defs(svg):
    svg.define('asph', '<linearGradient id="asph" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#555b63"/><stop offset="1" stop-color="#474d55"/></linearGradient>')
    svg.define('glass', '<linearGradient id="glass" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#33465a"/><stop offset=".55" stop-color="#1d2a38"/><stop offset="1" stop-color="#3e5670"/></linearGradient>')
    svg.define('sheen', '<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#000" stop-opacity=".22"/><stop offset=".3" stop-color="#fff" stop-opacity=".16"/><stop offset=".55" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#000" stop-opacity=".25"/></linearGradient>')
    svg.define('vsheen', '<linearGradient id="vsheen" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#fff" stop-opacity=".28"/><stop offset=".45" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></linearGradient>')
    svg.define('beam', '<linearGradient id="beam" x1="0" y1="1" x2="0" y2="0"><stop stop-color="#fff7d1" stop-opacity=".75"/><stop offset="1" stop-color="#fff7d1" stop-opacity="0"/></linearGradient>')


# ======================================================================
#  ЖАЛПЫ ЭЛЕМЕНТТЕР
# ======================================================================

def text(x, y, t, size=20, color='#fff', weight=800, anchor='middle', extra=''):
    return (f'<text x="{f(x)}" y="{f(y)}" font-size="{f(size)}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}" {extra}>{esc(t)}</text>')


def pill(x, y, t, bg='#e8433a', fg='#fff', size=17, pad=10):
    w = len(t) * size * 0.66 + pad * 2
    h = size + 12
    return (f'<g><rect x="{f(x - w / 2)}" y="{f(y - h / 2)}" width="{f(w)}" height="{f(h)}" rx="{f(h / 2)}" fill="{bg}" stroke="#fff" stroke-width="2.5"/>'
            + text(x, y + size * 0.36, t, size, fg) + '</g>')


def you(x, y):
    """«СІЗ» белгісі — сұрақтағы көлік."""
    return pill(x, y, 'СІЗ', '#e8433a', '#fff', 21, 11)


def qmark(x, y, r=20):
    return (f'<g><circle cx="{f(x)}" cy="{f(y)}" r="{f(r + 3)}" fill="#fff"/><circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#f59e0b"/>'
            + text(x, y + r * 0.42, '?', r * 1.25, '#fff', 900) + '</g>')


def path_arrow(svg, d, color='#ffd23f', width=7, dash=True, opacity=1.0, outline=True):
    m = svg.marker(color)
    da = f'stroke-dasharray="{f(width * 2.2)} {f(width * 1.4)}"' if dash else ''
    out = ''
    if outline:
        out += f'<path d="{d}" fill="none" stroke="#1b2430" stroke-opacity=".35" stroke-width="{f(width + 4)}" stroke-linecap="round" {da}/>'
    return (f'<g opacity="{opacity}">' + out +
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{f(width)}" stroke-linecap="round" {da} marker-end="url(#{m})"/></g>')


def shadow_rect(x, y, w, h, rx, dx=4, dy=6, op=.22):
    return f'<rect x="{f(x + dx)}" y="{f(y + dy)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" fill="#0b1520" opacity="{op}"/>'


def card(x, y, w, h, content='', fill='#ffffff', stroke='#d9e2ea'):
    return (shadow_rect(x, y, w, h, 16, 3, 6, .25) +
            f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="16" fill="{fill}" stroke="{stroke}" stroke-width="2"/>' + content)


def glow(svg, x, y, r, color, key=None, inner=.95):
    key = key or 'g' + color.replace('#', '') + str(int(inner * 100))
    fill = radial(svg, key, color, inner)
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{fill}"/>'


# ======================================================================
#  ЖОЛ БЕЛГІЛЕРІ (бет жағынан, центрі 0,0, өлшемі s)
# ======================================================================

def _ring(s, ring='#d6161e', fill='#fff'):
    r = s / 2
    return (f'<circle r="{f(r)}" fill="#fff"/><circle r="{f(r * .93)}" fill="{ring}"/>'
            f'<circle r="{f(r * .73)}" fill="{fill}"/>')


def _tri(s, inner=''):
    r = s / 2
    o = [(0, -r * 1.0), (r * 1.08, r * .82), (-r * 1.08, r * .82)]
    i = [(0, -r * .62), (r * .74, r * .6), (-r * .74, r * .6)]
    return (f'<polygon points="{pts(o)}" fill="#fff" stroke="#fff" stroke-width="{f(s * .05)}" stroke-linejoin="round"/>'
            f'<polygon points="{pts(o)}" fill="#d6161e" stroke="#d6161e" stroke-width="{f(s * .03)}" stroke-linejoin="round"/>'
            f'<polygon points="{pts(i)}" fill="#fff" stroke="#fff" stroke-width="{f(s * .03)}" stroke-linejoin="round"/>' + inner)


def sign_stop(s):
    r = s / 2
    o = [(r * math.cos(math.radians(22.5 + 45 * k)), r * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    i = [(x * .88, y * .88) for x, y in o]
    return (f'<polygon points="{pts(o)}" fill="#fff"/><polygon points="{pts(i)}" fill="#d6161e"/>'
            + text(0, s * .13, 'STOP', s * .34, '#fff', 900, extra='letter-spacing="-1"'))


def sign_yield(s):
    r = s / 2
    o = [(-r * 1.08, -r * .8), (r * 1.08, -r * .8), (0, r * 1.0)]
    i = [(-r * .72, -r * .57), (r * .72, -r * .57), (0, r * .6)]
    return (f'<polygon points="{pts(o)}" fill="#d6161e" stroke="#fff" stroke-width="{f(s * .05)}" stroke-linejoin="round"/>'
            f'<polygon points="{pts(i)}" fill="#fff"/>')


def sign_no_entry(s):
    r = s / 2
    return (f'<circle r="{f(r)}" fill="#fff"/><circle r="{f(r * .94)}" fill="#d6161e"/>'
            f'<rect x="{f(-r * .7)}" y="{f(-r * .17)}" width="{f(r * 1.4)}" height="{f(r * .34)}" fill="#fff"/>')


def sign_main_road(s):
    r = s / 2
    return (f'<g transform="rotate(45)"><rect x="{f(-r * .72)}" y="{f(-r * .72)}" width="{f(r * 1.44)}" height="{f(r * 1.44)}" fill="#fff" stroke="#222" stroke-width="{f(s * .02)}"/>'
            f'<rect x="{f(-r * .48)}" y="{f(-r * .48)}" width="{f(r * .96)}" height="{f(r * .96)}" fill="#f6c400" stroke="#222" stroke-width="{f(s * .015)}"/></g>')


def sign_number(s, num, unit=''):
    fs = s * (.42 if len(num) <= 2 else .32)
    t = text(0, fs * .36, num, fs, '#111', 900)
    if unit:
        t = text(0, fs * .2, num, fs, '#111', 900) + text(0, fs * .2 + s * .2, unit, s * .17, '#111', 800)
    return _ring(s) + t


def sign_speed(s, n='60'):
    return _ring(s) + text(0, s * .15, n, s * .44, '#111', 900, extra='letter-spacing="-1"')


def sign_temp_speed(s, n='40'):
    """Уақытша белгі — сары фонда."""
    r = s / 2
    return (f'<circle r="{f(r)}" fill="#fff"/><circle r="{f(r * .93)}" fill="#d6161e"/><circle r="{f(r * .73)}" fill="#ffd20a"/>'
            + text(0, s * .15, n, s * .44, '#111', 900, extra='letter-spacing="-1"'))


def _ped(scale=1.0, color='#111'):
    """Жаяу жүргінші силуэті (биіктігі ~1)."""
    k = scale
    return (f'<g fill="{color}" stroke="{color}" stroke-linecap="round" stroke-linejoin="round">'
            f'<circle cx="{f(.05 * k)}" cy="{f(-.4 * k)}" r="{f(.085 * k)}" stroke="none"/>'
            f'<path d="M{f(.02 * k)} {f(-.28 * k)} L{f(-.02 * k)} {f(.04 * k)}" stroke-width="{f(.13 * k)}" fill="none"/>'
            f'<path d="M{f(-.02 * k)} {f(.04 * k)} L{f(-.16 * k)} {f(.36 * k)} M{f(-.02 * k)} {f(.04 * k)} L{f(.13 * k)} {f(.2 * k)} L{f(.12 * k)} {f(.38 * k)}" stroke-width="{f(.09 * k)}" fill="none"/>'
            f'<path d="M{f(.02 * k)} {f(-.22 * k)} L{f(-.15 * k)} {f(-.03 * k)} M{f(.02 * k)} {f(-.22 * k)} L{f(.17 * k)} {f(-.06 * k)}" stroke-width="{f(.07 * k)}" fill="none"/></g>')


def sign_crosswalk(s):
    r = s / 2
    tri = [(0, -r * .66), (r * .7, r * .5), (-r * .7, r * .5)]
    zebra = ''.join(f'<rect x="{f(-r * .5 + i * r * .22)}" y="{f(r * .3)}" width="{f(r * .12)}" height="{f(r * .15)}" fill="#111"/>' for i in range(5))
    return (f'<rect x="{f(-r)}" y="{f(-r)}" width="{f(s)}" height="{f(s)}" rx="{f(s * .08)}" fill="#fff"/>'
            f'<rect x="{f(-r * .93)}" y="{f(-r * .93)}" width="{f(s * .93)}" height="{f(s * .93)}" rx="{f(s * .06)}" fill="#1565c0"/>'
            f'<polygon points="{pts(tri)}" fill="#fff" stroke="#fff" stroke-width="{f(s * .04)}" stroke-linejoin="round"/>'
            + zebra + f'<g transform="translate(0 {f(-r * .02)})">{_ped(s * .62)}</g>')


def sign_roundabout(s):
    r = s / 2
    out = f'<circle r="{f(r)}" fill="#fff"/><circle r="{f(r * .93)}" fill="#1565c0"/>'
    for k in range(3):
        a = k * 120
        out += (f'<g transform="rotate({a})"><path d="M{f(r * .2)} {f(-r * .5)} A{f(r * .54)} {f(r * .54)} 0 0 0 {f(-r * .42)} {f(-r * .33)}" '
                f'fill="none" stroke="#fff" stroke-width="{f(s * .085)}"/>'
                f'<polygon points="{pts([(-r * .62, -r * .18), (-r * .5, -r * .5), (-r * .27, -r * .22)])}" fill="#fff"/></g>')
    return out


def sign_no_stopping(s):
    r = s / 2
    return (f'<circle r="{f(r)}" fill="#fff"/><circle r="{f(r * .94)}" fill="#d6161e"/><circle r="{f(r * .74)}" fill="#1565c0"/>'
            f'<path d="M{f(-r * .52)} {f(-r * .52)}L{f(r * .52)} {f(r * .52)}M{f(r * .52)} {f(-r * .52)}L{f(-r * .52)} {f(r * .52)}" stroke="#d6161e" stroke-width="{f(s * .1)}"/>')


def sign_no_parking(s):
    r = s / 2
    return (f'<circle r="{f(r)}" fill="#fff"/><circle r="{f(r * .94)}" fill="#d6161e"/><circle r="{f(r * .74)}" fill="#1565c0"/>'
            f'<path d="M{f(-r * .52)} {f(-r * .52)}L{f(r * .52)} {f(r * .52)}" stroke="#d6161e" stroke-width="{f(s * .1)}"/>')


def sign_parking(s):
    r = s / 2
    return (f'<rect x="{f(-r)}" y="{f(-r)}" width="{f(s)}" height="{f(s)}" rx="{f(s * .08)}" fill="#fff"/>'
            f'<rect x="{f(-r * .93)}" y="{f(-r * .93)}" width="{f(s * .93)}" height="{f(s * .93)}" rx="{f(s * .06)}" fill="#1565c0"/>'
            + text(0, s * .23, 'P', s * .72, '#fff', 900))


def sign_road_works(s):
    r = s / 2
    k = s * .5
    man = (f'<g stroke="#111" stroke-linecap="round" fill="none" transform="translate({f(-r * .05)} {f(r * .05)})">'
           f'<circle cx="{f(-.12 * k)}" cy="{f(-.36 * k)}" r="{f(.07 * k)}" fill="#111" stroke="none"/>'
           f'<path d="M{f(-.12 * k)} {f(-.26 * k)} L{f(-.02 * k)} {f(.0 * k)} L{f(-.15 * k)} {f(.3 * k)} M{f(-.02 * k)} {f(0)} L{f(.1 * k)} {f(.28 * k)}" stroke-width="{f(.08 * k)}"/>'
           f'<path d="M{f(-.1 * k)} {f(-.2 * k)} L{f(.2 * k)} {f(-.05 * k)} L{f(.32 * k)} {f(.28 * k)}" stroke-width="{f(.055 * k)}"/>'
           f'<path d="M{f(.22 * k)} {f(.3 * k)} L{f(.42 * k)} {f(.3 * k)}" stroke-width="{f(.07 * k)}"/>'
           f'<path d="M{f(-.38 * k)} {f(.32 * k)} q{f(.1 * k)} {f(-.14 * k)} {f(.24 * k)} {f(-.1 * k)}" stroke-width="{f(.06 * k)}"/></g>')
    return _tri(s, man)


def sign_curve_right(s):
    r = s / 2
    return _tri(s, f'<path d="M{f(-r * .14)} {f(r * .45)} L{f(-r * .14)} {f(-r * .02)} Q{f(-r * .14)} {f(-r * .22)} {f(r * .1)} {f(-r * .22)}" fill="none" stroke="#111" stroke-width="{f(s * .07)}"/>'
                   f'<polygon points="{pts([(r * .08, -r * .38), (r * .32, -r * .22), (r * .08, -r * .06)])}" fill="#111"/>')


def sign_slippery(s):
    r = s / 2
    car = (f'<g transform="translate(0 {f(-r * .08)})"><rect x="{f(-r * .26)}" y="{f(-r * .14)}" width="{f(r * .52)}" height="{f(r * .2)}" rx="{f(r * .05)}" fill="#111"/>'
           f'<path d="M{f(-r * .16)} {f(-r * .14)} L{f(-r * .1)} {f(-r * .27)} L{f(r * .12)} {f(-r * .27)} L{f(r * .18)} {f(-r * .14)}Z" fill="#111"/></g>')
    tracks = (f'<path d="M{f(-r * .3)} {f(r * .5)} q{f(r * .2)} {f(-r * .14)} {f(0)} {f(-r * .28)} q{f(-r * .2)} {f(-r * .1)} {f(r * .05)} {f(-r * .22)}" fill="none" stroke="#111" stroke-width="{f(s * .035)}"/>'
              f'<path d="M{f(r * .12)} {f(r * .5)} q{f(r * .2)} {f(-r * .14)} {f(0)} {f(-r * .28)} q{f(-r * .2)} {f(-r * .1)} {f(r * .05)} {f(-r * .22)}" fill="none" stroke="#111" stroke-width="{f(s * .035)}"/>')
    return _tri(s, tracks + car)


def sign_steep_down(s, pct='10%'):
    r = s / 2
    return _tri(s, f'<polygon points="{pts([(-r * .52, -r * .08), (r * .52, r * .48), (-r * .52, r * .48)])}" fill="#111"/>'
                   + text(r * .02, -r * .12, pct, s * .2, '#111', 900))


def sign_crosswind(s):
    r = s / 2
    return _tri(s, f'<path d="M{f(-r * .45)} {f(r * .38)} L{f(-r * .45)} {f(-r * .12)}" stroke="#111" stroke-width="{f(s * .04)}"/>'
                   f'<path d="M{f(-r * .43)} {f(-r * .12)} C{f(-r * .1)} {f(-r * .2)} {f(r * .1)} {f(r * .1)} {f(r * .48)} {f(r * .1)} L{f(r * .44)} {f(r * .28)} C{f(r * .1)} {f(r * .26)} {f(-r * .1)} {f(r * .1)} {f(-r * .43)} {f(r * .1)}Z" fill="#d6161e" stroke="#111" stroke-width="{f(s * .02)}"/>')


def sign_rail_barrier(s):
    r = s / 2
    fence = (f'<g fill="#111"><rect x="{f(-r * .5)}" y="{f(r * .02)}" width="{f(r)}" height="{f(r * .1)}"/>'
             f'<rect x="{f(-r * .5)}" y="{f(r * .25)}" width="{f(r)}" height="{f(r * .1)}"/>'
             + ''.join(f'<rect x="{f(-r * .48 + i * r * .32)}" y="{f(-r * .12)}" width="{f(r * .1)}" height="{f(r * .62)}"/>' for i in range(4)) + '</g>')
    return _tri(s, fence)


def sign_st_andrew(s):
    r = s / 2
    w = s * .17
    bar = (f'<rect x="{f(-r * 1.15)}" y="{f(-w / 2)}" width="{f(r * 2.3)}" height="{f(w)}" fill="#fff" stroke="#d6161e" stroke-width="{f(s * .025)}"/>'
           + ''.join(f'<rect x="{f(-r * 1.0 + i * r * .58)}" y="{f(-w / 2 + s * .012)}" width="{f(r * .28)}" height="{f(w - s * .024)}" fill="#d6161e"/>' for i in range(4)))
    return f'<g transform="rotate(35)">{bar}</g><g transform="rotate(-35)">{bar}</g>'


def sign_height(s, val='3,5'):
    r = s / 2
    return (_ring(s) + text(0, s * .1, val, s * .28, '#111', 900) +
            f'<polygon points="{pts([(-r * .14, -r * .58), (r * .14, -r * .58), (0, -r * .38)])}" fill="#111"/>'
            f'<polygon points="{pts([(-r * .14, r * .58), (r * .14, r * .58), (0, r * .38)])}" fill="#111"/>')


def sign_weight(s, val='10т'):
    return _ring(s) + text(0, s * .12, val, s * .32, '#111', 900)


def sign_no_overtake(s):
    r = s / 2

    def carico(x, c):
        return (f'<g transform="translate({f(x)} {f(r * .05)})"><rect x="{f(-r * .17)}" y="{f(-r * .3)}" width="{f(r * .34)}" height="{f(r * .5)}" rx="{f(r * .08)}" fill="{c}"/>'
                f'<rect x="{f(-r * .12)}" y="{f(-r * .2)}" width="{f(r * .24)}" height="{f(r * .12)}" fill="#fff" opacity=".8"/></g>')
    return _ring(s) + carico(-r * .25, '#d6161e') + carico(r * .25, '#111')


def sign_lanes(s, arrows=('L', 'S', 'R')):
    r = s / 2
    n = len(arrows)
    w = s * 1.2
    out = (f'<rect x="{f(-w / 2)}" y="{f(-r)}" width="{f(w)}" height="{f(s)}" rx="{f(s * .07)}" fill="#fff"/>'
           f'<rect x="{f(-w / 2 + s * .04)}" y="{f(-r + s * .04)}" width="{f(w - s * .08)}" height="{f(s * .92)}" rx="{f(s * .05)}" fill="#1565c0"/>')
    for i, a in enumerate(arrows):
        x = -w / 2 + w * (i + .5) / n
        out += f'<g transform="translate({f(x)} {f(r * .1)})">' + lane_arrow_icon(a, s * .5, '#fff') + '</g>'
        if i:
            out += f'<path d="M{f(-w / 2 + w * i / n)} {f(-r * .7)}V{f(r * .7)}" stroke="#fff" stroke-width="{f(s * .025)}" stroke-dasharray="{f(s * .06)} {f(s * .05)}"/>'
    return out


def lane_arrow_icon(kind, s, color='#fff'):
    """Жолақ бағыты көрсеткіші (биіктігі s), төменнен жоғары."""
    h = s / 2
    sw = s * .13
    shaft = f'<path d="M0 {f(h)} V{f(-h * .1)}" stroke="{color}" stroke-width="{f(sw)}" fill="none"/>'
    head_up = f'<polygon points="{pts([(-s * .2, -h * .2), (s * .2, -h * .2), (0, -h)])}" fill="{color}"/>'
    if kind == 'S':
        return f'<path d="M0 {f(h)} V{f(-h * .3)}" stroke="{color}" stroke-width="{f(sw)}"/>' + head_up
    if kind == 'L':
        return (shaft + f'<path d="M0 {f(-h * .05)} Q0 {f(-h * .45)} {f(-s * .25)} {f(-h * .45)}" fill="none" stroke="{color}" stroke-width="{f(sw)}"/>'
                f'<polygon points="{pts([(-s * .2, -h * .72), (-s * .2, -h * .18), (-s * .46, -h * .45)])}" fill="{color}"/>')
    if kind == 'R':
        return (shaft + f'<path d="M0 {f(-h * .05)} Q0 {f(-h * .45)} {f(s * .25)} {f(-h * .45)}" fill="none" stroke="{color}" stroke-width="{f(sw)}"/>'
                f'<polygon points="{pts([(s * .2, -h * .72), (s * .2, -h * .18), (s * .46, -h * .45)])}" fill="{color}"/>')
    if kind == 'SR':
        return lane_arrow_icon('S', s, color) + lane_arrow_icon('R', s, color)
    if kind == 'SL':
        return lane_arrow_icon('S', s, color) + lane_arrow_icon('L', s, color)
    return ''


SIGNS = {
    'stop': sign_stop, 'yield': sign_yield, 'no_entry': sign_no_entry, 'main': sign_main_road,
    'crosswalk': sign_crosswalk, 'roundabout': sign_roundabout, 'no_stopping': sign_no_stopping,
    'no_parking': sign_no_parking, 'parking': sign_parking, 'road_works': sign_road_works,
    'curve_right': sign_curve_right, 'slippery': sign_slippery, 'rail_barrier': sign_rail_barrier,
    'st_andrew': sign_st_andrew, 'no_overtake': sign_no_overtake, 'crosswind': sign_crosswind,
}


def sign(kind, s, **kw):
    if kind == 'speed':
        return sign_speed(s, kw.get('n', '60'))
    if kind == 'temp_speed':
        return sign_temp_speed(s, kw.get('n', '40'))
    if kind == 'height':
        return sign_height(s, kw.get('val', '3,5'))
    if kind == 'weight':
        return sign_weight(s, kw.get('val', '10т'))
    if kind == 'steep_down':
        return sign_steep_down(s, kw.get('pct', '10%'))
    if kind == 'lanes':
        return sign_lanes(s, kw.get('arrows', ('L', 'S', 'R')))
    return SIGNS[kind](s)


def post_sign(x, y_ground, kind, s=70, pole=None, stack=(), **kw):
    """Тірекке ілінген белгі (жоғарыдан көріністе де, перспективада да)."""
    pole = pole if pole is not None else s * 1.15
    top = y_ground - pole
    out = (f'<ellipse cx="{f(x + s * .06)}" cy="{f(y_ground)}" rx="{f(s * .16)}" ry="{f(s * .06)}" fill="#0b1520" opacity=".3"/>'
           f'<rect x="{f(x - s * .035)}" y="{f(top)}" width="{f(s * .07)}" height="{f(pole)}" rx="{f(s * .02)}" fill="#8c98a4"/>'
           f'<rect x="{f(x - s * .035)}" y="{f(top)}" width="{f(s * .025)}" height="{f(pole)}" fill="#c3ccd4"/>')
    y = top
    out += f'<g transform="translate({f(x)} {f(y)})">{sign(kind, s, **kw)}</g>'
    for k2, kw2 in stack:
        y += s * 1.08
        out += f'<g transform="translate({f(x)} {f(y)})">{sign(k2, s, **kw2)}</g>'
    return out


# ======================================================================
#  БАҒДАРШАМ
# ======================================================================

def traffic_light(svg, x, y, s=1.0, state='red', pole=True, pole_len=None):
    """Көлік бағдаршамы. (x,y) — корпустың жоғарғы ортасы. s=1 → биіктігі 150px."""
    w, h = 54 * s, 150 * s
    r = 17 * s
    lamps = {'red': ['#ff3b30'], 'yellow': ['#ffcc00'], 'green': ['#2bd56b'], 'red-yellow': ['#ff3b30', '#ffcc00'],
             'yellow-flash': ['#ffcc00'], 'off': []}[state]
    colors = [('#ff3b30', '#4a1e1f'), ('#ffcc00', '#4a3d14'), ('#2bd56b', '#173d26')]
    out = ''
    if pole:
        pl = pole_len if pole_len is not None else 120 * s
        out += f'<rect x="{f(x - 5 * s)}" y="{f(y + h - 4)}" width="{f(10 * s)}" height="{f(pl)}" fill="#3a4450"/>'
    out += (f'<rect x="{f(x - w / 2 - 9 * s)}" y="{f(y - 6 * s)}" width="{f(w + 18 * s)}" height="{f(h + 12 * s)}" rx="{f(10 * s)}" fill="#f4f6f8" opacity=".9"/>'
            f'<rect x="{f(x - w / 2)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(12 * s)}" fill="#1c232b"/>')
    for i, (on, off) in enumerate(colors):
        cy = y + 26 * s + i * 49 * s
        lit = on in lamps
        out += f'<path d="M{f(x - r - 3 * s)} {f(cy - r + 2 * s)} q{f(r + 3 * s)} {f(-11 * s)} {f(2 * r + 6 * s)} 0" fill="none" stroke="#11161c" stroke-width="{f(5 * s)}"/>'
        if lit:
            out += glow(svg, x, cy, r * 3.1, on)
        out += f'<circle cx="{f(x)}" cy="{f(cy)}" r="{f(r)}" fill="{on if lit else off}"/>'
        if lit:
            out += f'<circle cx="{f(x - r * .3)}" cy="{f(cy - r * .3)}" r="{f(r * .35)}" fill="#fff" opacity=".55"/>'
            if state == 'yellow-flash':
                for k in (1.45, 1.9):
                    out += f'<circle cx="{f(x)}" cy="{f(cy)}" r="{f(r * k)}" fill="none" stroke="#ffcc00" stroke-width="{f(3 * s)}" stroke-dasharray="{f(6 * s)} {f(5 * s)}" opacity=".9"/>'
    return out


def rail_lights(svg, x, y, s=1.0, lit='left'):
    """Теміржол өткелінің қос қызыл шамы."""
    out = (f'<rect x="{f(x - 4 * s)}" y="{f(y)}" width="{f(8 * s)}" height="{f(150 * s)}" fill="#ececec" stroke="#333" stroke-width="{f(1.5 * s)}"/>'
           f'<rect x="{f(x - 62 * s)}" y="{f(y + 10 * s)}" width="{f(124 * s)}" height="{f(44 * s)}" rx="{f(22 * s)}" fill="#1c232b"/>')
    for i, cx in enumerate((x - 38 * s, x + 38 * s)):
        on = (lit == 'both') or (lit == 'left' and i == 0) or (lit == 'right' and i == 1)
        if on:
            out += glow(svg, cx, y + 32 * s, 52 * s, '#ff3b30')
        out += f'<circle cx="{f(cx)}" cy="{f(y + 32 * s)}" r="{f(16 * s)}" fill="{"#ff3b30" if on else "#4a1e1f"}"/>'
        if on:
            out += f'<circle cx="{f(cx - 5 * s)}" cy="{f(y + 27 * s)}" r="{f(5 * s)}" fill="#fff" opacity=".6"/>'
            for a in range(0, 360, 45):
                dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
                out += f'<path d="M{f(cx + dx * 24 * s)} {f(y + 32 * s + dy * 24 * s)} L{f(cx + dx * 33 * s)} {f(y + 32 * s + dy * 33 * s)}" stroke="#ff6b5f" stroke-width="{f(3 * s)}" stroke-linecap="round"/>'
    return out


# ======================================================================
#  ЖОҒАРЫДАН КӨРІНІС: ЖОЛДАР
# ======================================================================

GRASS = '#9fc98a'
GRASS2 = '#8dbd78'
WALK = '#d8d3c6'
CURB = '#b9b3a4'
MARK = '#f5f5ef'
LANE = 58  # жолақ ені (px)


def ground(svg, kind='city', seed=1):
    rnd = random.Random(seed)
    if kind == 'winter':
        base, dot = '#eef3f7', '#dfe8ef'
    elif kind == 'night':
        base, dot = '#2a3a33', '#24332c'
    else:
        base, dot = GRASS, GRASS2
    out = f'<rect width="{W}" height="{H}" fill="{base}"/>'
    for _ in range(160):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        out += f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rnd.uniform(6, 18))}" ry="{f(rnd.uniform(3, 9))}" fill="{dot}" opacity=".7"/>'
    return out


def tree_top(x, y, r=26, c1='#4f8f4a', c2='#6aab5d'):
    return (f'<circle cx="{f(x + 5)}" cy="{f(y + 7)}" r="{f(r)}" fill="#0b1520" opacity=".2"/>'
            f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{c1}"/>'
            f'<circle cx="{f(x - r * .25)}" cy="{f(y - r * .25)}" r="{f(r * .62)}" fill="{c2}"/>'
            f'<circle cx="{f(x - r * .38)}" cy="{f(y - r * .38)}" r="{f(r * .22)}" fill="#86c276" opacity=".8"/>')


def roof(x, y, w, h, c='#c9b59b', ridge=True):
    out = (f'<rect x="{f(x + 7)}" y="{f(y + 9)}" width="{f(w)}" height="{f(h)}" rx="4" fill="#0b1520" opacity=".22"/>'
           f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="4" fill="{c}"/>'
           f'<rect x="{f(x + 6)}" y="{f(y + 6)}" width="{f(w - 12)}" height="{f(h - 12)}" rx="3" fill="#fff" opacity=".12"/>')
    if ridge:
        out += f'<rect x="{f(x + w * .2)}" y="{f(y + h * .25)}" width="{f(w * .18)}" height="{f(h * .2)}" rx="2" fill="#000" opacity=".12"/>'
    return out


def block_fill(x, y, w, h, rx, style='grass', seed=3):
    """Квартал: шөп + ағаш немесе үй төбелері."""
    rnd = random.Random(seed)
    clip = f'cb{seed}{int(x)}{int(y)}'.replace('-', 'm')
    out = (f'<clipPath id="{clip}"><rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}"/></clipPath>'
           f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" fill="{GRASS if style != "winter" else "#f1f5f8"}" stroke="{CURB}" stroke-width="3"/>'
           f'<g clip-path="url(#{clip})">')
    # тек көрінетін бөлікте ғана сызамыз
    vx0, vy0 = max(x, -60), max(y, -60)
    vx1, vy1 = min(x + w, W + 60), min(y + h, H + 60)
    if style in ('city', 'grass', 'winter') and vx1 > vx0 and vy1 > vy0:
        cols = ['#c9b59b', '#b8c3cc', '#d4a98c', '#a9b7a4', '#c7bfb4']
        if style == 'city':
            # кварталдың жолға қараған шетінен бастаймыз
            sx = x + 26 if x > -60 else vx1 - 26
            dirx = 1 if x > -60 else -1
            sy = y + 26 if y > -60 else vy1 - 26
            diry = 1 if y > -60 else -1
            gx = sx
            while vx0 - 160 < gx < vx1 + 160:
                bw = rnd.uniform(90, 150)
                gy = sy
                while vy0 - 160 < gy < vy1 + 160:
                    bh = rnd.uniform(70, 120)
                    rx0 = gx if dirx > 0 else gx - bw
                    ry0 = gy if diry > 0 else gy - bh
                    if x + 20 <= rx0 and rx0 + bw <= x + w - 20 and y + 20 <= ry0 and ry0 + bh <= y + h - 20:
                        out += roof(rx0, ry0, bw, bh, rnd.choice(cols))
                    gy += diry * (bh + 28)
                gx += dirx * (bw + 28)
        else:
            area = (vx1 - vx0) * (vy1 - vy0)
            for _ in range(int(area / 9000) + 1):
                tx, ty = rnd.uniform(max(vx0, x + 30), min(vx1, x + w - 30)), rnd.uniform(max(vy0, y + 30), min(vy1, y + h - 30))
                out += tree_top(tx, ty, rnd.uniform(18, 30), *(('#7e9ba8', '#a8c0cb') if style == 'winter' else ('#4f8f4a', '#6aab5d')))
    out += '</g>'
    return out


def arm_marks(hw, d_edge, length, lanes_in=1, lanes_out=1, center='dashed', zebra=True, stop=True,
              zebra_gap=10, zebra_w=46, stop_gap=10, arrows=None):
    """Қол (arm) таңбалаулары: жергілікті жүйеде қол төмен (+y) қарай созылады,
    кіретін көліктер +x жағында жүреді."""
    lw = 2 * hw / (lanes_in + lanes_out)
    xc = -hw + lanes_out * lw
    y0 = d_edge
    out = ''
    zs = y0 + zebra_gap
    ze = zs + zebra_w if zebra else y0
    line_start = (ze + stop_gap + 6) if stop else ze + 4
    if zebra:
        n = int((2 * hw - 10) // 22)
        x = -hw + (2 * hw - (n * 22 - 10)) / 2
        for i in range(n):
            out += f'<rect x="{f(x + i * 22)}" y="{f(zs)}" width="12" height="{f(zebra_w)}" fill="{MARK}"/>'
    if stop:
        out += f'<rect x="{f(xc + 2)}" y="{f(ze + stop_gap)}" width="{f(hw - xc - 4)}" height="7" fill="{MARK}"/>'
    # орталық сызық
    if center == 'dashed':
        out += f'<path d="M{f(xc)} {f(line_start)} V{f(y0 + length)}" stroke="{MARK}" stroke-width="4" stroke-dasharray="26 22"/>'
    elif center == 'solid':
        out += f'<path d="M{f(xc)} {f(line_start)} V{f(y0 + length)}" stroke="{MARK}" stroke-width="4"/>'
    elif center == 'double':
        out += f'<path d="M{f(xc - 4)} {f(line_start)} V{f(y0 + length)} M{f(xc + 4)} {f(line_start)} V{f(y0 + length)}" stroke="{MARK}" stroke-width="3.5"/>'
    elif center == 'approach':  # қиылыс алдында тұтас, кейін үзік
        out += f'<path d="M{f(xc)} {f(line_start)} V{f(line_start + 90)}" stroke="{MARK}" stroke-width="4"/>'
        out += f'<path d="M{f(xc)} {f(line_start + 112)} V{f(y0 + length)}" stroke="{MARK}" stroke-width="4" stroke-dasharray="26 22"/>'
    for i in range(1, lanes_in):
        x = xc + i * lw
        if arrows:
            out += (f'<path d="M{f(x)} {f(line_start)} V{f(line_start + 150)}" stroke="{MARK}" stroke-width="3.5"/>'
                    f'<path d="M{f(x)} {f(line_start + 172)} V{f(y0 + length)}" stroke="{MARK}" stroke-width="3.5" stroke-dasharray="22 26"/>')
        else:
            out += f'<path d="M{f(x)} {f(line_start)} V{f(y0 + length)}" stroke="{MARK}" stroke-width="3.5" stroke-dasharray="22 26"/>'
    for i in range(1, lanes_out):
        x = xc - i * lw
        out += f'<path d="M{f(x)} {f(ze + 6)} V{f(y0 + length)}" stroke="{MARK}" stroke-width="3.5" stroke-dasharray="22 26"/>'
    if arrows:
        for i, a in enumerate(arrows):
            x = xc + (i + .5) * lw
            out += f'<g transform="translate({f(x)} {f(line_start + 70)})">{lane_arrow_icon(a, 64, MARK)}</g>'
    return out


def crossroads(svg, cx=480, cy=270, arms='NSEW', h_hw=LANE, v_hw=LANE, lanes=None, center=None,
               zebra='NSEW', stop='NSEW', r=44, side=24, blocks='grass', seed=5, arrows=None):
    """Қиылыс (немесе T, немесе тік/көлденең жол). lanes[arm]=(in,out)."""
    lanes = lanes or {}
    center = center or {}
    arrows = arrows or {}
    out = f'<rect width="{W}" height="{H}" fill="{WALK}"/>'
    # тротуар плиткасы
    out += f'<rect width="{W}" height="{H}" fill="url(#tiles)"/>'
    svg.define('tiles', '<pattern id="tiles" width="26" height="26" patternUnits="userSpaceOnUse"><path d="M0 0H26V26" fill="none" stroke="#c9c3b5" stroke-width="1.2"/></pattern>')
    x0, x1 = cx - v_hw, cx + v_hw
    y0, y1 = cy - h_hw, cy + h_hw
    big = 2000
    # кварталдар
    def has(a):
        return a in arms
    quads = []
    if has('N') and has('W'):
        quads.append((-big, -big, (x0 - side) + big, (y0 - side) + big))
    if has('N') and has('E'):
        quads.append((x1 + side, -big, big, (y0 - side) + big))
    if has('S') and has('W'):
        quads.append((-big, y1 + side, (x0 - side) + big, big))
    if has('S') and has('E'):
        quads.append((x1 + side, y1 + side, big, big))
    if not has('N'):
        quads.append((-big, -big, 2 * big, (y0 - side) + big))
    if not has('S'):
        quads.append((-big, y1 + side, 2 * big, big))
    if not has('W'):
        ya = (y0 - side) if not has('N') else -big
        yb = (y1 + side) if not has('S') else big
        quads.append((-big, ya, (x0 - side) + big, yb - ya))
    if not has('E'):
        ya = (y0 - side) if not has('N') else -big
        yb = (y1 + side) if not has('S') else big
        quads.append((x1 + side, ya, big, yb - ya))
    # асфальт
    a = 'fill="url(#asph)"'
    out += f'<rect x="{f(x0)}" y="{f(y0)}" width="{f(2 * v_hw)}" height="{f(2 * h_hw)}" {a}/>'
    if has('N'):
        out += f'<rect x="{f(x0)}" y="-5" width="{f(2 * v_hw)}" height="{f(y0 + 6)}" {a}/>'
    if has('S'):
        out += f'<rect x="{f(x0)}" y="{f(y1 - 1)}" width="{f(2 * v_hw)}" height="{f(H - y1 + 6)}" {a}/>'
    if has('W'):
        out += f'<rect x="-5" y="{f(y0)}" width="{f(x0 + 6)}" height="{f(2 * h_hw)}" {a}/>'
    if has('E'):
        out += f'<rect x="{f(x1 - 1)}" y="{f(y0)}" width="{f(W - x1 + 6)}" height="{f(2 * h_hw)}" {a}/>'
    # бұрыштар
    for (ax, ay, sx, sy) in (('E', 'N', 1, -1), ('W', 'N', -1, -1), ('E', 'S', 1, 1), ('W', 'S', -1, 1)):
        if has(ax) and has(ay):
            ex = x1 if sx > 0 else x0
            ey = y1 if sy > 0 else y0
            qx = ex if sx > 0 else ex - r
            qy = ey if sy > 0 else ey - r
            out += f'<rect x="{f(qx)}" y="{f(qy)}" width="{f(r)}" height="{f(r)}" {a}/>'
            out += f'<circle cx="{f(ex + sx * r)}" cy="{f(ey + sy * r)}" r="{f(r)}" fill="{WALK}"/>'
            out += f'<circle cx="{f(ex + sx * r)}" cy="{f(ey + sy * r)}" r="{f(r)}" fill="none" stroke="{CURB}" stroke-width="3"/>'
    rb = max(r - side, 6)
    for i, (bx, by, bw, bh) in enumerate(quads):
        out += block_fill(bx, by, bw, bh, rb, blocks, seed + i)
    # бордюр сызықтары
    curb = f'stroke="{CURB}" stroke-width="3"'
    segs = []
    if has('N'):
        segs += [(x0, 0, x0, y0 - (r if has('W') else 0)), (x1, 0, x1, y0 - (r if has('E') else 0))]
    if has('S'):
        segs += [(x0, y1 + (r if has('W') else 0), x0, H), (x1, y1 + (r if has('E') else 0), x1, H)]
    if has('W'):
        segs += [(0, y0, x0 - (r if has('N') else 0), y0), (0, y1, x0 - (r if has('S') else 0), y1)]
    if has('E'):
        segs += [(x1 + (r if has('N') else 0), y0, W, y0), (x1 + (r if has('S') else 0), y1, W, y1)]
    if not has('N'):
        segs.append((x0 if has('W') else x0, y0, x1, y0))
    if not has('S'):
        segs.append((x0, y1, x1, y1))
    if not has('W'):
        segs.append((x0, y0, x0, y1))
    if not has('E'):
        segs.append((x1, y0, x1, y1))
    for (ax, ay, bx, by) in segs:
        out += f'<path d="M{f(ax)} {f(ay)}L{f(bx)} {f(by)}" {curb}/>'
    # таңбалаулар
    spec = {'S': (0, v_hw, h_hw, H - cy - h_hw), 'W': (90, h_hw, v_hw, cx - v_hw),
            'N': (180, v_hw, h_hw, cy - h_hw), 'E': (270, h_hw, v_hw, W - cx - v_hw)}
    for arm in arms:
        rot, hw, d_edge, length = spec[arm]
        li, lo = lanes.get(arm, (1, 1))
        out += (f'<g transform="translate({f(cx)} {f(cy)}) rotate({rot})">'
                + arm_marks(hw, d_edge, length + 10, li, lo, center.get(arm, 'dashed'), arm in zebra, arm in stop,
                            arrows=arrows.get(arm)) + '</g>')
    return out


def straight_road(svg, orient='v', c=480, hw=LANE, lanes=(1, 1), center='dashed', blocks='grass', seed=9,
                  side=24, edge_lines=False):
    """Түзу жол. orient='v' — тік (lanes=(жоғары, төмен)), 'h' — көлденең (lanes=(оңға, солға))."""
    out = f'<rect width="{W}" height="{H}" fill="{WALK}"/><rect width="{W}" height="{H}" fill="url(#tiles)"/>'
    svg.define('tiles', '<pattern id="tiles" width="26" height="26" patternUnits="userSpaceOnUse"><path d="M0 0H26V26" fill="none" stroke="#c9c3b5" stroke-width="1.2"/></pattern>')
    if orient == 'v':
        out += block_fill(-60, -60, c - hw - side + 60, H + 120, 6, blocks, seed)
        out += block_fill(c + hw + side, -60, W, H + 120, 6, blocks, seed + 1)
        out += f'<rect x="{f(c - hw)}" y="-5" width="{f(2 * hw)}" height="{H + 10}" fill="url(#asph)"/>'
        out += f'<path d="M{f(c - hw)} 0V{H}M{f(c + hw)} 0V{H}" stroke="{CURB}" stroke-width="3"/>'
        out += f'<g transform="translate({f(c)} -10)">' + arm_marks(hw, 0, H + 20, lanes[0], lanes[1], center, False, False) + '</g>'
    else:
        out += block_fill(-60, -60, W + 120, c - hw - side + 60, 6, blocks, seed)
        out += block_fill(-60, c + hw + side, W + 120, H, 6, blocks, seed + 1)
        out += f'<rect x="-5" y="{f(c - hw)}" width="{W + 10}" height="{f(2 * hw)}" fill="url(#asph)"/>'
        out += f'<path d="M0 {f(c - hw)}H{W}M0 {f(c + hw)}H{W}" stroke="{CURB}" stroke-width="3"/>'
        out += f'<g transform="translate(-10 {f(c)}) rotate(90)">' + arm_marks(hw, 0, W + 20, lanes[0], lanes[1], center, False, False) + '</g>'
    return out


def zebra_v(x0, x1, y, w=46):
    """Көлденең жолдағы зебра (жол тігінен өтеді → жолақтар тік)."""
    n = int((x1 - x0 - 10) // 22)
    out = ''
    for i in range(n):
        out += f'<rect x="{f(x0 + 5 + i * 22)}" y="{f(y)}" width="12" height="{f(w)}" fill="{MARK}"/>'
    return out


def zebra_h(y0, y1, x, w=46):
    n = int((y1 - y0 - 10) // 22)
    out = ''
    for i in range(n):
        out += f'<rect x="{f(x)}" y="{f(y0 + 5 + i * 22)}" width="{f(w)}" height="12" fill="{MARK}"/>'
    return out


# ======================================================================
#  ЖОҒАРЫДАН КӨРІНІС: КӨЛІКТЕР ЖӘНЕ АДАМДАР
# ======================================================================

CAR_COLORS = {'red': '#e2463b', 'blue': '#2f6fd6', 'white': '#eef1f4', 'grey': '#8e99a6', 'black': '#2b313a',
              'yellow': '#f2c230', 'green': '#2f9e6b', 'orange': '#f08a24', 'teal': '#1f9aa8', 'silver': '#c3cbd3',
              'purple': '#7d5bd6'}


def _lights(svg, L, W_, signal, brake, hazard, head, beams, kind='car'):
    out = ''
    if beams:
        n = 210 if beams == 'high' else 120
        sp = 70 if beams == 'high' else 46
        out += (f'<polygon points="{pts([(-W_ / 2 + 7, -L / 2), (W_ / 2 - 7, -L / 2), (W_ / 2 + sp, -L / 2 - n), (-W_ / 2 - sp, -L / 2 - n)])}" fill="url(#beam)"/>')
    sides = []
    if signal in ('left', 'both') or hazard:
        sides.append(-1)
    if signal in ('right', 'both') or hazard:
        sides.append(1)
    for sx in sides:
        for sy in (-1, 1):
            out += glow(svg, sx * (W_ / 2 - 3), sy * (L / 2 - 4), 19, '#ffae00')
    if brake:
        for sx in (-1, 1):
            out += glow(svg, sx * (W_ / 2 - 8), L / 2 - 2, 20, '#ff2a1f')
    return out


def car(svg, x, y, ang=0, color='blue', kind='sedan', signal=None, brake=False, hazard=False, beams=None,
        scale=1.0, flash=False, label=None, cargo=None):
    """Көлік (жоғарыдан). ang=0 — жоғары (солтүстік) қарайды, 90 — оңға."""
    c = CAR_COLORS.get(color, color)
    dims = {'sedan': (100, 48), 'suv': (106, 52), 'police': (102, 48), 'ambulance': (118, 54), 'van': (122, 52),
            'truck': (210, 62), 'bus': (230, 62), 'tram': (300, 64), 'moto': (52, 20), 'bike': (46, 16), 'tractor': (78, 52),
            'dump': (170, 60)}
    L, Wd = dims[kind]
    under = _lights(svg, L, Wd, signal, brake, hazard, None, beams)
    body = ''
    if kind in ('sedan', 'suv', 'police'):
        if kind == 'police':
            c = '#f4f6f8'
        roofc = 'white' if kind == 'police' else c
        body += (f'<rect x="{f(-Wd / 2 + 3)}" y="{f(-L / 2 + 6)}" width="{f(Wd)}" height="{f(L)}" rx="14" fill="#0b1520" opacity=".28"/>'
                 f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2)}" width="{f(Wd)}" height="{f(L)}" rx="13" fill="{c}"/>'
                 f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2)}" width="{f(Wd)}" height="{f(L)}" rx="13" fill="url(#sheen)"/>'
                 f'<path d="M{f(-Wd / 2 + 10)} {f(-L / 2 + 5)} Q0 {f(-L / 2 - 1)} {f(Wd / 2 - 10)} {f(-L / 2 + 5)}" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>'
                 f'<path d="M{f(-9)} {f(-L / 2 + 8)} L{f(-7)} {f(-L / 2 + 25)} M9 {f(-L / 2 + 8)} L7 {f(-L / 2 + 25)}" stroke="#000" stroke-opacity=".12" stroke-width="2"/>'
                 f'<polygon points="{pts([(-Wd / 2 + 5, -L / 2 + 29), (Wd / 2 - 5, -L / 2 + 29), (Wd / 2 - 8, -L / 2 + 44), (-Wd / 2 + 8, -L / 2 + 44)])}" fill="url(#glass)"/>'
                 f'<rect x="{f(-Wd / 2 + 7)}" y="{f(-L / 2 + 44)}" width="{f(Wd - 14)}" height="{f(L - 70)}" rx="7" fill="{CAR_COLORS.get(roofc, roofc)}"/>'
                 f'<rect x="{f(-Wd / 2 + 7)}" y="{f(-L / 2 + 44)}" width="{f(Wd - 14)}" height="{f(L - 70)}" rx="7" fill="url(#vsheen)"/>'
                 f'<polygon points="{pts([(-Wd / 2 + 8, L / 2 - 26), (Wd / 2 - 8, L / 2 - 26), (Wd / 2 - 6, L / 2 - 14), (-Wd / 2 + 6, L / 2 - 14)])}" fill="url(#glass)"/>'
                 f'<rect x="{f(-Wd / 2 + 2)}" y="{f(-L / 2 + 42)}" width="3" height="{f(L - 66)}" fill="#1d2a38" opacity=".8"/>'
                 f'<rect x="{f(Wd / 2 - 5)}" y="{f(-L / 2 + 42)}" width="3" height="{f(L - 66)}" fill="#1d2a38" opacity=".8"/>'
                 f'<rect x="{f(-Wd / 2 - 5)}" y="{f(-L / 2 + 32)}" width="8" height="7" rx="3" fill="{c}" stroke="#1d2a38" stroke-width="1"/>'
                 f'<rect x="{f(Wd / 2 - 3)}" y="{f(-L / 2 + 32)}" width="8" height="7" rx="3" fill="{c}" stroke="#1d2a38" stroke-width="1"/>'
                 f'<rect x="{f(-Wd / 2 + 4)}" y="{f(-L / 2 + 1)}" width="11" height="5" rx="2" fill="#fff8d6"/>'
                 f'<rect x="{f(Wd / 2 - 15)}" y="{f(-L / 2 + 1)}" width="11" height="5" rx="2" fill="#fff8d6"/>'
                 f'<rect x="{f(-Wd / 2 + 4)}" y="{f(L / 2 - 6)}" width="11" height="5" rx="2" fill="#c4161c"/>'
                 f'<rect x="{f(Wd / 2 - 15)}" y="{f(L / 2 - 6)}" width="11" height="5" rx="2" fill="#c4161c"/>')
        if kind == 'police':
            body += (f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + 30)}" width="5" height="{f(L - 50)}" fill="#1f5fd1"/>'
                     f'<rect x="{f(Wd / 2 - 5)}" y="{f(-L / 2 + 30)}" width="5" height="{f(L - 50)}" fill="#1f5fd1"/>'
                     f'<rect x="{f(-Wd / 2 + 9)}" y="{f(-4)}" width="{f(Wd - 18)}" height="9" rx="3" fill="#1d2a38"/>'
                     f'<rect x="{f(-Wd / 2 + 10)}" y="-3" width="{f(Wd / 2 - 10)}" height="7" rx="2" fill="#2f7bff"/>'
                     f'<rect x="0" y="-3" width="{f(Wd / 2 - 10)}" height="7" rx="2" fill="#ff3b30"/>')
    elif kind in ('ambulance', 'van'):
        cabL = 34
        body += (f'<rect x="{f(-Wd / 2 + 3)}" y="{f(-L / 2 + 6)}" width="{f(Wd)}" height="{f(L)}" rx="10" fill="#0b1520" opacity=".28"/>'
                 f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2)}" width="{f(Wd)}" height="{f(cabL + 8)}" rx="12" fill="{c if kind == "van" else "#f4f6f8"}"/>'
                 f'<polygon points="{pts([(-Wd / 2 + 5, -L / 2 + 12), (Wd / 2 - 5, -L / 2 + 12), (Wd / 2 - 7, -L / 2 + 27), (-Wd / 2 + 7, -L / 2 + 27)])}" fill="url(#glass)"/>'
                 f'<rect x="{f(-Wd / 2 - 5)}" y="{f(-L / 2 + 18)}" width="8" height="7" rx="3" fill="#2b313a"/>'
                 f'<rect x="{f(Wd / 2 - 3)}" y="{f(-L / 2 + 18)}" width="8" height="7" rx="3" fill="#2b313a"/>'
                 f'<rect x="{f(-Wd / 2 + 4)}" y="{f(-L / 2 + 1)}" width="10" height="5" rx="2" fill="#fff8d6"/>'
                 f'<rect x="{f(Wd / 2 - 14)}" y="{f(-L / 2 + 1)}" width="10" height="5" rx="2" fill="#fff8d6"/>')
        boxc = '#f4f6f8' if kind == 'ambulance' else (cargo if cargo and cargo.startswith('#') else '#e9edf1')
        if cargo == 'flatbed' or cargo == 'flatbed-load':
            body += (f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + cabL + 4)}" width="{f(Wd)}" height="{f(L - cabL - 4)}" rx="4" fill="#7b8794"/>'
                     f'<rect x="{f(-Wd / 2 + 4)}" y="{f(-L / 2 + cabL + 8)}" width="{f(Wd - 8)}" height="{f(L - cabL - 12)}" rx="2" fill="#a9763f"/>')
            for i in range(5):
                body += f'<path d="M{f(-Wd / 2 + 4)} {f(-L / 2 + cabL + 20 + i * 15)}H{f(Wd / 2 - 4)}" stroke="#8a5a2b" stroke-width="2"/>'
            if cargo == 'flatbed-load':
                for (bx, by) in ((-12, 10), (10, 12), (-12, 36), (10, 38), (0, 62)):
                    body += f'<rect x="{f(bx - 10)}" y="{f(-L / 2 + cabL + by)}" width="20" height="20" rx="2" fill="#c9965a" stroke="#8a5a2b" stroke-width="1.5"/>'
        else:
            body += (f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + cabL + 2)}" width="{f(Wd)}" height="{f(L - cabL - 2)}" rx="5" fill="{boxc}" stroke="#c7cfd7" stroke-width="1.5"/>'
                     f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + cabL + 2)}" width="{f(Wd)}" height="{f(L - cabL - 2)}" rx="5" fill="url(#sheen)"/>')
        body += (f'<rect x="{f(-Wd / 2 + 4)}" y="{f(L / 2 - 5)}" width="10" height="4" rx="2" fill="#c4161c"/>'
                 f'<rect x="{f(Wd / 2 - 14)}" y="{f(L / 2 - 5)}" width="10" height="4" rx="2" fill="#c4161c"/>')
        if kind == 'ambulance':
            body += (f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + cabL + 20)}" width="{f(Wd)}" height="8" fill="#e53935"/>'
                     f'<rect x="-11" y="{f(8)}" width="22" height="8" fill="#e53935"/><rect x="-4" y="1" width="8" height="22" fill="#e53935"/>'
                     f'<rect x="{f(-Wd / 2 + 8)}" y="{f(-L / 2 + 30)}" width="{f(Wd - 16)}" height="8" rx="3" fill="#1d2a38"/>'
                     f'<rect x="{f(-Wd / 2 + 9)}" y="{f(-L / 2 + 31)}" width="{f(Wd - 18)}" height="6" rx="2" fill="#2f7bff"/>')
    elif kind in ('truck', 'dump'):
        cabL = 46
        body += (f'<rect x="{f(-Wd / 2 + 4)}" y="{f(-L / 2 + 7)}" width="{f(Wd)}" height="{f(L)}" rx="8" fill="#0b1520" opacity=".3"/>'
                 f'<rect x="{f(-Wd / 2 + 1)}" y="{f(-L / 2)}" width="{f(Wd - 2)}" height="{f(cabL)}" rx="9" fill="{c}"/>'
                 f'<rect x="{f(-Wd / 2 + 1)}" y="{f(-L / 2)}" width="{f(Wd - 2)}" height="{f(cabL)}" rx="9" fill="url(#sheen)"/>'
                 f'<rect x="{f(-Wd / 2 + 6)}" y="{f(-L / 2 + 4)}" width="{f(Wd - 12)}" height="12" rx="3" fill="url(#glass)"/>'
                 f'<rect x="{f(-Wd / 2 - 8)}" y="{f(-L / 2 + 8)}" width="9" height="12" rx="3" fill="#2b313a"/>'
                 f'<rect x="{f(Wd / 2 - 1)}" y="{f(-L / 2 + 8)}" width="9" height="12" rx="3" fill="#2b313a"/>')
        if kind == 'dump':
            body += (f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + cabL + 6)}" width="{f(Wd)}" height="{f(L - cabL - 6)}" rx="6" fill="#d98b2b"/>'
                     f'<rect x="{f(-Wd / 2 + 6)}" y="{f(-L / 2 + cabL + 12)}" width="{f(Wd - 12)}" height="{f(L - cabL - 18)}" rx="4" fill="#8b7a63"/>')
        else:
            boxc = cargo if cargo and cargo.startswith('#') else '#eef1f4'
            body += (f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + cabL + 6)}" width="{f(Wd)}" height="{f(L - cabL - 6)}" rx="4" fill="{boxc}" stroke="#c7cfd7" stroke-width="2"/>'
                     f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2 + cabL + 6)}" width="{f(Wd)}" height="{f(L - cabL - 6)}" rx="4" fill="url(#sheen)"/>'
                     + ''.join(f'<path d="M{f(-Wd / 2 + 3)} {f(-L / 2 + cabL + 6 + k * (L - cabL - 6) / 6)}H{f(Wd / 2 - 3)}" stroke="#000" stroke-opacity=".06" stroke-width="2"/>' for k in range(1, 6)))
        body += (f'<rect x="{f(-Wd / 2 + 4)}" y="{f(-L / 2 + 1)}" width="10" height="4" rx="2" fill="#fff8d6"/><rect x="{f(Wd / 2 - 14)}" y="{f(-L / 2 + 1)}" width="10" height="4" rx="2" fill="#fff8d6"/>'
                 f'<rect x="{f(-Wd / 2 + 3)}" y="{f(L / 2 - 5)}" width="10" height="4" rx="2" fill="#c4161c"/><rect x="{f(Wd / 2 - 13)}" y="{f(L / 2 - 5)}" width="10" height="4" rx="2" fill="#c4161c"/>')
    elif kind == 'bus':
        body += (f'<rect x="{f(-Wd / 2 + 4)}" y="{f(-L / 2 + 7)}" width="{f(Wd)}" height="{f(L)}" rx="10" fill="#0b1520" opacity=".3"/>'
                 f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2)}" width="{f(Wd)}" height="{f(L)}" rx="10" fill="{c}"/>'
                 f'<rect x="{f(-Wd / 2)}" y="{f(-L / 2)}" width="{f(Wd)}" height="{f(L)}" rx="10" fill="url(#sheen)"/>'
                 f'<rect x="{f(-Wd / 2 + 6)}" y="{f(-L / 2 + 4)}" width="{f(Wd - 12)}" height="12" rx="3" fill="url(#glass)"/>'
                 + ''.join(f'<rect x="{f(-Wd / 2 + 10)}" y="{f(-L / 2 + 40 + k * 40)}" width="{f(Wd - 20)}" height="24" rx="4" fill="#fff" opacity=".22"/>' for k in range(4)))
    elif kind == 'tram':
        seg = L / 2
        for k in (0, 1):
            sy = -L / 2 + k * (seg + 4)
            body += (f'<rect x="{f(-Wd / 2 + 4)}" y="{f(sy + 7)}" width="{f(Wd)}" height="{f(seg - 4)}" rx="12" fill="#0b1520" opacity=".3"/>'
                     f'<rect x="{f(-Wd / 2)}" y="{f(sy)}" width="{f(Wd)}" height="{f(seg - 4)}" rx="{f(22 if k == 0 else 10)}" fill="#e23b3b"/>'
                     f'<rect x="{f(-Wd / 2)}" y="{f(sy)}" width="{f(Wd)}" height="{f(seg - 4)}" rx="{f(22 if k == 0 else 10)}" fill="url(#sheen)"/>'
                     f'<rect x="{f(-Wd / 2 + 8)}" y="{f(sy + 30)}" width="{f(Wd - 16)}" height="{f(seg - 64)}" rx="6" fill="#f2f2f2" opacity=".9"/>'
                     f'<rect x="-10" y="{f(sy + seg / 2 - 14)}" width="20" height="28" rx="3" fill="#7a2020" opacity=".55"/>')
        body += f'<rect x="{f(-Wd / 2 + 6)}" y="{f(-L / 2 + 6)}" width="{f(Wd - 12)}" height="16" rx="6" fill="url(#glass)"/>'
        body += f'<rect x="-12" y="{f(-2)}" width="24" height="8" fill="#7a2020"/>'
    elif kind == 'moto':
        body += (f'<ellipse cx="2" cy="4" rx="9" ry="26" fill="#0b1520" opacity=".25"/>'
                 f'<rect x="-4" y="-26" width="8" height="14" rx="3" fill="#222"/><rect x="-4" y="12" width="8" height="14" rx="3" fill="#222"/>'
                 f'<rect x="-7" y="-14" width="14" height="28" rx="6" fill="{c}"/><path d="M-13 -14H13" stroke="#333" stroke-width="3" stroke-linecap="round"/>'
                 f'<circle cx="0" cy="2" r="8" fill="#333"/><circle cx="0" cy="0" r="6" fill="#f2f2f2"/>')
    elif kind == 'bike':
        body += (f'<path d="M0 -22V22" stroke="#222" stroke-width="4" stroke-linecap="round"/><path d="M-11 -12H11" stroke="#333" stroke-width="3" stroke-linecap="round"/>'
                 f'<ellipse cx="0" cy="4" rx="12" ry="7" fill="{c}"/><circle cx="0" cy="-1" r="7" fill="#ffcf3f" stroke="#c99b12" stroke-width="1.5"/>')
    elif kind == 'tractor':
        body += (f'<rect x="-22" y="-36" width="44" height="72" rx="8" fill="#0b1520" opacity=".25"/>'
                 f'<rect x="-30" y="6" width="14" height="32" rx="5" fill="#222"/><rect x="16" y="6" width="14" height="32" rx="5" fill="#222"/>'
                 f'<rect x="-24" y="-36" width="10" height="20" rx="4" fill="#222"/><rect x="14" y="-36" width="10" height="20" rx="4" fill="#222"/>'
                 f'<rect x="-14" y="-38" width="28" height="44" rx="6" fill="{c}"/><rect x="-18" y="0" width="36" height="34" rx="6" fill="{c}"/>'
                 f'<rect x="-13" y="6" width="26" height="22" rx="4" fill="url(#glass)"/>')
    over = ''
    if kind in ('police', 'ambulance') and flash:
        over += glow(svg, -10, -L / 2 + 34 if kind == 'ambulance' else 0, 34, '#2f7bff') + glow(svg, 10, -L / 2 + 34 if kind == 'ambulance' else 0, 28, '#5aa0ff' if kind == 'ambulance' else '#ff3b30')
    if signal or hazard or brake:
        sides = []
        if signal in ('left', 'both') or hazard:
            sides.append(-1)
        if signal in ('right', 'both') or hazard:
            sides.append(1)
        for sx in sides:
            for sy in (-1, 1):
                over += f'<circle cx="{f(sx * (Wd / 2 - 3))}" cy="{f(sy * (L / 2 - 4))}" r="4.5" fill="#ffb300" stroke="#fff" stroke-width="1"/>'
        if brake:
            for sx in (-1, 1):
                over += f'<rect x="{f(sx * (Wd / 2 - 9) - 6)}" y="{f(L / 2 - 6)}" width="12" height="5" rx="2" fill="#ff2a1f"/>'
    g = f'<g transform="translate({f(x)} {f(y)}) rotate({f(ang)}) scale({f(scale)})">{under}{body}{over}</g>'
    if label:
        g += label
    return g


def person_top(x, y, ang=0, coat='#3b82c4', scale=1.3, stride=True):
    """Жаяу жүргінші (жоғарыдан)."""
    legs = ('<ellipse cx="-5" cy="-9" rx="4" ry="6" fill="#2b313a"/><ellipse cx="5" cy="9" rx="4" ry="6" fill="#2b313a"/>' if stride
            else '<ellipse cx="-5" cy="2" rx="4" ry="6" fill="#2b313a"/><ellipse cx="5" cy="2" rx="4" ry="6" fill="#2b313a"/>')
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({f(ang)}) scale({f(scale)})">'
            f'<ellipse cx="4" cy="6" rx="17" ry="10" fill="#0b1520" opacity=".22"/>' + legs +
            f'<ellipse cx="0" cy="0" rx="19" ry="12" fill="#fff" opacity=".85"/>' +
            f'<ellipse cx="0" cy="0" rx="16" ry="9" fill="{coat}"/>'
            f'<ellipse cx="-15" cy="{3 if stride else 0}" rx="4" ry="6" fill="{coat}"/><ellipse cx="15" cy="{-3 if stride else 0}" rx="4" ry="6" fill="{coat}"/>'
            f'<circle cx="0" cy="-1" r="7.5" fill="#3a2a20"/><circle cx="0" cy="-3.5" r="4" fill="#5b4334"/></g>')


def officer_top(x, y, ang=0):
    """Реттеуші (жоғарыдан): қолдары екі жаққа созылған."""
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({f(ang)})">'
            f'<ellipse cx="5" cy="7" rx="44" ry="12" fill="#0b1520" opacity=".22"/>'
            f'<rect x="-44" y="-5" width="88" height="10" rx="5" fill="#1f3550"/>'
            f'<rect x="-44" y="-5" width="10" height="10" rx="4" fill="#f1f1f1"/><rect x="34" y="-5" width="10" height="10" rx="4" fill="#f1f1f1"/>'
            f'<rect x="44" y="-3" width="20" height="6" rx="3" fill="#fff" stroke="#111" stroke-width="1"/>'
            f'<rect x="48" y="-3" width="4" height="6" fill="#111"/><rect x="56" y="-3" width="4" height="6" fill="#111"/>'
            f'<ellipse cx="0" cy="0" rx="19" ry="11" fill="#c6e83a"/>'
            f'<path d="M-18 -2H18M-18 4H18" stroke="#d9d9d9" stroke-width="2.5"/>'
            f'<circle cx="0" cy="0" r="10" fill="#1f3550"/><circle cx="0" cy="0" r="7" fill="#f4f6f8"/><path d="M-7 -6 Q0 -13 7 -6" fill="#1f3550"/></g>')


def wind_lines(x, y, n=4, length=90, color='#ffffff', ang=0):
    out = f'<g transform="translate({f(x)} {f(y)}) rotate({f(ang)})" stroke="{color}" stroke-width="5" stroke-linecap="round" fill="none" opacity=".9">'
    for i in range(n):
        yy = i * 26
        out += f'<path d="M0 {f(yy)} H{f(length - (i % 2) * 22)} q22 0 22 -14 q0 -12 -12 -12"/>'
    return out + '</g>'


# ======================================================================
#  ПЕРСПЕКТИВА (жүргізуші көзімен)
# ======================================================================

class P:
    def __init__(self, horizon=165, cx=480, focal=720, cam_h=2.6, bend=0.0):
        self.hz, self.cx, self.fc, self.ch, self.bend = horizon, cx, focal, cam_h, bend

    def off(self, z):
        return self.bend * z * z

    def pt(self, u, z, h=0.0):
        z = max(z, .3)
        return (self.cx + self.fc * (u - self.off(z)) / z, self.hz + self.fc * (self.ch - h) / z)

    def scale(self, z):
        return self.fc / max(z, .3)

    def quad(self, u0, u1, z0, z1, h=0.0, steps=1):
        if steps == 1:
            return [self.pt(u0, z0, h), self.pt(u1, z0, h), self.pt(u1, z1, h), self.pt(u0, z1, h)]
        zs = [z0 + (z1 - z0) * i / steps for i in range(steps + 1)]
        left = [self.pt(u0, z, h) for z in zs]
        right = [self.pt(u1, z, h) for z in zs]
        return left + right[::-1]


def sky(kind='day', horizon=225):
    if kind == 'day':
        g = ('#8ec5ea', '#d6ecf7')
    elif kind == 'overcast':
        g = ('#9aa8b4', '#cfd6dc')
    elif kind == 'night':
        g = ('#0a1424', '#1d2d45')
    elif kind == 'fog':
        g = ('#c9d1d6', '#e3e7ea')
    elif kind == 'winter':
        g = ('#b7cbdc', '#e8eef3')
    else:
        g = ('#8ec5ea', '#d6ecf7')
    key = 'sky' + kind
    return (f'<defs><linearGradient id="{key}" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{g[0]}"/><stop offset="1" stop-color="{g[1]}"/></linearGradient></defs>'
            f'<rect width="{W}" height="{f(horizon + 2)}" fill="url(#{key})"/>')


def p_ground(p, kind='day'):
    col = {'day': ('#a9cf8f', '#88b673'), 'overcast': ('#93ad84', '#7b9670'), 'night': ('#162019', '#1d2a21'),
           'fog': ('#c8d1c9', '#aebcae'), 'winter': ('#eef2f5', '#dfe7ed'), 'city': ('#cfcabd', '#b9b3a4')}[kind]
    key = 'gr' + kind
    return (f'<defs><linearGradient id="{key}" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{col[0]}"/><stop offset="1" stop-color="{col[1]}"/></linearGradient></defs>'
            f'<rect y="{f(p.hz)}" width="{W}" height="{f(H - p.hz)}" fill="url(#{key})"/>')


def p_hills(p, seed=2, color='#9cb8a8', op=.6, amp=40):
    rnd = random.Random(seed)
    xs = list(range(-40, W + 80, 80))
    path = f'M-40 {f(p.hz + 2)} '
    for x in xs:
        path += f'L{x} {f(p.hz - rnd.uniform(8, amp))} '
    path += f'L{W + 40} {f(p.hz + 2)}Z'
    return f'<path d="{path}" fill="{color}" opacity="{op}"/>'


def p_city(p, seed=4, color='#9fb1bf', op=.75):
    rnd = random.Random(seed)
    out = f'<g fill="{color}" opacity="{op}">'
    x = -20
    while x < W:
        w = rnd.uniform(36, 80)
        h = rnd.uniform(25, 95)
        out += f'<rect x="{f(x)}" y="{f(p.hz - h)}" width="{f(w)}" height="{f(h + 2)}"/>'
        x += w + rnd.uniform(2, 10)
    return out + '</g>'


def p_road(p, u0=-5.25, u1=1.75, z0=1.5, z1=400, color='#5a6069', steps=40, shoulder=True):
    out = ''
    if shoulder:
        out += f'<polygon points="{pts(p.quad(u0 - 1.6, u1 + 1.6, z0, z1, steps=steps))}" fill="#c9c2b0"/>'
    out += f'<polygon points="{pts(p.quad(u0, u1, z0, z1, steps=steps))}" fill="{color}"/>'
    return out


def p_line(p, u, z0, z1, width=.14, dash=None, color=MARK, op=1.0):
    out = ''
    if dash:
        on, offd = dash
        z = z0
        while z < z1:
            out += f'<polygon points="{pts(p.quad(u - width / 2, u + width / 2, z, min(z + on, z1), steps=2))}" fill="{color}" opacity="{op}"/>'
            z += on + offd
    else:
        out += f'<polygon points="{pts(p.quad(u - width / 2, u + width / 2, z0, z1, steps=30))}" fill="{color}" opacity="{op}"/>'
    return out


def p_band(p, u0, u1, z0, z1, color, op=1.0):
    return f'<polygon points="{pts(p.quad(u0, u1, z0, z1, steps=1 if p.bend == 0 else 6))}" fill="{color}" opacity="{op}"/>'


def p_zebra(p, u0, u1, z0, z1):
    out = ''
    u = u0 + .25
    while u + .5 <= u1:
        out += p_band(p, u, u + .5, z0, z1, MARK)
        u += 1.0
    return out


def p_crossroad(p, z0, z1, color='#5a6069', walk=True):
    """Көлденең жол (z0..z1 аралығында)."""
    out = ''
    if walk:
        out += p_band(p, -60, 60, z0 - 2.2, z0, '#cfc8b6') + p_band(p, -60, 60, z1, z1 + 2.2, '#cfc8b6')
    out += p_band(p, -60, 60, z0, z1, color)
    return out


def p_post(p, u, z, height=2.3, color='#8c98a4'):
    x, yb = p.pt(u, z, 0)
    _, yt = p.pt(u, z, height)
    w = max(p.scale(z) * .07, 2)
    return (f'<ellipse cx="{f(x + w)}" cy="{f(yb)}" rx="{f(w * 2.2)}" ry="{f(w * .8)}" fill="#0b1520" opacity=".25"/>'
            f'<rect x="{f(x - w / 2)}" y="{f(yt)}" width="{f(w)}" height="{f(yb - yt)}" fill="{color}"/>'
            f'<rect x="{f(x - w / 2)}" y="{f(yt)}" width="{f(w * .35)}" height="{f(yb - yt)}" fill="#c3ccd4"/>')


def p_sign(p, u, z, kind, size=.75, height=2.6, stack=(), **kw):
    """Перспективадағы белгі (тірегімен)."""
    s = p.scale(z) * size
    x, ys = p.pt(u, z, height)
    out = p_post(p, u, z, height + size * .2)
    out += f'<g transform="translate({f(x)} {f(ys)})">{sign(kind, s, **kw)}</g>'
    y = ys
    for k2, kw2 in stack:
        y += s * 1.1
        out += f'<g transform="translate({f(x)} {f(y)})">{sign(k2, s, **kw2)}</g>'
    return out


def p_tlight(svg, p, u, z, state, size=1.0, height=2.9):
    s = p.scale(z) * .0085 * size
    x, yt = p.pt(u, z, height + 1.25 * size)
    out = p_post(p, u, z, height, '#3a4450')
    out += traffic_light(svg, x, yt, s, state, pole=False)
    return out


def p_tree(p, u, z, h=6.0, kind='round', seed=0):
    rnd = random.Random(seed)
    x, yb = p.pt(u, z, 0)
    s = p.scale(z)
    tw = max(s * .25, 1.5)
    th = s * h * .4
    out = f'<ellipse cx="{f(x + s * .3)}" cy="{f(yb)}" rx="{f(s * 1.3)}" ry="{f(s * .25)}" fill="#0b1520" opacity=".18"/>'
    out += f'<rect x="{f(x - tw / 2)}" y="{f(yb - th)}" width="{f(tw)}" height="{f(th)}" fill="#6b5240"/>'
    if kind == 'pine':
        for k in range(3):
            w = s * (1.6 - k * .4)
            y = yb - th * .6 - k * s * h * .22
            out += f'<polygon points="{pts([(x - w, y), (x + w, y), (x, y - s * h * .38)])}" fill="{["#2f6b4a", "#3a7d55", "#468e60"][k]}"/>'
    elif kind == 'bare':
        for a in (-35, -10, 15, 40):
            out += f'<path d="M{f(x)} {f(yb - th)} l{f(math.sin(math.radians(a)) * s * 1.6)} {f(-s * h * .35)}" stroke="#6b5240" stroke-width="{f(tw * .5)}"/>'
    else:
        r = s * h * .26
        cy = yb - th - r * .55
        out += (f'<circle cx="{f(x)}" cy="{f(cy)}" r="{f(r)}" fill="#4f8f4a"/>'
                f'<circle cx="{f(x - r * .35)}" cy="{f(cy - r * .2)}" r="{f(r * .7)}" fill="#5f9f55"/>'
                f'<circle cx="{f(x + r * .3)}" cy="{f(cy + r * .1)}" r="{f(r * .6)}" fill="#467f42"/>'
                f'<circle cx="{f(x - r * .45)}" cy="{f(cy - r * .45)}" r="{f(r * .28)}" fill="#7ab86b"/>')
    return out


def p_building(p, u, z, w=10, h=12, depth=8, color='#c8bfb2', side='right'):
    """Жол бойындағы үй (бет жағы жолға қараған)."""
    a, b = p.pt(u, z, 0), p.pt(u, z + depth, 0)
    a2, b2 = p.pt(u, z, h), p.pt(u, z + depth, h)
    face = [a, b, b2, a2]
    out = f'<polygon points="{pts(face)}" fill="{color}"/>'
    # терезелер
    for i in range(1, 4):
        for j in range(1, int(h / 3.2)):
            zz = z + depth * i / 4
            x0, y0 = p.pt(u, zz - depth * .08, j * 3.2)
            x1, y1 = p.pt(u, zz + depth * .08, j * 3.2 + 1.6)
            out += f'<polygon points="{pts([(x0, y0), (x1, p.pt(u, zz + depth * .08, j * 3.2)[1]), (x1, y1), (x0, p.pt(u, zz - depth * .08, j * 3.2 + 1.6)[1])])}" fill="#7f97ab" opacity=".75"/>'
    return out


def car_rear(svg, x, yb, w, color='blue', brake=False, signal=None, hazard=False, night=False, truck=False, plate=True):
    """Алдағы көлік (артынан көрініс). x — ортасы, yb — жерге тиетін жері, w — ені px."""
    c = CAR_COLORS.get(color, color)
    h = w * (.78 if not truck else 1.25)
    out = f'<ellipse cx="{f(x)}" cy="{f(yb)}" rx="{f(w * .58)}" ry="{f(w * .07)}" fill="#0b1520" opacity=".35"/>'
    out += f'<rect x="{f(x - w * .44)}" y="{f(yb - w * .16)}" width="{f(w * .16)}" height="{f(w * .16)}" rx="{f(w * .03)}" fill="#15191e"/>'
    out += f'<rect x="{f(x + w * .28)}" y="{f(yb - w * .16)}" width="{f(w * .16)}" height="{f(w * .16)}" rx="{f(w * .03)}" fill="#15191e"/>'
    if truck:
        out += (f'<rect x="{f(x - w * .5)}" y="{f(yb - h)}" width="{f(w)}" height="{f(h - w * .12)}" rx="{f(w * .03)}" fill="{c}"/>'
                f'<rect x="{f(x - w * .5)}" y="{f(yb - h)}" width="{f(w)}" height="{f(h - w * .12)}" rx="{f(w * .03)}" fill="url(#vsheen)"/>'
                f'<path d="M{f(x)} {f(yb - h + w * .04)}V{f(yb - w * .2)}" stroke="#000" stroke-opacity=".2" stroke-width="{f(w * .012)}"/>'
                f'<rect x="{f(x - w * .5)}" y="{f(yb - w * .2)}" width="{f(w)}" height="{f(w * .07)}" fill="#2b313a"/>')
        ly = yb - w * .17
    else:
        out += (f'<path d="M{f(x - w * .5)} {f(yb - w * .12)} L{f(x - w * .5)} {f(yb - h * .52)} Q{f(x - w * .48)} {f(yb - h * .62)} {f(x - w * .36)} {f(yb - h * .64)} '
                f'L{f(x - w * .3)} {f(yb - h * .95)} Q{f(x)} {f(yb - h * 1.02)} {f(x + w * .3)} {f(yb - h * .95)} L{f(x + w * .36)} {f(yb - h * .64)} '
                f'Q{f(x + w * .48)} {f(yb - h * .62)} {f(x + w * .5)} {f(yb - h * .52)} L{f(x + w * .5)} {f(yb - w * .12)} Z" fill="{c}"/>'
                f'<path d="M{f(x - w * .27)} {f(yb - h * .66)} L{f(x - w * .23)} {f(yb - h * .9)} Q{f(x)} {f(yb - h * .95)} {f(x + w * .23)} {f(yb - h * .9)} L{f(x + w * .27)} {f(yb - h * .66)}Z" fill="url(#glass)"/>'
                f'<rect x="{f(x - w * .5)}" y="{f(yb - h * .6)}" width="{f(w)}" height="{f(h * .5)}" fill="url(#vsheen)" opacity=".7"/>'
                f'<rect x="{f(x - w * .5)}" y="{f(yb - w * .2)}" width="{f(w)}" height="{f(w * .09)}" rx="{f(w * .03)}" fill="#2b313a"/>')
        ly = yb - h * .5
    lc = '#ff2a1f' if (brake or night) else '#b8141a'
    for sx in (-1, 1):
        out += f'<rect x="{f(x + sx * w * .41 - w * .07)}" y="{f(ly)}" width="{f(w * .14)}" height="{f(w * .08)}" rx="{f(w * .02)}" fill="{lc}"/>'
        if brake or night:
            out += glow(svg, x + sx * w * .41, ly + w * .04, w * (.32 if brake else .2), '#ff2a1f')
    sides = []
    if signal in ('left', 'both') or hazard:
        sides.append(-1)
    if signal in ('right', 'both') or hazard:
        sides.append(1)
    for sx in sides:
        out += glow(svg, x + sx * w * .43, ly - w * .02, w * .28, '#ffae00')
        out += f'<circle cx="{f(x + sx * w * .43)}" cy="{f(ly - w * .02)}" r="{f(w * .035)}" fill="#ffc400"/>'
    if plate:
        out += f'<rect x="{f(x - w * .13)}" y="{f(ly + w * .02)}" width="{f(w * .26)}" height="{f(w * .07)}" rx="{f(w * .01)}" fill="#f4f4f4" stroke="#333" stroke-width="{f(max(w * .006, .6))}"/>'
    return out


def car_front(svg, x, yb, w, color='white', lights='low', night=False):
    c = CAR_COLORS.get(color, color)
    h = w * .78
    out = f'<ellipse cx="{f(x)}" cy="{f(yb)}" rx="{f(w * .58)}" ry="{f(w * .07)}" fill="#0b1520" opacity=".35"/>'
    out += (f'<path d="M{f(x - w * .5)} {f(yb - w * .12)} L{f(x - w * .5)} {f(yb - h * .5)} Q{f(x - w * .47)} {f(yb - h * .6)} {f(x - w * .36)} {f(yb - h * .62)} '
            f'L{f(x - w * .3)} {f(yb - h * .95)} Q{f(x)} {f(yb - h * 1.02)} {f(x + w * .3)} {f(yb - h * .95)} L{f(x + w * .36)} {f(yb - h * .62)} '
            f'Q{f(x + w * .47)} {f(yb - h * .6)} {f(x + w * .5)} {f(yb - h * .5)} L{f(x + w * .5)} {f(yb - w * .12)} Z" fill="{c}"/>'
            f'<path d="M{f(x - w * .33)} {f(yb - h * .64)} L{f(x - w * .25)} {f(yb - h * .9)} Q{f(x)} {f(yb - h * .95)} {f(x + w * .25)} {f(yb - h * .9)} L{f(x + w * .33)} {f(yb - h * .64)}Z" fill="url(#glass)"/>'
            f'<rect x="{f(x - w * .2)}" y="{f(yb - h * .42)}" width="{f(w * .4)}" height="{f(w * .09)}" rx="{f(w * .02)}" fill="#2b313a"/>')
    for sx in (-1, 1):
        lx = x + sx * w * .36
        ly = yb - h * .45
        out += f'<rect x="{f(lx - w * .09)}" y="{f(ly - w * .04)}" width="{f(w * .18)}" height="{f(w * .08)}" rx="{f(w * .03)}" fill="#fffbe6"/>'
        if lights:
            r = w * (2.6 if lights == 'high' else .9)
            out += glow(svg, lx, ly, r, '#fff6cc', 'gl' + ('h' if lights == 'high' else 'l'), .98 if lights == 'high' else .9)
    return out


def truck_rear_big(svg, x, yb, w, color='#e9edf1', brake=False, night=False, hazard=False):
    return car_rear(svg, x, yb, w, color, brake=brake, night=night, truck=True, hazard=hazard)


def car_side(svg, x, yb, L, color='red', facing='right', kind='sedan'):
    """Бүйірден көрінетін жеңіл көлік (перспективада көлденең жүргенде)."""
    c = CAR_COLORS.get(color, color)
    s = L / 100
    sx = 1 if facing == 'right' else -1
    body = (f'<path d="M-50 -8 L-50 -22 Q-48 -30 -38 -31 L-26 -32 L-14 -46 Q-8 -50 4 -50 L22 -50 Q30 -49 36 -42 L44 -32 Q52 -30 52 -22 L52 -8 Z" fill="{c}"/>'
            f'<path d="M-11 -44 L-1 -46 L-1 -33 L-22 -33 Z M3 -46 L20 -46 Q27 -45 31 -40 L37 -33 L3 -33 Z" fill="url(#glass)"/>'
            f'<rect x="-50" y="-31" width="102" height="16" fill="url(#vsheen)" opacity=".6"/>'
            f'<rect x="46" y="-28" width="6" height="5" rx="2" fill="#fff8d6"/><rect x="-50" y="-28" width="5" height="5" rx="2" fill="#c4161c"/>'
            f'<circle cx="-30" cy="-8" r="10" fill="#1b1f24"/><circle cx="-30" cy="-8" r="5" fill="#9aa4ae"/>'
            f'<circle cx="32" cy="-8" r="10" fill="#1b1f24"/><circle cx="32" cy="-8" r="5" fill="#9aa4ae"/>')
    return (f'<ellipse cx="{f(x)}" cy="{f(yb)}" rx="{f(L * .55)}" ry="{f(L * .05)}" fill="#0b1520" opacity=".3"/>'
            f'<g transform="translate({f(x)} {f(yb)}) scale({f(sx * s)} {f(s)})">{body}</g>')


def person(x, yb, h, coat='#3b82c4', pants='#2b3440', pose='walk', facing=1, skin='#e0b18f', hair='#3a2a20'):
    """Адам (бүйірден/алдыдан). h — биіктігі px."""
    s = h / 170
    if pose == 'walk':
        legs = (f'<path d="M0 -80 L-14 -40 L-22 0 M0 -80 L12 -42 L22 -2" stroke="{pants}" stroke-width="15" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
                f'<path d="M-30 0 H-14 M14 -2 H30" stroke="#222" stroke-width="9" stroke-linecap="round"/>')
        arms = (f'<path d="M0 -130 L-18 -98 L-22 -76" stroke="{coat}" stroke-width="12" stroke-linecap="round" fill="none"/>'
                f'<path d="M2 -130 L18 -100 L28 -82" stroke="{coat}" stroke-width="12" stroke-linecap="round" fill="none"/>')
    else:
        legs = (f'<path d="M-7 -80 L-9 0 M7 -80 L9 0" stroke="{pants}" stroke-width="15" stroke-linecap="round" fill="none"/>'
                f'<path d="M-16 0 H-4 M4 0 H16" stroke="#222" stroke-width="9" stroke-linecap="round"/>')
        arms = (f'<path d="M-14 -130 L-20 -95 L-20 -74 M14 -130 L20 -95 L20 -74" stroke="{coat}" stroke-width="12" stroke-linecap="round" fill="none"/>')
    torso = f'<path d="M-17 -138 Q0 -146 17 -138 L15 -78 L-15 -78 Z" fill="{coat}"/>'
    head = (f'<circle cx="0" cy="-153" r="15" fill="{skin}"/><path d="M-15 -155 Q-14 -172 0 -170 Q14 -172 15 -155 Q8 -164 0 -162 Q-8 -164 -15 -155Z" fill="{hair}"/>')
    return (f'<g transform="translate({f(x)} {f(yb)}) scale({f(s * facing)} {f(s)})">'
            f'<ellipse cx="0" cy="0" rx="30" ry="6" fill="#0b1520" opacity=".25"/>' + legs + arms + torso + head + '</g>')


def officer_front(x, yb, h):
    """Реттеуші (алдынан): қолдары екі жаққа созылған."""
    s = h / 170
    return (f'<g transform="translate({f(x)} {f(yb)}) scale({f(s)})">'
            f'<ellipse cx="0" cy="0" rx="34" ry="7" fill="#0b1520" opacity=".3"/>'
            f'<path d="M-8 -80 L-10 0 M8 -80 L10 0" stroke="#1f3550" stroke-width="16" stroke-linecap="round"/>'
            f'<path d="M-18 0 H-4 M4 0 H18" stroke="#111" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M-16 -132 L-88 -130 M16 -132 L88 -130" stroke="#1f3550" stroke-width="13" stroke-linecap="round"/>'
            f'<circle cx="-92" cy="-130" r="7" fill="#f1f1f1"/><circle cx="92" cy="-130" r="7" fill="#f1f1f1"/>'
            f'<rect x="96" y="-134" width="34" height="8" rx="4" fill="#fff" stroke="#222" stroke-width="1.5"/>'
            f'<rect x="102" y="-134" width="6" height="8" fill="#111"/><rect x="114" y="-134" width="6" height="8" fill="#111"/>'
            f'<path d="M-19 -140 Q0 -148 19 -140 L17 -76 L-17 -76 Z" fill="#1f3550"/>'
            f'<path d="M-18 -138 Q0 -146 18 -138 L16 -90 L-16 -90 Z" fill="#c6e83a"/>'
            f'<path d="M-17 -120 H17 M-16 -104 H16" stroke="#dcdcdc" stroke-width="4"/>'
            f'<circle cx="0" cy="-154" r="14" fill="#e0b18f"/>'
            f'<path d="M-17 -160 Q0 -176 17 -160 Z" fill="#f4f6f8"/><rect x="-19" y="-162" width="38" height="5" rx="2" fill="#1f3550"/>'
            f'<rect x="-14" y="-160" width="28" height="3" fill="#1f3550"/></g>')


def windshield(dash='#1a2129', light=False):
    """Жүргізуші орнынан қарағандағы терезе жақтауы мен панель."""
    c = dash
    return (f'<path d="M0 0 L70 0 L28 {H} L0 {H} Z" fill="{c}"/>'
            f'<path d="M{W} 0 L{W - 70} 0 L{W - 28} {H} L{W} {H} Z" fill="{c}"/>'
            f'<path d="M0 0 H{W} V16 Q480 30 0 16 Z" fill="{c}"/>'
            f'<path d="M0 {H} L0 {H - 66} Q240 {H - 104} 480 {H - 106} Q720 {H - 104} {W} {H - 66} L{W} {H} Z" fill="{c}"/>'
            f'<path d="M0 {H - 66} Q240 {H - 104} 480 {H - 106} Q720 {H - 104} {W} {H - 66}" fill="none" stroke="#37414c" stroke-width="3"/>'
            f'<rect x="425" y="20" width="110" height="36" rx="12" fill="#11161c"/><rect x="431" y="25" width="98" height="26" rx="9" fill="#3a4b5c"/>'
            f'<rect x="474" y="12" width="12" height="12" fill="#11161c"/>')


def rain(seed=3, n=170, op=.55):
    rnd = random.Random(seed)
    out = f'<g stroke="#dce8f2" stroke-width="2" stroke-linecap="round" opacity="{op}">'
    for _ in range(n):
        x, y = rnd.uniform(-40, W), rnd.uniform(-20, H)
        l = rnd.uniform(14, 30)
        out += f'<path d="M{f(x)} {f(y)} l{f(l * .25)} {f(l)}"/>'
    return out + '</g>'


def drops(seed=5, n=60):
    rnd = random.Random(seed)
    out = '<g>'
    for _ in range(n):
        x, y, r = rnd.uniform(0, W), rnd.uniform(0, H - 120), rnd.uniform(2, 6)
        out += f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#e9f3fb" opacity=".35"/><circle cx="{f(x - r * .3)}" cy="{f(y - r * .3)}" r="{f(r * .35)}" fill="#fff" opacity=".6"/>'
    return out + '</g>'


def snow(seed=7, n=220, op=.85):
    rnd = random.Random(seed)
    out = f'<g fill="#fff" opacity="{op}">'
    for _ in range(n):
        out += f'<circle cx="{f(rnd.uniform(0, W))}" cy="{f(rnd.uniform(0, H))}" r="{f(rnd.uniform(1.5, 4.5))}"/>'
    return out + '</g>'


def fog_layer(p, strength=.85, color='#e6eaed'):
    key = 'fog' + str(int(strength * 100))
    return (f'<defs><linearGradient id="{key}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity="{strength}"/>'
            f'<stop offset="{f((p.hz + 40) / H)}" stop-color="{color}" stop-opacity="{strength}"/>'
            f'<stop offset="{f((p.hz + 150) / H)}" stop-color="{color}" stop-opacity="{strength * .6}"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="{strength * .15}"/></linearGradient></defs>'
            f'<rect width="{W}" height="{H}" fill="url(#{key})"/>')


def night_tint(op=.55):
    return f'<rect width="{W}" height="{H}" fill="#06101d" opacity="{op}"/>'


def cone(x, yb, h):
    w = h * .55
    return (f'<ellipse cx="{f(x)}" cy="{f(yb)}" rx="{f(w * .7)}" ry="{f(h * .08)}" fill="#0b1520" opacity=".25"/>'
            f'<rect x="{f(x - w * .6)}" y="{f(yb - h * .1)}" width="{f(w * 1.2)}" height="{f(h * .1)}" rx="{f(h * .03)}" fill="#e85d1a"/>'
            f'<polygon points="{pts([(x - w * .45, yb - h * .08), (x + w * .45, yb - h * .08), (x + w * .1, yb - h), (x - w * .1, yb - h)])}" fill="#ff7a2f"/>'
            f'<polygon points="{pts([(x - w * .33, yb - h * .38), (x + w * .33, yb - h * .38), (x + w * .26, yb - h * .55), (x - w * .26, yb - h * .55)])}" fill="#fff"/>')


def barrier_stripes(x0, y0, x1, y1, w, n=8):
    """Ақ-қызыл жолақты шлагбаум/тосқауыл."""
    ang = math.degrees(math.atan2(y1 - y0, x1 - x0))
    L = math.hypot(x1 - x0, y1 - y0)
    out = f'<g transform="translate({f(x0)} {f(y0)}) rotate({f(ang)})"><rect x="0" y="{f(-w / 2)}" width="{f(L)}" height="{f(w)}" rx="{f(w / 3)}" fill="#fff" stroke="#999" stroke-width="1"/>'
    for i in range(0, n, 2):
        out += f'<rect x="{f(L * i / n)}" y="{f(-w / 2)}" width="{f(L / n)}" height="{f(w)}" fill="#e02a2a"/>'
    return out + '</g>'


# ======================================================================
#  БҮЙІРДЕН КӨРІНІС: ЖҮК КӨЛІКТЕРІ
# ======================================================================

def wheel(x, y, r, rim='#a7b1bb'):
    return (f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="#1b1f24"/><circle cx="{f(x)}" cy="{f(y)}" r="{f(r * .58)}" fill="{rim}"/>'
            f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r * .2)}" fill="#59636d"/>'
            + ''.join(f'<circle cx="{f(x + r * .38 * math.cos(math.radians(a)))}" cy="{f(y + r * .38 * math.sin(math.radians(a)))}" r="{f(r * .06)}" fill="#59636d"/>' for a in range(0, 360, 60)))


def gazelle_side(x, yg, s=1.0, cab='#f4f6f8', body='flatbed', box='#eef1f4', sag=0.0, tilt=0.0, facing=1, lights=False):
    """ГАЗель (бүйірден). x — артқы шеті, yg — жер деңгейі. Ұзындығы ≈ 540*s. Алдыңғы жағы оңға (facing=1)."""
    g = ''
    sh = sag
    # шасси
    g += f'<ellipse cx="270" cy="2" rx="290" ry="12" fill="#0b1520" opacity=".25"/>'
    g += f'<rect x="10" y="{f(-62 + sh)}" width="500" height="14" rx="4" fill="#2b313a"/>'
    # кабина
    g += (f'<path d="M372 {f(-62 + sh)} L372 -200 Q374 -214 390 -216 L470 -216 Q492 -214 502 -192 L528 -128 Q536 -116 536 -100 L536 {f(-60 + sh)} Z" fill="{cab}"/>'
          f'<path d="M372 {f(-62 + sh)} L372 -200 Q374 -214 390 -216 L470 -216 Q492 -214 502 -192 L528 -128 Q536 -116 536 -100 L536 {f(-60 + sh)} Z" fill="url(#vsheen)" opacity=".7"/>'
          f'<path d="M455 -204 L478 -204 Q488 -202 494 -190 L516 -134 L455 -134 Z" fill="url(#glass)"/>'
          f'<path d="M386 -204 L446 -204 L446 -134 L386 -134 Z" fill="url(#glass)"/>'
          f'<path d="M450 -134 V{f(-66 + sh)}" stroke="#000" stroke-opacity=".18" stroke-width="3"/>'
          f'<rect x="428" y="-124" width="16" height="5" rx="2" fill="#000" opacity=".25"/>'
          f'<rect x="526" y="-112" width="12" height="16" rx="3" fill="{"#fff3b0" if lights else "#fffbe6"}" stroke="#bbb"/>'
          f'<rect x="520" y="{f(-74 + sh)}" width="22" height="16" rx="4" fill="#3a4450"/>'
          f'<rect x="364" y="-170" width="10" height="26" rx="3" fill="#2b313a"/>')
    # кузов
    if body == 'flatbed':
        g += (f'<rect x="0" y="{f(-104 + sh)}" width="362" height="44" rx="3" fill="#8b98a5"/>'
              f'<rect x="0" y="{f(-104 + sh)}" width="362" height="8" fill="#a9b4bf"/>'
              + ''.join(f'<path d="M{f(30 + i * 60)} {f(-100 + sh)} V{f(-62 + sh)}" stroke="#6e7a86" stroke-width="3"/>' for i in range(6)))
    elif body == 'box':
        g += (f'<rect x="0" y="{f(-250 + sh)}" width="362" height="190" rx="5" fill="{box}" stroke="#c7cfd7" stroke-width="2"/>'
              f'<rect x="0" y="{f(-250 + sh)}" width="362" height="190" rx="5" fill="url(#vsheen)" opacity=".6"/>')
    elif body == 'tent':
        g += (f'<path d="M0 {f(-60 + sh)} V{f(-236 + sh)} Q0 {f(-250 + sh)} 14 {f(-250 + sh)} H348 Q362 {f(-250 + sh)} 362 {f(-236 + sh)} V{f(-60 + sh)} Z" fill="#3f7fb8"/>'
              + ''.join(f'<path d="M{f(30 + i * 60)} {f(-246 + sh)} V{f(-66 + sh)}" stroke="#2f6696" stroke-width="3"/>' for i in range(6)))
    g += f'<rect x="-6" y="{f(-58 + sh)}" width="14" height="12" rx="3" fill="#c4161c"/>'
    if lights:
        g += f'<circle cx="0" cy="{f(-52 + sh)}" r="26" fill="#ff2a1f" opacity=".25"/>'
    g += wheel(92, -26, 30) + wheel(452, -26, 30)
    tr = f'translate({f(x)} {f(yg)}) scale({f(s * facing)} {f(s)})'
    if tilt:
        tr += f' rotate({f(tilt)} 270 0)'
    return f'<g transform="{tr}">{g}</g>'


def heavy_truck_side(x, yg, s=1.0, cab='#2f6fd6', box='#eef1f4', body='box', axles=3, facing=1, load=None):
    """Ауыр жүк көлігі (бүйірден, кабина үстінде). Ұзындығы ≈ 760*s."""
    g = '<ellipse cx="380" cy="2" rx="400" ry="14" fill="#0b1520" opacity=".25"/>'
    g += '<rect x="10" y="-80" width="740" height="18" rx="4" fill="#2b313a"/>'
    # кабина
    g += (f'<path d="M600 -70 V-300 Q600 -318 618 -318 H730 Q756 -318 758 -292 L764 -120 Q766 -80 744 -70 Z" fill="{cab}"/>'
          f'<path d="M600 -70 V-300 Q600 -318 618 -318 H730 Q756 -318 758 -292 L764 -120 Q766 -80 744 -70 Z" fill="url(#vsheen)" opacity=".7"/>'
          f'<path d="M680 -300 H738 Q748 -298 750 -286 L754 -210 H680 Z" fill="url(#glass)"/>'
          f'<path d="M612 -300 H668 V-210 H612 Z" fill="url(#glass)"/>'
          f'<rect x="590" y="-270" width="12" height="40" rx="3" fill="#2b313a"/>'
          f'<rect x="740" y="-140" width="20" height="18" rx="3" fill="#fffbe6" stroke="#bbb"/>'
          f'<rect x="610" y="-150" width="40" height="70" rx="6" fill="#000" opacity=".18"/>')
    if body == 'box':
        g += (f'<rect x="0" y="-330" width="586" height="246" rx="5" fill="{box}" stroke="#c7cfd7" stroke-width="2"/>'
              f'<rect x="0" y="-330" width="586" height="246" rx="5" fill="url(#vsheen)" opacity=".6"/>')
    elif body == 'flatbed':
        g += (f'<rect x="0" y="-130" width="586" height="50" rx="3" fill="#8b98a5"/><rect x="0" y="-130" width="586" height="9" fill="#a9b4bf"/>')
    elif body == 'tipper':
        g += (f'<path d="M0 -84 L0 -230 L586 -230 L586 -84 Z" fill="#d98b2b"/><path d="M0 -230 H586" stroke="#b56f1c" stroke-width="8"/>'
              + ''.join(f'<path d="M{f(60 + i * 100)} -226 V-90" stroke="#b56f1c" stroke-width="5"/>' for i in range(6)))
    if load:
        g += load
    g += '<rect x="-6" y="-80" width="14" height="14" rx="3" fill="#c4161c"/>'
    xs = [90, 180] if axles >= 3 else [130]
    for wx in xs:
        g += wheel(wx, -36, 38)
    g += wheel(680, -36, 38)
    return f'<g transform="translate({f(x)} {f(yg)}) scale({f(s * facing)} {f(s)})">{g}</g>'


def box_crate(x, y, w, h, c='#c9965a', tape=True):
    out = (f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="3" fill="{c}" stroke="#8a5a2b" stroke-width="2"/>'
           f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h * .22)}" fill="#fff" opacity=".12"/>')
    if tape:
        out += f'<rect x="{f(x + w * .44)}" y="{f(y)}" width="{f(w * .12)}" height="{f(h)}" fill="#e7d3a8" opacity=".9"/>'
    return out


def strap(x0, y0, x1, y1, c='#f2a516'):
    return f'<path d="M{f(x0)} {f(y0)} L{f(x1)} {f(y1)}" stroke="{c}" stroke-width="7" stroke-linecap="round"/><path d="M{f(x0)} {f(y0)} L{f(x1)} {f(y1)}" stroke="#000" stroke-opacity=".2" stroke-width="7" stroke-dasharray="3 9"/>'


def spec_card(x, y, title, value, w=300, sub=None):
    h = 92 if not sub else 114
    out = card(x, y, w, h, '', '#ffffff', '#cfd9e2')
    out += f'<rect x="{f(x)}" y="{f(y)}" width="10" height="{h}" rx="5" fill="#2f6fd6"/>'
    out += text(x + 26, y + 30, title, 17, '#5b6b7b', 800, 'start')
    out += text(x + 26, y + 72, value, 36, '#111c27', 900, 'start')
    if sub:
        out += text(x + 26, y + 100, sub, 17, '#5b6b7b', 700, 'start')
    return out


def dim_arrow(x0, y0, x1, y1, label='', color='#111c27', lx=None, ly=None, size=20):
    ang = math.atan2(y1 - y0, x1 - x0)
    def head(x, y, a):
        p1 = (x - 14 * math.cos(a - .45), y - 14 * math.sin(a - .45))
        p2 = (x - 14 * math.cos(a + .45), y - 14 * math.sin(a + .45))
        return f'<polygon points="{pts([(x, y), p1, p2])}" fill="{color}"/>'
    out = f'<path d="M{f(x0)} {f(y0)} L{f(x1)} {f(y1)}" stroke="{color}" stroke-width="3"/>' + head(x1, y1, ang) + head(x0, y0, ang + math.pi)
    if label:
        lx = lx if lx is not None else (x0 + x1) / 2
        ly = ly if ly is not None else (y0 + y1) / 2 - 10
        out += (f'<rect x="{f(lx - len(label) * size * .32 - 8)}" y="{f(ly - size)}" width="{f(len(label) * size * .64 + 16)}" height="{f(size + 12)}" rx="8" fill="#fff" opacity=".92"/>'
                + text(lx, ly + 1, label, size, color, 900))
    return out


def rear_truck(x, yg, s=1.0, cab='#f4f6f8', body='flatbed', plate=True, covered_plate=False, lights_covered=False, load=None, tilt=0.0):
    """ГАЗель артынан. x — ортасы. Ені ≈ 300*s."""
    g = '<ellipse cx="0" cy="2" rx="170" ry="12" fill="#0b1520" opacity=".3"/>'
    g += wheel(-104, -28, 30, '#7f8a95') + wheel(104, -28, 30, '#7f8a95')
    g += f'<path d="M-120 -260 Q-118 -276 -100 -278 H100 Q118 -276 120 -260 V-150 H-120 Z" fill="{cab}"/>'
    g += '<rect x="-96" y="-262" width="192" height="60" rx="8" fill="url(#glass)" opacity=".5"/>'
    if body == 'flatbed':
        g += '<rect x="-150" y="-150" width="300" height="70" rx="4" fill="#8b98a5"/><rect x="-150" y="-150" width="300" height="10" fill="#a9b4bf"/>'
        g += '<path d="M-150 -118 H150" stroke="#6e7a86" stroke-width="3"/>'
    else:
        g += '<rect x="-150" y="-330" width="300" height="250" rx="6" fill="#eef1f4" stroke="#c7cfd7" stroke-width="2"/><path d="M0 -326 V-84" stroke="#b4bec8" stroke-width="3"/>'
    g += '<rect x="-150" y="-82" width="300" height="20" rx="3" fill="#2b313a"/>'
    for sx in (-1, 1):
        g += f'<rect x="{f(sx * 128 - 18)}" y="-110" width="36" height="22" rx="4" fill="#d01a1f"/><rect x="{f(sx * 128 - 18)}" y="-110" width="12" height="22" rx="3" fill="#f59e0b"/>'
    if plate:
        g += ('<rect x="-62" y="-74" width="124" height="30" rx="4" fill="#fff" stroke="#222" stroke-width="2.5"/>'
              '<rect x="-60" y="-72" width="20" height="26" fill="#00afca"/>' + text(-50, -53, 'KZ', 9, '#fff', 900) +
              text(12, -51, '123 ABC 02', 17, '#111', 900))
    if load:
        g += load
    tr = f'translate({f(x)} {f(yg)}) scale({f(s)})'
    if tilt:
        tr += f' rotate({f(tilt)} 0 0)'
    return f'<g transform="{tr}">{g}</g>'
