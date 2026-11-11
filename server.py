#!/usr/bin/env python3
"""QAZAQ PDD — Telegram бот + Mini App сервері.

Тек стандартты Python кітапханасы қолданылады (pip install қажет емес).

Жалғыз міндетті баптау — BOT_TOKEN орта айнымалысы (@BotFather берген токен).
Сервер іске қосылғанда өзі:
  * Mini App беттерін HTTPS арқылы таратады (Render сияқты хостингте);
  * Telegram webhook-ты орнатады;
  * ботқа "🚦 ПДД емтиханы" мәзір батырмасын қосады;
  * /start, /help командаларын және бот сипаттамасын баптайды.

Қосымша орта айнымалылары (міндетті емес):
  MINI_APP_URL  — Mini App адресі (бөлек статикалық сайт болса). Әдепкі: осы сервердің адресі.
  PUBLIC_URL    — осы сервердің ашық HTTPS адресі. Render-де RENDER_EXTERNAL_URL автоматты алынады.
  PORT          — тыңдайтын порт (Render өзі береді).

Ашық HTTPS адрес табылмаса (мысалы, үй компьютерінде), бот long polling режимінде жұмыс
істейді; бұл жағдайда MINI_APP_URL міндетті түрде HTTPS болуы керек.
"""
import hashlib
import hmac
import json
import mimetypes
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
WEBAPP = ROOT / 'webapp'

BOT_TOKEN = os.getenv('BOT_TOKEN', '').strip()
PORT = int(os.getenv('PORT', '8000'))
SELF_URL = (os.getenv('PUBLIC_URL') or os.getenv('RENDER_EXTERNAL_URL') or '').strip().rstrip('/')
MINI_APP_URL = (os.getenv('MINI_APP_URL') or SELF_URL).strip().rstrip('/')
API_BASE = os.getenv('TELEGRAM_API_BASE', 'https://api.telegram.org').rstrip('/')

MENU_TEXT = '🚦 ПДД емтиханы'
OPEN_TEXT = '🚦 Емтиханды ашу'
WELCOME = (
    '🚘 QAZAQ PDD — Қазақстан жол ережелері бойынша емтихан тренажері.\n\n'
    '40 сұрақ • 40 минут • өту шегі 32 • B, C1, C санаттары.\n'
    'Әр жолы жаңа сұрақтар, суретті жағдайлар, соңында толық талдау.\n\n'
    'Бастау үшін төмендегі батырманы басыңыз 👇'
)
HELP = (
    'ℹ️ Қалай пайдалану керек:\n'
    '1. «Емтиханды ашу» батырмасын немесе төменгі мәзірдегі «ПДД емтиханы»-н басыңыз.\n'
    '2. Санатты таңдаңыз: B немесе B + C1/C.\n'
    '3. 40 минут ішінде 40 сұраққа жауап беріңіз.\n'
    '4. Дұрыс/қате жауаптар емтихан соңында көрсетіледі.\n\n'
    'Бұл оқу тренажері, ресми СпецЦОН жүйесі емес.'
)
DESCRIPTION = (
    'Қазақстан ПДД емтиханына дайындық: B, C1, C санаттары. '
    '40 сұрақ, 40 минут, суретті жағдайлар және әр қатеге түсіндірме. '
    'Бастау үшін /start басыңыз.'
)
SHORT_DESCRIPTION = 'ПДД емтихан тренажері: 40 сұрақ, 40 минут, B / C1 / C санаттары.'

STATE = {
    'mode': 'off',          # webhook | polling | off
    'token_set': bool(BOT_TOKEN),
    'bot': None,
    'mini_app_url': MINI_APP_URL or None,
    'webhook': False,
    'menu_button': False,
    'commands': False,
    'last_error': None,
    'updates_handled': 0,
    'started_at': int(time.time()),
}


def log(*args):
    print(time.strftime('%H:%M:%S'), *args, flush=True)


