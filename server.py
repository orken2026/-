#!/usr/bin/env python3
"""QAZAQ PDD — Telegram бот + Mini App сервері + API.

Тек стандартты Python кітапханасы (pip қажет емес).

Міндетті айнымалы: BOT_TOKEN. Қалғаны міндетті емес:
  MINI_APP_URL   Mini App адресі (бөлек статикалық сайт). Әдепкі — осы сервер.
  PUBLIC_URL     осы сервердің ашық HTTPS адресі (Render-де автоматты).
  PRICE_STARS    толық нұсқаның бағасы Telegram Stars-пен (әдепкі 50 ⭐ ≈ 500 ₸).
  PLAN_DAYS      неше күнге ашылады; 0 — біржолғы тіркелу, мерзімсіз (әдепкі 0).
  ADMIN_IDS      әкімшілердің Telegram ID-лері, үтірмен (тегін толық қолжетімділік, /stats, /refund).
  SUPPORT        төлем бойынша байланыс (мысалы, @username немесе телефон).
  DATA_DIR       SQLite базасына арналған папка. Бос болса — тек жадта (қайта іске қосқанда өшеді).
  ANTHROPIC_API_KEY, AI_MODEL, AI_DAILY_LIMIT   «Неге?» батырмасының AI түсіндірмесі.
  DAILY_HOUR     күнделікті сұрақ жіберілетін сағат (Алматы уақыты, әдепкі 19). DAILY=0 — өшіру.
  DEV_AUTH=1     тек жергілікті тест үшін: Telegram-сыз кіруге рұқсат (өндірісте ҚОСПАҢЫЗ).
"""
import base64
import hashlib
import hmac
import json
import mimetypes
import os
import random
import secrets
import sqlite3
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qsl, unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
WEBAPP = ROOT / 'webapp'
BANK_FILE = ROOT / 'data' / 'questions.json'

env = os.getenv
BOT_TOKEN = env('BOT_TOKEN', '').strip()
PORT = int(env('PORT', '8000'))
SELF_URL = (env('PUBLIC_URL') or env('RENDER_EXTERNAL_URL') or '').strip().rstrip('/')
MINI_APP_URL = (env('MINI_APP_URL') or SELF_URL).strip().rstrip('/')
API_BASE = env('TELEGRAM_API_BASE', 'https://api.telegram.org').rstrip('/')
PRICE_STARS = int(env('PRICE_STARS', '50'))
PLAN_DAYS = int(env('PLAN_DAYS', '0'))
ADMIN_IDS = {int(x) for x in env('ADMIN_IDS', '').replace(' ', '').split(',') if x.strip().lstrip('-').isdigit()}
SUPPORT = env('SUPPORT', '').strip()
DATA_DIR = env('DATA_DIR', '').strip()
AI_KEY = env('ANTHROPIC_API_KEY', '').strip()
AI_MODEL = env('AI_MODEL', 'claude-haiku-5-5').strip()
AI_DAILY_LIMIT = int(env('AI_DAILY_LIMIT', '30'))
AI_BASE = env('ANTHROPIC_API_BASE', 'https://api.anthropic.com').rstrip('/')
DAILY_ON = env('DAILY', '1') != '0'
DAILY_HOUR = int(env('DAILY_HOUR', '19'))
DEV_AUTH = env('DEV_AUTH', '') == '1'
ALMATY = timezone(timedelta(hours=5))

SECRET = hashlib.sha256(f'app:{BOT_TOKEN or secrets.token_hex(16)}'.encode()).digest()
WEBHOOK_PATH = '/tg/' + hashlib.sha256(f'path:{BOT_TOKEN}'.encode()).hexdigest()[:40]
WEBHOOK_SECRET = hashlib.sha256(f'secret:{BOT_TOKEN}'.encode()).hexdigest()[:64]

EXAM_COUNT, EXAM_MINUTES, PASS_SCORE = 40, 40, 32

STATE = {
    'mode': 'off', 'token_set': bool(BOT_TOKEN), 'bot': None, 'mini_app_url': MINI_APP_URL or None,
    'webhook': False, 'menu_button': False, 'commands': False, 'payments_synced': False,
    'price_stars': PRICE_STARS, 'plan_days': PLAN_DAYS, 'db_persistent': bool(DATA_DIR),
    'ai': bool(AI_KEY), 'daily': DAILY_ON, 'last_error': None, 'updates_handled': 0,
    'started_at': int(time.time()),
}


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ====================================================================== BANK
def load_bank():
    data = json.loads(BANK_FILE.read_text(encoding='utf-8'))
    qs = {q['id']: q for q in data['questions']}
    return data, qs


BANK_DATA, Q = load_bank()
TOPICS = BANK_DATA['topics']
STATE['questions'] = len(Q)


def pool(cat=None, image=None, free_only=False, topic=None):
    out = []
    for q in Q.values():
        if cat and q['cat'] != cat:
            continue
        if image is not None and bool(q['image']) != image:
            continue
        if free_only and not q['free']:
            continue
        if topic and q['topic'] != topic:
            continue
        out.append(q)
    return out


# ====================================================================== DB
_db_lock = threading.Lock()
if DATA_DIR:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    DB = sqlite3.connect(str(Path(DATA_DIR) / 'qazaq_pdd.sqlite3'), check_same_thread=False)
else:
    DB = sqlite3.connect(':memory:', check_same_thread=False)
