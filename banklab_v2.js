/* BANK:LAB v2 — evidence-first discovery; no synthetic price/news data. */
(() => {
  'use strict';
  const GROUPS = {
    '대형 금융지주':['105560','055550','086790','316140'],
    '특수은행':['024110'],
    '지역 금융지주·지방은행':['138930','175330','139130','006220'],
    '인터넷전문은행':['323410','279570']
  };
  const groupOf = c => Object.keys(GROUPS).find(g => GROUPS[g].includes(c)) || '기타';
  const esc = s => String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const color = ['#176d6a','#be7863','#5f79a7','#886ca3','#b8963c','#338d8e','#a36485','#7d8c4a','#445d8a','#ad7555','#6897a3'];
  const groups = Object.keys(GROUPS), labels = codes.map(c => names[c]+' ('+c+')');
  let groupFilter='전체', selected = new Set(codes.filter(c=>['105560','024110','055550'].includes(c))), newsData={articles:[],updated_at:null};
  const visible = () => codes.filter(c=>groupFilter==='전체'||groupOf(c)===groupFilter);
  const topbar=document.querySelector('#market .toolbar');
  topbar.insertAdjacentHTML('afterbegin','<div class="controls"><label>은행 유형<select id="bankGroup"><option>전체</option>'+groups.map(g=>'<option>'+esc(g)+'</option>').join('')+'</select></label></div>');
  document.getElementById('bankGroup').addEventListener('change',e=>{groupFilter=e.target.value;market()});
  document.querySelector('[data-tab="quality"]')?.remove(); // validation still runs in the pipeline
  document.getElementById('quality')?.remove();
  const statsPanel=document.getElementById('statistics');
  [...statsPanel.children].forEach(el=>{el.style.display='none'});
  statsPanel.insertAdjacentHTML('afterbegin',[
    '<div class="card" style="margin-bottom:16px"><h3>분석할 종목 자유 선택</h3><p class="intro">1~11개 종목을 체크하면 모든 그래프·상관관계가 함께 갱신됩니다.</p>',
    '<div class="v2-pills" id="v2Pick"></div><p class="plotnote" id="v2Count"></p></div>',
    '<div class="grid" id="v2Metrics"></div>',
    '<div class="sectionhead"><h2>선택 종목 정규화 가격</h2><small>각 종목의 첫 관측일 = 100; 공통일 비교는 아래 표시</small></div><div class="card"><div id="v2Indexed" class="chart-tall"></div></div>',
    '<div class="sectionhead"><h2>선택 종목 수익률 분포</h2></div><div class="card"><div id="v2Distribution" class="chart"></div></div>',
    '<div class="sectionhead"><h2>선택 종목 상관관계</h2><small>공통 날짜의 일별 수익률 기준</small></div><div class="card"><div id="v2Corr" class="chart-tall"></div></div>',
    '<div class="note warning" id="v2Caveat"></div>'
  ].join(''));
  const nav=document.querySelector('nav.tabs');
  nav.insertAdjacentHTML('beforeend','<button data-tab="signals" id="signalTab">SIGNAL X-RAY · 뉴스</button>');
  const panel=document.createElement('section');panel.className='panel';panel.id='signals';
  panel.innerHTML=[
    '<p class="intro">선택 날짜의 실제 수익률을 동종 은행주의 평균 움직임과 비교합니다. 회귀모형은 이전 관측치만 학습합니다.</p>',
    '<div class="toolbar"><div class="controls"><label>종목<select id="signalStock"></select></label><label>거래일<select id="signalDate"></select></label></div></div>',
    '<div class="grid" id="signalMetrics"></div>',
    '<div class="sectionhead"><h2>이례적인 움직임 분석</h2></div><div class="card" id="signalResult"></div>',
    '<div class="sectionhead"><h2>선택 날짜 뉴스 브리핑</h2><small>출처를 확인할 수 있는 기사만 표시</small></div><div class="card" id="signalNews">관련 뉴스를 불러오는 중입니다.</div>',
    '<div class="note">통계적 잔차는 개별 악재의 증거가 아닙니다. 뉴스와 주가의 동시 발생도 인과관계를 입증하지 않습니다. 역사적 KRX 다변량 회귀의 결과는 위 연구 보고서에서 확인하세요.</div>'
  ].join('');
  nav.after(panel);
  const style=document.createElement('style');
  style.textContent='.v2-pills{display:flex;flex-wrap:wrap;gap:8px}.v2-pill{border:1px solid #dce3e6;padding:9px 12px;border-radius:8px;background:#fff;color:#48606a;font-size:12px;cursor:pointer}.v2-pill.on{background:#e8f4f1;border-color:#176d6a;color:#145553;font-weight:750}.v2-narrative{line-height:1.9;color:#45606d;font-size:13px}.v2-article{border-bottom:1px solid #edf0f1;padding:12px 0}.v2-article:last-child{border-bottom:none}.v2-article a{color:#176d6a;text-decoration:underline;text-underline-offset:3px}.v2-source{font-size:11px;color:#71808d}.v2-flag{font-weight:700;color:#9b563e}.v2-results{display:flex;gap:16px;flex-wrap:wrap}.v2-results .card{flex:1;min-width:180px}';
  document.head.appendChild(style);
  document.getElementById('signalStock').innerHTML=codes.map(c=>'<option value="'+esc(c)+'">'+esc(names[c])+'</option>').join('');
  document.getElementById('signalStock').value=codes.includes('105560')?'105560':codes[0];
  document.getElementById('v2Pick').addEventListener('click',e=>{const b=e.target.closest('[data-code]');if(!b)return;const c=b.dataset.code;selected.has(c)?selected.delete(c):selected.add(c);stats()});
  const renderChoices=()=>{
    document.getElementById('v2Pick').innerHTML=groups.map(g=>'<div style="width:100%;font-weight:700;margin-top:8px;font-size:12px;color:#71808d">'+esc(g)+'</div>'+GROUPS[g].filter(c=>codes.includes(c)).map(c=>'<button class="v2-pill '+(selected.has(c)?'on':'')+'" data-code="'+c+'" aria-pressed="'+selected.has(c)+'">'+esc(names[c])+'</button>').join('')).join('');
    document.getElementById('v2Count').textContent=selected.size+'개 선택 · 원하는 만큼 클릭/해제할 수 있습니다.';
  };
  market=function(){
    const cs=visible(),rr=range().filter(r=>cs.includes(r['종목코드'])),lastDay=[...new Set(rr.map(r=>r['거래일']))].sort().at(-1);
    const snaps=rr.filter(r=>r['거래일']===lastDay),perf=cs.map(c=>({c,name:names[c],value:rtn(series(c))})).sort((a,b)=>b.value-a.value);
    const valid=perf.filter(v=>Number.isFinite(v.value));
    document.getElementById('kpis').innerHTML=metric('필터된 종목',cs.length+'개',groupFilter)+metric('관측 거래일',[...new Set(rr.map(r=>r['거래일']))].length+'일','현재 선택 기간')+metric('평균 누적수익률',pct(valid.length?mean(valid.map(o=>o.value)):NaN),'동일가중')+metric('최근 거래일',lastDay||'—','보유 데이터 기준');
    plot('retChart',[{type:'bar',orientation:'h',x:perf.map(o=>o.value).reverse(),y:perf.map(o=>o.name).reverse(),marker:{color:'#247d81'}}],{margin:{t:15,b:45,l:125,r:18},xaxis:{title:'누적수익률 (%)'}});
    const changes=[...snaps].sort((a,b)=>num(b['등락률(%)'])-num(a['등락률(%)']));
    plot('dayChart',[{type:'bar',orientation:'h',x:changes.map(r=>num(r['등락률(%)'])).reverse(),y:changes.map(r=>r['종목명']).reverse(),marker:{color:'#c38d78'}}],{margin:{t:15,b:45,l:125,r:18},xaxis:{title:'일별 등락률 (%)'}});
    document.getElementById('marketTable').innerHTML='<thead><tr><th>종목</th><th>유형</th><th>종가(원)</th><th>일간 등락률</th><th>기간 수익률</th><th>거래량</th></tr></thead><tbody>'+snaps.map(r=>'<tr><td>'+esc(r['종목명'])+'</td><td>'+esc(groupOf(r['종목코드']))+'</td><td>'+fmt(px(r))+'</td><td>'+pct(num(r['등락률(%)']))+'</td><td>'+pct(rtn(series(r['종목코드'])))+'</td><td>'+fmt(num(r['거래량']))+'</td></tr>').join('')+'</tbody>';
    document.getElementById('marketNote').textContent='은행 유형을 필터해 볼 수 있습니다. 기간 수익률은 선택 구간의 첫·마지막 관측 종가로 계산했습니다. 주가 변동의 배경은 SIGNAL X-RAY·뉴스 탭에서 확인하세요.';
  };
  stats=function(){
    renderChoices();const cs=[...selected].filter(c=>codes.includes(c));
    if(!cs.length){document.getElementById('v2Metrics').innerHTML='종목을 1개 이상 선택하세요.';['v2Indexed','v2Distribution','v2Corr'].forEach(id=>document.getElementById(id).replaceChildren());return}
    const s=cs.map(c=>({c,rows:series(c)})), metrics=s.map(o=>({c:o.c,r:rtn(o.rows),vol:sd(returns(o.rows).map(v=>v.value))}));
    document.getElementById('v2Metrics').innerHTML=metric('선택한 종목',cs.length+'개','상한 11개')+metric('평균 누적수익률',pct(mean(metrics.map(o=>o.r).filter(Number.isFinite))),'계산 가능한 종목')+metric('평균 일간 변동성',pct(mean(metrics.map(o=>o.vol).filter(Number.isFinite))),'표본표준편차')+metric('표본 기간',start+' ~ '+end,'각 종목 상장시점 확인');
    plot('v2Indexed',s.filter(o=>o.rows.length&&px(o.rows[0])>0).map((o,i)=>({type:'scatter',mode:'lines',name:names[o.c],x:o.rows.map(r=>r['거래일']),y:o.rows.map(r=>100*px(r)/px(o.rows[0])),line:{color:color[i%color.length],width:2}})),{showlegend:true,legend:{orientation:'h',y:1.20},xaxis:{type:'category'},yaxis:{title:'최초 종가 = 100'}});
    plot('v2Distribution',s.map((o,i)=>({type:'histogram',name:names[o.c],x:returns(o.rows).map(v=>v.value),opacity:.55,marker:{color:color[i%color.length]}})),{showlegend:true,barmode:'overlay',xaxis:{title:'일별 수익률 (%)'},yaxis:{title:'관측 수'}});
    const z=cs.map(c=>cs.map(d=>{const [x,y]=aligned(series(c),series(d)),r=corr(x,y);return Number.isFinite(r)?r:null}));
    plot('v2Corr',[{type:'heatmap',x:cs.map(c=>names[c]),y:cs.map(c=>names[c]),z,zmin:-1,zmax:1,colorscale:[[0,'#2876bd'],[.5,'#f5f8fb'],[1,'#bf4b5e']],hovertemplate:'%{y} / %{x}<br>r = %{z:.3f}<extra></extra>'}],{margin:{t:20,b:115,l:130,r:30},xaxis:{tickangle:-45}});
    const spans=cs.map(c=>series(c).length);
    document.getElementById('v2Caveat').textContent='상관계수는 두 종목이 모두 관측된 날짜의 수익률만 사용합니다. 관측이 3개 미만이면 표시하지 않습니다. '+(Math.min(...spans)<30?'현재 최소 종목 관측치가 30일 미만이어서 장기적 위험 추정은 부적절합니다.':'기간·종목별 관측기간 차이를 주의하세요.');
  };
  const pearson=(x,y)=>{const mx=mean(x),my=mean(y),den=x.reduce((s,v)=>s+(v-mx)**2,0);if(den<=0)return null;const beta=x.reduce((s,v,i)=>s+(v-mx)*(y[i]-my),0)/den;return {a:my-beta*mx,b:beta}};
  function signal(){
    const code=document.getElementById('signalStock').value, all=series(code),datesFor=returns(all).map(o=>o.date),dateEl=document.getElementById('signalDate'),prior=dateEl.value;
    dateEl.innerHTML=datesFor.map(d=>'<option value="'+d+'">'+d+'</option>').join('');
    dateEl.value=datesFor.includes(prior)?prior:datesFor.at(-1)||'';
    const date=dateEl.value, ix=datesFor.indexOf(date), targetReturns=returns(all);
    const dayDateMap=new Map(data.filter(r=>r['거래일']>=start&&r['거래일']<=end).map(r=>[r['거래일'],r]));
    // Peer return is average of same-day other banks, with minimum three peers.
    const x=[],y=[];let todayX=null;
    const lookup=Object.fromEntries(codes.filter(c=>c!==code).map(c=>[c,new Map(returns(series(c)).map(v=>[v.date,v.value]))]));
    for(let i=0;i<targetReturns.length;i++){
      const t=targetReturns[i], peers=Object.values(lookup).map(m=>m.get(t.date)).filter(Number.isFinite);
      if(peers.length<3)continue;
      const peer=mean(peers);
      if(t.date===date)todayX=peer;
      if(t.date<date){x.push(peer);y.push(t.value)}
    }
    let text='',pred=NaN,z=NaN,actual=targetReturns[ix]?.value;
    if(x.length>=30&&Number.isFinite(todayX)&&Number.isFinite(actual)){
      const model=pearson(x,y);
      if(model){pred=model.a+model.b*todayX;const residuals=x.map((v,i)=>y[i]-(model.a+model.b*v)),scale=sd(residuals);z=scale>0?(actual-pred)/scale:NaN}
      text='<strong>동종 은행 움직임 대비 분석</strong><p class="v2-narrative">선택 날짜 이전 '+x.length+'개의 공통 관측치로 추정한 동종 은행 평균수익률 기반 회귀모형입니다. 실제 수익률은 '+pct(actual)+'이며 모형 기대값은 '+pct(pred)+'입니다. 잔차는 '+pct(actual-pred)+'p, 표준화 잔차는 '+(Number.isFinite(z)?z.toFixed(2):'—')+'입니다.</p><p class="v2-narrative">이는 시장 전체(KOSPI)나 거시변수를 통제한 인과적 분석이 아닙니다. 동종 은행과 비교해 비정상적으로 움직였는지 알아보기 위한 탐색 분석입니다.</p>';
    }else{
      text='<strong>아직 이상 움직임을 판정하지 않습니다.</strong><p class="v2-narrative">이 종목은 선택 날짜 이전에 동일 기간 동종 은행들과 비교할 수 있는 관측치가 '+x.length+'개 있습니다. 통계적 이상 여부를 계산하려면 최소 30개 이상의 과거 관측치가 필요합니다. 데이터가 충분히 쌓일 때까지 결과를 추측하지 않습니다.</p>';
    }
    document.getElementById('signalMetrics').innerHTML=metric('선택 날짜',date||'—',names[code])+metric('실제 일간 수익률',pct(actual),'종가 기준')+metric('동종 은행 기반 예상',pct(pred),'30개 이상 관측치 필요')+metric('표준화 잔차',Number.isFinite(z)?z.toFixed(2):'—','표본 잔차의 표준편차 단위');
    document.getElementById('signalResult').innerHTML=text;news(code,date);
  }
  function news(code,date){
    const box=document.getElementById('signalNews');
    if(!date){box.textContent='비교할 거래일을 선택하세요.';return;}
    const target=new Date(date+'T12:00:00');
    const gap=a=>Math.abs((new Date(a.date+'T12:00:00')-target)/864e5);
    const relevant=(newsData.articles||[]).filter(a=>a.code===code && gap(a)<=3)
      .sort((a,b)=>gap(a)-gap(b) || Number(b.score||0)-Number(a.score||0));
    const exact=relevant.filter(a=>a.date===date),others=relevant.filter(a=>a.date!==date);
    const articles=[...exact,...others].slice(0,7);
    const archive=(newsData.fetched_windows||[]).length;
    if(!articles.length){
      box.innerHTML='<p class="v2-narrative"><strong>'+esc(names[code])+' · '+esc(date)+'</strong>에 대한 검증 가능한 기사를 보관한 자료에서 찾지 못했습니다.</p>'+
      '<p class="v2-narrative">뉴스가 없다는 의미가 아닙니다. 외부 뉴스 검색은 GitHub Actions 실행 시 수행되며, 사이트에서 날짜를 선택할 때 직접 인터넷을 검색하지는 않습니다. 검색 누락이나 매체 제공 범위의 한계가 있을 수 있습니다.</p>'+
      '<a href="https://www.google.com/search?'+
      'q='+encodeURIComponent(names[code]+' after:'+date+' before:'+new Date(target.getTime()+864e5).toISOString().slice(0,10))+
      '&tbm=nws" target="_blank" rel="noopener noreferrer">선택 날짜 뉴스 검색 결과 확인 ↗</a>'+
      '<p class="plotnote">백그라운드 아카이브 검색 구간: '+archive+'개. 주가 변동의 원인을 확인할 근거는 부족합니다.</p>';
      return;
    }
    const sourceCount=new Set(articles.map(a=>a.source).filter(Boolean)).size;
    const sameDay=exact.length;
    const items=articles.map(a=>({
      ...a,
      title: String(a.title||'').trim(),
      summary: String(a.summary||'').trim(),
      source: String(a.source||'').trim()
    }));
    const thematic=[
      ['실적·수익성',/실적|순이익|이익|마진|NIM|대손|충당금|연체|건전성/],
      ['주주환원·자본',/배당|자사주|주주환원|증자|CET1|자본비율/],
      ['금리·환율·정책',/금리|환율|규제|금융당국|정책|대출/],
      ['증권사 평가',/목표주가|투자의견|매수|매도|증권사/]
    ].filter(([,rx])=>items.some(a=>rx.test(a.title))).map(([label])=>label);
    let headline='선택일 '+date+'에 보도된 기사 '+sameDay+'건';
    if(!sameDay)headline='선택일 당일 기사 없이 전후 3일 자료로 정리';
    const summaryLine=thematic.length
      ? '관련 기사에서 '+thematic.map(esc).join(' · ')+' 주제가 언급됐습니다. 아래 기사별 핵심 내용과 원문을 확인할 수 있습니다.'
      : '선택 기간 관련 기사 '+articles.length+'건이 확인됐습니다. 아래에서 개별 보도를 확인하세요.';
    box.innerHTML='<div class="v2-narrative"><strong>'+esc(names[code])+' · '+esc(date)+' 뉴스 브리핑</strong>'+
      '<p>'+esc(headline)+' · 화면에 표시된 기사 '+articles.length+'건 · 언론사 '+sourceCount+'곳</p>'+
      '<p>'+summaryLine+'</p>'+
      '<p class="plotnote">제목의 키워드를 기반으로 주제를 분류한 것이며, 기사 원문 전체를 읽은 AI 요약이나 주가변동 원인 판정이 아닙니다.</p></div>'+
      items.map(a=>'<div class="v2-article"><div class="v2-source">'+esc(a.date===date?'● 선택일 당일':'전후 관련 기사')+' · '+esc(a.date)+' · '+esc(a.source||'매체명 미확인')+'</div>'+
      '<strong>'+esc(a.title)+'</strong>'+
      '<p class="v2-narrative">'+(a.summary?esc(a.summary):'기사 제목만 확인됐습니다. 본문은 확보되지 않아 내용을 추측하지 않았습니다.')+'</p>'+
      (String(a.url||'').startsWith('https://')?'<a href="'+esc(a.url)+'" target="_blank" rel="noopener noreferrer">기사 원문 확인 ↗</a>':'')+'</div>').join('')+
      '<p class="plotnote">표시된 보도는 관련 가능성이 있는 자료이지 주가 변동의 인과적 설명은 아닙니다. 정보가 부족한 경우 원인을 단정하지 않습니다.</p>';
  }
  document.getElementById('signalStock').addEventListener('change',signal);
  document.getElementById('signalDate').addEventListener('change',()=>{const code=document.getElementById('signalStock').value;const date=document.getElementById('signalDate').value;signal()});
  document.getElementById('signalTab').addEventListener('click',()=>{active='signals';document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.id==='signalTab'));document.querySelectorAll('.panel').forEach(p=>p.classList.toggle('active',p.id==='signals'));signal()});
  ['start','end'].forEach(id=>document.getElementById(id).addEventListener('change',()=>{if(active==='signals')signal()}));
  fetch('./bank_data/news_briefs.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('뉴스 자료 없음');return r.json()}).then(j=>{newsData=j;if(active==='signals')signal()}).catch(()=>{newsData={articles:[]};});
  market();
})();