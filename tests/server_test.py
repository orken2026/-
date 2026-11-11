"""server.py толық тесті: жалған Telegram API және жалған AI API арқылы (интернет қажет емес).

Іске қосу:  python3 tests/server_test.py
Тексерілетіні:
  * initData қолтаңбасы (дұрыс / бұрмаланған / ескі)
  * тегін және толық нұсқа шекарасы, жауаптар клиентке ашылмайды
  * емтихан бағалау, токенді бұрмалау және басқа пайдаланушының токені
  * Telegram Stars: invoice (XTR), pre_checkout_query, successful_payment, getStarTransactions арқылы қалпына келтіру, қайтару
  * бот командалары (/start, /terms, /paysupport, /daily, /stats)
  * «Неге?» AI түсіндірмесі (тек төлегендерге, кэш)
  * статикалық файлдар және құпия файлдардың жабықтығы
"""
import hashlib
import hmac
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
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
TOKEN = '123456:TEST_TOKEN'
ADMIN = 900
CALLS = []
AI_CALLS = []
UPDATES = []
LOCK = threading.Lock()
BANK = json.loads((ROOT / 'data' / 'questions.json').read_text(encoding='utf-8'))
BYID = {q['id']: q for q in BANK['questions']}


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


STAR_TXS = [
    {'id': 'ch_restored', 'amount': 50, 'date': int(time.time()) - 3600,
     'source': {'type': 'user', 'user': {'id': 555}, 'invoice_payload': 'plan:555:0:abcd'}},
    {'id': 'ch_refunded', 'amount': 50, 'date': int(time.time()) - 7200,
     'source': {'type': 'user', 'user': {'id': 556}, 'invoice_payload': 'plan:556:0:abce'}},
    {'id': 'ch_refunded', 'amount': 50, 'date': int(time.time()) - 3000,
     'receiver': {'type': 'user', 'user': {'id': 556}}},
]