DB.executescript('''
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, lang TEXT, first_seen INTEGER, last_seen INTEGER, daily INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS payments (charge_id TEXT PRIMARY KEY, user_id INTEGER, stars INTEGER, days INTEGER, ts INTEGER, refunded INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS results (user_id INTEGER, ts INTEGER, mode TEXT, cat TEXT, score INTEGER, total INTEGER);
CREATE TABLE IF NOT EXISTS ai_cache (key TEXT PRIMARY KEY, text TEXT);
CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
''')


def db(sql, args=(), one=False, commit=False):
    with _db_lock:
        cur = DB.execute(sql, args)
        rows = cur.fetchall()
        if commit:
            DB.commit()
    return (rows[0] if rows else None) if one else rows


def touch_user(uid, lang=None):
    now = int(time.time())
    db('INSERT INTO users(id, lang, first_seen, last_seen) VALUES(?,?,?,?) '
       'ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen, lang=COALESCE(excluded.lang, users.lang)',
       (uid, lang, now, now), commit=True)


def record_payment(charge_id, uid, stars, days, ts=None):
    db('INSERT OR IGNORE INTO payments(charge_id, user_id, stars, days, ts) VALUES(?,?,?,?,?)',
       (charge_id, uid, stars, days, ts or int(time.time())), commit=True)


def entitlement(uid):
    if uid in ADMIN_IDS:
        return {'paid': True, 'until': None, 'admin': True}
    rows = db('SELECT days, ts FROM payments WHERE user_id=? AND refunded=0', (uid,))
    until = 0
    for days, ts in rows:
        if days <= 0:
            return {'paid': True, 'until': None, 'admin': False}
        until = max(until, ts + days * 86400)
    if until > time.time():
        return {'paid': True, 'until': until, 'admin': False}
    return {'paid': False, 'until': until or None, 'admin': False}


