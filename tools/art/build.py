"""Барлық суреттерді webapp/assets/ ішіне жазу.

    python3 tools/art/build.py            # бәрін
    python3 tools/art/build.py g001 c007  # тек таңдалғандарын
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scenes import SCENES  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / 'webapp' / 'assets'


def main(ids):
    OUT.mkdir(parents=True, exist_ok=True)
    todo = ids or sorted(SCENES)
    for qid in todo:
        fn, _ = SCENES[qid]
        svg = fn().render()
        (OUT / f'q-{qid}.svg').write_text(svg, encoding='utf-8')
    print(f'{len(todo)} сурет жазылды → {OUT}')


if __name__ == '__main__':
    main(sys.argv[1:])
