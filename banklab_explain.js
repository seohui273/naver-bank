/* BANK:LAB | 설명하는 종목 탐색 v1
 * 선택 종목·기간에 따라 주가/거래량 그래프 해석을 자동 작성.
 * 데이터에서 확인되는 사실만 쓰며 뉴스 원인/투자 예측을 생성하지 않음.
 */
(() => {
  'use strict';
  if (typeof explore !== 'function' || !document.getElementById('explore')) return;
  const root = document.getElementById('explore');
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const won = value => Number.isFinite(value)
    ? Math.round(value).toLocaleString('ko-KR') + '원' : '확인 불가';
  const stocks = value => Number.isFinite(value)
    ? Math.round(value).toLocaleString('ko-KR') + '주' : '확인 불가';
  const signed = (value, unit = '%') => Number.isFinite(value)
    ? (value > 0 ? '+' : '') + value.toFixed(2) + unit : '계산 불가';
  const natural = x => Number.isFinite(x) ? x.toFixed(2) + '배' : '계산 불가';
  const validPrice = row => {
    const value = px(row);
    return Number.isFinite(value) && value > 0;
  };
  const validVolume = row => {
    const value = num(row['거래량']);
    return Number.isFinite(value) && value >= 0;
  };
  const volume = row => num(row['거래량']);
  const change = (a, b) => validPrice(a) && validPrice(b)
    ? (px(b) / px(a) - 1) * 100 : NaN;
  const avg = values => values.length ? values.reduce((a,b) => a+b,0) / values.length : NaN;
  const display = (id, html) => {const node=document.getElementById(id);if(node)node.innerHTML=html;};
  const latestDate = rows => rows.length ? rows[rows.length - 1]['거래일'] : '';
  const originalExplore = explore;

  const insertAfter = (selector, html) => {
    const chart = root.querySelector(selector);
    const card = chart && chart.closest('.card');
    if (card) card.insertAdjacentHTML('afterend', html);
  };

  insertAfter('#priceChart', [
    '<div class="card lab-explain" id="labPriceExplain" aria-live="polite">',
    '<div class="lab-explain-head"><div><span class="lab-kicker">DATA INTERPRETATION</span><h3>이 주가 그래프가 의미하는 것</h3></div><span class="lab-tag">선택 종목·기간 자동 해석</span></div>',
    '<div class="grid" id="labPriceMetrics"></div>',
    '<div class="lab-readings" id="labPriceNarrative"></div>',
    '<div class="lab-explain-foot" id="labPriceFoot"></div>',
    '</div>'
  ].join(''));

  insertAfter('#volumeChart', [
    '<div class="card lab-explain" id="labVolumeExplain" aria-live="polite">',
    '<div class="lab-explain-head"><div><span class="lab-kicker">VOLUME INSIGHT</span><h3>거래량 그래프를 이렇게 읽으면 돼요</h3></div><span class="lab-tag">관측된 거래량 기반</span></div>',
    '<div class="lab-readings" id="labVolumeNarrative"></div>',
    '<div class="lab-explain-foot" id="labVolumeFoot"></div>',
    '<div class="lab-actions" id="labNewsActions"></div>',
    '</div>'
  ].join(''));

  const style = document.createElement('style');
  style.textContent = [
    '.lab-explain{margin-top:13px;border-color:#dbe8e5;padding:23px 25px;}',
    '.lab-explain-head{display:flex;justify-content:space-between;align-items:start;gap:10px;margin-bottom:17px;flex-wrap:wrap;}',
    '.lab-explain-head h3{margin:4px 0 0;font-size:17px;color:#173a41;}',
    '.lab-kicker{font-size:10px;letter-spacing:1.5px;font-weight:800;color:#15796f;}',
    '.lab-tag{font-size:11px;border:1px solid #d6e7e2;background:#f5fbf9;color:#3b7971;padding:5px 9px;border-radius:6px;}',
    '.lab-explain .grid{grid-template-columns:repeat(3,minmax(0,1fr));margin:0 0 16px;}',
    '.lab-explain .grid .card{padding:14px 15px;background:#fafcfb;}',
    '.lab-explain .value{font-size:22px;}',
    '.lab-readings{font-size:13px;line-height:1.85;color:#455d66;}',
    '.lab-readings p{margin:0;padding:11px 0;border-bottom:1px solid #edf1ef;}',
    '.lab-readings p:last-child{border-bottom:0;}',
    '.lab-readings strong{color:#193e46;}',
    '.lab-explain-foot{margin-top:12px;font-size:11px;line-height:1.8;color:#819098;}',
    '.lab-actions{margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;}',
    '.lab-news-btn{border:1px solid #c9dcda;background:white;border-radius:7px;padding:9px 12px;font-size:12px;font-weight:700;color:#216d67;cursor:pointer;}',
    '.lab-news-btn:hover{background:#eef8f5;}',
    '@media(max-width:670px){.lab-explain{padding:17px 15px;}.lab-explain .grid{grid-template-columns:1fr;}.lab-explain .grid .card{padding:11px;}}'
  ].join('');
  document.head.appendChild(style);

  function peerComparison(code, firstDate, lastDate, ownReturn) {
    if (!Number.isFinite(ownReturn) || firstDate === lastDate) return null;
    const samples = [];
    for (const otherCode of codes) {
      if (otherCode === code) continue;
      const rows = series(otherCode);
      const first = rows.find(r => r['거래일'] === firstDate);
      const last = rows.find(r => r['거래일'] === lastDate);
      if (first && last && validPrice(first) && validPrice(last)) samples.push(change(first,last));
    }
    if (samples.length < 3) return null;
    const baseline = avg(samples);
    return { baseline, diff: ownReturn - baseline, count: samples.length };
  }

  function summarize(code) {
    const selected = series(code);
    const priced = selected.filter(validPrice);
    const quantity = selected.filter(validVolume);
    const stockName = names[code] || code;
    const label = '<strong>' + esc(stockName) + '</strong>';
    if (!priced.length) {
      display('labPriceMetrics','');
      display('labPriceNarrative','<p>이 기간에 유효한 종가가 없어 주가 흐름을 해석할 수 없습니다. 기간을 넓혀 확인해 주세요.</p>');
      display('labPriceFoot','값이 없는 날짜를 임의로 채우지 않습니다.');
      display('labVolumeNarrative','<p>유효한 종가가 없어 수익률과 거래량의 동시 움직임을 분석하지 않습니다.</p>');
      display('labVolumeFoot','');
      display('labNewsActions','');
      return;
    }

    const first = priced[0], last = priced[priced.length - 1];
    const firstDay = first['거래일'], lastDay = last['거래일'];
    const totalReturn = priced.length >= 2 ? change(first,last) : NaN;
    const highest = priced.reduce((best,r) => px(r)>px(best)?r:best,priced[0]);
    const lowest = priced.reduce((best,r) => px(r)<px(best)?r:best,priced[0]);
    const fromHigh = highest && px(highest)>0 ? (px(last)/px(highest)-1)*100 : NaN;
    const intervals = [];
    for(let i=1;i<priced.length;i++){
      const previous=priced[i-1], current=priced[i],ret=change(previous,current);
      if(Number.isFinite(ret)) intervals.push({date:current['거래일'],value:ret});
    }
    const biggest = [...intervals].sort((a,b) => Math.abs(b.value)-Math.abs(a.value))[0];
    const recent = intervals.slice(-3);
    const recentUp = recent.filter(x=>x.value>0).length;
    const recentDown = recent.filter(x=>x.value<0).length;
    const lastRow = selected[selected.length-1];
    const pricesNotObserved = selected.length-priced.length;
    const compare = peerComparison(code,firstDay,lastDay,totalReturn);
    const sameDayCount = codes.filter(c=>series(c).some(r=>r['거래일']===lastDay)).length;

    display('labPriceMetrics', [
      metric('선택 기간 누적수익률',signed(totalReturn),priced.length+'개 유효 종가 기준'),
      metric('기간 최고 종가',won(px(highest)),highest['거래일']),
      metric('기간 최저 종가',won(px(lowest)),lowest['거래일'])
    ].join(''));

    let paragraphs = [];
    if(priced.length>=2){
      const trend = totalReturn>0?'상승':totalReturn<0?'하락':'보합';
      paragraphs.push('<p><strong>① 전체 흐름:</strong> '+label+'은(는) '+esc(firstDay)+'부터 '+esc(lastDay)+
        '까지 종가가 '+won(px(first))+'에서 '+won(px(last))+'으로 움직였습니다. '+
        '선택 기간의 수익률은 <strong>'+signed(totalReturn)+'</strong>로, 출발점 대비 '+trend+'했습니다.</p>');
      paragraphs.push('<p><strong>② 고점·저점:</strong> 이 기간 최고 종가는 '+esc(highest['거래일'])+'의 '+won(px(highest))+
        ', 최저 종가는 '+esc(lowest['거래일'])+'의 '+won(px(lowest))+
        '입니다. 마지막 종가는 기간 최고 종가보다 <strong>'+signed(fromHigh)+'</strong> 낮거나 같습니다. '+
        '단, 이는 관측 종가 간 차이이지 장중 최고·최저가를 뜻하지 않습니다.</p>');
      if(biggest){
        paragraphs.push('<p><strong>③ 가장 큰 변화:</strong> 직전 관측 종가와 비교한 변동폭이 가장 컸던 날은 <strong>'+
          esc(biggest.date)+'</strong>이며, 해당 관측 구간 수익률은 <strong>'+signed(biggest.value)+
          '</strong>였습니다. 이날의 변동 배경은 관련 뉴스와 함께 확인해 볼 만합니다.</p>');
      }
      if(recent.length>=2){
        paragraphs.push('<p><strong>④ 최근 흐름:</strong> 마지막 '+recent.length+
          '개 관측 구간 중 상승 '+recentUp+'회, 하락 '+recentDown+
          '회였습니다. 이 숫자는 최근 방향을 설명하지만 앞으로도 같은 흐름이 지속된다는 근거는 아닙니다.</p>');
      }
      if(compare){
        const relative = compare.diff>0?'높았습니다':compare.diff<0?'낮았습니다':'같았습니다';
        paragraphs.push('<p><strong>⑤ 다른 은행과 비교:</strong> 같은 시작일·종료일에 종가가 있는 다른 은행주 '+
          compare.count+'개의 평균 누적수익률은 '+signed(compare.baseline)+'입니다. '+
          esc(stockName)+'의 수익률은 이보다 <strong>'+signed(Math.abs(compare.diff),'%p')+
          '</strong> '+relative+' 은행 전체와 다른 움직임을 보였는지 확인할 수 있지만, '+
          '시장 영향을 통제한 초과수익률이나 통계적 유의성을 뜻하지는 않습니다.</p>');
      } else {
        paragraphs.push('<p><strong>⑤ 다른 은행과 비교:</strong> 정확히 같은 시작일과 종료일에 종가가 확인되는 '+
          '비교 종목이 3개 미만이어서 종목 간 수익률 차이는 계산하지 않았습니다.</p>');
      }
    } else {
      paragraphs.push('<p><strong>현재 확인 가능한 사실:</strong> '+esc(firstDay)+' '+label+
        '의 종가는 '+won(px(first))+'입니다. 유효한 종가가 한 개뿐이라 상승·하락 추세나 누적수익률을 판단할 수 없습니다.</p>');
    }
    display('labPriceNarrative',paragraphs.join(''));
    display('labPriceFoot','해석 구간: '+esc(firstDay)+' ~ '+esc(lastDay)+
      ' · 유효 종가 '+priced.length+'개, 관측 구간 수익률 '+intervals.length+'개'+
      (pricesNotObserved?' · 종가 결측 '+pricesNotObserved+'개':'')+
      ' · 차트 확대·축소는 해석 기간을 변경하지 않습니다. 상단 시작일·종료일을 변경해 주세요.'+
      (priced.length<20?' · 현재 표본이 짧으므로 지속적인 추세·위험 추정을 일반화하지 마세요.':''));

    // Volume comparisons are made against prior observations only, excluding the latest volume.
    const volBlocks = [];
    if (!quantity.length) {
      volBlocks.push('<p>선택한 기간에 유효한 거래량이 없어 거래 강도를 비교할 수 없습니다.</p>');
    } else {
      const current = quantity[quantity.length-1];
      const previous = quantity.slice(Math.max(0,quantity.length-6),-1);
      const reference = previous.length>=3 ? avg(previous.map(volume)) : NaN;
      const multiple = Number.isFinite(reference)&&reference>0 ? volume(current)/reference : NaN;
      const maxVol = quantity.reduce((best,r)=>volume(r)>volume(best)?r:best,quantity[0]);
      const typical=avg(quantity.map(volume));
      const maxMultiple=typical>0 ? volume(maxVol)/typical : NaN;
      let relText='이전 관측치가 3개 미만이어서 평소 대비 거래량 증감을 평가하지 않았습니다.';
      if(Number.isFinite(multiple)){
        relText='직전 '+previous.length+'개 관측일의 거래량 평균 '+stocks(reference)+'와 비교하면 <strong>'+
          natural(multiple)+'</strong> 수준입니다. '+
          (multiple>=1.5?'최근 관측치보다 거래량이 상대적으로 많았습니다.':
            multiple<=0.67?'최근 관측치보다 거래량이 상대적으로 적었습니다.':'최근 평균과 크게 동떨어지지 않은 수준입니다.');
      }
      volBlocks.push('<p><strong>① 최근 거래량:</strong> '+esc(current['거래일'])+' 거래량은 <strong>'+
        stocks(volume(current))+'</strong>였습니다. '+relText+'</p>');
      volBlocks.push('<p><strong>② 거래 집중일:</strong> 선택 기간 거래량이 가장 많았던 날은 <strong>'+
        esc(maxVol['거래일'])+'</strong>이며 '+stocks(volume(maxVol))+'가 거래됐습니다. '+
        '기간 평균('+stocks(typical)+') 대비 '+natural(maxMultiple)+'입니다. '+
        '거래량 증감만으로 매수·매도 방향이나 상승·하락의 원인을 확정할 수는 없습니다.</p>');
      const anomalyDate = biggest?.date || latestDate(priced);
      if(anomalyDate) {
        const related = quantity.find(x=>x['거래일']===anomalyDate);
        const totalOnDate = related?volume(related):NaN;
        volBlocks.push('<p><strong>③ 주가 변화와 함께 확인:</strong> '+
          (biggest?'주가 변동폭이 가장 컸던 '+esc(biggest.date)+'의 수익률은 '+signed(biggest.value)+
            ', 같은 날 거래량은 '+stocks(totalOnDate)+'였습니다.':
            '종가가 기록된 최근 거래일과 거래량을 함께 살펴보세요.')+
          ' 두 지표가 함께 움직였더라도 뉴스·공시 없이 원인을 단정할 수 없습니다.</p>');
      }
      const mixed = selected.some(r=>(r['비고']||'').includes('백필'));
      display('labVolumeFoot','거래량 비교는 선택 기간의 관측 자료 기준이며, 직전 평균에 당일 거래량을 포함하지 않습니다.'+
        (mixed?' · 선택 기간에 백필 자료가 있습니다. KRX 일봉 거래량과 NXT 포함 통합 시세의 집계 범위가 다를 수 있으므로 평균 배수를 비교할 때 주의하세요.':'')+
        ' · 거래량은 매수 또는 매도세의 순방향을 직접 알려주지 않습니다.');
    }
    display('labVolumeNarrative',volBlocks.join(''));

    let buttons = '';
    const possibleDates = [];
    if (biggest?.date) possibleDates.push({date:biggest.date, label:'변동폭 최대일 뉴스·해설 보기'});
    if (intervals.length && latestDate(priced)!==biggest?.date)
      possibleDates.push({date:latestDate(priced),label:'최근 거래일 뉴스·해설 보기'});
    if (possibleDates.length) {
      buttons = possibleDates.map(item=>'<button type="button" class="lab-news-btn" data-explain-date="'+
        esc(item.date)+'" data-explain-code="'+esc(code)+'">'+esc(item.label)+' ('+esc(item.date)+') ↗</button>').join('');
    }
    display('labNewsActions',buttons);
    if (!quantity.length) display('labVolumeFoot','거래량 자료가 없어 분석하지 않았습니다.');
  }

  root.addEventListener('click',event=>{
    const button=event.target.closest('[data-explain-date][data-explain-code]');
    if(!button)return;
    const target=button.dataset.explainDate,code=button.dataset.explainCode;
    const signalTab=document.getElementById('signalTab');
    if(!signalTab)return;
    signalTab.click();
    const stock=document.getElementById('signalStock');
    const day=document.getElementById('signalDate');
    stock.value=code;
    stock.dispatchEvent(new Event('change',{bubbles:true}));
    if(Array.from(day.options).some(option=>option.value===target)){
      day.value=target;
      day.dispatchEvent(new Event('change',{bubbles:true}));
    }
    document.querySelector('nav.tabs')?.scrollIntoView({behavior:'smooth',block:'start'});
  });

  explore = function () {
    originalExplore();
    try { summarize(document.getElementById('stock').value); }
    catch (err) {
      console.warn('BANK:LAB descriptive interpretation error:',err);
      display('labPriceNarrative','<p>해석을 계산하는 중 오류가 발생했습니다. 원본 가격·거래량 그래프는 계속 사용할 수 있습니다.</p>');
    }
  };
})();
