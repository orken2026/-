"""Сұрақтар базасын жинап, тексеріп, data/questions.json жасайды.

    python3 content/build_bank.py            # json жасау
    python3 content/build_bank.py --xlsx     # + маман тексеруіне арналған Excel
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

from schema import BANK, TOPICS  # noqa: E402
import bank_g1, bank_g2, bank_g3, bank_g4, bank_c  # noqa: E402,F401

OUT = ROOT / 'data' / 'questions.json'
ASSETS = ROOT / 'webapp' / 'assets'

# Тегін нұсқаға кіретін сұрақтар саны (B: 20 суретті + 20 мәтінді; B+C: 16+16 жалпы + 4+4 жүк)
FREE_G_IMG, FREE_G_TXT, FREE_C_IMG, FREE_C_TXT = 24, 24, 5, 5


def ref_text(ref, lang):
    """'24.5' → 'ЖЖҚ 24-т., 5) тт.' ; 'z2.5' → белгі ; 'm1.1' → таңбалау."""
    if not ref:
        return ''
    if ref.startswith('z'):
        return f'ЖЖҚ, {ref[1:]} белгісі' if lang == 'kk' else f'ПДД РК, знак {ref[1:]}'
    if ref.startswith('m'):
        return f'ЖЖҚ, {ref[1:]} таңбалауы' if lang == 'kk' else f'ПДД РК, разметка {ref[1:]}'
    p, _, sp = ref.partition('.')
    if lang == 'kk':
        return f'ЖЖҚ, {p}-тармақ' + (f', {sp})-тармақша' if sp else '')
    return f'ПДД РК, п. {p}' + (f', пп. {sp})' if sp else '')


def pick_free(items, n):
    """Тақырыптар бойынша кезекпен таңдау — тегін нұсқа әр тақырыптан болсын."""
    by_topic = {}
    for q in items:
        by_topic.setdefault(q['topic'], []).append(q)
    out = []
    while len(out) < n and any(by_topic.values()):
        for t in list(by_topic):
            if by_topic[t] and len(out) < n:
                out.append(by_topic[t].pop(0))
    return out


def validate():
    errors = []
    ids = [q['id'] for q in BANK]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        errors.append(f'Қайталанған id: {sorted(dup)}')
    for q in BANK:
        for lang in ('kk', 'ru'):
            d = q[lang]
            if not d['text'].strip() or not d['why'].strip():
                errors.append(f"{q['id']} {lang}: мәтін бос")
            if len(set(o.strip().lower() for o in d['options'])) != 4:
                errors.append(f"{q['id']} {lang}: нұсқалар қайталанады")
        if q['image'] and not (ASSETS / f"{q['image']}.svg").exists():
            errors.append(f"{q['id']}: сурет жоқ {q['image']}.svg")
    return errors


def poll_ok(q, lang):
    """Telegram quiz шектеулері: сұрақ ≤300, нұсқа ≤100, түсіндірме ≤200."""
    d = q[lang]
    return len(d['text']) <= 300 and all(len(o) <= 100 for o in d['options']) and len(d['why']) <= 200


def build():
    errs = validate()
    if errs:
        print('\n'.join(errs))
        sys.exit(1)
    g = [q for q in BANK if q['cat'] == 'g']
    c = [q for q in BANK if q['cat'] == 'c']
    free = set()
    for pool, n_img, n_txt in ((g, FREE_G_IMG, FREE_G_TXT), (c, FREE_C_IMG, FREE_C_TXT)):
        free |= {q['id'] for q in pick_free([q for q in pool if q['image']], n_img)}
        free |= {q['id'] for q in pick_free([q for q in pool if not q['image']], n_txt)}
    questions = []
    for q in sorted(BANK, key=lambda x: (x['cat'] != 'g', x['id'])):
        item = dict(q)
        item['free'] = q['id'] in free
        item['kk'] = dict(q['kk'], ref=ref_text(q['ref'], 'kk'))
        item['ru'] = dict(q['ru'], ref=ref_text(q['ref'], 'ru'))
        item['poll'] = poll_ok(q, 'kk') and poll_ok(q, 'ru')
        questions.append(item)
    data = {
        'version': 2,
        'rules_source': 'ҚР ІІМ 2023 ж. 30 маусымдағы №534 бұйрығы (НҚА тізілімі №33003)',
        'topics': {k: {'kk': v[0], 'ru': v[1]} for k, v in TOPICS.items()},
        'questions': questions,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    n_ref = sum(1 for q in questions if q['ref'])
    print(f"Сұрақ: {len(questions)} (жалпы {len(g)}, жүк {len(c)}), суретті: {sum(1 for q in questions if q['image'])}, "
          f"тегін: {len(free)}, ЖЖҚ сілтемесі бар: {n_ref}, quiz-ке жарамды: {sum(q['poll'] for q in questions)}")
    return questions


def export_xlsx(questions, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    ws = wb.active
    ws.title = 'Сұрақтар'
    head = ['ID', 'Тақырып', 'Сурет', 'ЖЖҚ сілтемесі', 'Сұрақ (қаз.)', 'Дұрыс жауап (қаз.)', 'Қате 1', 'Қате 2', 'Қате 3',
            'Түсіндірме (қаз.)', 'Вопрос (рус.)', 'Правильный ответ (рус.)', 'Пояснение (рус.)',
            'Маман бағасы', 'Ескерту / түзету']
    ws.append(head)
    for q in questions:
        k, r = q['kk'], q['ru']
        ws.append([q['id'], TOPICS[q['topic']][0], 'иә' if q['image'] else '', k['ref'], k['text'], k['options'][0],
                   k['options'][1], k['options'][2], k['options'][3], k['why'], r['text'], r['options'][0], r['why'], '', ''])
    widths = [7, 22, 7, 18, 48, 34, 24, 24, 24, 48, 48, 34, 48, 16, 36]
    for i, w in enumerate(widths):
        ws.column_dimensions[chr(65 + i)].width = w
    hdr = PatternFill('solid', fgColor='1F3550')
    for cell in ws[1]:
        cell.font = Font(bold=True, color='FFFFFF')
        cell.fill = hdr
        cell.alignment = Alignment(wrap_text=True, vertical='center')
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical='top')
        row[5].fill = PatternFill('solid', fgColor='E3F4E1')
        row[13].fill = PatternFill('solid', fgColor='FFF6D6')
    dv = DataValidation(type='list', formula1='"Дұрыс,Түзету керек,Алып тастау"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f'N2:N{len(questions) + 1}')
    ws.freeze_panes = 'B2'
    ws.auto_filter.ref = f'A1:O{len(questions) + 1}'
    info = wb.create_sheet('Нұсқаулық')
    lines = [
        'Маманға (нұсқаушыға) арналған тексеру парағы',
        '',
        '1. Әр жолды оқып, «Маман бағасы» бағанынан таңдаңыз: Дұрыс / Түзету керек / Алып тастау.',
        '2. Түзету керек болса, «Ескерту / түзету» бағанына дұрыс нұсқаны жазыңыз.',
        '3. Дұрыс жауап әрқашан F бағанында (жасыл). Тестте нұсқалар араласып көрсетіледі.',
        '4. ЖЖҚ сілтемесі — ҚР ІІМ 2023 жылғы 30 маусымдағы №534 бұйрығымен бекітілген Жол жүрісі қағидалары.',
        '',
        f'Барлығы: {len(questions)} сұрақ.',
    ]
    for ln in lines:
        info.append([ln])
    info.column_dimensions['A'].width = 110
    info['A1'].font = Font(bold=True, size=14)
    wb.save(path)
    print('Excel:', path)


if __name__ == '__main__':
    qs = build()
    if '--xlsx' in sys.argv:
        export_xlsx(qs, sys.argv[sys.argv.index('--xlsx') + 1] if len(sys.argv) > sys.argv.index('--xlsx') + 1 else ROOT / 'Qazaq_PDD_suraqtar_tekseru.xlsx')