class FakeTelegram(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _reply(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
        if self.path == '/v1/messages':  # жалған Anthropic API
            AI_CALLS.append(data)
            assert self.headers.get('x-api-key') == 'test-ai-key'
            return self._reply({'content': [{'type': 'text', 'text': 'AI түсіндірмесі: тест мәтіні.'}]})
        assert self.path.startswith(f'/bot{TOKEN}/'), self.path
        method = self.path.rsplit('/', 1)[-1]
        with LOCK:
            CALLS.append((method, data))
        result = True
        if method == 'getMe':
            result = {'id': 1, 'is_bot': True, 'username': 'qazaq_pdd_test_bot'}
        elif method == 'getStarTransactions':
            result = {'transactions': STAR_TXS if data.get('offset', 0) == 0 else []}
        elif method == 'createInvoiceLink':
            result = 'https://t.me/$test_invoice'
        elif method == 'getUpdates':
            with LOCK:
                ups = UPDATES[:]
                UPDATES.clear()
            if not ups:
                time.sleep(0.15)
            result = ups
        self._reply({'ok': True, 'result': result})


def init_data(uid, lang='kk', age=0, tamper=False):
    user = json.dumps({'id': uid, 'first_name': 'Тест', 'language_code': lang}, ensure_ascii=False, separators=(',', ':'))
    fields = {'auth_date': str(int(time.time()) - age), 'query_id': 'AAE', 'user': user}
    check = '\n'.join(f'{k}={v}' for k, v in sorted(fields.items()))
    key = hmac.new(b'WebAppData', TOKEN.encode(), hashlib.sha256).digest()
    h = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    if tamper:
        fields['user'] = fields['user'].replace(str(uid), str(uid + 1))
    fields['hash'] = h
    return urlencode(fields)


class T:
    base = ''
    passed = 0

    @classmethod
    def post(cls, path, body, uid=None, raw_init=None):
        body = dict(body)
        body['initData'] = raw_init if raw_init is not None else (init_data(uid) if uid else '')
        req = Request(cls.base + path, data=json.dumps(body).encode(), headers={'Content-Type': 'text/plain'})
        try:
            with urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read() or b'{}')
        except HTTPError as e:
            return e.code, json.loads(e.read() or b'{}')

    @classmethod
    def get(cls, path):
        try:
            with urlopen(cls.base + path, timeout=10) as r:
                return r.status, r.read()
        except HTTPError as e:
            return e.code, e.read()

    @classmethod
    def ok(cls, cond, label):
        if not cond:
            raise AssertionError(label)
        cls.passed += 1
        print('  ✓', label)


def wait_for(pred, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if pred():
                return True
        except OSError:
            pass
        time.sleep(0.05)
    return False


def calls(method):
    with LOCK:
        return [d for m, d in CALLS if m == method]


def correct_index(qview):
    """Банкте дұрыс жауап әрқашан 0-индексте; клиентке берілген араласқан нұсқалардан табамыз."""
    q = BYID[qview['id']]
    for lang in ('kk', 'ru'):
        if q[lang]['options'][0] in qview['options']:
            return qview['options'].index(q[lang]['options'][0])
    raise AssertionError('дұрыс жауап табылмады')


def main():
    tg_port, app_port = free_port(), free_port()
    fake = ThreadingHTTPServer(('127.0.0.1', tg_port), FakeTelegram)
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    env = dict(os.environ, BOT_TOKEN=TOKEN, PORT=str(app_port), TELEGRAM_API_BASE=f'http://127.0.0.1:{tg_port}',
               MINI_APP_URL='https://app.example.kz', PUBLIC_URL='', ADMIN_IDS=str(ADMIN), SUPPORT='@help_test',
               ANTHROPIC_API_KEY='test-ai-key', ANTHROPIC_API_BASE=f'http://127.0.0.1:{tg_port}', DAILY='0',
               DEV_AUTH='', RENDER_EXTERNAL_URL='', DATA_DIR='')
    proc = subprocess.Popen([sys.executable, str(ROOT / 'server.py')], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    T.base = f'http://127.0.0.1:{app_port}'
    try:
        assert wait_for(lambda: T.get('/health')[0] == 200), 'сервер іске қосылмады'
        assert wait_for(lambda: json.loads(T.get('/status')[1]).get('payments_synced')), 'бот бапталмады'
        run_tests()
        proc.terminate()
        proc.wait(timeout=5)
        webhook_tests(env, app_port)
        print(f'\nБАРЛЫҒЫ ӨТТІ: {T.passed} тексеру ✓')
    finally:
        proc.terminate()
        try:
            out = proc.communicate(timeout=5)[0].decode('utf-8', 'replace')
        except subprocess.TimeoutExpired:
            proc.kill()
            out = ''
        if os.environ.get('SHOW_LOG'):
            print(out)
        fake.shutdown()


def run_tests():
    print('Бот баптауы')
    st = json.loads(T.get('/status')[1])
    T.ok(st['mode'] == 'polling' and st['bot'] == '@qazaq_pdd_test_bot', 'polling режимі, getMe')
    T.ok(st['menu_button'] and st['commands'], 'мәзір батырмасы және командалар орнатылды')
    mb = calls('setChatMenuButton')[0]['menu_button']
    T.ok(mb['type'] == 'web_app' and mb['web_app']['url'] == 'https://app.example.kz/', 'мәзір батырмасы Mini App-ты ашады')
    cmds = calls('setMyCommands')
    names = {c['command'] for c in cmds[0]['commands']}
    T.ok({'start', 'terms', 'paysupport'} <= names, 'Telegram талабы: /terms және /paysupport бар')
    T.ok(any(c.get('language_code') == 'ru' for c in cmds), 'орысша командалар')
    T.ok(BOT_TOKEN_NOT_IN(T.get('/status')[1]), '/status бот токенін көрсетпейді')

    print('Статикалық файлдар')
    code, body = T.get('/')
    T.ok(code == 200 and b'app.js' in body and b'questions.js' not in body, 'index.html беріледі, ескі questions.js жоқ')
    T.ok(T.get('/assets/q-g006.svg')[0] == 200, 'сұрақ суреті беріледі')
    T.ok(T.get('/assets/signs/stop.svg')[0] == 200, 'белгі суреті беріледі')
    T.ok(T.get('/data/questions.json')[0] == 404, 'жауаптар базасы (data/questions.json) жабық')
    T.ok(T.get('/../server.py')[0] == 404 and T.get('/%2e%2e/server.py')[0] == 404, 'папкадан шығу (path traversal) жабық')
    T.ok(T.get('/questions.js')[0] == 404, 'клиентте жауаптары бар файл жоқ')

    print('Авторизация')
    T.ok(T.post('/api/me', {})[0] == 401, 'initData жоқ → 401')
    T.ok(T.post('/api/me', {}, raw_init=init_data(101, tamper=True))[0] == 401, 'бұрмаланған initData → 401')
    T.ok(T.post('/api/me', {}, raw_init=init_data(101, age=8 * 86400))[0] == 401, 'ескі initData → 401')
    code, me = T.post('/api/me', {'lang': 'ru'}, uid=101)
    T.ok(code == 200 and me['user']['id'] == 101 and me['lang'] == 'ru', '/api/me жұмыс істейді')
    T.ok(me['access']['paid'] is False and me['price'] == {'stars': 50, 'days': 0}, 'тегін пайдаланушы, баға 50⭐ мерзімсіз')
    T.ok(me['bank']['total'] == len(BANK['questions']) and me['bank']['free'] < me['bank']['total'], 'банк және тегін бөлік')
    T.ok(sum(t['total'] for t in me['bank']['topics']) == me['bank']['total'], 'тақырыптар саны сәйкес')
    T.ok(me['ai'] is True and me['bot'] == 'qazaq_pdd_test_bot', 'AI қосулы, бот аты (@-сыз) бар')

    print('Тегін емтихан')
    code, ex = T.post('/api/exam/start', {'cat': 'B', 'lang': 'kk'}, uid=101)
    T.ok(code == 200 and len(ex['questions']) == 40 and ex['free'] is True, 'B емтиханы: 40 сұрақ')
    T.ok(all(BYID[q['id']]['free'] for q in ex['questions']), 'тегін емтиханда тек тегін сұрақтар')
    T.ok(all(BYID[q['id']]['cat'] == 'g' for q in ex['questions']), 'B санатында жүк көлігі сұрақтары жоқ')
    T.ok(sum(1 for q in ex['questions'] if q['image']) == 20, '20 суретті + 20 мәтінді')
    leak_keys = {'correct', 'why', 'ref', 'answer'}
    T.ok(all(not (leak_keys & set(q)) for q in ex['questions']), 'сұрақтарда дұрыс жауап/түсіндірме жоқ')
    T.ok(all(sorted(q['options']) == sorted(BYID[q['id']]['kk']['options']) for q in ex['questions']), 'нұсқалар — сол сұрақтың нұсқалары')
    firsts = [q['options'].index(BYID[q['id']]['kk']['options'][0]) for q in ex['questions']]
    T.ok(len(set(firsts)) > 1, 'дұрыс жауаптың орны араласқан')
    answers = [correct_index(q) for q in ex['questions']]
    answers[0] = (answers[0] + 1) % 4
    answers[1] = None
    code, res = T.post('/api/exam/finish', {'token': ex['token'], 'answers': answers}, uid=101)
    T.ok(code == 200 and res['score'] == 38 and res['passed'] is True, 'бағалау: 38/40, өтті')
    T.ok(res['items'][0]['answer'] != res['items'][0]['correct'] and res['items'][1]['answer'] is None, 'қате және бос жауап белгіленді')
    T.ok(all(it['why'] for it in res['items']), 'аяқталғанда түсіндірмелер беріледі')
    code, _ = T.post('/api/exam/finish', {'token': ex['token'], 'answers': [0] * 40}, uid=102)
    T.ok(code == 403, 'басқа пайдаланушының токені → 403')
    raw, mac = ex['token'].rsplit('.', 1)
    T.ok(T.post('/api/exam/finish', {'token': raw + '.' + '0' * 32, 'answers': []}, uid=101)[0] == 403, 'бұрмаланған токен → 403')
    code, ex2 = T.post('/api/exam/start', {'cat': 'BC'}, uid=101)
    cats = [BYID[q['id']]['cat'] for q in ex2['questions']]
    T.ok(code == 200 and cats.count('c') == 8 and cats.count('g') == 32, 'B+C емтиханы: 32 жалпы + 8 жүк')
    code, ex3 = T.post('/api/exam/start', {'cat': 'B', 'recent': [q['id'] for q in ex['questions']]}, uid=101)
    T.ok(code == 200 and len(ex3['questions']) == 40, 'қайталанатын сұрақтар тізімімен де 40 сұрақ')

    print('Жаттығу (тегін)')
    code, pr = T.post('/api/practice', {'mode': 'topic', 'topic': 'signs'}, uid=101)
    T.ok(code == 200 and pr['locked'] is True and pr['questions'], 'тақырып: тегін бөлігі ашық, қалғаны жабық')
    T.ok(all(BYID[q['id']]['free'] and BYID[q['id']]['topic'] == 'signs' for q in pr['questions']), 'тек тегін және сол тақырып')
    paid_only = next(q['id'] for q in BANK['questions'] if not q['free'])
    code, pl = T.post('/api/practice', {'mode': 'list', 'ids': [paid_only]}, uid=101)
    T.ok(code == 200 and pl['questions'] == [], 'тізім арқылы ақылы сұрақты алу мүмкін емес')
    q0 = pr['questions'][0]
    good = correct_index(q0)
    code, ck = T.post('/api/check', {'token': pr['token'], 'qid': q0['id'], 'choice': good}, uid=101)
    T.ok(code == 200 and ck['ok'] is True and ck['correct'] == good and ck['why'], '/api/check: дұрыс жауап')
    code, ck = T.post('/api/check', {'token': pr['token'], 'qid': q0['id'], 'choice': (good + 1) % 4}, uid=101)
    T.ok(code == 200 and ck['ok'] is False, '/api/check: қате жауап')
    T.ok(T.post('/api/check', {'token': pr['token'], 'qid': paid_only, 'choice': 0}, uid=101)[0] == 403, 'токенде жоқ сұрақты тексеру → 403')
    code, er = T.post('/api/explain', {'token': pr['token'], 'qid': q0['id'], 'choice': 1}, uid=101)
    T.ok(code == 402, 'AI түсіндірмесі тегін пайдаланушыға жабық (402)')

    print('Telegram Stars төлемі')
    code, inv = T.post('/api/invoice', {'lang': 'kk'}, uid=101)
    T.ok(code == 200 and inv['link'].startswith('https://t.me/'), 'invoice сілтемесі жасалды')
    ci = calls('createInvoiceLink')[-1]
    T.ok(ci['currency'] == 'XTR' and ci['prices'][0]['amount'] == 50 and not ci.get('provider_token'), 'XTR валютасы, 50⭐, provider_token жоқ')
    payload = ci['payload']
    T.ok(payload.startswith('plan:101:0:'), 'payload пайдаланушыға байланған')
    UPDATES.append({'update_id': 10, 'pre_checkout_query': {'id': 'pcq1', 'from': {'id': 101}, 'currency': 'XTR',
                                                             'total_amount': 50, 'invoice_payload': payload}})
    UPDATES.append({'update_id': 11, 'pre_checkout_query': {'id': 'pcq2', 'from': {'id': 999}, 'currency': 'XTR',
                                                             'total_amount': 50, 'invoice_payload': payload}})
    T.ok(wait_for(lambda: len(calls('answerPreCheckoutQuery')) >= 2), 'pre_checkout_query жауабы жіберілді')
    ans = {a['pre_checkout_query_id']: a for a in calls('answerPreCheckoutQuery')}
    T.ok(ans['pcq1']['ok'] is True and ans['pcq2']['ok'] is False, 'бөтен пайдаланушының төлемі қабылданбайды')
    UPDATES.append({'update_id': 12, 'message': {'message_id': 1, 'chat': {'id': 101, 'type': 'private'}, 'from': {'id': 101, 'language_code': 'kk'},
                                                 'successful_payment': {'currency': 'XTR', 'total_amount': 50, 'invoice_payload': payload,
                                                                        'telegram_payment_charge_id': 'ch_new_101'}}})
    T.ok(wait_for(lambda: T.post('/api/me', {}, uid=101)[1]['access']['paid']), 'successful_payment → толық нұсқа ашылды')
    T.ok(any('Төлем қабылданды' in m.get('text', '') for m in calls('sendMessage')), 'төлем туралы хабарлама жіберілді')

    print('Төлемдерді Telegram-нан қалпына келтіру')
    T.ok(T.post('/api/me', {}, uid=555)[1]['access']['paid'] is True, 'getStarTransactions: бұрынғы төлем қалпына келді')
    T.ok(T.post('/api/me', {}, uid=556)[1]['access']['paid'] is False, 'қайтарылған төлем есептелмейді')

    print('Толық нұсқа')
    code, pr = T.post('/api/practice', {'mode': 'marathon'}, uid=101)
    T.ok(code == 200 and pr['locked'] is False and len(pr['questions']) == len(BANK['questions']), 'марафон: барлық сұрақ')
    code, pr = T.post('/api/practice', {'mode': 'marathon', 'cat': 'g', 'lang': 'ru'}, uid=101)
    T.ok(all(BYID[q['id']]['cat'] == 'g' for q in pr['questions']), 'марафон B: тек жалпы сұрақтар')
    T.ok(pr['questions'][0]['text'] == BYID[pr['questions'][0]['id']]['ru']['text'], 'орысша мәтін')
    code, ex = T.post('/api/exam/start', {'cat': 'B'}, uid=101)
    T.ok(ex['free'] is False and not all(BYID[q['id']]['free'] for q in ex['questions']), 'толық емтихан бүкіл банктен')
    q0 = pr['questions'][0]
    bad = (correct_index(q0) + 1) % 4
    code, er = T.post('/api/explain', {'token': pr['token'], 'qid': q0['id'], 'choice': bad, 'lang': 'ru'}, uid=101)
    T.ok(code == 200 and er['text'] and len(AI_CALLS) == 1, '«Неге?» AI түсіндірмесі')
    T.ok('Ответ ученика' in AI_CALLS[0]['messages'][0]['content'], 'AI-ға оқушы жауабы мен ереже жіберіледі')
    T.post('/api/explain', {'token': pr['token'], 'qid': q0['id'], 'choice': bad, 'lang': 'ru'}, uid=101)
    T.ok(len(AI_CALLS) == 1, 'AI жауабы кэштеледі')
    T.ok(T.post('/api/me', {}, uid=ADMIN)[1]['access']['admin'] is True, 'ADMIN_IDS — тегін толық қолжетімділік')

    print('Бот командалары')
    before = len(calls('sendMessage'))
    for i, (text, lang) in enumerate([('/start', 'kk'), ('/terms', 'ru'), ('/paysupport', 'kk'), ('/daily', 'kk'), ('/stats', 'kk')]):
        uid = ADMIN if text == '/stats' else 202
        UPDATES.append({'update_id': 20 + i, 'message': {'message_id': 5 + i, 'chat': {'id': uid, 'type': 'private'},
                                                         'from': {'id': uid, 'language_code': lang}, 'text': text}})
    T.ok(wait_for(lambda: len(calls('sendMessage')) >= before + 5), 'командаларға жауап берілді')
    msgs = calls('sendMessage')[before:]
    T.ok('web_app' in json.dumps(msgs[0]['reply_markup']) and 'QAZAQ PDD' in msgs[0]['text'], '/start → Mini App батырмасы')
    T.ok('Условия' in msgs[1]['text'] and '50' in msgs[1]['text'], '/terms → шарттар (орысша)')
    T.ok('@help_test' in msgs[2]['text'] and '202' in msgs[2]['text'], '/paysupport → байланыс және ID')
    T.ok('қосылды' in msgs[3]['text'], '/daily → күн сұрағы қосылды')
    T.ok('Пайдаланушылар' in msgs[4]['text'], '/stats → әкімші статистикасы')
    T.ok(T.post('/api/daily', {'on': False}, uid=202)[1]['daily'] is False, '/api/daily өшіреді')
    T.ok(BOT_TOKEN_NOT_IN(json.dumps(msgs, ensure_ascii=False).encode()), 'хабарламаларда токен жоқ')


def webhook_tests(env, port):
    print('Webhook режимі (Render)')
    env = dict(env, PUBLIC_URL='https://bot.example.kz')
    with LOCK:
        CALLS.clear()
    proc = subprocess.Popen([sys.executable, str(ROOT / 'server.py')], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        assert wait_for(lambda: json.loads(T.get('/status')[1]).get('webhook')), 'webhook орнатылмады'
        wh = calls('setWebhook')[0]
        path = '/tg/' + hashlib.sha256(f'path:{TOKEN}'.encode()).hexdigest()[:40]
        secret = hashlib.sha256(f'secret:{TOKEN}'.encode()).hexdigest()[:64]
        T.ok(wh['url'] == 'https://bot.example.kz' + path and wh['secret_token'] == secret, 'setWebhook: жасырын жол және secret_token')
        T.ok(TOKEN not in wh['url'], 'webhook адресінде токен жоқ')
        T.ok(set(wh['allowed_updates']) == {'message', 'pre_checkout_query'}, 'allowed_updates: message, pre_checkout_query')
        upd = json.dumps({'update_id': 1, 'message': {'message_id': 1, 'chat': {'id': 7, 'type': 'private'},
                                                      'from': {'id': 7, 'language_code': 'ru'}, 'text': '/start'}}).encode()
        def hook(sec):
            req = Request(T.base + path, data=upd, headers={'Content-Type': 'application/json', 'X-Telegram-Bot-Api-Secret-Token': sec})
            try:
                with urlopen(req, timeout=10) as r:
                    return r.status, r.read()
            except HTTPError as e:
                return e.code, e.read()
        T.ok(hook('wrong')[0] == 403, 'қате secret_token → 403')
        code, body = hook(secret)
        reply = json.loads(body)
        T.ok(code == 200 and reply['method'] == 'sendMessage' and reply['chat_id'] == 7, 'webhook жауабында бірден sendMessage')
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def BOT_TOKEN_NOT_IN(raw):
    return TOKEN.encode() not in raw


if __name__ == '__main__':
    main()