def _digest(label):
    return hashlib.sha256(f'{label}:{BOT_TOKEN}'.encode()).hexdigest()


WEBHOOK_PATH = '/tg/' + _digest('path')[:40]
WEBHOOK_SECRET = _digest('secret')[:64]


def is_https(url):
    try:
        return urlparse(url).scheme == 'https' and bool(urlparse(url).netloc)
    except ValueError:
        return False


# ---------------------------------------------------------------- Telegram API
def api(method, data=None, timeout=40):
    payload = json.dumps(data or {}).encode('utf-8')
    req = Request(
        f'{API_BASE}/bot{BOT_TOKEN}/{method}',
        data=payload,
        headers={'Content-Type': 'application/json; charset=utf-8'},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = json.load(resp)
    except HTTPError as err:
        try:
            body = json.load(err)
        except ValueError:
            body = {'ok': False, 'description': f'HTTP {err.code}'}
    if not body.get('ok'):
        raise RuntimeError(f"{method}: {body.get('description', 'белгісіз қате')}")
    return body.get('result')


def open_button():
    return {'inline_keyboard': [[{'text': OPEN_TEXT, 'web_app': {'url': MINI_APP_URL + '/'}}]]}


def build_reply(update):
    """Telegram жаңартуына жауап (sendMessage параметрлері) немесе None."""
    msg = update.get('message') or {}
    chat = msg.get('chat') or {}
    if chat.get('type') != 'private' or not chat.get('id'):
        return None
    text = (msg.get('text') or '').strip()
    cmd = text.split()[0].split('@')[0].lower() if text.startswith('/') else ''
    if cmd == '/help':
        body = HELP
    elif cmd in ('/start', '/exam', '/test', '/pdd') or not text:
        body = WELCOME
    else:
        body = 'Емтиханды ашу үшін төмендегі батырманы басыңыз 👇'
    reply = {'chat_id': chat['id'], 'text': body}
    if is_https(MINI_APP_URL):
        reply['reply_markup'] = open_button()
    return reply


# ---------------------------------------------------------------- auto setup
def configure_bot():
    """Webhook, мәзір батырмасы, командалар — бәрін автоматты баптайды."""
    me = api('getMe')
    STATE['bot'] = '@' + me.get('username', '')
    log('Бот табылды:', STATE['bot'])

    if STATE['mode'] == 'webhook':
        api('setWebhook', {
            'url': SELF_URL + WEBHOOK_PATH,
            'secret_token': WEBHOOK_SECRET,
            'allowed_updates': ['message'],
            'max_connections': 40,
        })
        STATE['webhook'] = True
        log('Webhook орнатылды.')
    else:
        api('deleteWebhook', {'drop_pending_updates': False})

    if is_https(MINI_APP_URL):
        api('setChatMenuButton', {'menu_button': {
            'type': 'web_app', 'text': MENU_TEXT, 'web_app': {'url': MINI_APP_URL + '/'}}})
        STATE['menu_button'] = True
        log('Мәзір батырмасы қосылды →', MINI_APP_URL + '/')
    else:
        log('ЕСКЕРТУ: MINI_APP_URL HTTPS емес, мәзір батырмасы қосылмады.')

    api('setMyCommands', {'commands': [
        {'command': 'start', 'description': 'Емтиханды ашу'},
        {'command': 'help', 'description': 'Қалай пайдалану керек'},
    ]})
    STATE['commands'] = True
    for method, field, value in (
        ('setMyDescription', 'description', DESCRIPTION),
        ('setMyShortDescription', 'short_description', SHORT_DESCRIPTION),
    ):
        try:
            api(method, {field: value})
        except Exception as err:  # сипаттама міндетті емес
            log('Сипаттама орнатылмады:', err)
    STATE['last_error'] = None
    log('Бот толық бапталды ✓')


def setup_loop():
    delay = 3
    while True:
        try:
            configure_bot()
            return
        except Exception as err:
            STATE['last_error'] = str(err)
            log('Баптау қатесі:', err)
            if 'Unauthorized' in str(err) or 'Not Found' in str(err):
                log('Токен қате сияқты. BOT_TOKEN мәнін @BotFather-дан қайта көшіріңіз.')
                delay = 300
            time.sleep(delay)
            delay = min(delay * 2, 300)


def polling_loop():
    offset = None
    while True:
        try:
            updates = api('getUpdates', {'offset': offset, 'timeout': 25,
                                         'allowed_updates': ['message']}, timeout=40)
            for update in updates or []:
                offset = update['update_id'] + 1
                reply = build_reply(update)
                if reply:
                    api('sendMessage', reply)
                    STATE['updates_handled'] += 1
        except Exception as err:
            STATE['last_error'] = str(err)
            log('Polling қатесі:', err)
            time.sleep(5)


# ---------------------------------------------------------------- HTTP server
class Handler(BaseHTTPRequestHandler):
    server_version = 'QazaqPDD/1.0'

    def log_message(self, fmt, *args):  # webhook жолы (құпия) логқа түспесін
        path = self.path.split('?')[0]
        if path.startswith('/tg/'):
            return
        sys.stderr.write('%s %s\n' % (self.command, path))

    def _send(self, code, body=b'', ctype='text/plain; charset=utf-8', extra=None, head=False):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if not head:
            self.wfile.write(body)

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

    def do_HEAD(self):
        self.do_GET(head=True)

    def do_GET(self, head=False):
        path = urlparse(self.path).path
        if path == '/health':
            return self._send(200, b'ok', head=head)
        if path == '/status':
            body = json.dumps(STATE, ensure_ascii=False, indent=2).encode('utf-8')
            return self._send(200, body, 'application/json; charset=utf-8',
                              {'Cache-Control': 'no-store'}, head=head)
        return self._static(head=head)

    def do_POST(self):
        if urlparse(self.path).path != WEBHOOK_PATH or not BOT_TOKEN:
            return self._send(404, b'Not found')
        secret = self.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
        if not hmac.compare_digest(secret, WEBHOOK_SECRET):
            return self._send(403, b'Forbidden')
        try:
            length = min(int(self.headers.get('Content-Length', '0')), 1_000_000)
            update = json.loads(self.rfile.read(length) or b'{}')
        except ValueError:
            return self._send(400, b'Bad request')
        reply = build_reply(update) if isinstance(update, dict) else None
        if not reply:
            return self._send(200, b'')
        STATE['updates_handled'] += 1
        # Жауапты webhook жауабының ішінде қайтарамыз — қосымша сұраныс қажет емес.
        body = json.dumps({'method': 'sendMessage', **reply}, ensure_ascii=False).encode('utf-8')
        self._send(200, body, 'application/json; charset=utf-8')


def main():
    mimetypes.add_type('application/javascript', '.js')
    mimetypes.add_type('image/svg+xml', '.svg')
    if not WEBAPP.is_dir():
        sys.exit('webapp/ папкасы табылмады.')

    if not BOT_TOKEN:
        log('BOT_TOKEN орнатылмаған — тек Mini App беттері жұмыс істейді.')
        log('Render: Dashboard → осы сервис → Environment → BOT_TOKEN қосып, Save басыңыз.')
    elif is_https(SELF_URL):
        STATE['mode'] = 'webhook'
        threading.Thread(target=setup_loop, daemon=True).start()
    else:
        STATE['mode'] = 'polling'
        if not is_https(MINI_APP_URL):
            log('ЕСКЕРТУ: ашық HTTPS адрес жоқ. MINI_APP_URL=https://... орнатыңыз, '
                'әйтпесе Mini App батырмасы жұмыс істемейді.')

        def _poll():
            setup_loop()
            polling_loop()
        threading.Thread(target=_poll, daemon=True).start()

    httpd = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    log(f'Сервер іске қосылды: порт {PORT}, режим: {STATE["mode"]}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
