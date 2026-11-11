"""Жол белгілері анықтамалығына арналған SVG-лер: webapp/assets/signs/<id>.svg"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import (FONT, _ring, _tri, pts, sign, f, text, _ped)  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / 'webapp' / 'assets' / 'signs'


def blue_circle(s):
    r = s / 2
    return f'<circle r="{f(r)}" fill="#fff"/><circle r="{f(r * .93)}" fill="#1565c0"/>'


def arrow_up(s, color='#fff', x=0, y=0, rot=0):
    r = s / 2
    return (f'<g transform="translate({f(x)} {f(y)}) rotate({rot})"><path d="M0 {f(r * .55)} V{f(-r * .15)}" stroke="{color}" stroke-width="{f(s * .12)}"/>'
            f'<polygon points="{pts([(-r * .32, -r * .1), (r * .32, -r * .1), (0, -r * .6)])}" fill="{color}"/></g>')


def extra(kind, s):
    r = s / 2
    if kind == 'no_vehicles':
        return _ring(s)
    if kind == 'no_horn':
        horn = (f'<path d="M{f(-r * .45)} {f(-r * .12)} H{f(-r * .2)} L{f(r * .25)} {f(-r * .4)} V{f(r * .4)} L{f(-r * .2)} {f(r * .12)} H{f(-r * .45)}Z" fill="#111"/>'
                f'<path d="M{f(r * .35)} {f(-r * .25)} q{f(r * .15)} {f(r * .25)} 0 {f(r * .5)}" fill="none" stroke="#111" stroke-width="{f(s * .04)}"/>')
        return _ring(s) + horn + f'<path d="M{f(-r * .55)} {f(-r * .55)}L{f(r * .55)} {f(r * .55)}" stroke="#d6161e" stroke-width="{f(s * .09)}"/>'
    if kind == 'no_left':
        arr = (f'<path d="M{f(r * .15)} {f(r * .55)} V{f(-r * .05)} Q{f(r * .15)} {f(-r * .25)} {f(-r * .1)} {f(-r * .25)} H{f(-r * .2)}" fill="none" stroke="#111" stroke-width="{f(s * .1)}"/>'
               f'<polygon points="{pts([(-r * .2, -r * .5), (-r * .2, 0), (-r * .5, -r * .25)])}" fill="#111"/>')
        return _ring(s) + arr + f'<path d="M{f(-r * .55)} {f(-r * .55)}L{f(r * .55)} {f(r * .55)}" stroke="#d6161e" stroke-width="{f(s * .09)}"/>'
    if kind == 'no_uturn':
        arr = (f'<path d="M{f(r * .25)} {f(r * .55)} V{f(-r * .1)} A{f(r * .22)} {f(r * .22)} 0 0 0 {f(-r * .19)} {f(-r * .1)} V{f(r * .15)}" fill="none" stroke="#111" stroke-width="{f(s * .09)}"/>'
               f'<polygon points="{pts([(-r * .42, r * .1), (r * .04, r * .1), (-r * .19, r * .45)])}" fill="#111"/>')
        return _ring(s) + arr + f'<path d="M{f(-r * .55)} {f(-r * .55)}L{f(r * .55)} {f(r * .55)}" stroke="#d6161e" stroke-width="{f(s * .09)}"/>'
    if kind == 'straight':
        return blue_circle(s) + arrow_up(s)
    if kind == 'right':
        return blue_circle(s) + arrow_up(s, rot=90)
    if kind == 'one_way':
        return (f'<rect x="{f(-r)}" y="{f(-r)}" width="{f(s)}" height="{f(s)}" rx="{f(s * .08)}" fill="#fff"/>'
                f'<rect x="{f(-r * .93)}" y="{f(-r * .93)}" width="{f(s * .93)}" height="{f(s * .93)}" rx="{f(s * .06)}" fill="#1565c0"/>'
                + arrow_up(s * 1.15, '#fff', 0, r * .05))
    if kind == 'ped_warning':
        return _tri(s, f'<g transform="translate({f(-r * .02)} {f(r * .18)})">{_ped(s * .55)}</g>')
    if kind == 'danger':
        return _tri(s, f'<rect x="{f(-r * .07)}" y="{f(-r * .38)}" width="{f(r * .14)}" height="{f(r * .52)}" rx="{f(r * .05)}" fill="#111"/>'
                       f'<circle cy="{f(r * .35)}" r="{f(r * .09)}" fill="#111"/>')
    return None


SIGNS = [
    # id, сызу түрі, kwargs
    ('main', 'main', {}), ('yield', 'yield', {}), ('stop', 'stop', {}),
    ('no_entry', 'no_entry', {}), ('no_vehicles', 'no_vehicles', {}), ('speed60', 'speed', {'n': '60'}),
    ('no_overtake', 'no_overtake', {}), ('no_horn', 'no_horn', {}), ('no_stopping', 'no_stopping', {}),
    ('no_parking', 'no_parking', {}), ('height', 'height', {'val': '3,5'}), ('weight', 'weight', {'val': '10т'}),
    ('no_left', 'no_left', {}), ('no_uturn', 'no_uturn', {}),
    ('straight', 'straight', {}), ('right', 'right', {}), ('roundabout', 'roundabout', {}),
    ('lanes', 'lanes', {'arrows': ('L', 'S', 'R')}), ('crosswalk', 'crosswalk', {}), ('parking', 'parking', {}),
    ('one_way', 'one_way', {}),
    ('curve_right', 'curve_right', {}), ('slippery', 'slippery', {}), ('road_works', 'road_works', {}),
    ('steep_down', 'steep_down', {'pct': '10%'}), ('crosswind', 'crosswind', {}), ('rail_barrier', 'rail_barrier', {}),
    ('st_andrew', 'st_andrew', {}), ('ped_warning', 'ped_warning', {}), ('danger', 'danger', {}),
    ('temp_speed', 'temp_speed', {'n': '40'}),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = 150
    for sid, kind, kw in SIGNS:
        body = extra(kind, s) or sign(kind, s, **kw)
        w = 220 if kind == 'lanes' else 180
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-w / 2} -90 {w} 180" width="{w}" height="180" '
               f'font-family="{FONT}" role="img">{body}</svg>')
        (OUT / f'{sid}.svg').write_text(svg, encoding='utf-8')
    print(f'{len(SIGNS)} белгі → {OUT}')


if __name__ == '__main__':
    main()
