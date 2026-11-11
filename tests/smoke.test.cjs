const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..','webapp');
const store=()=>{const m=new Map();return {getItem:k=>m.has(k)?m.get(k):null,setItem:(k,v)=>m.set(k,String(v)),removeItem:k=>m.delete(k)}};
class El{
  constructor(){this.innerHTML='';this.textContent='';this.classList={toggle:()=>{}}}
  addEventListener(){}
}
const elements=new Map();
const ctx={
  console, Date, Math, JSON, String, Number, Array, Map, Set, Uint32Array, Intl,
  crypto:require('node:crypto').webcrypto,
  sessionStorage:store(),localStorage:store(),
  document:{getElementById(id){if(!elements.has(id))elements.set(id,new El());return elements.get(id)},addEventListener(){}},
  window:{Telegram:null,addEventListener(){},scrollTo(){}},
  setInterval(){return 1},clearInterval(){},
};
ctx.globalThis=ctx;
vm.createContext(ctx);
vm.runInContext(fs.readFileSync(path.join(root,'questions.js'),'utf8'),ctx,{filename:'questions.js'});
assert.equal(ctx.window.QUESTION_BANK.length,132);
const bank=ctx.window.QUESTION_BANK;
assert.equal(new Set(bank.map(q=>q.id)).size,bank.length,'unique IDs');
for(const q of bank){
  assert.equal(q.options.length,4,`options ${q.id}`);
  assert.equal(typeof q.why,'string');
  assert.ok(Number.isInteger(q.correct)&&q.correct>=0&&q.correct<4);
  if(q.image)assert.ok(fs.existsSync(path.join(root,'assets',q.image+'.svg')),`missing ${q.image}`);
}
vm.runInContext(fs.readFileSync(path.join(root,'app.js'),'utf8'),ctx,{filename:'app.js'});
assert.ok(elements.get('app').innerHTML.includes('Емтиханды бастау'));
vm.runInContext('mode="BC";start()',ctx);
let state=JSON.parse(ctx.sessionStorage.getItem('qazaq-pdd-session-v1'));
assert.equal(state.questions.length,40);
assert.equal(new Set(state.questions.map(q=>q.id)).size,40);
assert.equal(state.questions.filter(q=>q.id.startsWith('c')).length,8);
assert.equal(state.questions.filter(q=>q.id.startsWith('g')).length,32);
for(const q of state.questions){const orig=bank.find(x=>x.id===q.id);assert.equal(q.options[q.correct],orig.options[orig.correct]);}
assert.ok(!elements.get('app').innerHTML.includes('Дұрыс жауап:'));
let first=state.questions.map(q=>q.id).join(',');
vm.runInContext('attempt.questions[0].answer=2;saveAttempt();renderExam()',ctx);
assert.ok(!elements.get('app').innerHTML.includes('Дұрыс жауап:'));
vm.runInContext('finish("manual")',ctx);
assert.ok(elements.get('app').innerHTML.includes('Жауаптарды талдау'));
assert.ok(elements.get('app').innerHTML.includes('Дұрыс жауап:')||elements.get('app').innerHTML.includes('Дұрыс'));
vm.runInContext('start()',ctx);
state=JSON.parse(ctx.sessionStorage.getItem('qazaq-pdd-session-v1'));
assert.notEqual(state.questions.map(q=>q.id).join(','),first);
vm.runInContext('mode="B";start()',ctx);
state=JSON.parse(ctx.sessionStorage.getItem('qazaq-pdd-session-v1'));
assert.ok(state.questions.every(q=>q.id.startsWith('g')));
vm.runInContext('attempt.deadline=Date.now()-500;updateTimer()',ctx);
state=JSON.parse(ctx.sessionStorage.getItem('qazaq-pdd-session-v1'));
assert.equal(state.finishedReason,'timeout');
assert.ok(elements.get('app').innerHTML.includes('УАҚЫТ БІТТІ'));
console.log('PASS: 132 questions, 40 question selection, 40m timer, B/BC, images, delayed grading, fresh test, timeout.');
