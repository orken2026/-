/* QAZAQ PDD — Telegram Mini App.
   Сұрақтар мен дұрыс жауаптар серверде сақталады: клиент тек сұрақ мәтінін алады,
   жауапты /api/check немесе /api/exam/finish арқылы тексереді. */
(() => {
  'use strict';
  const W = window.Telegram && window.Telegram.WebApp;
  const inTg = !!(W && W.initData);
  const CFG = window.APP_CONFIG || {};
  const API = (CFG.api || '').replace(/\/$/, '');
  const DEV = new URLSearchParams(location.search).get('dev');
  const I18N = window.I18N;
  const $app = document.getElementById('app');
  const $modal = document.getElementById('modal-root');
  const LET = ['A', 'B', 'C', 'D'];
  const ICON = '<svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"><path d="M5 20L10 4M19 20L14 4M12 8v2m0 4v2m0 4v1"/></svg>';

  // ------------------------------------------------------------------ сақтау
  const mk = area => ({
    get(k, d) { try { const v = window[area].getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { window[area].setItem(k, JSON.stringify(v)); } catch (e) { /* толы */ } },
    del(k) { try { window[area].removeItem(k); } catch (e) { /* жоқ */ } },
  });
  const store = mk('localStorage');

  const tgLang = inTg && W.initDataUnsafe && W.initDataUnsafe.user ? (W.initDataUnsafe.user.language_code || '') : (navigator.language || '');
  const S = {
    lang: store.get('qp_lang', null) || (/^(ru|uk|be)/.test(tgLang) ? 'ru' : 'kk'),
    me: null, cat: store.get('qp_cat', 'B') === 'BC' ? 'BC' : 'B', screen: 'boot', err: null,
    exam: null, result: null, filter: 'wrong', practice: null, ai: {}, topics: {},
    P: {st: {}, bm: [], hist: [], recent: {B: [], BC: []}, u: 0},
  };

  const t = (k, ...a) => {
    const v = (I18N[S.lang] || I18N.kk)[k];
    return typeof v === 'function' ? v(...a) : (v == null ? k : v);
  };
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const pad = n => String(n).padStart(2, '0');
  const fmtClock = s => `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;
  const fmtDate = ms => {
    const d = new Date(ms);
    try { return d.toLocaleDateString(S.lang === 'ru' ? 'ru-RU' : 'kk-KZ', {day: 'numeric', month: 'short', year: 'numeric'}); } catch (e) { return d.toISOString().slice(0, 10); }
  };
  const topicName = k => (S.topics[k] && S.topics[k][S.lang]) || k;
  const paid = () => !!(S.me && S.me.access.paid);

  const haptic = k => {
    if (!inTg || !W.HapticFeedback) return;
    try {
      if (k === 'sel') W.HapticFeedback.selectionChanged();
      else if (k === 'light') W.HapticFeedback.impactOccurred('light');
      else W.HapticFeedback.notificationOccurred(k);
    } catch (e) { /* ескі нұсқа */ }
  };
  const openLink = url => { if (inTg && W.openLink) W.openLink(url); else window.open(url, '_blank', 'noopener'); };

  // ------------------------------------------------------------------ API
  class ApiError extends Error {
    constructor(status, code) { super(code || 'http_' + status); this.status = status; this.code = code; }
  }
  async function api(path, body, opts) {
    opts = opts || {};
    const ctrl = new AbortController();
    const kill = setTimeout(() => ctrl.abort(), opts.timeout || 80000);
    const slow = opts.quiet ? null : setTimeout(() => loaderText(t('waking')), 3500);
    try {
      const headers = {'Content-Type': 'text/plain;charset=UTF-8'};
      if (DEV) headers['X-Dev-User'] = DEV;
      const res = await fetch(API + path, {
        method: 'POST', headers, signal: ctrl.signal,
        body: JSON.stringify(Object.assign({}, body || {}, {initData: inTg ? W.initData : '', lang: S.lang})),
      });
      let data = null;
      try { data = await res.json(); } catch (e) { /* бос жауап */ }
      if (!res.ok) throw new ApiError(res.status, data && data.error);
      return data;
    } catch (e) {
      if (e instanceof ApiError) throw e;
      throw new ApiError(0, 'network');
    } finally {
      clearTimeout(kill);
      if (slow) clearTimeout(slow);
    }
  }

  function loading(on) {
    let el = document.getElementById('loader');
    if (!on) { if (el) el.remove(); return; }
    if (!el) {
      el = document.createElement('div');
      el.id = 'loader';
      el.className = 'loader';
      el.innerHTML = `<div class="spinner"></div><div class="loader-text">${esc(t('loading'))}</div>`;
      document.body.appendChild(el);
    }
  }
  function loaderText(s) { const el = document.querySelector('#loader .loader-text'); if (el) el.textContent = s; }
  async function withLoader(fn) { loading(true); try { return await fn(); } finally { loading(false); } }

  function toast(msg, kind) {
    document.querySelectorAll('.toast').forEach(x => x.remove());
    const el = document.createElement('div');
    el.className = 'toast ' + (kind || '');
    el.setAttribute('role', 'status');
    el.textContent = msg;
    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(() => { el.classList.remove('show'); setTimeout(() => el.remove(), 300); }, 3200);
  }

  function fail(e) {
    if (e.status === 401) return toast(t('openInTg'), 'bad');
    if (e.status === 402 || e.code === 'paid_only') return openPaywall();
    if (e.code === 'ai_limit') return toast(t('aiLimit'));
    if (e.code === 'ai_failed' || e.code === 'ai_off') return toast(t('aiErr'), 'bad');
    if (e.status === 429) return toast(t('tooFast'), 'bad');
    toast(t('netError'), 'bad');
  }

  // ------------------------------------------------------------------ прогресс (Telegram CloudStorage + localStorage)
  const CS = inTg && W.CloudStorage && W.isVersionAtLeast && W.isVersionAtLeast('6.9') ? W.CloudStorage : null;
  const csGet = keys => new Promise(res => { try { CS.getItems(keys, (err, v) => res(err ? null : v)); } catch (e) { res(null); } });
  const csSet = (k, v) => new Promise(res => { try { CS.setItem(k, v, err => res(!err)); } catch (e) { res(false); } });

  function normalize(p) {
    p = p && typeof p === 'object' ? p : {};
    return {
      st: p.st && typeof p.st === 'object' ? p.st : {}, bm: Array.isArray(p.bm) ? p.bm : [],
      hist: Array.isArray(p.hist) ? p.hist : [], recent: Object.assign({B: [], BC: []}, p.recent || {}), u: p.u || 0,
    };
  }
  async function loadProgress() {
    let p = store.get('qp_prog', null);
    if (CS) {
      const head = await Promise.race([csGet(['pn']), sleep(2500).then(() => null)]);
      const n = head ? parseInt(head.pn, 10) : 0;
      if (n > 0 && n < 60) {
        const keys = Array.from({length: n}, (_, i) => 'p' + i);
        const v = await Promise.race([csGet(keys), sleep(3000).then(() => null)]);
        if (v) {
          try {
            const cp = JSON.parse(keys.map(k => v[k] || '').join(''));
            if (cp && (!p || (cp.u || 0) >= (p.u || 0))) p = cp;
          } catch (e) { /* бүлінген — жергілікті нұсқа қалады */ }
        }
      }
    }
    S.P = normalize(p);
  }
  let saveTimer = null;
  function saveProgress() {
    S.P.u = Date.now();
    store.set('qp_prog', S.P);
    clearTimeout(saveTimer);
    saveTimer = setTimeout(pushCloud, 1500);
  }
  async function pushCloud() {
    if (!CS) return;
    const s = JSON.stringify(S.P);
    const parts = [];
    for (let i = 0; i < s.length; i += 4000) parts.push(s.slice(i, i + 4000));
    for (let i = 0; i < parts.length; i++) await csSet('p' + i, parts[i]);
    await csSet('pn', String(parts.length));
  }
  function record(qid, ok) {
    const r = S.P.st[qid] || [0, 0, 0];
    r[0] += 1;
    if (ok) r[1] += 1;
    r[2] = ok ? 1 : 0;
    S.P.st[qid] = r;
  }
  const mistakeIds = () => Object.keys(S.P.st).filter(k => S.P.st[k][2] === 0);
  const knownCount = () => Object.keys(S.P.st).filter(k => S.P.st[k][2] === 1).length;
  function readiness() {
    const total = S.me ? S.me.bank.total : 1;
    const k = Math.min(1, knownCount() / total);
    const h = S.P.hist.slice(0, 5);
    if (!h.length) return Math.round(100 * k);
    const avg = h.reduce((a, x) => a + x.s / x.n, 0) / h.length;
    return Math.round(100 * (0.5 * k + 0.5 * avg));
  }
  function toggleBm(qid) {
    const i = S.P.bm.indexOf(qid);
    if (i >= 0) S.P.bm.splice(i, 1); else S.P.bm.unshift(qid);
    S.P.bm = S.P.bm.slice(0, 300);
    saveProgress();
    haptic('light');
    render();
  }

  // ------------------------------------------------------------------ емтихан сеансын сақтау (қайта ашқанда жалғастыру)
  const saveExam = () => store.set('qp_exam', S.exam);
  const clearExam = () => store.del('qp_exam');
  function loadExam() {
    const e = store.get('qp_exam', null);
    if (!e || !e.token || !Array.isArray(e.questions) || e.endAt < Date.now() - 5000) { clearExam(); return null; }
    e.finishing = false;
    return e;
  }

  // ------------------------------------------------------------------ навигация
  function go(screen) {
    S.screen = screen;
    render();
    window.scrollTo({top: 0, left: 0, behavior: 'instant'});
  }
  function back() {
    if ($modal.innerHTML) return closeModal();
    if (S.screen === 'exam') return confirmExit();
    if (S.screen === 'practice' && S.practice) return go(S.practice.from || 'home');
    if (S.screen !== 'home' && S.me) return go('home');
  }

  let timerId = null;
  const remaining = () => (S.exam ? Math.max(0, Math.round((S.exam.endAt - Date.now()) / 1000)) : 0);
  function stopTimer() { if (timerId) clearInterval(timerId); timerId = null; }
  function startTimer() {
    if (timerId) return;
    timerId = setInterval(() => {
      if (!S.exam || S.screen !== 'exam') return stopTimer();
      const r = remaining();
      const el = document.getElementById('timer');
      if (el) { el.textContent = fmtClock(r); el.classList.toggle('warning', r <= 300); }
      if (r <= 0) { stopTimer(); finishExam(true); }
    }, 1000);
  }

  const SCREENS = {};
  function render() {
    const fn = SCREENS[S.screen] || SCREENS.home;
    $app.innerHTML = fn();
    document.documentElement.lang = S.lang === 'ru' ? 'ru' : 'kk';
    if (inTg && W.BackButton) {
      try { if (S.screen === 'home' || S.screen === 'error' || S.screen === 'boot') W.BackButton.hide(); else W.BackButton.show(); } catch (e) { /* ескі нұсқа */ }
    }
    if (S.screen === 'exam') startTimer(); else stopTimer();
  }

  // ------------------------------------------------------------------ жалпы бөліктер
  const topbar = () => `
    <header class="topbar">
      <div class="logo"><div class="logo-icon">${ICON}</div><div><div class="logo-title">QAZAQ PDD</div><div class="logo-caption">${t('caption')}</div></div></div>
      <div class="top-actions">
        <button class="ghost-link" data-act="lang" aria-label="${t('otherLang')}">${t('otherLang')}</button>
        <button class="ghost-link round" data-act="info" aria-label="${esc(t('termsTitle'))}">i</button>
      </div>
    </header>`;
  const subhead = (title, right) => `
    <div class="sub-top">
      <button class="back-button" data-act="back" aria-label="${t('back')}">←</button>
      <div class="sub-title">${esc(title)}</div>
      ${right || '<span class="sub-spacer"></span>'}
    </div>`;
  const qimg = q => `<div class="image-wrap"><img src="./assets/q-${esc(q.id)}.svg" alt="" decoding="async"><span class="image-label">${t('picture')}</span></div>`;
  const refLine = r => (r ? `<div class="ref">📖 ${esc(r)}</div>` : '');
  const lockBanner = (f, total) => `
    <div class="lock-banner"><span>🔒 ${esc(t('lockedNote', f, total))}</span>
    <button class="small-button accent" data-act="buy">${t('unlock')}</button></div>`;

  function aiBlock(src, qid, choice) {
    if (!S.me || !S.me.ai) return '';
    if (!paid()) return `<button class="ai-btn locked" data-act="buy">✦ ${t('why')} · 🔒</button>`;
    const k = `${src}:${qid}:${choice}`;
    const s = S.ai[k];
    if (s && s.text) return `<div class="ai-box"><div class="ai-head">✦ AI</div>${esc(s.text)}<div class="ai-note">${t('aiNote')}</div></div>`;
    if (s && s.loading) return `<div class="ai-box loading"><span class="dot-pulse"></span> ${t('whyLoading')}</div>`;
    return `<button class="ai-btn" data-act="ai" data-src="${src}" data-q="${esc(qid)}" data-c="${choice == null ? '' : choice}">✦ ${t('why')}</button>`;
  }
  async function explain(el) {
    const src = el.dataset.src, qid = el.dataset.q, choice = el.dataset.c === '' ? null : +el.dataset.c;
    const token = src === 'p' ? S.practice && S.practice.token : S.result && S.result.exam.token;
    if (!token) return;
    const k = `${src}:${qid}:${choice}`;
    S.ai[k] = {loading: true};
    render();
    try {
      const d = await api('/api/explain', {token, qid, choice}, {quiet: true, timeout: 45000});
      S.ai[k] = {text: d.text};
    } catch (e) {
      delete S.ai[k];
      fail(e);
    }
    render();
  }

  // ------------------------------------------------------------------ басты бет
  SCREENS.boot = () => `<div class="app-shell">${topbar()}<div class="boot"><div class="spinner"></div></div></div>`;

  SCREENS.error = () => {
    const notTg = S.err && S.err.status === 401;
    const bot = (S.me && S.me.bot) || CFG.bot;
    return `<div class="app-shell">${topbar()}
      <section class="error-box">
        <div class="err-icon">${notTg ? '📱' : '⚠️'}</div>
        <h2>${notTg ? t('openInTgTitle') : t('netError')}</h2>
        ${notTg ? `<p>${t('openInTg')}</p>${bot ? `<button class="main-button" data-act="botlink">@${esc(bot)}</button>` : ''}` : `<p>${t('wakeHint')}</p><button class="main-button" data-act="retry">${t('retry')}</button>`}
      </section></div>`;
  };

  SCREENS.home = () => {
    const me = S.me, a = me.access, bank = me.bank, ex = me.exam;
    const isB = S.cat === 'B';
    const hist = S.P.hist;
    const r = readiness();
    const last5 = hist.slice(0, 5);
    const passed = last5.filter(h => h.p).length;
    const mist = mistakeIds().length;
    const marathonN = a.paid ? (isB ? bank.g : bank.total) : (isB ? bank.free_g : bank.free);
    const visibleTopics = bank.topics.filter(tp => !isB || tp.g > 0).length;

    const access = a.paid
      ? `<section class="access-card paid"><div class="access-icon">✓</div><div><div class="access-title">${a.admin ? t('admin') : t('full')}</div>
           <div class="access-sub">${a.until ? t('fullUntil', fmtDate(a.until * 1000)) : t('fullForever')}</div></div></section>`
      : `<section class="access-card"><div class="access-row"><div class="access-icon free">★</div><div><div class="access-title">${t('free')}</div>
           <div class="access-sub">${t('freeText', bank.free, bank.total)}</div></div></div>
           <button class="main-button buy" data-act="buy">${t('buy', me.price.stars)}</button></section>`;

    const modes = [
      ['topics', '📚', t('mTopics'), t('mTopicsD', visibleTopics)],
      ['mistakes', '🎯', t('mMistakes'), t('mMistakesD', mist)],
      ['marathon', '🏁', t('mMarathon'), t('mMarathonD', marathonN)],
      ['marked', '★', t('mMarked'), t('mMarkedD', S.P.bm.length)],
      ['signs', '⛔', t('mSigns'), t('mSignsD')],
      ['guide', '🪪', t('mGuide'), t('mGuideD')],
    ];

    return `<div class="app-shell">${topbar()}
      <section class="hero">
        <div class="hero-backdrop"></div>
        <div class="overline">${t('heroOver')}</div>
        <h1>${t('heroTitle')}</h1>
        <p>${t('heroText')}</p>
        <div class="hero-bottom"><span class="mini-badge">${t('questionsBadge', bank.total)}</span><span class="mini-badge">${t('refBadge')}</span></div>
      </section>
      ${access}
      <section class="ready-card">
        <div class="ready-top"><span>${t('readiness')}</span><b>${r}%</b></div>
        <div class="progress-track big"><div class="progress-fill" style="width:${r}%"></div></div>
        <div class="ready-sub">${t('known', knownCount(), bank.total)} · ${hist.length ? t('passedLast', passed, last5.length) : t('noExams')}</div>
      </section>
      <div class="title-row"><h2 class="section-title">${t('pickCat')}</h2></div>
      <div class="category-grid">
        <button class="category-button ${isB ? 'active' : ''}" data-act="cat" data-c="B" aria-pressed="${isB}"><span class="category-symbol">${t('catB')}</span><span class="category-description">${t('catBDesc')}</span></button>
        <button class="category-button ${!isB ? 'active' : ''}" data-act="cat" data-c="BC" aria-pressed="${!isB}"><span class="category-symbol">${t('catBC')}</span><span class="category-description">${t('catBCDesc')}</span></button>
      </div>
      <div class="stat-row">
        <div class="stat"><div class="stat-number">${ex.count}</div><div class="stat-caption">${t('statQ')}</div></div>
        <div class="stat"><div class="stat-number">${ex.minutes}′</div><div class="stat-caption">${t('statT')}</div></div>
        <div class="stat"><div class="stat-number">${ex.pass}</div><div class="stat-caption">${t('statP')}</div></div>
      </div>
      <button class="main-button" data-act="start">${t('startExam')} <span aria-hidden="true">→</span></button>
      <div class="title-row"><h2 class="section-title">${t('modes')}</h2></div>
      <div class="mode-grid">${modes.map(m => `
        <button class="mode-card" data-act="${m[0]}"><span class="mode-icon">${m[1]}</span><span class="mode-name">${esc(m[2])}</span><span class="mode-desc">${esc(m[3])}</span></button>`).join('')}
      </div>
      ${inTg ? `<button class="toggle-row" data-act="daily" aria-pressed="${!!me.daily}">
        <span><b>🔔 ${t('daily')}</b><small>${t('dailyHint')}</small></span><span class="switch ${me.daily ? 'on' : ''}"><i></i></span></button>` : ''}
      ${hist.length ? `<div class="title-row"><h2 class="section-title">${t('lastResults')}</h2></div>
        ${hist.slice(0, 3).map(h => `<div class="last-result"><div><strong class="${h.p ? 'yes' : 'no'}">${h.s}/${h.n}</strong> <span>${h.c === 'B' ? 'B' : 'B + C1/C'} · ${h.p ? t('passShort') : t('failShort')}</span></div><span>${fmtDate(h.t)}</span></div>`).join('')}` : ''}
      <p class="footnote">${t('disclaimer')}</p>
      <div class="foot-links"><button class="link-btn" data-act="info">${t('termsLink')}</button></div>
    </div>`;
  };

  // ------------------------------------------------------------------ емтихан
  async function startExam() {
    if (S.exam) return go('exam');
    let d;
    try { d = await withLoader(() => api('/api/exam/start', {cat: S.cat, recent: (S.P.recent[S.cat] || []).slice(0, 160)})); } catch (e) { return fail(e); }
    S.exam = {
      token: d.token, cat: d.cat, free: d.free, questions: d.questions,
      answers: d.questions.map(() => null), marked: [], idx: 0,
      endAt: Date.now() + (d.deadline - d.started) * 1000, startedAt: Date.now(),
    };
    saveExam();
    if (inTg && W.enableClosingConfirmation) try { W.enableClosingConfirmation(); } catch (e) { /* */ }
    go('exam');
  }

  SCREENS.exam = () => {
    const E = S.exam, n = E.questions.length, q = E.questions[E.idx];
    const done = E.answers.filter(x => x !== null).length;
    const marked = E.marked.includes(E.idx);
    const rem = remaining();
    return `<div class="app-shell">
      <div class="exam-sticky-top">
        <div class="exam-header">
          <button class="back-button" data-act="back" aria-label="${t('exit')}">✕</button>
          <div class="exam-header-center"><span class="header-mini">${t('examRunning')}</span><span class="header-major">${t('catLabel', E.cat)}</span></div>
          <div class="timer ${rem <= 300 ? 'warning' : ''}" id="timer" role="timer">${fmtClock(rem)}</div>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width:${done / n * 100}%"></div></div>
      </div>
      <main class="exam-body">
        <div class="question-top">
          <div><div class="question-count"><b>${E.idx + 1}</b> / ${n}</div><div class="question-sub">${t('answered', done)}</div></div>
          <span class="topic">${esc(topicName(q.topic))}</span>
        </div>
        ${q.image ? qimg(q) : ''}
        <h2 class="question-title">${esc(q.text)}</h2>
        <div class="answer-list">${q.options.map((o, i) => {
          const sel = E.answers[E.idx] === i;
          return `<button class="answer-button ${sel ? 'selected' : ''}" data-act="answer" data-i="${i}" aria-pressed="${sel}"><span class="answer-letter">${LET[i]}</span><span class="answer-text">${esc(o)}</span>${sel ? '<span class="selected-dot"></span>' : ''}</button>`;
        }).join('')}</div>
        <button class="mark-button ${marked ? 'active' : ''}" data-act="mark">${marked ? t('markOn') : t('markOff')}</button>
        ${E.free ? `<div class="footer-hint">${t('freeExamNote')}</div>` : ''}
        <div class="footer-hint">${t('hintLater')}</div>
      </main>
      <nav class="exam-bottom">
        <button class="nav-btn" data-act="prev" ${E.idx === 0 ? 'disabled' : ''} aria-label="${t('prev')}">←</button>
        <button class="nav-btn" data-act="grid" aria-label="${t('grid')}">▦ <span class="number-badge">${done}/${n}</span></button>
        ${E.idx === n - 1
          ? `<button class="nav-btn nav-btn-next" data-act="finishAsk">${t('finish')}</button>`
          : `<button class="nav-btn nav-btn-next" data-act="next">${t('next')}</button>`}
      </nav>
    </div>`;
  };

  function openGrid() {
    const E = S.exam, done = E.answers.filter(x => x !== null).length;
    modal(`<h2 class="modal-title">${t('grid')}</h2>
      <p class="modal-description">${t('gridText', done)}</p>
      <div class="legend"><span><i></i>${t('lgDone')}</span><span><i class="empty"></i>${t('lgEmpty')}</span><span><i class="marked"></i>${t('lgMarked')}</span></div>
      <div class="question-grid">${E.questions.map((_, i) => `<button class="grid-number ${E.answers[i] !== null ? 'done' : ''} ${i === E.idx ? 'current' : ''} ${E.marked.includes(i) ? 'marked' : ''}" data-act="jump" data-i="${i}">${i + 1}</button>`).join('')}</div>
      <div class="modal-buttons"><button class="small-button" data-act="close">${t('close')}</button><button class="main-button" data-act="finishAsk">${t('finish')}</button></div>`);
  }
  function finishAsk() {
    const missing = S.exam.answers.filter(x => x === null).length;
    modal(`<h2 class="modal-title">${t('finishQ')}</h2>
      <p class="modal-description">${missing ? t('finishMissing', missing) : ''}${t('finishText')}</p>
      <div class="modal-buttons"><button class="small-button" data-act="close">${t('cont')}</button><button class="main-button" data-act="finish">${t('finish')}</button></div>`);
  }
  function confirmExit() {
    modal(`<h2 class="modal-title">${t('exitQ')}</h2><p class="modal-description">${t('exitText')}</p>
      <div class="modal-buttons"><button class="small-button" data-act="close">${t('stay')}</button><button class="main-button danger" data-act="exitExam">${t('exit')}</button></div>`);
  }
  function exitExam() {
    S.exam = null;
    clearExam();
    closeModal();
    if (inTg && W.disableClosingConfirmation) try { W.disableClosingConfirmation(); } catch (e) { /* */ }
    go('home');
  }

  async function finishExam(timeout) {
    const E = S.exam;
    if (!E || E.finishing) return;
    E.finishing = true;
    closeModal();
    let d;
    try {
      d = await withLoader(() => api('/api/exam/finish', {token: E.token, answers: E.answers}));
    } catch (e) {
      E.finishing = false;
      fail(e);
      if (timeout) render();
      return;
    }
    d.items.forEach(it => record(it.id, it.answer !== null && it.answer === it.correct));
    S.P.hist.unshift({t: Date.now(), c: E.cat, s: d.score, n: d.total, p: d.passed ? 1 : 0});
    S.P.hist = S.P.hist.slice(0, 20);
    S.P.recent[E.cat] = E.questions.map(q => q.id).concat(S.P.recent[E.cat] || []).slice(0, 160);
    saveProgress();
    S.result = {exam: E, res: d, timeout: !!timeout, elapsed: Math.min(d.elapsed, Math.round((Date.now() - (E.startedAt || Date.now())) / 1000) || d.elapsed)};
    S.filter = d.score === d.total ? 'all' : 'wrong';
    S.ai = {};
    S.exam = null;
    clearExam();
    if (inTg && W.disableClosingConfirmation) try { W.disableClosingConfirmation(); } catch (e) { /* */ }
    haptic(d.passed ? 'success' : 'error');
    go('result');
  }

  SCREENS.result = () => {
    const {exam: E, res: d, timeout} = S.result;
    const pct = Math.round(d.score / d.total * 100);
    const blank = d.items.filter(it => it.answer === null).length;
    const wrongN = d.total - d.score;
    const rows = d.items.map((it, i) => ({it, q: E.questions[i], i})).filter(x => S.filter === 'all' || x.it.answer !== x.it.correct);
    return `<div class="app-shell">${subhead(t('resultTitle'))}
      <section class="result-hero ${d.passed ? '' : 'fail'}">
        <div class="overline">${timeout ? t('timeout') : t('examDone')}</div>
        <div class="result-ring" style="--ring-progress:${pct}%"><div class="ring-inner"><strong>${d.score}</strong><span>/ ${d.total}</span></div></div>
        <h1>${d.passed ? t('congrats') : t('again')}</h1>
        <p>${d.passed ? t('passText') : t('failText', S.me.exam.pass)}</p>
        <p>${t('spent', fmtClock(S.result.elapsed))} · ${t('accuracy', pct)}</p>
      </section>
      <div class="result-stats">
        <div class="result-stat"><strong class="yes">${d.score}</strong><span>${t('right')}</span></div>
        <div class="result-stat"><strong class="no">${wrongN - blank}</strong><span>${t('wrong')}</span></div>
        <div class="result-stat"><strong>${blank}</strong><span>${t('blank')}</span></div>
      </div>
      <div class="result-actions">
        <button class="small-button" data-act="home">${t('home')}</button>
        <button class="main-button" data-act="newExam">${t('newExam')}</button>
      </div>
      ${wrongN ? `<button class="small-button wide" data-act="examMistakes">🎯 ${t('toMistakes')} (${wrongN})</button>` : ''}
      <p class="footnote">${t('resultNote')}</p>
      <div class="review-header">
        <h2 class="section-title">${t('review')}</h2>
        <div class="review-filter">
          <button class="pill ${S.filter === 'wrong' ? 'active' : ''}" data-act="filter" data-f="wrong">${t('fWrong', wrongN)}</button>
          <button class="pill ${S.filter === 'all' ? 'active' : ''}" data-act="filter" data-f="all">${t('fAll')}</button>
        </div>
      </div>
      ${rows.length ? rows.map(({it, q, i}) => {
        const ok = it.answer !== null && it.answer === it.correct;
        return `<article class="review-card">
          <div class="review-top"><span class="review-num">${t('qN', i + 1)} · ${esc(topicName(q.topic))}</span>
            <span class="review-status ${ok ? 'correct' : 'wrong'}">${ok ? '✓ ' + t('right') : (it.answer === null ? '— ' + t('blank') : '✕ ' + t('wrong'))}</span></div>
          ${q.image ? `<img class="review-image" src="./assets/q-${esc(q.id)}.svg" alt="" loading="lazy">` : ''}
          <h3>${esc(q.text)}</h3>
          ${ok ? '' : `<div class="review-choice ${it.answer === null ? '' : 'wrong'}"><b>${t('yourAns')}</b> ${it.answer === null ? t('notChosen') : esc(LET[it.answer] + ') ' + q.options[it.answer])}</div>`}
          <div class="review-choice right"><b>${t('correctAns')}</b> ${esc(LET[it.correct] + ') ' + q.options[it.correct])}</div>
          <div class="explain"><b>${t('explain')}</b> ${esc(it.why)}${refLine(it.ref)}</div>
          ${ok ? '' : aiBlock('r', it.id, it.answer)}
          <button class="mark-button ${S.P.bm.includes(q.id) ? 'active' : ''}" data-act="bm" data-q="${esc(q.id)}">${S.P.bm.includes(q.id) ? t('bookmarked') : t('bookmark')}</button>
        </article>`;
      }).join('') : `<div class="empty-box">${t('allRight')}</div>`}
    </div>`;
  };

  // ------------------------------------------------------------------ жаттығу
  async function startPractice(opts, title, from, lockInfo) {
    let d;
    try { d = await withLoader(() => api('/api/practice', opts)); } catch (e) { return fail(e); }
    if (!d.questions.length) {
      if (!paid()) return openPaywall();
      return toast(t('emptySet'));
    }
    S.practice = {opts, title, from, lockInfo: d.free && lockInfo ? lockInfo : null, token: d.token, qs: d.questions, idx: 0, res: {}, pending: null, done: false};
    S.ai = {};
    go('practice');
  }

  async function pick(i) {
    const P = S.practice, q = P.qs[P.idx];
    if (P.res[q.id] || P.pending !== null) return;
    P.pending = i;
    haptic('sel');
    render();
    try {
      const r = await api('/api/check', {token: P.token, qid: q.id, choice: i}, {quiet: true, timeout: 30000});
      r.choice = i;
      P.res[q.id] = r;
      record(q.id, r.ok);
      saveProgress();
      haptic(r.ok ? 'success' : 'error');
    } catch (e) {
      fail(e);
    }
    P.pending = null;
    render();
  }
  function pnext() {
    const P = S.practice;
    if (P.idx >= P.qs.length - 1) { P.done = true; go('practice'); return; }
    P.idx += 1;
    go('practice');
  }

  SCREENS.practice = () => {
    const P = S.practice;
    if (P.done) return practiceDone();
    const n = P.qs.length, q = P.qs[P.idx], r = P.res[q.id];
    const vals = Object.values(P.res), right = vals.filter(x => x.ok).length;
    const bm = S.P.bm.includes(q.id);
    return `<div class="app-shell">
      <div class="exam-sticky-top">
        <div class="exam-header">
          <button class="back-button" data-act="back" aria-label="${t('back')}">←</button>
          <div class="exam-header-center"><span class="header-mini clip">${esc(P.title)}</span><span class="header-major">${t('qOf', P.idx + 1, n)}</span></div>
          <div class="score-chip"><span class="yes">✓ ${right}</span> <span class="no">✕ ${vals.length - right}</span></div>
        </div>
        <div class="progress-track"><div class="progress-fill" style="width:${(P.idx + (r ? 1 : 0)) / n * 100}%"></div></div>
      </div>
      <main class="exam-body">
        ${P.idx === 0 && P.lockInfo ? lockBanner(P.lockInfo[0], P.lockInfo[1]) : ''}
        <div class="question-top">
          <span class="topic">${esc(topicName(q.topic))}</span>
          <button class="mark-button inline ${bm ? 'active' : ''}" data-act="bm" data-q="${esc(q.id)}">${bm ? t('bookmarked') : t('bookmark')}</button>
        </div>
        ${q.image ? qimg(q) : ''}
        <h2 class="question-title">${esc(q.text)}</h2>
        <div class="answer-list">${q.options.map((o, i) => {
          let cls = '';
          if (r) cls = i === r.correct ? 'right' : (i === r.choice ? 'wrong' : 'dim');
          else if (P.pending === i) cls = 'selected';
          const mark = r && i === r.correct ? '<span class="res-mark">✓</span>' : (r && i === r.choice ? '<span class="res-mark">✕</span>' : '');
          return `<button class="answer-button ${cls}" data-act="pick" data-i="${i}" ${r || P.pending !== null ? 'disabled' : ''}><span class="answer-letter">${LET[i]}</span><span class="answer-text">${esc(o)}</span>${mark}</button>`;
        }).join('')}</div>
        ${r ? `<div class="feedback ${r.ok ? 'ok' : 'bad'}">
            <div class="fb-title">${r.ok ? t('correct') : t('incorrect')}</div>
            <div class="fb-why">${esc(r.why)}</div>${refLine(r.ref)}
            ${r.ok ? '' : aiBlock('p', q.id, r.choice)}
          </div>` : `<div class="footer-hint">${t('pickHint')}</div>`}
      </main>
      ${r ? `<nav class="exam-bottom single"><button class="nav-btn nav-btn-next" data-act="pnext">${P.idx === n - 1 ? t('finishPr') : t('nextQ')}</button></nav>` : ''}
    </div>`;
  };

  function practiceDone() {
    const P = S.practice, vals = Object.values(P.res), right = vals.filter(x => x.ok).length;
    const pct = vals.length ? Math.round(right / vals.length * 100) : 0;
    const wrongIds = Object.keys(P.res).filter(k => !P.res[k].ok);
    return `<div class="app-shell">${subhead(P.title)}
      <section class="result-hero ${pct >= 80 ? '' : 'fail'}">
        <div class="overline">${t('prDone')}</div>
        <div class="result-ring" style="--ring-progress:${pct}%"><div class="ring-inner"><strong>${pct}%</strong><span>${right}/${vals.length}</span></div></div>
        <p>${t('prScore', right, vals.length)}</p>
      </section>
      ${P.lockInfo ? lockBanner(P.lockInfo[0], P.lockInfo[1]) : ''}
      <div class="result-actions">
        <button class="small-button" data-act="home">${t('home')}</button>
        <button class="main-button" data-act="prestart">↻ ${t('again2')}</button>
      </div>
      ${wrongIds.length ? `<button class="small-button wide" data-act="pmistakes">🎯 ${t('toMistakes')} (${wrongIds.length})</button>` : ''}
    </div>`;
  }

  function openTopic(k) {
    const tp = S.me.bank.topics.find(x => x.key === k);
    if (!tp) return;
    const isB = S.cat === 'B';
    const total = isB ? tp.g : tp.total, free = isB ? tp.free_g : tp.free;
    if (!paid() && !free) return openPaywall();
    startPractice({mode: 'topic', topic: k, cat: isB ? 'g' : undefined}, tp[S.lang], 'topics', [free, total]);
  }

  SCREENS.topics = () => {
    const isB = S.cat === 'B', p = paid();
    const rows = S.me.bank.topics.filter(tp => !isB || tp.g > 0);
    return `<div class="app-shell">${subhead(t('topicsTitle'), `<span class="cat-chip">${isB ? 'B' : 'B+C'}</span>`)}
      <p class="screen-note">${t('topicsNote')}</p>
      <div class="topic-list">${rows.map(tp => {
        const total = isB ? tp.g : tp.total, free = isB ? tp.free_g : tp.free;
        const locked = !p && !free;
        return `<button class="topic-row ${locked ? 'locked' : ''}" data-act="topic" data-k="${esc(tp.key)}">
          <span class="tr-name">${esc(tp[S.lang])}</span>
          <span class="tr-count">${locked ? '🔒 ' : ''}${t('topicCount', total, free, p)}</span><span class="tr-arrow">›</span></button>`;
      }).join('')}</div>
      ${p ? '' : `<button class="main-button buy" data-act="buy">${t('buy', S.me.price.stars)}</button>`}
    </div>`;
  };

  // ------------------------------------------------------------------ анықтамалықтар
  SCREENS.signs = () => {
    const groups = {};
    (window.SIGNS_INFO || []).forEach(s => (groups[s.g] = groups[s.g] || []).push(s));
    return `<div class="app-shell">${subhead(t('signsTitle'))}
      ${Object.keys(groups).map(g => `<h3 class="group-title">${esc(window.SIGN_GROUPS[g][S.lang])}</h3>
        <div class="sign-list">${groups[g].map(s => `<div class="sign-card"><img src="./assets/signs/${s.id}.svg" alt="" loading="lazy"><div><b>${esc(s[S.lang][0])}</b><p>${esc(s[S.lang][1])}</p></div></div>`).join('')}</div>`).join('')}
      <p class="footnote">${t('signsNote')}</p>
    </div>`;
  };

  SCREENS.guide = () => {
    const G = window.GUIDE;
    return `<div class="app-shell">${subhead(t('guideTitle'))}
      <div class="steps">${G[S.lang].map(s => `<div class="step"><div class="step-num">${esc(s[0])}</div><div><b>${esc(s[1])}</b><p>${esc(s[2])}</p></div></div>`).join('')}</div>
      <h3 class="group-title">${t('links')}</h3>
      ${G.links.map((l, i) => `<button class="link-row" data-act="link" data-i="${i}"><span>${esc(l[0])}</span><span>↗</span></button>`).join('')}
      <p class="footnote">${t('guideNote')}</p>
    </div>`;
  };

  // ------------------------------------------------------------------ модальдар
  function modal(html) {
    $modal.innerHTML = `<div class="modal-screen" data-act="modalBg"><div class="modal-sheet" role="dialog" aria-modal="true"><div class="modal-handle"></div>${html}</div></div>`;
  }
  function closeModal() { $modal.innerHTML = ''; }

  function openPaywall() {
    const me = S.me;
    if (!me) return;
    if (paid()) return toast(t('payOk'), 'good');
    modal(`<div class="pay-badge">⭐</div>
      <h2 class="modal-title center">${t('payTitle')}</h2>
      <p class="modal-description center">${t('payPrice', me.price.stars, me.price.days)}</p>
      <ul class="feature-list">${t('payFeatures', me.bank.total, me.ai).map(f => `<li>${esc(f)}</li>`).join('')}</ul>
      ${inTg ? `<button class="main-button" data-act="pay">${t('payBtn')}</button>` : `<p class="modal-description">${t('payNeedTg')}</p>`}
      <button class="small-button wide" data-act="close">${t('close')}</button>
      <p class="footnote">${t('payTerms')}</p>`);
  }
  async function pay() {
    let d;
    try { d = await withLoader(() => api('/api/invoice', {})); } catch (e) { return fail(e); }
    if (!W || !W.openInvoice) return toast(t('payNeedTg'), 'bad');
    W.openInvoice(d.link, async status => {
      if (status === 'paid') {
        closeModal();
        loading(true);
        loaderText(t('payWait'));
        for (let i = 0; i < 10; i++) {
          await sleep(1500);
          try {
            const me = await api('/api/me', {}, {quiet: true});
            S.me = me;
            if (me.access.paid) break;
          } catch (e) { /* қайталаймыз */ }
        }
        loading(false);
        if (paid()) { toast(t('payOk'), 'good'); haptic('success'); } else toast(t('payLate'));
        render();
      } else if (status === 'failed') {
        toast(t('payFail'), 'bad');
      }
    });
  }

  function openInfo() {
    const me = S.me;
    modal(`<h2 class="modal-title">${t('termsTitle')}</h2>
      <div class="terms">${t('termsBody', me ? me.price.stars : 0, me ? me.price.days : 0, me && me.bot ? '@' + me.bot : '')}</div>
      <div class="modal-buttons"><button class="small-button" data-act="resetAsk">${t('resetProgress')}</button><button class="main-button" data-act="close">${t('close')}</button></div>`);
  }
  function resetAsk() {
    modal(`<h2 class="modal-title">${t('resetProgress')}</h2><p class="modal-description">${t('resetQ')}</p>
      <div class="modal-buttons"><button class="small-button" data-act="close">${t('stay')}</button><button class="main-button danger" data-act="resetGo">${t('reset')}</button></div>`);
  }
  function resetGo() {
    S.P = normalize(null);
    saveProgress();
    closeModal();
    toast(t('resetDone'));
    go('home');
  }

  async function toggleDaily() {
    try {
      const d = await api('/api/daily', {on: !S.me.daily}, {quiet: true});
      S.me.daily = d.daily;
      haptic('light');
      toast(d.daily ? t('dailyOnMsg') : t('dailyOffMsg'));
      render();
    } catch (e) { fail(e); }
  }

  // ------------------------------------------------------------------ әрекеттер
  const A = {
    lang() { S.lang = S.lang === 'kk' ? 'ru' : 'kk'; store.set('qp_lang', S.lang); haptic('sel'); render(); },
    info: openInfo, buy: openPaywall, pay, close: closeModal, back, retry: boot,
    home: () => go('home'),
    botlink() { const bot = (S.me && S.me.bot) || CFG.bot; if (bot) openLink('https://t.me/' + bot); },
    cat(el) { S.cat = el.dataset.c === 'BC' ? 'BC' : 'B'; store.set('qp_cat', S.cat); haptic('sel'); render(); },
    start: startExam, newExam: startExam,
    answer(el) { const E = S.exam; E.answers[E.idx] = +el.dataset.i; saveExam(); haptic('sel'); render(); },
    mark() { const E = S.exam, i = E.marked.indexOf(E.idx); if (i >= 0) E.marked.splice(i, 1); else E.marked.push(E.idx); saveExam(); haptic('light'); render(); },
    prev() { if (S.exam.idx > 0) { S.exam.idx -= 1; saveExam(); go('exam'); } },
    next() { if (S.exam.idx < S.exam.questions.length - 1) { S.exam.idx += 1; saveExam(); go('exam'); } },
    grid: openGrid,
    jump(el) { S.exam.idx = +el.dataset.i; saveExam(); closeModal(); go('exam'); },
    finishAsk, finish: () => finishExam(false), exitExam,
    filter(el) { S.filter = el.dataset.f; render(); },
    examMistakes() {
      const d = S.result.res;
      startPractice({mode: 'list', ids: d.items.filter(it => it.answer !== it.correct).map(it => it.id)}, t('mMistakes'), 'result');
    },
    topics: () => go('topics'),
    topic: el => openTopic(el.dataset.k),
    mistakes() {
      const ids = mistakeIds();
      if (!ids.length) return toast(t('noMistakes'));
      startPractice({mode: 'list', ids}, t('mMistakes'), 'home');
    },
    marathon() {
      const isB = S.cat === 'B', b = S.me.bank;
      startPractice({mode: 'marathon', cat: isB ? 'g' : undefined}, t('mMarathon'), 'home', [isB ? b.free_g : b.free, isB ? b.g : b.total]);
    },
    marked() {
      if (!S.P.bm.length) return toast(t('noMarked'));
      startPractice({mode: 'list', ids: S.P.bm.slice()}, t('mMarked'), 'home');
    },
    signs: () => go('signs'), guide: () => go('guide'),
    daily: toggleDaily,
    pick: el => pick(+el.dataset.i), pnext,
    prestart() { const P = S.practice; startPractice(P.opts, P.title, P.from, P.lockInfo); },
    pmistakes() {
      const P = S.practice;
      startPractice({mode: 'list', ids: Object.keys(P.res).filter(k => !P.res[k].ok)}, t('mMistakes'), P.from);
    },
    bm: el => toggleBm(el.dataset.q),
    ai: explain,
    link: el => openLink(window.GUIDE.links[+el.dataset.i][1]),
    resetAsk, resetGo,
    modalBg(el, e) { if (e.target === el) closeModal(); },
  };
  document.addEventListener('click', e => {
    const el = e.target.closest('[data-act]');
    if (!el || el.disabled) return;
    const f = A[el.dataset.act];
    if (f) f(el, e);
  });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && $modal.innerHTML) closeModal(); });

  // ------------------------------------------------------------------ іске қосу
  async function boot() {
    S.screen = 'boot';
    render();
    try {
      S.me = await withLoader(() => api('/api/me', {}));
    } catch (e) {
      S.err = e;
      S.screen = 'error';
      return render();
    }
    S.topics = {};
    S.me.bank.topics.forEach(tp => { S.topics[tp.key] = {kk: tp.kk, ru: tp.ru}; });
    const saved = loadExam();
    if (saved) { S.exam = saved; S.screen = 'exam'; } else S.screen = 'home';
    render();
  }

  async function init() {
    if (W) {
      try {
        W.ready();
        W.expand();
        if (W.isVersionAtLeast && W.isVersionAtLeast('6.1')) { W.setHeaderColor('#101925'); W.setBackgroundColor('#101925'); W.BackButton.onClick(back); }
        if (W.isVersionAtLeast && W.isVersionAtLeast('7.7') && W.disableVerticalSwipes) W.disableVerticalSwipes();
      } catch (e) { /* браузерде ашылған */ }
    }
    await loadProgress();
    await boot();
  }
  init();
})();