# ====================================================================== Telegram API
def tg(method, data=None, timeout=40):
    req = Request(f'{API_BASE}/bot{BOT_TOKEN}/{method}', data=json.dumps(data or {}).encode(),
                  headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urlopen(req, timeout=timeout) as r:
            body = json.load(r)
    except HTTPError as e:
        try:
            body = json.load(e)
        except ValueError:
            body = {'ok': False, 'description': f'HTTP {e.code}'}
    if not body.get('ok'):
        raise RuntimeError(f"{method}: {body.get('description', 'қате')}")
    return body.get('result')


def is_https(u):
    try:
        p = urlparse(u)
        return p.scheme == 'https' and bool(p.netloc)
    except ValueError:
        return False


# ====================================================================== bot texts
def L(lang):
    return 'ru' if (lang or '').startswith('ru') else 'kk'


def plan_text(lang):
    if PLAN_DAYS <= 0:
        return 'мерзімсіз' if lang == 'kk' else 'бессрочно'
    return f'{PLAN_DAYS} күнге' if lang == 'kk' else f'на {PLAN_DAYS} дн.'


TEXT = {
    'kk': {
        'open': '🚦 Тестті ашу',
        'welcome': ('🚘 QAZAQ PDD — Қазақстан жол жүрісі қағидалары бойынша емтихан тренажері.\n\n'
                    '• 40 сұрақ, 40 минут, өту шегі — 32 (ресми форматпен)\n'
                    '• Тақырып бойынша жаттығу, қателермен жұмыс, марафон\n'
                    '• Әр сұраққа түсіндірме және ЖЖҚ тармағына сілтеме\n'
                    '• Қазақ және орыс тілдерінде\n\n'
                    'Тегін нұсқамен бастаңыз 👇'),
        'help': ('ℹ️ Командалар:\n/start — тестті ашу\n/daily — күнделікті сұрақты қосу/өшіру\n'
                 '/terms — пайдалану шарттары\n/paysupport — төлем бойынша көмек\n\n'
                 'Бұл оқу тренажері, ресми спецЦОН жүйесі емес.'),
        'other': 'Тестті ашу үшін төмендегі батырманы басыңыз 👇',
        'paid': '✅ Төлем қабылданды! Толық нұсқа ашылды ({plan}). Mini App-ты қайта ашыңыз.',
        'daily_on': '✅ Күнделікті сұрақ қосылды. Әр күні кешке бір сұрақ жіберемін. Өшіру: /daily',
        'daily_off': '🔕 Күнделікті сұрақ өшірілді. Қосу: /daily',
        'terms': ('📄 Пайдалану шарттары (қысқаша)\n\n'
                  '1. QAZAQ PDD — жол жүрісі қағидаларын оқуға арналған тренажер. Ресми емтихан жүйесі емес, емтиханнан өтуге кепілдік бермейді.\n'
                  '2. Толық нұсқа Telegram Stars арқылы төленеді: {price} ⭐, {plan}.\n'
                  '3. Сақталатын деректер: Telegram ID, тіл және төлем жазбалары. Оқу прогресі Telegram бұлтында сақталады.\n'
                  '4. Төлем бойынша сұрақтар: /paysupport'),
        'support': '💬 Төлем бойынша көмек: {contact}\nХабарламаға төлем күнін және Telegram ID-іңізді жазыңыз: {uid}',
        'support_none': 'осы ботқа хабарлама жазыңыз — әкімші жауап береді',
    },
    'ru': {
        'open': '🚦 Открыть тест',
        'welcome': ('🚘 QAZAQ PDD — тренажёр экзамена по Правилам дорожного движения РК.\n\n'
                    '• 40 вопросов, 40 минут, проходной балл — 32 (как на официальном экзамене)\n'
                    '• Тренировка по темам, работа над ошибками, марафон\n'
                    '• Пояснение к каждому вопросу и ссылка на пункт ПДД\n'
                    '• На казахском и русском языках\n\n'
                    'Начните с бесплатной версии 👇'),
        'help': ('ℹ️ Команды:\n/start — открыть тест\n/daily — включить/выключить вопрос дня\n'
                 '/terms — условия использования\n/paysupport — помощь по оплате\n\n'
                 'Это учебный тренажёр, а не официальная система спецЦОН.'),
        'other': 'Нажмите кнопку ниже, чтобы открыть тест 👇',
        'paid': '✅ Оплата получена! Полная версия открыта ({plan}). Откройте Mini App заново.',
        'daily_on': '✅ Вопрос дня включён. Каждый вечер буду присылать один вопрос. Выключить: /daily',
        'daily_off': '🔕 Вопрос дня выключен. Включить: /daily',
        'terms': ('📄 Условия использования (кратко)\n\n'
                  '1. QAZAQ PDD — тренажёр для изучения ПДД. Это не официальная экзаменационная система и не гарантия сдачи экзамена.\n'
                  '2. Полная версия оплачивается через Telegram Stars: {price} ⭐, {plan}.\n'
                  '3. Хранятся: Telegram ID, язык и записи об оплате. Прогресс обучения хранится в облаке Telegram.\n'
                  '4. Вопросы по оплате: /paysupport'),
        'support': '💬 Помощь по оплате: {contact}\nУкажите в сообщении дату оплаты и ваш Telegram ID: {uid}',
        'support_none': 'напишите сообщение этому боту — администратор ответит',
    },
}


def open_markup(lang):
    if not is_https(MINI_APP_URL):
        return None
    return {'inline_keyboard': [[{'text': TEXT[lang]['open'], 'web_app': {'url': MINI_APP_URL + '/'}}]]}


def msg(chat_id, text, lang=None, button=True):
    out = {'method': 'sendMessage', 'chat_id': chat_id, 'text': text}
    if button and lang:
        mk = open_markup(lang)
        if mk:
            out['reply_markup'] = mk
    return out


def parse_payload(p):
    """plan:<uid>:<days>:<nonce>"""
    parts = (p or '').split(':')
    if len(parts) != 4 or parts[0] != 'plan':
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


def handle_update(update):
    """Telegram жаңартуы → бір әдіс (webhook жауабында қайтарылады) немесе None."""
    pcq = update.get('pre_checkout_query')
    if pcq:
        pl = parse_payload(pcq.get('invoice_payload'))
        ok = bool(pl) and pl[0] == (pcq.get('from') or {}).get('id') and pcq.get('currency') == 'XTR'
        ans = {'method': 'answerPreCheckoutQuery', 'pre_checkout_query_id': pcq['id'], 'ok': ok}
        if not ok:
            ans['error_message'] = 'Төлем деректері сәйкес келмейді / Неверные данные платежа'
        return ans
    m = update.get('message') or {}
    chat = m.get('chat') or {}
    frm = m.get('from') or {}
    if not chat.get('id'):
        return None
    lang = L(frm.get('language_code'))
    sp = m.get('successful_payment')
    if sp:
        pl = parse_payload(sp.get('invoice_payload'))
        if pl and sp.get('currency') == 'XTR':
            record_payment(sp['telegram_payment_charge_id'], pl[0], sp.get('total_amount', 0), pl[1])
            log('Төлем қабылданды:', pl[0], sp.get('total_amount'), '⭐')
            return msg(chat['id'], TEXT[lang]['paid'].format(plan=plan_text(lang)), lang)
        return None
    if chat.get('type') != 'private':
        return None
    uid = frm.get('id')
    touch_user(uid, lang)
    text = (m.get('text') or '').strip()
    cmd = text.split()[0].split('@')[0].lower() if text.startswith('/') else ''
    args = text.split()[1:]
    t = TEXT[lang]
    if cmd in ('/start', '/exam', '/test', '/pdd') or not text:
        return msg(chat['id'], t['welcome'], lang)
    if cmd == '/help':
        return msg(chat['id'], t['help'], lang)
    if cmd == '/terms':
        return msg(chat['id'], t['terms'].format(price=PRICE_STARS, plan=plan_text(lang)), lang, button=False)
    if cmd == '/paysupport':
        return msg(chat['id'], t['support'].format(contact=SUPPORT or t['support_none'], uid=uid), lang, button=False)
    if cmd == '/daily':
        row = db('SELECT daily FROM users WHERE id=?', (uid,), one=True)
        new = 0 if (row and row[0]) else 1
        db('UPDATE users SET daily=? WHERE id=?', (new, uid), commit=True)
        return msg(chat['id'], t['daily_on'] if new else t['daily_off'], lang, button=False)
    if cmd == '/stats' and uid in ADMIN_IDS:
        users = db('SELECT COUNT(*) FROM users', one=True)[0]
        pays = db('SELECT COUNT(DISTINCT user_id), COALESCE(SUM(stars),0) FROM payments WHERE refunded=0', one=True)
        week = db('SELECT COUNT(*) FROM results WHERE ts>?', (int(time.time()) - 7 * 86400,), one=True)[0]
        daily = db('SELECT COUNT(*) FROM users WHERE daily=1', one=True)[0]
        return msg(chat['id'], f'📊 Пайдаланушылар: {users}\n💳 Төлегендер: {pays[0]} ({pays[1]} ⭐)\n'
                               f'📝 7 күндегі тест: {week}\n📩 Күнделікті сұрақ: {daily}\n'
                               f'💾 Деректер: {"тұрақты" if DATA_DIR else "тек жадта"}', button=False)
    if cmd == '/refund' and uid in ADMIN_IDS:
        if len(args) != 2 or not args[0].isdigit():
            return msg(chat['id'], 'Қолданылуы: /refund <user_id> <charge_id>', button=False)
        try:
            tg('refundStarPayment', {'user_id': int(args[0]), 'telegram_payment_charge_id': args[1]})
            db('UPDATE payments SET refunded=1 WHERE charge_id=?', (args[1],), commit=True)
            return msg(chat['id'], '✅ Қайтарылды', button=False)
        except Exception as e:  # noqa: BLE001
            return msg(chat['id'], f'Қате: {e}', button=False)
    return msg(chat['id'], t['other'], lang)


# ====================================================================== setup / payments sync
def sync_payments():
    """Төлемдерді Telegram-ның өзінен қалпына келтіру (база өшіп қалса да төлем жоғалмайды)."""
    offset, seen, refunds = 0, 0, []
    while True:
        res = tg('getStarTransactions', {'offset': offset, 'limit': 100}) or {}
        txs = res.get('transactions', [])
        for t in txs:
            src, rcv = t.get('source') or {}, t.get('receiver') or {}
            if src.get('type') == 'user':
                pl = parse_payload(src.get('invoice_payload'))
                if pl:
                    record_payment(t['id'], pl[0], t.get('amount', 0), pl[1], t.get('date'))
                    seen += 1
            elif rcv.get('type') == 'user':
                refunds.append(t['id'])
        if len(txs) < 100:
            break
        offset += 100
    for rid in refunds:
        db('UPDATE payments SET refunded=1 WHERE charge_id=?', (rid,), commit=True)
    STATE['payments_synced'] = True
    log(f'Telegram-нан төлемдер қалпына келтірілді: {seen}, қайтарылғаны: {len(refunds)}')


def configure_bot():
    me = tg('getMe')
    STATE['bot'] = '@' + me.get('username', '')
    log('Бот:', STATE['bot'])
    allowed = ['message', 'pre_checkout_query']
    if STATE['mode'] == 'webhook':
        tg('setWebhook', {'url': SELF_URL + WEBHOOK_PATH, 'secret_token': WEBHOOK_SECRET,
                          'allowed_updates': allowed, 'max_connections': 40})
        STATE['webhook'] = True
        log('Webhook орнатылды.')
    else:
        tg('deleteWebhook', {'drop_pending_updates': False})
    if is_https(MINI_APP_URL):
        tg('setChatMenuButton', {'menu_button': {'type': 'web_app', 'text': '🚦 ПДД тест',
                                                 'web_app': {'url': MINI_APP_URL + '/'}}})
        STATE['menu_button'] = True
    for lang_code, lang in ((None, 'kk'), ('ru', 'ru')):
        cmds = [
            {'command': 'start', 'description': 'Тестті ашу' if lang == 'kk' else 'Открыть тест'},
            {'command': 'daily', 'description': 'Күнделікті сұрақ' if lang == 'kk' else 'Вопрос дня'},
            {'command': 'terms', 'description': 'Пайдалану шарттары' if lang == 'kk' else 'Условия'},
            {'command': 'paysupport', 'description': 'Төлем бойынша көмек' if lang == 'kk' else 'Помощь по оплате'},
            {'command': 'help', 'description': 'Көмек' if lang == 'kk' else 'Помощь'},
        ]
        body = {'commands': cmds}
        if lang_code:
            body['language_code'] = lang_code
        tg('setMyCommands', body)
    STATE['commands'] = True
    for method, field, kk, ru in (
        ('setMyDescription', 'description',
         'Қазақстан ПДД емтиханына дайындық: 260+ сұрақ, 40 сұрақ / 40 минут, тақырыптар, қателермен жұмыс, ЖЖҚ сілтемелері. Қазақша және орысша.',
         'Подготовка к экзамену ПДД РК: 260+ вопросов, 40 вопросов / 40 минут, темы, работа над ошибками, ссылки на ПДД. На казахском и русском.'),
        ('setMyShortDescription', 'short_description',
         'ПДД емтихан тренажері: 40 сұрақ, 40 минут, B / C1 / C.', 'Тренажёр ПДД РК: 40 вопросов, 40 минут, B / C1 / C.'),
    ):
        try:
            tg(method, {field: kk})
            tg(method, {field: ru, 'language_code': 'ru'})
        except Exception as e:  # noqa: BLE001
            log('Сипаттама:', e)
    try:
        sync_payments()
    except Exception as e:  # noqa: BLE001
        log('Төлемдерді қалпына келтіру мүмкін болмады:', e)
    STATE['last_error'] = None
    log('Бот толық бапталды ✓')


def setup_loop():
    delay = 3
    while True:
        try:
            configure_bot()
            return
        except Exception as e:  # noqa: BLE001
            STATE['last_error'] = str(e)
            log('Баптау қатесі:', e)
            if 'Unauthorized' in str(e) or 'Not Found' in str(e):
                delay = 300
            time.sleep(delay)
            delay = min(delay * 2, 300)


def polling_loop():
    offset = None
    while True:
        try:
            ups = tg('getUpdates', {'offset': offset, 'timeout': 25, 'allowed_updates': ['message', 'pre_checkout_query']}, 40)
            for u in ups or []:
                offset = u['update_id'] + 1
                r = handle_update(u)
                if r:
                    method = r.pop('method')
                    tg(method, r)
                    STATE['updates_handled'] += 1
        except Exception as e:  # noqa: BLE001
            STATE['last_error'] = str(e)
            log('Polling қатесі:', e)
            time.sleep(5)


# ====================================================================== daily quiz
def send_daily(force=False):
    today = datetime.now(ALMATY).strftime('%Y-%m-%d')
    row = db('SELECT v FROM kv WHERE k=?', ('daily',), one=True)
    if row and row[0] == today and not force:
        return 0
    db('INSERT OR REPLACE INTO kv(k, v) VALUES(?, ?)', ('daily', today), commit=True)
    users = db('SELECT id, lang FROM users WHERE daily=1')
    cands = [q for q in Q.values() if q.get('poll')]
    if not users or not cands:
        return 0
    rnd = random.Random(today)
    q = rnd.choice(cands)
    sent = 0
    for uid, lang in users:
        lang = L(lang)
        d = q[lang]
        order = list(range(4))
        rnd.shuffle(order)
        head = '📅 Күн сұрағы' if lang == 'kk' else '📅 Вопрос дня'
        body = {'chat_id': uid, 'question': f'{head}: {d["text"]}'[:300], 'options': [d['options'][i] for i in order],
                'type': 'quiz', 'correct_option_id': order.index(0), 'is_anonymous': False,
                'explanation': (d['why'] + (f' ({d["ref"]})' if d.get('ref') else ''))[:200]}
        if len(body['question']) > 300:
            continue
        try:
            tg('sendPoll', body, 15)
            sent += 1
        except Exception as e:  # noqa: BLE001
            if 'blocked' in str(e) or 'chat not found' in str(e) or 'deactivated' in str(e):
                db('UPDATE users SET daily=0 WHERE id=?', (uid,), commit=True)
        time.sleep(0.05)
    log(f'Күн сұрағы жіберілді: {sent}')
    return sent


def daily_loop():
    while True:
        try:
            now = datetime.now(ALMATY)
            if now.hour == DAILY_HOUR:
                send_daily()
        except Exception as e:  # noqa: BLE001
            log('Күн сұрағы қатесі:', e)
        time.sleep(60)


# ====================================================================== auth
def check_init_data(init_data):
    """Telegram Mini App initData тексеру (HMAC-SHA256)."""
    if not init_data or not BOT_TOKEN:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=True))
    except ValueError:
        return None
    got = pairs.pop('hash', '')
    if not got:
        return None
    key = hmac.new(b'WebAppData', BOT_TOKEN.encode(), hashlib.sha256).digest()
    variants = [pairs]
    if 'signature' in pairs:
        variants.append({k: v for k, v in pairs.items() if k != 'signature'})
    for fields in variants:
        check = '\n'.join(f'{k}={v}' for k, v in sorted(fields.items()))
        if hmac.compare_digest(hmac.new(key, check.encode(), hashlib.sha256).hexdigest(), got):
            break
    else:
        return None
    try:
        if time.time() - int(pairs.get('auth_date', '0')) > 7 * 86400:
            return None
        user = json.loads(pairs.get('user', '{}'))
    except ValueError:
        return None
    return user if user.get('id') else None


