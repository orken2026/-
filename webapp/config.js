// API адресі: Mini App бөлек статикалық сайтта тұрса — бот серверіне жүгінеді, әйтпесе — өз серверіне.
window.APP_CONFIG = window.APP_CONFIG || {
  api: location.hostname === 'qazaq-pdd-app.onrender.com' ? 'https://qazaq-pdd-bot.onrender.com' : '',
  bot: 'Qazaqpdd_bot'
};
