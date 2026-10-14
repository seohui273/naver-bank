#!/usr/bin/env python3
"""Refresh BANK:LAB v4 embedded data and a reproducible descriptive-statistics report."""
import csv
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORY = ROOT / 'bank_data' / 'bank_history.csv'
HTML = ROOT / 'index.html'
REPORT = ROOT / 'reports' / 'latest.md'
STAT_CSV = ROOT / 'reports' / 'stock_stats.csv'
KST = timezone(timedelta(hours=9))
EXPECTED = 11

def number(x):
    s = str(x or '').replace(',', '').replace('원', '').replace('%', '').replace('배', '').strip()
    try:
        v = float(s)
        return v if math.isfinite(v) else None
    except ValueError:
        return None

def main():
    if not HISTORY.exists() or not HTML.exists():
        raise SystemExit('bank_data/bank_history.csv and root index.html are required')
    with HISTORY.open(encoding='utf-8-sig', newline='') as f:
        records = list(csv.DictReader(f))
    needed = {'거래일', '종목코드', '종목명', '현재가', '거래량'}
    if not records or not needed.issubset(records[0]):
        raise SystemExit('Missing or empty bank_history.csv columns')
    # Preserve the latest occurrence for each date + stock code; never invent missing entries.
    unique = {}
    for row in records:
        date, code = (row.get('거래일') or '').strip(), (row.get('종목코드') or '').strip().zfill(6)
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date) or not re.fullmatch(r'\d{6}', code):
            raise SystemExit(f'Invalid date/code in row: {date}/{code}')
        row['거래일'], row['종목코드'] = date, code
        unique[(date, code)] = row
    rows = sorted(unique.values(), key=lambda r: (r['거래일'], r['종목코드']))
    dates = sorted({r['거래일'] for r in rows})
    if len({r['종목코드'] for r in rows}) > EXPECTED:
        raise SystemExit('Unexpected >11 stock codes: check your history file')
    html = HTML.read_text(encoding='utf-8')
    # Compatible with BANK:LAB v4: replace only the embedded data payload.
    regex = r'(<script\s+id="dataset"\s+type="application/json">)(.*?)(</script>)'
    payload = json.dumps(rows, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    updated, n = re.subn(regex, lambda m: m.group(1) + payload + m.group(3), html, count=1, flags=re.S)
    if n != 1:
        raise SystemExit('Missing v4 dataset script: do not overwrite HTML with a different template')
    updated = updated.replace('현재 HTML은 데이터 내장형 미리보기로 자동 갱신 기능은 아직 연결되지 않았습니다.', '매일 수집 데이터가 GitHub Actions를 통해 자동 반영됩니다.')
    HTML.write_text(updated, encoding='utf-8')
    groups = defaultdict(list)
    for r in rows: groups[r['종목코드']].append(r)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    metric_rows = []
    for code, values in sorted(groups.items()):
        obs = [(r['거래일'], number(r['현재가'])) for r in values]
        obs = [(date, price) for date, price in obs if price is not None and price > 0]
        returns = [obs[i][1] / obs[i-1][1] - 1 for i in range(1, len(obs))]  # adjacent observed sessions
        cumulative = (obs[-1][1] / obs[0][1] - 1) * 100 if len(obs) >= 2 else None
        mean = sum(returns)/len(returns) * 100 if returns else None
        stdev = math.sqrt(sum((x - sum(returns)/len(returns))**2 for x in returns)/(len(returns)-1)) * 100 if len(returns)>1 else None
        metric_rows.append({'종목코드':code,'종목명': values[-1]['종목명'], '관측일수':len(obs),
                            '누적수익률(%)':cumulative, '평균관측수익률(%)':mean, '표본표준편차(%)':stdev})
    with STAT_CSV.open('w', newline='', encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f, fieldnames=list(metric_rows[0]));writer.writeheader()
        for r in metric_rows:
            writer.writerow({k:(f'{v:.4f}' if isinstance(v,float) else ('' if v is None else v)) for k,v in r.items()})
    coverage=Counter(r['거래일'] for r in rows)
    backfill=sorted({r['거래일'] for r in rows if '백필' in (r.get('비고') or '')})
    missing_price=sum(number(r['현재가']) is None for r in rows)
    missing_volume=sum(number(r['거래량']) is None for r in rows)
    now=datetime.now(KST).strftime('%Y-%m-%d %H:%M KST')
    summary=[
        '# BANK:LAB 자동 금융통계 보고서','',f'- 생성: {now}',
        f'- 관측 기간: {dates[0]} ~ {dates[-1]}',f'- 거래일: {len(dates)}일 / 종목: {len(groups)}개 / 행: {len(rows)}개',
        f'- 종가 결측: {missing_price}행 / 거래량 결측: {missing_volume}행',
        f'- 백필 표기 날짜: {", ".join(backfill) if backfill else "없음"}',
        '', '## 날짜별 수집 완전성', '', '| 거래일 | 관측 종목 | 11종목 충족 |', '|---|---:|---|',
        *[f'| {d} | {coverage[d]} | {"예" if coverage[d]==EXPECTED else "아니오"} |' for d in dates],
        '', '## 종목별 기술통계', '', '| 종목 | 관측일 | 누적수익률(%) | 평균 관측수익률(%) | 표본표준편차(%p) |', '|---|---:|---:|---:|---:|',
    ]
    def fmt(x):return 'NA' if x is None else f'{x:.2f}'
    summary.extend(f'| {r["종목명"]} | {r["관측일수"]} | {fmt(r["누적수익률(%)"])} | {fmt(r["평균관측수익률(%)"])} | {fmt(r["표본표준편차(%)"])} |' for r in metric_rows)
    summary += ['', '## 계산 및 해석 기준', '',
                '- 수익률 = (이번 관측 종가 / 직전 관측 종가) − 1. 실제 연속 거래일 여부와 관계없이 **관측된 두 날짜 사이**의 수익률입니다.',
                '- 누적수익률은 선택 자료에서 첫 종가 대비 마지막 종가 변화율입니다.',
                '- 평균은 관측 구간별 수익률의 산술평균, 표준편차는 표본표준편차(ddof=1)이며 연율화하지 않았습니다.',
                '- 결측값은 임의의 가격으로 대체하지 않았습니다. 백필 자료의 거래량 집계 기준이 다를 수 있습니다.',
                '- 관측 기간이 짧으면 분석 결과의 통계적 해석에 주의해야 합니다. 투자 권유가 아닙니다.','']
    REPORT.write_text('\n'.join(summary),encoding='utf-8')
    print(f'Updated index.html and reports for {len(rows)} rows / {len(dates)} dates / {len(groups)} stocks')
if __name__=='__main__': main()