def sign(obj):
    raw = base64.urlsafe_b64encode(json.dumps(obj, separators=(',', ':')).encode()).decode().rstrip('=')
    mac = hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()[:32]
    return f'{raw}.{mac}'


def unsign(tok):
    try:
        raw, mac = tok.rsplit('.', 1)
        if not hmac.compare_digest(hmac.new(SECRET, raw.encode(), hashlib.sha256).hexdigest()[:32], mac):
            return None
        return json.loads(base64.urlsafe_b64decode(raw + '=' * (-len(raw) % 4)))
    except (ValueError, TypeError):
        return None


# ====================================================================== API logic
_rate = defaultdict(list)
_ai_used = defaultdict(int)


def rate_ok(uid, limit=240):
    now = time.time()
    lst = [t for t in _rate[uid] if now - t < 60]
    lst.append(now)
    _rate[uid] = lst
    return len(lst) <= limit


def present(q, perm, lang):
    d = q[lang]
    return {'id': q['id'], 'topic': q['topic'], 'image': q['image'], 'text': d['text'],
            'options': [d['options'][i] for i in perm]}


def draw(items, n, recent):
    fresh = [q for q in items if q['id'] not in recent]
    old = [q for q in items if q['id'] in recent]
    random.shuffle(fresh)
    random.shuffle(old)
    return (fresh + old)[:n]


