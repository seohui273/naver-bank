/* BANK:LAB daily insight desk — descriptive research, not investment advice. */
(()=>{
'use strict';
const el=id=>document.getElementById(id);
if(!el('market')||!el('signalTab'))return;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const groups={'105560':'대형 금융지주','055550':'대형 금융지주','086790':'대형 금융지주','316140':'대형 금융지주','024110':'특수은행','138930':'지역 금융지주','175330':'지역 금융지주','139130':'지역 금융지주','006220':'지방은행','323410':'인터넷은행','279570':'인터넷은행'};
const nav=document.querySelector('nav.tabs');
const tab=document.createElement('button');tab.textContent='오늘의 관찰 · 종목 탐색';tab.dataset.tab='insights';nav.insertBefore(tab,nav.firstChild);
const p=document.createElement('section');p.className='panel';p.id='insights';
p.innerHTML='<p class="intro">매일 11개 주식을 하나씩 열 필요 없이, 오늘 동종 은행과 다르게 움직인 종목을 먼저 확인해 보세요.</p>'+
'<div class="toolbar"><div class="controls"><label>거래일<select id="insDate"></select></label><label>은행 유형<select id="insGroup"><option>전체</option><option>대형 금융지주</option><option>특수은행</option><option>지역 금융지주</option><option>지방은행</option><option>인터넷은행</option></select></label><label>정렬 기준<select id="insSort"><option value="peer">비교 평균 대비 차이</option><option value="size">변동폭 큰 순서</option><option value="low">하락률 높은 순서</option><option value="high">상승률 높은 순서</option></select></label></div></div>'+
'<div class="grid" id="insStats"></div><div class="sectionhead"><h2>오늘의 핵심 관찰</h2><small>실제 관측 수익률 기준</small></div><div class="card" id="insHighlights"></div>'+
'<div class="sectionhead"><h2>전체 은행 움직임과 비교</h2><small>종목 수익률 − 나머지 은행 평균 수익률</small></div><div class="card"><div class="chart-tall" id="insChart"></div></div>'+
'<div class="sectionhead"><h2>주가 변동 배경 조사</h2><small>뉴스·SIGNAL X-RAY로 한 번에 이동</small></div><div class="card scroll"><table id="insTable"></table></div>'+
'<div class="note" id="insNote">차이는 다른 은행들의 단순평균 수익률과 비교한 값이며, 개별 악재나 통계적 이상을 증명하지 않습니다. 종목별 관측일이 다르면 비교 시 주의하세요.</div>';
nav.after(p);
const st=document.createElement('style');st.textContent='.ins-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.ins-card{background:#f6faf9;border:1px solid #e3edeb;border-radius:9px;padding:16px}.ins-card strong{display:block;font-size:14px}.ins-card p{color:#637680;font-size:12px;margin:7px 0 0}.ins-open{border:1px solid #b7d2cd;background:white;color:#166360;border-radius:7px;padding:6px 10px;font-weight:700;cursor:pointer}@media(max-width:780px){.ins-cards{grid-template-columns:1fr}#insTable{min-width:720px}}';document.head.appendChild(st);
const cache=new Map();let day='';
const percent=x=>Number.isFinite(x)?(x>0?'+':'')+x.toFixed(2)+'%':'—',points=x=>Number.isFinite(x)?(x>0?'+':'')+x.toFixed(2)+'%p':'—';
const pairs=()=>{
 const key=start+'|'+end;
 if(cache.has(key))return cache.get(key);
 const byDay=new Map();
 for(const code of codes)for(const r of returns(series(code))){
   if(!byDay.has(r.date))byDay.set(r.date,[]);
   byDay.get(r.date).push({code:code,name:names[code],value:r.value,group:groups[code]||'기타'});
 }
 cache.clear();cache.set(key,byDay);return byDay;
};
const rows=d=>{
 const group=pairs().get(d)||[];
 return group.map(r=>{
   const same=group.filter(o=>o.code!==r.code&&o.group===r.group);
   const peers=same.length>=2?same:group.filter(o=>o.code!==r.code);
   const baseline=peers.length>=2?mean(peers.map(o=>o.value)):NaN;
   return {...r,baseline:baseline,diff:r.value-baseline,basis:same.length>=2?'같은 은행 유형':'다른 모든 은행',peerCount:peers.length};
 });
};
function render(){
 const ds=[...pairs().entries()].filter(([d,r])=>r.length>=3).map(([d])=>d).sort();
 if(!ds.length){el('insHighlights').textContent='유효한 관측 자료가 부족합니다.';return;}
 if(!ds.includes(day))day=ds.at(-1);
 el('insDate').innerHTML=ds.slice().reverse().map(d=>'<option value="'+esc(d)+'">'+esc(d)+'</option>').join('');
 el('insDate').value=day;
 let arr=rows(day).filter(x=>el('insGroup').value==='전체'||x.group===el('insGroup').value);
 const ups=arr.filter(x=>x.value>0).length,downs=arr.filter(x=>x.value<0).length;
 const avg=arr.length?mean(arr.map(x=>x.value)):NaN;
 const most=[...arr].filter(x=>Number.isFinite(x.diff)).sort((a,b)=>Math.abs(b.diff)-Math.abs(a.diff))[0];
 el('insStats').innerHTML=metric('거래일',day,'관측된 주가 데이터')+metric('비교 종목',arr.length+'개','현재 유형 필터')+metric('상승 / 하락',ups+' / '+downs+'개','보합 제외')+metric('평균 수익률',percent(avg),'동일가중 평균');
 el('insHighlights').innerHTML='<div class="ins-cards"><div class="ins-card"><strong>시장 분위기</strong><p>'+arr.length+'개 중 상승 '+ups+'개·하락 '+downs+'개. 업종 전체가 한 방향으로 움직였는지 확인하세요.</p></div>'+
 '<div class="ins-card"><strong>비교 평균과 가장 다른 종목</strong><p>'+(most?esc(most.name)+' '+points(most.diff)+' ('+esc(most.basis)+' 대비)':'충분한 비교 자료 없음')+'</p></div>'+
 '<div class="ins-card"><strong>다음 조사 단계</strong><p>아래 종목별 뉴스 버튼을 누르면 해당 날짜의 기사와 SIGNAL X-RAY를 확인할 수 있습니다.</p></div></div>';
 const mode=el('insSort').value;arr.sort((a,b)=>mode==='size'?Math.abs(b.value)-Math.abs(a.value):mode==='low'?a.value-b.value:mode==='high'?b.value-a.value:Math.abs(b.diff)-Math.abs(a.diff));
 if(arr.length)plot('insChart',[{type:'bar',orientation:'h',x:arr.map(x=>x.diff).reverse(),y:arr.map(x=>x.name).reverse(),marker:{color:arr.map(x=>x.diff>=0?'#328b84':'#b56e69').reverse()},hovertemplate:'%{y}<br>비교 평균 대비 %{x:.2f}%p<extra></extra>'}],{margin:{l:115,r:20,t:15,b:50},xaxis:{title:'나머지 은행 평균 대비 (%p)',zeroline:true,zerolinecolor:'#b3bec3'}});
 else el('insChart').replaceChildren();
 el('insTable').innerHTML='<thead><tr><th>종목</th><th>은행 유형</th><th>수익률</th><th>비교 평균</th><th>차이</th><th>비교 기준</th><th>조사</th></tr></thead><tbody>'+arr.map(r=>'<tr><td>'+esc(r.name)+'</td><td>'+esc(r.group)+'</td><td>'+percent(r.value)+'</td><td>'+percent(r.baseline)+'</td><td>'+points(r.diff)+'</td><td>'+esc(r.basis)+' '+r.peerCount+'개</td><td><button class="ins-open" data-code="'+esc(r.code)+'" data-date="'+esc(day)+'">뉴스 보기 ↗</button></td></tr>').join('')+'</tbody>';
}
el('insDate').addEventListener('change',e=>{day=e.target.value;render()});
el('insGroup').addEventListener('change',render);el('insSort').addEventListener('change',render);
el('insTable').addEventListener('click',e=>{
 const b=e.target.closest('button[data-code]');if(!b)return;
 el('signalTab').click();
 const stock=el('signalStock');stock.value=b.dataset.code;stock.dispatchEvent(new Event('change'));
 const date=el('signalDate');if([...date.options].some(o=>o.value===b.dataset.date)){date.value=b.dataset.date;date.dispatchEvent(new Event('change'));}
 document.querySelector('nav.tabs').scrollIntoView({behavior:'smooth'});
});
tab.addEventListener('click',()=>{active='insights';document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x===tab));document.querySelectorAll('.panel').forEach(x=>x.classList.toggle('active',x===p));render()});
for(const id of ['start','end'])el(id).addEventListener('change',()=>{if(active==='insights'){day='';render()}});
const header=document.querySelector('#market .sectionhead');
if(header){header.insertAdjacentHTML('beforebegin','<div class="note" style="margin:0 0 20px"><strong>오늘 어떤 은행주부터 확인할까?</strong> 움직임이 유난히 달랐던 종목을 먼저 찾아보세요. <button class="ins-open" id="insGo">오늘의 관찰 →</button></div>');el('insGo').addEventListener('click',()=>tab.click());}
})();