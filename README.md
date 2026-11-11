# 🚘 QAZAQ PDD — Telegram бот + Mini App

Қазақстандағы B, C1, C санаттарына арналған ПДД емтихан тренажері: 40 сұрақ, 40 минут, өту шегі 32, 132 сұрақтық база, 40 сурет.

## Не қайда орналасқан

| Бөлік | Адрес | Не істейді |
|---|---|---|
| Mini App (сайт) | https://qazaq-pdd-app.onrender.com | Емтиханның өзі. Статикалық сайт, ешқашан ұйықтамайды |
| Бот сервері | https://qazaq-pdd-bot.onrender.com | /start-қа жауап береді, мәзір батырмасын өзі қосады |
| Күйін тексеру | https://qazaq-pdd-bot.onrender.com/status | Бот қосылды ма, webhook пен мәзір орнатылды ма |

## Сізден керегі — тек BOT_TOKEN

1. Telegram-да **@BotFather** → `/newbot` → бот атын беріңіз → токенді көшіріңіз (`123456789:AA...`).
2. Render-де **qazaq-pdd-bot** сервисін ашыңыз → **Environment** → **Add Environment Variable**.
3. Key: `BOT_TOKEN`, Value: көшірілген токен → **Save, rebuild, and deploy**.

1–2 минуттан кейін сервер өзі:
- webhook орнатады;
- ботқа **🚦 ПДД емтиханы** мәзір батырмасын қосады;
- `/start`, `/help` командаларын және бот сипаттамасын жазады.

Ботты ашып, `/start` жіберіңіз немесе төменгі мәзір батырмасын басыңыз.

Тексеру: `https://qazaq-pdd-bot.onrender.com/status` бетінде `"bot": "@сіздің_бот"`, `"webhook": true`, `"menu_button": true` болуы керек.

**Токенді** кодқа, GitHub-қа немесе чатқа жазбаңыз — тек Render Environment ішінде сақталады.

## Тегін тарифтің ерекшелігі

Бот сервері Render Free тарифінде 15 минут қолданылмаса ұйықтайды. Ұйықтап тұрғанда бірінші `/start` жауабы 30–60 секунд кешігуі мүмкін (кейін бірден жауап береді). **Mini App бөлек статикалық сайтта тұр, ол әрқашан бірден ашылады.**

## Құрылымы

```
webapp/            Mini App: index.html, app.js, questions.js, styles.css, assets/*.svg
server.py          Бот + сайт сервері (тек стандартты Python, pip қажет емес)
render.yaml        Render Blueprint (екі сервис)
tools/generate_art.py   SVG суреттерді қайта жасау
tests/             smoke.test.cjs (Mini App), server_test.py (бот)
```

## Компьютерде іске қосу (міндетті емес)

```bash
python server.py                      # http://localhost:8000 — сайт
```

Ботты үйден іске қосу (long polling) — Mini App үшін бәрібір HTTPS адрес керек:

```powershell
$env:BOT_TOKEN="123456789:AA..."
$env:MINI_APP_URL="https://qazaq-pdd-app.onrender.com"
python server.py
```

Ескерту: бір токен бір уақытта бір жерде ғана жұмыс істейді. Үйден polling іске қоссаңыз, Render-дегі webhook өшеді; Render-ге қайта қайтару үшін ондағы сервисті Restart жасаңыз.

## Сұрақ қосу

`webapp/questions.js` ішіне жазба қосыңыз:

```js
{ id: 'g091', topic: 'Жол белгілері', text: 'Сұрақ мәтіні',
  options: ['Дұрыс жауап', 'Қате 1', 'Қате 2', 'Қате 3'], correct: 0,
  why: 'Түсіндірме.', image: 'stop' },
```

`id` қайталанбасын (`g…` — жалпы, `c…` — жүк көлігі). `image` — `webapp/assets/` ішіндегі `.svg` атауы. GitHub-қа push жасасаңыз, Render өзі жаңартады.

## Тексерулер

```bash
node tests/smoke.test.cjs
python tests/server_test.py
```

## Ескерту

Бұл ресми СпецЦОН жүйесі емес. Сұрақтар — авторлық жаттығу материалы. Ресми ереже: https://adilet.zan.kz/kaz/docs/V2300033003