def assemble_exam(cat, free_only, recent):
    if cat == 'B':
        parts = [(pool('g', True, free_only), 20), (pool('g', False, free_only), 20)]
    else:
        parts = [(pool('g', True, free_only), 16), (pool('g', False, free_only), 16),
                 (pool('c', True, free_only), 4), (pool('c', False, free_only), 4)]
    chosen = []
    for items, n in parts:
        chosen += draw(items, n, recent)
    random.shuffle(chosen)
    return chosen


def perm4():
    p = [0, 1, 2, 3]
    random.shuffle(p)
    return p


def api_me(user, body):
    lang = L(body.get('lang') or user.get('language_code'))
    ent = entitlement(user['id'])
    by_topic = {}
    for q in Q.values():
        t = by_topic.setdefault(q['topic'], {'key': q['topic'], 'kk': TOPICS[q['topic']]['kk'], 'ru': TOPICS[q['topic']]['ru'],
                                             'total': 0, 'free': 0, 'g': 0, 'c': 0, 'free_g': 0, 'free_c': 0})
        t['total'] += 1
        t['free'] += q['free']
        t[q['cat']] += 1
        t['free_' + q['cat']] += q['free']
    row = db('SELECT daily FROM users WHERE id=?', (user['id'],), one=True)
    return {
        'user': {'id': user['id'], 'name': user.get('first_name', '')},
        'access': ent, 'price': {'stars': PRICE_STARS, 'days': PLAN_DAYS},
        'bank': {'total': len(Q), 'free': sum(q['free'] for q in Q.values()),
                 'free_g': sum(q['free'] for q in pool('g')),
                 'g': len(pool('g')), 'c': len(pool('c')), 'topics': list(by_topic.values())},
        'exam': {'count': EXAM_COUNT, 'minutes': EXAM_MINUTES, 'pass': PASS_SCORE},
        'ai': bool(AI_KEY), 'daily': bool(row and row[0]), 'bot': (STATE['bot'] or '').lstrip('@') or None, 'lang': lang,
    }


