const $ = id => document.getElementById(id);
const fmt = (v, digits = 2) => Number(v).toLocaleString('ko-KR', {minimumFractionDigits:digits, maximumFractionDigits:digits});
const today = () => new Intl.DateTimeFormat('sv-SE', {timeZone:'Asia/Seoul'}).format(new Date());
let snapshot = null, settings = {USD:90, JPY:90, CNY:50}, calculation = null, calculating = false, loading = false;
const flags = {USD:'🇺🇸', JPY:'🇯🇵', CNY:'🇨🇳'};
const message = text => { $('notice').textContent = text; };
async function setupShutdown() {
  try {
    const health = await api('/api/health');
    if (!health.token) return;
    const button = document.createElement('button');
    button.className = 'secondary'; button.textContent = '프로그램 종료';
    document.querySelector('header').append(button);
    button.addEventListener('click', async () => {
      if (!confirm('프로그램을 종료할까요? 저장하지 않은 계산은 보관되지 않습니다.')) return;
      button.disabled = true;
      try {
        await api('/api/shutdown', {token:health.token});
        document.querySelector('main').replaceChildren();
        const text = document.createElement('p');
        text.textContent = '프로그램이 종료되었습니다. 이 탭을 닫아 주세요. 다시 사용하려면 ExchangeStudio를 실행하세요.';
        document.querySelector('main').append(text);
        button.textContent = '종료됨';
      } catch(error) { message(error.message); button.disabled = false; }
    });
  } catch(error) { message(error.message); }
}
async function api(path, body) {
  const response = await fetch(path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || '요청을 처리하지 못했습니다.');
  return result;
}
function invalidate() { calculation = null; $('save').disabled = true; $('result').innerHTML = '<p class="empty">입력 조건이 변경되었습니다.<br>다시 계산해 주세요.</p>'; }
function renderCards() {
  $('cards').replaceChildren();
  if (!snapshot) return;
  for (const r of snapshot.rates) {
    const card = document.createElement('article'); card.className = 'card';
    card.innerHTML = `<div class="card-top"><span class="flag">${flags[r.code]}</span><div><div class="code">${r.code}</div><div class="name">${r.name}</div></div><span class="badge">기본 우대 ${fmt(settings[r.code], 0)}%</span></div><div class="card-rate">${fmt(r.base)}<small>원 / ${r.unit} ${r.code}</small></div><div class="name">매매기준율</div><dl><dt>현찰 살 때</dt><dd>${fmt(r.cash)} 원</dd><dt>송금 보낼 때</dt><dd>${fmt(r.remittance)} 원</dd></dl>`;
    $('cards').append(card);
  }
}
async function loadRates() {
  if (loading || !$('date').reportValidity()) return;
  loading = true; snapshot = null; invalidate(); renderCards(); message('');
  $('load').disabled = true; $('calculate').disabled = true; $('stamp').textContent = '하나은행에서 환율을 조회하고 있습니다…';
  const day = $('date').value;
  try {
    const response = await api(`/api/rates?date=${encodeURIComponent(day)}`);
    if ($('date').value !== day) return;
    snapshot = response; renderCards();
    $('stamp').textContent = `기준일 ${snapshot.baseDate} · 고시 ${snapshot.publishedAt.slice(0,19).replace('T',' ')} · ${snapshot.sequence}회차`;
    if (snapshot.baseDate !== day) message(`요청일 ${day}의 조회 결과로 기준일 ${snapshot.baseDate} 환율이 반환되었습니다.`);
  } catch(error) { message(error.message); $('stamp').textContent = '조회 실패 · 다시 시도해 주세요.'; }
  finally { loading = false; $('load').disabled = false; $('calculate').disabled = !snapshot; }
}
function payload() { return {date:$('date').value, currency:$('currency').value, mode:$('mode').value, amount:$('amount').value, discount:$('discount').value}; }
function renderResult(r) {
  $('result').innerHTML = `<div class="result-label">${fmt(r.amount)} ${r.currency} 구매 시 필요한 원화</div><div class="total">${fmt(r.total,0)} <small>원</small></div><div class="saving">우대 전보다 ${fmt(r.savings,0)}원 절약</div><dl class="breakdown"><dt>매매기준율</dt><dd>${fmt(r.base)}원</dd><dt>우대 전 환율</dt><dd>${fmt(r.before)}원</dd><dt>우대 후 스프레드</dt><dd>+ ${fmt(r.afterSpread)}원</dd><dt>최종 구매환율 / ${r.unit} ${r.currency}</dt><dd>${fmt(r.finalRate)}원</dd></dl><p class="hint">${r.publishedAt.slice(0,19).replace('T',' ')} · ${r.sequence}회차 기준</p>`;
}
$('calculator').addEventListener('submit', async event => {
  event.preventDefault(); if (calculating || !snapshot) return;
  const request = payload(), signature = JSON.stringify(request);
  calculating = true; $('calculate').disabled = true; $('save').disabled = true; message('');
  try {
    const result = await api('/api/calculate', request);
    if (signature !== JSON.stringify(payload())) return;
    calculation = {request, result}; renderResult(result); $('save').disabled = false;
  } catch(error) { invalidate(); message(error.message); }
  finally { calculating = false; $('calculate').disabled = !snapshot; }
});
$('save').addEventListener('click', async () => {
  if (!calculation) return;
  const current = calculation; $('save').disabled = true;
  try {
    // The server recalculates against its authoritative cached/current quote.
    const saved = await api('/api/history', current.request);
    if (calculation === current) { renderResult(saved); calculation = null; }
    await loadHistory(); message('계산 기록을 저장했습니다. 저장 시점의 고시환율이 적용되었습니다.');
  } catch(error) { message(error.message); if (calculation === current) $('save').disabled = false; }
});
async function loadHistory() {
  const records = await api('/api/history'); $('count').textContent = records.length; $('history').replaceChildren();
  if (!records.length) { const row = $('history').insertRow(); const cell = row.insertCell(); cell.colSpan = 8; cell.textContent = '아직 저장한 계산이 없습니다. 첫 환전 계획을 저장해 보세요.'; return; }
  for (const r of records) {
    const row = $('history').insertRow();
    [r.created.slice(0,16).replace('T',' '), `${r.publishedAt.slice(0,10)} / ${r.sequence}`, `${r.currency} · ${r.mode === 'cash' ? '현찰' : '송금'}`,fmt(r.amount),`${fmt(r.discount)}%`,fmt(r.finalRate),`${fmt(r.total,0)}원`,`${fmt(r.savings,0)}원`].forEach(value => { row.insertCell().textContent = value; });
  }
}
$('save-settings').addEventListener('click', async () => {
  if (!$('discount').reportValidity()) return;
  const next = {...settings, [$('currency').value]:$('discount').value};
  try { await api('/api/settings', next); settings = next; renderCards(); message('통화별 기본 우대율을 저장했습니다.'); } catch(error) {message(error.message);}
});
$('currency').addEventListener('change', () => { $('discount').value = settings[$('currency').value]; $('amount-unit').textContent = $('currency').value; invalidate(); });
['mode','amount','discount'].forEach(id => $(id).addEventListener('input', invalidate));
$('date').addEventListener('change', () => { snapshot = null; renderCards(); invalidate(); $('calculate').disabled = true; $('stamp').textContent = '변경한 날짜로 환율을 조회해 주세요.'; });
$('load').addEventListener('click', loadRates);
$('today').addEventListener('click', () => { $('date').value = today(); loadRates(); });
(async () => {
  await setupShutdown();
  $('date').value = today(); $('date').max = today(); $('calculate').disabled = true;
  try { settings = await api('/api/settings'); $('discount').value = settings.USD; await loadHistory(); } catch(error) { message(error.message); }
  await loadRates();
})();
