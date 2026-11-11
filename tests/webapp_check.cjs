// Mini App тексерісі: JS синтаксисі, қаз/рус аудармалар толықтығы, суреттер, клиентте жауаптар жоқтығы.
// Іске қосу: node tests/webapp_check.cjs
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const W = path.join(__dirname, '..', 'webapp');
let n = 0;
const ok = (c, label) => { if (!c) { console.error('✗', label); process.exit(1); } n++; console.log('  ✓', label); };

const src = f => fs.readFileSync(path.join(W, f), 'utf8');
for (const f of ['app.js', 'i18n.js', 'config.js']) {
  try { new vm.Script(src(f), {filename: f}); ok(true, `${f} синтаксисі дұрыс`); } catch (e) { ok(false, `${f}: ${e.message}`); }
}
const ctx = {window: {}, location: {hostname: 'x'}};
vm.runInNewContext(src('i18n.js'), ctx);
const {I18N, SIGNS_INFO, SIGN_GROUPS, GUIDE} = ctx.window;
const kk = Object.keys(I18N.kk).sort(), ru = Object.keys(I18N.ru).sort();
ok(JSON.stringify(kk) === JSON.stringify(ru), `қазақша және орысша кілттер бірдей (${kk.length})`);
const used = [...new Set([...src('app.js').matchAll(/\bt\('([A-Za-z0-9]+)'/g)].map(m => m[1]))];
const missing = used.filter(k => !(k in I18N.kk));
ok(!missing.length, `app.js қолданатын барлық мәтін бар (${used.length})` + (missing.length ? ': ' + missing : ''));
ok(SIGNS_INFO.every(s => fs.existsSync(path.join(W, 'assets', 'signs', s.id + '.svg'))), `белгілер анықтамалығының суреттері бар (${SIGNS_INFO.length})`);
ok(SIGNS_INFO.every(s => SIGN_GROUPS[s.g] && s.kk[0] && s.ru[0] && s.kk[1] && s.ru[1]), 'әр белгінің қаз/рус атауы мен сипаттамасы бар');
ok(GUIDE.kk.length === GUIDE.ru.length && GUIDE.links.every(l => /^https:\/\//.test(l[1])), 'нұсқаулық толық, сілтемелер HTTPS');

const bank = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'questions.json'), 'utf8'));
ok(bank.questions.filter(q => q.image).every(q => fs.existsSync(path.join(W, 'assets', `q-${q.id}.svg`))), 'әр суретті сұрақтың суреті бар');
const all = fs.readdirSync(W).filter(f => /\.(js|html|json)$/.test(f)).map(src).join('\n');
const leaks = bank.questions.filter(q => all.includes(q.kk.why) || all.includes(q.ru.why));
ok(!leaks.length, 'webapp/ ішінде сұрақтар түсіндірмесі мен жауаптар жоқ');
ok(!/QUESTION_BANK|questions\.js/.test(src('index.html') + src('app.js')), 'ескі клиенттік сұрақтар базасы қолданылмайды');
ok(!/\b\d{8,10}:[A-Za-z0-9_-]{30,}\b/.test(all), 'бот токені клиент кодында жоқ');
console.log(`\nwebapp: ${n} тексеру өтті ✓`);