def api_exam_start(user, body):
    lang = L(body.get('lang'))
    cat = 'B' if body.get('cat') == 'B' else 'BC'
    ent = entitlement(user['id'])
    recent = set(body.get('recent') or [])
    qs = assemble_exam(cat, not ent['paid'], recent)
    if len(qs) != EXAM_COUNT:
        return 500, {'error': 'not_enough_questions'}
    perms = [perm4() for _ in qs]
    started = int(time.time())
    tok = sign({'u': user['id'], 'k': 'exam', 'c': cat, 't': started, 'q': [[q['id'], ''.join(map(str, p))] for q, p in zip(qs, perms)]})
    return 200, {'token': tok, 'started': started, 'deadline': started + EXAM_MINUTES * 60, 'cat': cat, 'free': not ent['paid'],
                 'questions': [present(q, p, lang) for q, p in zip(qs, perms)]}


def explain_item(q, perm, lang):
    d = q[lang]
    return {'id': q['id'], 'correct': perm.index(0), 'why': d['why'], 'ref': d.get('ref', '')}


def api_exam_finish(user, body):
    lang = L(body.get('lang'))
    data = unsign(body.get('token', ''))
    if not data or data.get('u') != user['id'] or data.get('k') != 'exam':
        return 403, {'error': 'bad_token'}
    answers = body.get('answers') or []
    items, score = [], 0
    for i, (qid, ps) in enumerate(data['q']):
        q = Q.get(qid)
        if not q:
            continue
        perm = [int(c) for c in ps]
        it = explain_item(q, perm, lang)
        a = answers[i] if i < len(answers) else None
        it['answer'] = a if isinstance(a, int) and 0 <= a < 4 else None
        if it['answer'] is not None and it['answer'] == it['correct']:
            score += 1
        items.append(it)
    elapsed = min(EXAM_MINUTES * 60, max(0, int(time.time()) - int(data['t'])))
    db('INSERT INTO results(user_id, ts, mode, cat, score, total) VALUES(?,?,?,?,?,?)',
       (user['id'], int(time.time()), 'exam', data['c'], score, len(items)), commit=True)
    return 200, {'score': score, 'total': len(items), 'passed': score >= PASS_SCORE, 'elapsed': elapsed, 'items': items}


def api_practice(user, body):
    lang = L(body.get('lang'))
    ent = entitlement(user['id'])
    mode = body.get('mode')
    cat = body.get('cat') if body.get('cat') in ('g', 'c') else None
    free_only = not ent['paid']
    if mode == 'topic':
        items = pool(None, None, free_only, body.get('topic'))
        if cat == 'g':
            items = [q for q in items if q['cat'] == 'g']
        random.shuffle(items)
    elif mode == 'list':
        ids = [i for i in (body.get('ids') or []) if isinstance(i, str)][:400]
        items = [Q[i] for i in ids if i in Q and (Q[i]['free'] or not free_only)]
    else:  # marathon
        items = pool(cat, None, free_only)
        random.shuffle(items)
    items = items[:int(body.get('limit') or 400)]
    perms = [perm4() for _ in items]
    tok = sign({'u': user['id'], 'k': 'prac', 't': int(time.time()), 'q': [[q['id'], ''.join(map(str, p))] for q, p in zip(items, perms)]})
    return 200, {'token': tok, 'free': free_only, 'locked': (not ent['paid']) and mode != 'list',
                 'questions': [present(q, p, lang) for q, p in zip(items, perms)]}


def token_question(user, body):
    data = unsign(body.get('token', ''))
    if not data or data.get('u') != user['id']:
        return None, None
    for qid, ps in data['q']:
        if qid == body.get('qid') and qid in Q:
            return Q[qid], [int(c) for c in ps]
    return None, None


