"""server.py тесті: жалған Telegram API арқылы (желі қажет емес).

Іске қосу:  python3 tests/server_test.py
"""
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
TOKEN = '123456:TEST_TOKEN'
CALLS = []
POLL_SENT = {'done': False}


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class FakeTelegram(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        method = self.path.rsplit('/', 1)[-1]
        assert self.path.startswith(f'/bot{TOKEN}/'), self.path
        data = json.loads(self.rfile.read(int(self.headers['Content-Length'])) or b'{}')
        CALLS.append((method, data))
        result = True
        if method == 'getMe':
            result = {'id': 1, 'is_bot': True, 'username': 'qazaq_pdd_test_bot'}
        elif method == 'getUpdates':
            if not POLL_SENT['done']:
                POLL_SENT['done'] = True
                result = [{'update_id': 7, 'message': {'chat': {'id': 55, 'type': 'private'}, 'text': '/start'}}]
            else:
                time.sleep(0.3)
                result = []
        body = json.dumps({'ok': True, 'result': result}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass  # сервер процесі тест соңында өшірілген


def http(url, data=None, headers=None):
    req = Request(url, data=data, headers=headers or {})
    try:
        with urlopen(req, timeout=5) as r:
            return r.status, r.read(), dict(r.headers)
    except HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def start_server(env_extra):
    port = free_port()
    env = {k: v for k, v in os.environ.items() if k not in ('RENDER_EXTERNAL_URL', 'PUBLIC_URL', 'MINI_APP_URL', 'BOT_TOKEN')}
    env.update({'PORT': str(port), 'PYTHONUNBUFFERED': '1', **env_extra})
    proc = subprocess.Popen([sys.executable, '-I', str(ROOT / 'server.py')], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    base = f'http://127.0.0.1:{port}'
    for _ in range(50):
        try:
            if http(base + '/health')[0] == 200:
                return proc, base
        except OSError:
            time.sleep(0.1)
    proc.kill()
    raise SystemExit('server did not start: ' + proc.stdout.read().decode())


def wait_status(base, key, timeout=8):
    end = time.time() + timeout
    while time.time() < end:
        st = json.loads(http(base + '/status')[1])
        if st.get(key):
            return st
        time.sleep(0.1)
    raise AssertionError(f'status.{key} never became true: {st}')


def main():
    api_port = free_port()
    api = ThreadingHTTPServer(('127.0.0.1', api_port), FakeTelegram)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    api_base = f'http://127.0.0.1:{api_port}'

    # 1) Webhook режимі (Render сияқты)
    proc, base = start_server({'BOT_TOKEN': TOKEN, 'PUBLIC_URL': 'https://bot.example.test',
                               'MINI_APP_URL': 'https://app.example.test', 'TELEGRAM_API_BASE': api_base})
    try:
        st = wait_status(base, 'commands')
        assert st['mode'] == 'webhook' and st['bot'] == '@qazaq_pdd_test_bot', st
        assert st['webhook'] and st['menu_button'], st
        assert TOKEN not in json.dumps(st), 'token leaked in /status'
        methods = [m for m, _ in CALLS]
        for m in ('getMe', 'setWebhook', 'setChatMenuButton', 'setMyCommands', 'setMyDescription', 'setMyShortDescription'):
            assert m in methods, (m, methods)
        hook = dict(CALLS)['setWebhook']
        path = '/tg/' + hashlib.sha256(f'path:{TOKEN}'.encode()).hexdigest()[:40]
        secret = hashlib.sha256(f'secret:{TOKEN}'.encode()).hexdigest()[:64]
        assert hook['url'] == 'https://bot.example.test' + path, hook
        assert hook['secret_token'] == secret
        assert TOKEN not in hook['url']
        menu = dict(CALLS)['setChatMenuButton']['menu_button']
        assert menu['type'] == 'web_app' and menu['web_app']['url'] == 'https://app.example.test/', menu

        # Статикалық файлдар
        code, body, hdr = http(base + '/')
        assert code == 200 and b'QAZAQ PDD' in body and 'text/html' in hdr['Content-Type']
        assert http(base + '/app.js')[0] == 200
        code, body, hdr = http(base + '/assets/stop.svg')
        assert code == 200 and 'image/svg+xml' in hdr['Content-Type']
        for bad in ('/server.py', '/../server.py', '/%2e%2e/server.py', '/assets/../../server.py', '/nope.html'):
            assert http(base + bad)[0] == 404, bad

        # Webhook қорғанысы
        upd = json.dumps({'update_id': 1, 'message': {'chat': {'id': 42, 'type': 'private'}, 'text': '/start'}}).encode()
        assert http(base + path, upd)[0] == 403
        assert http(base + path, upd, {'X-Telegram-Bot-Api-Secret-Token': 'wrong'})[0] == 403
        assert http(base + '/tg/other', upd, {'X-Telegram-Bot-Api-Secret-Token': secret})[0] == 404

        code, body, _ = http(base + path, upd, {'X-Telegram-Bot-Api-Secret-Token': secret})
        reply = json.loads(body)
        assert code == 200 and reply['method'] == 'sendMessage' and reply['chat_id'] == 42
        btn = reply['reply_markup']['inline_keyboard'][0][0]
        assert btn['web_app']['url'] == 'https://app.example.test/', btn

        help_upd = json.dumps({'update_id': 2, 'message': {'chat': {'id': 42, 'type': 'private'}, 'text': '/help@qazaq_pdd_test_bot'}}).encode()
        reply = json.loads(http(base + path, help_upd, {'X-Telegram-Bot-Api-Secret-Token': secret})[1])
        assert 'Қалай пайдалану' in reply['text']

        group = json.dumps({'update_id': 3, 'message': {'chat': {'id': -5, 'type': 'group'}, 'text': '/start'}}).encode()
        code, body, _ = http(base + path, group, {'X-Telegram-Bot-Api-Secret-Token': secret})
        assert code == 200 and body == b''
    finally:
        proc.kill()

    # 2) Polling режимі (үй компьютері)
    CALLS.clear()
    proc, base = start_server({'BOT_TOKEN': TOKEN, 'MINI_APP_URL': 'https://app.example.test',
                               'TELEGRAM_API_BASE': api_base})
    try:
        end = time.time() + 8
        while time.time() < end and 'sendMessage' not in [m for m, _ in CALLS]:
            time.sleep(0.1)
        sent = [d for m, d in CALLS if m == 'sendMessage']
        assert sent and sent[0]['chat_id'] == 55, CALLS
        methods = [m for m, _ in CALLS]
        assert 'deleteWebhook' in methods and 'setWebhook' not in methods, methods
        assert json.loads(http(base + '/status')[1])['mode'] == 'polling'
    finally:
        proc.kill()

    # 3) Токенсіз — сайт бәрібір ашылады
    CALLS.clear()
    proc, base = start_server({'TELEGRAM_API_BASE': api_base})
    try:
        assert http(base + '/')[0] == 200
        st = json.loads(http(base + '/status')[1])
        assert st['mode'] == 'off' and not st['token_set'], st
        time.sleep(0.5)
        assert CALLS == [], CALLS
        assert http(base + '/tg/anything', b'{}')[0] == 404
    finally:
        proc.kill()

    api.shutdown()
    print('PASS: webhook setup, menu button, commands, secret check, /start & /help replies, '
          'static files, path traversal blocked, polling mode, no-token mode.')


if __name__ == '__main__':
    main()
