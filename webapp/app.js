const QUESTION_BANK = window.QUESTION_BANK;

const tg = window.Telegram?.WebApp;
const APP = document.getElementById('app');
const MODAL = document.getElementById('modal-root');
const SAVE_KEY = 'qazaq-pdd-session-v1';
const HISTORY_KEY = 'qazaq-pdd-results-v1';
const LAST_KEY = 'qazaq-pdd-last-questions-v1';
const COUNT = 40;
const MINUTES = 40;
const PASS = 32;
const LETTERS = ['A','B','C','D'];
let mode = 'BC';
let attempt = null;
let screen = 'home';
let cursor = 0;
let resultFilter = 'wrong';
let timerInterval = null;
let isModalOpen = false;

if (tg) {
  try {
    tg.ready();
    tg.expand();
    tg.setHeaderColor?.('#101925');
    tg.setBackgroundColor?.('#101925');
  } catch (err) { console.warn('Telegram environment:', err); }
}

const escapeHTML = v => String(v).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function storageRead(storage,key,fallback){try{return JSON.parse(storage.getItem(key))??fallback;}catch{return fallback;}}
function saveAttempt(){try{sessionStorage.setItem(SAVE_KEY,JSON.stringify(attempt));}catch{}}
function cleanupAttempt(){try{sessionStorage.removeItem(SAVE_KEY);}catch{}}
function fmt(seconds){const total=Math.max(0,Math.ceil(seconds));return `${String(Math.floor(total/60)).padStart(2,'0')}:${String(total%60).padStart(2,'0')}`;}
function vib(){try{tg?.HapticFeedback?.selectionChanged?.();}catch{}}
function randomInt(max){if (globalThis.crypto?.getRandomValues){const a=new Uint32Array(1);const lim=Math.floor(2**32/max)*max;do{crypto.getRandomValues(a);}while(a[0]>=lim);return a[0]%max;}return Math.floor(Math.random()*max);}
function shuffle(items){const a=[...items];for(let i=a.length-1;i>0;i--){const j=randomInt(i+1);[a[i],a[j]]=[a[j],a[i]];}return a;}
function drawFromPool(pool,n,prev){const fresh=shuffle(pool.filter(q=>!prev.includes(q.id)));const old=shuffle(pool.filter(q=>prev.includes(q.id)));return [...fresh,...old].slice(0,n);}
function assembleQuestions(cat){
  const prev=storageRead(localStorage,LAST_KEY,{});
  const last=Array.isArray(prev[cat])?prev[cat]:[];
  const common=QUESTION_BANK.filter(q=>q.id.startsWith('g'));
  const cargo=QUESTION_BANK.filter(q=>q.id.startsWith('c'));
  const group=(pool,picCount,textCount)=>[
    ...drawFromPool(pool.filter(q=>Boolean(q.image)),picCount,last),
    ...drawFromPool(pool.filter(q=>!q.image),textCount,last)
  ];
  let chosen=cat==='B' ? group(common,20,20) : [...group(common,16,16),...group(cargo,4,4)];
  if(chosen.length!==COUNT || new Set(chosen.map(q=>q.id)).size!==COUNT)throw new Error('Сұрақтардың саны жеткіліксіз.');
  const payload=shuffle(chosen).map(q=>{
    const order=shuffle([0,1,2,3]);
    return {id:q.id,options:order.map(i=>q.options[i]), correct:order.indexOf(q.correct), answer:null,marked:false};
  });
  try{localStorage.setItem(LAST_KEY,JSON.stringify({...prev,[cat]:payload.map(q=>q.id)}));}catch{}
  return payload;
}
function start(){
  const selected=assembleQuestions(mode);
  attempt={version:1,category:mode,startedAt:Date.now(),deadline:Date.now()+MINUTES*60*1000,finishedAt:null,finishedReason:null,questions:selected};
  cursor=0;resultFilter='wrong';screen='exam';saveAttempt();render();
}
function remaining(){return attempt ? Math.max(0,(attempt.deadline-Date.now())/1000):0;}
function countAnswered(){return attempt.questions.filter(q=>Number.isInteger(q.answer)).length;}
function finish(reason='manual'){
  if(!attempt || attempt.finishedAt)return;
  attempt.finishedAt=Date.now();attempt.finishedReason=reason;
  const correct=attempt.questions.filter(q=>Number.isInteger(q.answer)&&q.answer===q.correct).length;
  const list=storageRead(localStorage,HISTORY_KEY,[]);
  list.unshift({at:attempt.finishedAt,category:attempt.category,score:correct,elapsedSeconds:Math.round((attempt.finishedAt-attempt.startedAt)/1000)});
  try{localStorage.setItem(HISTORY_KEY,JSON.stringify(list.slice(0,20)));}catch{}
  saveAttempt();resultFilter='wrong';screen='result';closeModal();render();
}
function load(){
  attempt=storageRead(sessionStorage,SAVE_KEY,null);
  const valid=attempt && attempt.version===1 && Array.isArray(attempt.questions) && attempt.questions.length===40 && attempt.questions.every(q=>QUESTION_BANK.some(item=>item.id===q.id));
  if(!valid){attempt=null;cleanupAttempt();return;}
  mode=attempt.category==='B'?'B':'BC';
  if(attempt.finishedAt){screen='result';}
  else if(remaining()<=0){finish('timeout');}
  else{screen='exam';}
}
function renderBrand(){return `<div class="logo"><div class="logo-icon"><svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round"><path d="M5 20L10 4M19 20L14 4M12 8v2m0 4v2m0 4v1"/></svg></div><div><div class="logo-title">QAZAQ PDD</div><div class="logo-caption">EXAM SIMULATOR</div></div></div>`;}
function renderHome(){
  const hist=storageRead(localStorage,HISTORY_KEY,[]);
  const last=hist[0];
  APP.innerHTML=`<main class="app-shell"><header class="topbar">${renderBrand()}<div class="quiet">ҚАЗАҚСТАН · 2026</div></header>
    <section class="hero"><div class="hero-backdrop"></div><div class="overline">СПЕЦЦОН ФОРМАТЫ</div><h1>Емтиханға<br><span>сенімді дайындал.</span></h1><p>Жеңіл көлік пен жүк ГАЗеліне арналған жол ережелері. Әр жолы жаңа сұрақтар, нақты уақытпен сынақ.</p><div class="hero-bottom"><span class="mini-badge">● 132 сұрақтық база</span><span class="mini-badge">● Суретті жағдайлар</span></div></section>
    <div class="title-row"><h2 class="section-title">Санатыңды таңда</h2><span class="quiet">1 нұсқаны таңда</span></div>
    <div class="category-grid"><button class="category-button ${mode==='B'?'active':''}" data-action="category" data-value="B" aria-pressed="${mode==='B'}"><span class="category-symbol">B санаты</span><span class="category-description">Жеңіл көлік және 3,5 т дейінгі ГАЗель</span></button><button class="category-button ${mode==='BC'?'active':''}" data-action="category" data-value="BC" aria-pressed="${mode==='BC'}"><span class="category-symbol">B + C1 / C</span><span class="category-description">Жеңіл көлік және ауыр жүк көлігі</span></button></div>
    <div class="stat-row"><div class="stat"><div class="stat-number">40</div><div class="stat-caption">Сұрақ</div></div><div class="stat"><div class="stat-number">40:00</div><div class="stat-caption">Уақыт</div></div><div class="stat"><div class="stat-number">32/40</div><div class="stat-caption">Өту шегі</div></div></div>
    <button class="main-button" data-action="start">Емтиханды бастау <span aria-hidden="true">→</span></button>
    ${last?`<div class="last-result"><div><span>Соңғы нәтиже · ${last.category==='B'?'B':'B + C1 / C'}</span><div><strong>${last.score}/40</strong> <span class="${last.score>=PASS?'yes':'no'}">${last.score>=PASS?'✓ Тапсырылды':'Қайталау керек'}</span></div></div><span>${new Date(last.at).toLocaleDateString('kk-KZ')}</span></div>`:''}
    <p class="footnote">Оқу тренажері. Сұрақтар авторлық, СпецЦОН-ның ресми жабық базасынан алынбаған. Барлық нәтиже осы құрылғыда сақталады.</p>
  </main>`;
}
function currentQuestion(){const state=attempt.questions[cursor];const original=QUESTION_BANK.find(q=>q.id===state.id);return {state,original};}
function updateTimer(){
  if(screen!=='exam'||!attempt||attempt.finishedAt)return;
  const s=remaining();const timer=document.getElementById('exam-timer');
  if(timer){timer.textContent=fmt(s);timer.classList.toggle('warning',s<=300);}
  if(s<=0)finish('timeout');
}
function renderExam(){
  const {state,original}=currentQuestion();const answered=countAnswered();
  APP.innerHTML=`<main class="app-shell">
    <div class="exam-sticky-top"><header class="exam-header"><button class="back-button" data-action="exit" aria-label="Емтиханнан шығу">✕</button><div class="exam-header-center"><div class="header-mini">ЕМТИХАН ЖҮРІП ЖАТЫР</div><div class="header-major">${mode==='B'?'B':'B + C1 / C'} санаты</div></div><div id="exam-timer" class="timer" role="timer">${fmt(remaining())}</div></header><div class="progress-track" aria-label="${answered} сұрақ жауапталды"><div class="progress-fill" style="width:${answered/COUNT*100}%"></div></div></div>
    <div class="exam-body"><div class="question-top"><div><div class="question-count"><b>${String(cursor+1).padStart(2,'0')}</b> / ${COUNT}</div><div class="question-sub">${answered} жауап берілді</div></div><span class="topic">${escapeHTML(original.topic)}</span></div>
      ${original.image?`<figure class="image-wrap"><img src="./assets/${encodeURIComponent(original.image)}.svg" alt="Жол қозғалысының жағдайын бейнелейтін сурет" draggable="false"><span class="image-label">СУРЕТТІ СҰРАҚ</span></figure>`:''}
      <h1 class="question-title">${escapeHTML(original.text)}</h1><div class="answer-list" role="group" aria-label="Жауап нұсқалары">
      ${state.options.map((opt,i)=>`<button class="answer-button ${state.answer===i?'selected':''}" data-action="answer" data-index="${i}" aria-pressed="${state.answer===i}"><span class="answer-letter">${LETTERS[i]}</span><span class="answer-text">${escapeHTML(opt)}</span>${state.answer===i?'<span class="selected-dot" aria-hidden="true"></span>':''}</button>`).join('')}
      </div><button class="mark-button ${state.marked?'active':''}" data-action="mark" aria-pressed="${state.marked}">${state.marked?'★':'☆'} ${state.marked?'Белгі алынды':'Кейін қарау үшін белгілеу'}</button>
      <div class="footer-hint">Дұрыс және қате жауаптар тек емтихан аяқталған соң көрсетіледі.</div>
    </div>
    <footer class="exam-bottom"><button class="nav-btn" data-action="prev" ${cursor===0?'disabled':''} aria-label="Алдыңғы сұрақ">←</button><button class="nav-btn" data-action="grid">☷ &nbsp; ${answered}/40</button><button class="nav-btn nav-btn-next" data-action="${cursor===COUNT-1?'finishAsk':'next'}">${cursor===COUNT-1?'Аяқтау ✓':'Келесі сұрақ →'}</button></footer>
  </main>`;
  updateTimer();
}
function reviews(){
  const visible=attempt.questions.map((state,i)=>({state,i,original:QUESTION_BANK.find(q=>q.id===state.id)}))
    .filter(({state})=>resultFilter==='all'||state.answer!==state.correct);
  if(!visible.length)return '<p class="quiet" style="text-align:center;padding:25px">Қате жауап жоқ. Барлығы дұрыс!</p>';
  return visible.map(({state,i,original})=>{
    const status=state.answer===state.correct?'correct':'wrong';
    return `<article class="review-card"><div class="review-top"><span class="review-num">${String(i+1).padStart(2,'0')}-СҰРАҚ · ${escapeHTML(original.topic)}</span><span class="review-status ${status}">${status==='correct'?'✓ Дұрыс':state.answer===null?'○ Жауап берілмеді':'✕ Қате'}</span></div>
      <h3>${escapeHTML(original.text)}</h3>${original.image?`<img class="review-image" src="./assets/${encodeURIComponent(original.image)}.svg" alt="Жол жағдайы">`:''}
      ${state.answer!==null?`<div class="review-choice ${status==='correct'?'right':'wrong'}"><b>Сенің жауабың:</b> ${LETTERS[state.answer]}. ${escapeHTML(state.options[state.answer])}</div>`:'<div class="review-choice wrong"><b>Сенің жауабың:</b> таңдалмаған</div>'}
      ${status!=='correct'?`<div class="review-choice right"><b>Дұрыс жауап:</b> ${LETTERS[state.correct]}. ${escapeHTML(state.options[state.correct])}</div>`:''}
      <div class="explain"><b>Түсіндірме:</b> ${escapeHTML(original.why)}</div></article>`;
  }).join('');
}
function renderResult(){
  const correct=attempt.questions.filter(q=>q.answer===q.correct).length;
  const unanswered=COUNT-countAnswered();
  const wrong=COUNT-correct-unanswered;
  const success=correct>=PASS;
  const elapsed=Math.min(MINUTES*60,Math.round((attempt.finishedAt-attempt.startedAt)/1000));
  const pct=Math.round(correct/COUNT*100);
  APP.innerHTML=`<main class="app-shell"><header class="topbar">${renderBrand()}<button class="ghost-link" data-action="home">Басты бет</button></header>
    <div class="result-hero ${success?'':'fail'}"><div class="overline">${attempt.finishedReason==='timeout'?'УАҚЫТ БІТТІ':'ЕМТИХАН АЯҚТАЛДЫ'}</div><div class="result-ring" style="--ring-progress:${pct}%"><div class="ring-inner"><strong>${correct}<span style="font-size:21px">/40</span></strong><span>${pct}% дәлдік</span></div></div><h1>${success?'Құттықтаймыз!':'Тағы жаттығайық'}</h1><p>${success?'Сынақ емтиханынан өттің!':'Өту үшін кемінде 32 дұрыс жауап қажет.'}<br>Жұмсалған уақыт: ${fmt(elapsed)}</p></div>
    <div class="result-stats"><div class="result-stat"><strong style="color:var(--green)">${correct}</strong><span>Дұрыс</span></div><div class="result-stat"><strong style="color:var(--red)">${wrong}</strong><span>Қате</span></div><div class="result-stat"><strong>${unanswered}</strong><span>Жауапсыз</span></div></div>
    <div class="result-actions"><button class="main-button" data-action="restart">↻ Жаңа 40 сұрақ</button><button class="small-button" data-action="home">⌂ Басты бет</button></div>
    <div class="review-header"><h2 class="section-title">Жауаптарды талдау</h2><div class="review-filter"><button class="pill ${resultFilter==='wrong'?'active':''}" data-action="filter" data-value="wrong">Қате (${COUNT-correct})</button><button class="pill ${resultFilter==='all'?'active':''}" data-action="filter" data-value="all">Бәрі</button></div></div><div id="review-list">${reviews()}</div>
    <p class="footnote">Бұл — оқу нәтижесі, мемлекеттік емтихан қорытындысы емес.</p>
  </main>`;
}
function render(){
  clearInterval(timerInterval);
  if(screen==='home')renderHome();
  else if(screen==='exam'){
    renderExam();timerInterval=setInterval(updateTimer,400);
    try{tg?.enableClosingConfirmation?.();tg?.BackButton?.show?.();}catch{}
  }
  else if(screen==='result')renderResult();
  if(screen!=='exam')try{tg?.disableClosingConfirmation?.();tg?.BackButton?.hide?.();}catch{}
}
function openModal(content){MODAL.innerHTML=`<div class="modal-screen" data-action="modalBackdrop"><div class="modal-sheet" role="dialog" aria-modal="true"><div class="modal-handle"></div>${content}</div></div>`;isModalOpen=true;}
function closeModal(){MODAL.innerHTML='';isModalOpen=false;}
function showGrid(){
  const answered=countAnswered();
  openModal(`<h2 class="modal-title">Сұрақтар картасы</h2><p class="modal-description">${answered} сұраққа жауап бердің. Боялғандары — жауап берілген сұрақтар; жасыл түс жауаптың дұрыстығын білдірмейді.</p>
  <div class="question-grid">${attempt.questions.map((q,i)=>`<button class="grid-number ${q.answer!==null?'done':''} ${cursor===i?'current':''} ${q.marked?'marked':''}" data-action="jump" data-index="${i}" aria-label="${i+1}-сұрақ">${i+1}</button>`).join('')}</div>
  <div class="legend"><span><i></i> Жауап берілген</span><span><i class="empty"></i> Жауапсыз</span><span><i class="marked"></i> Белгіленген</span></div>
  <div class="modal-buttons" style="margin-top:22px"><button class="small-button" data-action="close">Жабу</button><button class="main-button" data-action="finishAsk">Емтиханды аяқтау</button></div>`);
}
function showFinish(){
  const missing=COUNT-countAnswered();
  openModal(`<h2 class="modal-title">Емтиханды аяқтаймыз ба?</h2><p class="modal-description">${missing?`Сен <strong style="color:var(--amber)">${missing} сұраққа жауап берген жоқсың</strong>. Олар қате болып есептеледі. `:''}Аяқтағаннан кейін барлық дұрыс және қате жауаптарың көрсетіледі.</p><div class="modal-buttons"><button class="small-button" data-action="close">Жалғастыру</button><button class="main-button" data-action="finish">Аяқтау ✓</button></div>`);
}
function showExit(){openModal(`<h2 class="modal-title">Емтиханнан шығу</h2><p class="modal-description">Нәтиже сақталмайды. Келесі жолы жаңа 40 сұрақ беріледі.</p><div class="modal-buttons"><button class="small-button" data-action="close">Қалу</button><button class="main-button" data-action="confirmExit">Шығу</button></div>`);}
function navigate(n){cursor=Math.max(0,Math.min(COUNT-1,n));render();window.scrollTo(0,0);}
function handleAction(action,node){
  if(action==='category'){mode=node.dataset.value;vib();renderHome();return;}
  if(action==='start'||action==='restart'){vib();start();return;}
  if(action==='home'){attempt=null;cleanupAttempt();screen='home';render();window.scrollTo(0,0);return;}
  if(action==='answer'){
    if(screen!=='exam')return;
    if(remaining()<=0){finish('timeout');return;}
    attempt.questions[cursor].answer=Number(node.dataset.index);vib();saveAttempt();renderExam();return;
  }
  if(action==='mark'){attempt.questions[cursor].marked=!attempt.questions[cursor].marked;saveAttempt();renderExam();return;}
  if(action==='prev'){navigate(cursor-1);return;}
  if(action==='next'){navigate(cursor+1);return;}
  if(action==='grid'){showGrid();return;}
  if(action==='jump'){closeModal();navigate(Number(node.dataset.index));return;}
  if(action==='finishAsk'){showFinish();return;}
  if(action==='finish'){finish('manual');return;}
  if(action==='exit'){showExit();return;}
  if(action==='confirmExit'){closeModal();attempt=null;cleanupAttempt();screen='home';render();return;}
  if(action==='close'){closeModal();return;}
  if(action==='filter'){resultFilter=node.dataset.value;renderResult();return;}
  if(action==='modalBackdrop'){closeModal();return;}
}
document.addEventListener('click',event=>{
  const node=event.target.closest('[data-action]');if(!node||node.disabled)return;
  if(node.dataset.action==='modalBackdrop' && event.target!==node)return;
  handleAction(node.dataset.action,node);
});
window.addEventListener('keydown',event=>{
  if(isModalOpen){if(event.key==='Escape')closeModal();return;}
  if(screen!=='exam')return;
  if(/^[1-4]$/.test(event.key)){attempt.questions[cursor].answer=Number(event.key)-1;saveAttempt();renderExam();}
  if(event.key==='ArrowRight')navigate(cursor+1);
  if(event.key==='ArrowLeft')navigate(cursor-1);
});
try{tg?.BackButton?.onClick?.(()=>{if(isModalOpen)closeModal();else if(screen==='exam')showExit();});}catch{}
document.addEventListener('visibilitychange',()=>{if(!document.hidden && screen==='exam')updateTimer();});
load();render();