def api_check(user, body):
    q, perm = token_question(user, body)
    if not q:
        return 403, {'error': 'bad_token'}
    lang = L(body.get('lang'))
    it = explain_item(q, perm, lang)
    choice = body.get('choice')
    it['ok'] = choice == it['correct']
    return 200, it


def ai_explain(q, choice_orig, lang):
    key = f'{q["id"]}:{choice_orig}:{lang}'
    row = db('SELECT text FROM ai_cache WHERE key=?', (key,), one=True)
    if row:
        return row[0]
    d = q[lang]
    opts = '\n'.join(f'{"✓" if i == 0 else "✗"} {o}' for i, o in enumerate(d['options']))
    chosen = d['options'][choice_orig] if isinstance(choice_orig, int) and 0 <= choice_orig < 4 else '—'
    if lang == 'kk':
        system = ('Сен Қазақстан Республикасының Жол жүрісі қағидалары (ІІМ 2023 ж. №534 бұйрығы) бойынша тәжірибелі нұсқаушысың. '
                  'Емтиханға дайындалып жүрген адамға қазақ тілінде қарапайым, нақты түсіндіресің. Markdown қолданба. 4–6 сөйлем.')
        user_msg = (f'Сұрақ: {d["text"]}\nНұсқалар:\n{opts}\nОқушы таңдаған жауап: {chosen}\n'
                    f'Ресми түсіндірме: {d["why"]}\nЕреже сілтемесі: {d.get("ref") or "жоқ"}\n\n'
                    'Неліктен дұрыс жауап дұрыс, ал таңдалған жауап неге қате екенін түсіндір, өмірлік мысал келтір. '
                    'Ережеде жоқ сандарды ойдан шығарма.')
    else:
        system = ('Ты опытный инструктор по Правилам дорожного движения Республики Казахстан (приказ МВД 2023 г. №534). '
                  'Объясняй на русском языке просто и по делу человеку, который готовится к экзамену. Без Markdown. 4–6 предложений.')
        user_msg = (f'Вопрос: {d["text"]}\nВарианты:\n{opts}\nОтвет ученика: {chosen}\n'
                    f'Официальное пояснение: {d["why"]}\nСсылка на ПДД: {d.get("ref") or "нет"}\n\n'
                    'Объясни, почему правильный ответ верен, а выбранный — нет, приведи жизненный пример. Не выдумывай цифры, которых нет в правилах.')
    req = Request(f'{AI_BASE}/v1/messages', data=json.dumps({
        'model': AI_MODEL, 'max_tokens': 500, 'system': system,
        'messages': [{'role': 'user', 'content': user_msg}]}).encode(),
        headers={'x-api-key': AI_KEY, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'})
    with urlopen(req, timeout=40) as r:
        res = json.load(r)
    text = ''.join(b.get('text', '') for b in res.get('content', []) if b.get('type') == 'text').strip()
    if text:
        db('INSERT OR REPLACE INTO ai_cache(key, text) VALUES(?,?)', (key, text), commit=True)
    return text


def api_explain(user, body):
    if not AI_KEY:
        return 404, {'error': 'ai_off'}
    if not entitlement(user['id'])['paid']:
        return 402, {'error': 'paid_only'}
    q, perm = token_question(user, body)
    if not q:
        return 403, {'error': 'bad_token'}
    day_key = (user['id'], time.strftime('%Y-%m-%d'))
    if _ai_used[day_key] >= AI_DAILY_LIMIT and user['id'] not in ADMIN_IDS:
        return 429, {'error': 'ai_limit'}
    choice = body.get('choice')
    choice_orig = perm[choice] if isinstance(choice, int) and 0 <= choice < 4 else None
    try:
        text = ai_explain(q, choice_orig, L(body.get('lang')))
    except Exception as e:  # noqa: BLE001
        log('AI қатесі:', e)
        return 502, {'error': 'ai_failed'}
    _ai_used[day_key] += 1
    return 200, {'text': text}


def api_invoice(user, body):
    if not BOT_TOKEN:
        return 503, {'error': 'no_bot'}
    lang = L(body.get('lang'))
    title = 'QAZAQ PDD — толық нұсқа' if lang == 'kk' else 'QAZAQ PDD — полная версия'
    desc = (f'{len(Q)} сұрақ, барлық режимдер, тақырыптар, қателермен жұмыс — {plan_text(lang)}' if lang == 'kk'
            else f'{len(Q)} вопросов, все режимы, темы, работа над ошибками — {plan_text(lang)}')
    link = tg('createInvoiceLink', {'title': title, 'description': desc[:255],
                                    'payload': f'plan:{user["id"]}:{PLAN_DAYS}:{secrets.token_hex(4)}',
                                    'currency': 'XTR', 'prices': [{'label': title, 'amount': PRICE_STARS}]})
    return 200, {'link': link}


def api_daily(user, body):
    on = 1 if body.get('on') else 0
    db('UPDATE users SET daily=? WHERE id=?', (on, user['id']), commit=True)
    return 200, {'daily': bool(on)}


API = {'/api/me': api_me, '/api/exam/start': api_exam_start, '/api/exam/finish': api_exam_finish,
       '/api/practice': api_practice, '/api/check': api_check, '/api/explain': api_explain,
       '/api/invoice': api_invoice, '/api/daily': api_daily}


def api_user(body, headers):
    init = body.get('initData') or headers.get('X-Init-Data', '')
    user = check_init_data(init)
    if not user and DEV_AUTH:
        uid = int(headers.get('X-Dev-User', '1') or 1)
        user = {'id': uid, 'first_name': 'Dev', 'language_code': 'kk'}
    return user


def allowed_origin(origin):
    if not origin:
        return None
    if DEV_AUTH:
        return origin
    ok = {f'{urlparse(u).scheme}://{urlparse(u).netloc}' for u in (MINI_APP_URL, SELF_URL) if u}
    return origin if origin in ok else None


# ====================================================================== HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = 'QazaqPDD/2.0'

    def log_message(self, fmt, *args):
        path = self.path.split('?')[0]
        if not path.startswith('/tg/'):
            sys.stderr.write('%s %s\n' % (self.command, path))

    def _send(self, code, body=b'', ctype='text/plain; charset=utf-8', extra=None, head=False):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        ao = allowed_origin(self.headers.get('Origin'))
        if ao:
            self.send_header('Access-Control-Allow-Origin', ao)
            self.send_header('Vary', 'Origin')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if not head:
            self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), 'application/json; charset=utf-8', {'Cache-Control': 'no-store'})

    def _static(self, head=False):
        raw = unquote(urlparse(self.path).path)
        if raw in ('', '/'):
            raw = '/index.html'
        target = (WEBAPP / raw.lstrip('/')).resolve()
        if WEBAPP not in target.parents or not target.is_file():
            return self._send(404, b'Not found', head=head)
        ctype = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/javascript', 'image/svg+xml'):
            ctype += '; charset=utf-8'
        cache = 'no-cache' if target.suffix in ('.html', '.js', '.css') else 'public, max-age=86400'
        self._send(200, target.read_bytes(), ctype, {'Cache-Control': cache}, head=head)

    def do_OPTIONS(self):
        self._send(204, b'', extra={'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
                                    'Access-Control-Allow-Headers': 'Content-Type, X-Init-Data, X-Dev-User',
                                    'Access-Control-Max-Age': '86400'})

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_GET(self, head=False):
        path = urlparse(self.path).path
        if path == '/health':
            return self._send(200, b'ok', head=head)
        if path == '/status':
            return self._send(200, json.dumps(STATE, ensure_ascii=False, indent=2).encode(),
                              'application/json; charset=utf-8', {'Cache-Control': 'no-store'}, head=head)
        return self._static(head=head)

    def _read_json(self, limit=200_000):
        try:
            n = min(int(self.headers.get('Content-Length', '0')), limit)
            data = json.loads(self.rfile.read(n) or b'{}')
            return data if isinstance(data, dict) else {}
        except ValueError:
            return None

    def do_POST(self):
        path = urlparse(self.path).path
        if path == WEBHOOK_PATH and BOT_TOKEN:
            if not hmac.compare_digest(self.headers.get('X-Telegram-Bot-Api-Secret-Token', ''), WEBHOOK_SECRET):
                return self._send(403, b'Forbidden')
            update = self._read_json(1_000_000)
            if update is None:
                return self._send(400, b'Bad request')
            try:
                reply = handle_update(update)
            except Exception as e:  # noqa: BLE001
                log('Жаңартуды өңдеу қатесі:', e)
                reply = None
            if not reply:
                return self._send(200, b'')
            STATE['updates_handled'] += 1
            return self._send(200, json.dumps(reply, ensure_ascii=False).encode(), 'application/json; charset=utf-8')
        fn = API.get(path)
        if not fn:
            return self._send(404, b'Not found')
        body = self._read_json()
        if body is None:
            return self._json(400, {'error': 'bad_json'})
        user = api_user(body, self.headers)
        if not user:
            return self._json(401, {'error': 'auth'})
        if not rate_ok(user['id']):
            return self._json(429, {'error': 'rate'})
        try:
            touch_user(user['id'], L(user.get('language_code')))
            res = fn(user, body)
            code, obj = res if isinstance(res, tuple) else (200, res)
        except Exception as e:  # noqa: BLE001
            log('API қатесі', path, e)
            code, obj = 500, {'error': 'server'}
        self._json(code, obj)


def main():
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('image/svg+xml', '.svg')
    if not BOT_TOKEN:
        log('BOT_TOKEN орнатылмаған — тек Mini App беттері жұмыс істейді.')
    elif is_https(SELF_URL):
        STATE['mode'] = 'webhook'
        threading.Thread(target=setup_loop, daemon=True).start()
    else:
        STATE['mode'] = 'polling'

        def _poll():
            setup_loop()
            polling_loop()
        threading.Thread(target=_poll, daemon=True).start()
    if BOT_TOKEN and DAILY_ON:
        threading.Thread(target=daily_loop, daemon=True).start()
    if DEV_AUTH:
        log('⚠️  DEV_AUTH қосулы — тек тест үшін!')
    httpd = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    log(f'Сервер: порт {PORT}, режим {STATE["mode"]}, сұрақ {len(Q)}, баға {PRICE_STARS}⭐, '
        f'мерзім {"шексіз" if PLAN_DAYS <= 0 else str(PLAN_DAYS) + " күн"}, база {"тұрақты" if DATA_DIR else "жадта"}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
