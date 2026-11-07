#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BANK:LAB 1차 면담 | 전체 591일 코스피·코스닥 관측 종목 수 시각화.

읽기 전용. 학교 서버 SQLite의 obs를 사용하거나, 이미 추출한 월별 CSV를 읽어 재생성한다.
- SQLite 우선: python3 banklab_week1_market_counts_v2.py
- CSV 재생성: python3 banklab_week1_market_counts_v2.py --csv 근거_월별종목수.csv

생성: 04_종목범위_그림.png / 04_종목범위_그림.svg / 근거_월별종목수.csv
한글 폰트가 서버에 없으면 대체 영문 표기로 출력(깨진 한글 대신 읽을 수 있는 표기).
"""
import argparse
import csv
import sqlite3
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

DEFAULT_DB = Path('/home/s202420500/banklab_close_location_full/full_20261105_154548_1759967/market_ohlc.sqlite')
VERIFIED = {'start': '2024-03-27', 'end': '2026-09-02', 'days': 591, 'html': 2403074, 'codes': 4813}
CSV_COLUMNS = ['month', 'days', 'kospi_avg', 'kosdaq_avg', 'kospi_min', 'kosdaq_min', 'kospi_max', 'kosdaq_max']


def get_korean_font():
    """글꼴 캐시가 오래되어도 설치된 글꼴 파일을 직접 등록한다."""
    path_keywords = ('nanumsquare', 'nanumgothic', 'noto', 'malgun', 'applegothic', 'undotum', 'baekmuk')
    paths = list(font_manager.findSystemFonts(fontext='ttf')) + list(font_manager.findSystemFonts(fontext='otf'))
    def priority(path):
        p = path.lower()
        names = ('nanumsquare', 'nanumgothic', 'notosanscjk', 'notosanskr', 'malgun', 'applegothic', 'undotum', 'baekmuk')
        return next((i for i, term in enumerate(names) if term in p), 99)
    for p in sorted(paths, key=priority):
        if not any(x in p.lower() for x in path_keywords):
            continue
        try:
            font_manager.fontManager.addfont(p)
            name = font_manager.FontProperties(fname=p).get_name()
            if name and any(x in (name+p).lower().replace(' ', '') for x in ('nanum','noto','malgun','apple','undotum','baekmuk')):
                plt.rcParams['font.family'] = name
                plt.rcParams['axes.unicode_minus'] = False
                plt.rcParams['svg.fonttype'] = 'path' # 서버/브라우저에서 동일하게 보이도록 글자를 경로로 저장
                return name
        except Exception:
            continue
    plt.rcParams['font.family'] = 'DejaVu Sans'
    return None


def month_sequence(start, end):
    y, m = map(int, start[:7].split('-'))
    ey, em = map(int, end[:7].split('-'))
    while (y, m) <= (ey, em):
        yield f'{y:04d}-{m:02d}'
        m += 1
        if m == 13:
            y, m = y+1, 1


def extract_db(dbfile):
    if not dbfile.is_file():
        raise FileNotFoundError(f'SQLite 파일을 찾지 못했습니다: {dbfile}')
    con = sqlite3.connect(f'file:{dbfile.resolve()}?mode=ro', uri=True)
    con.execute('PRAGMA query_only=ON')
    try:
        a = con.execute('SELECT MIN(d),MAX(d),COUNT(DISTINCT d),COUNT(*),COUNT(DISTINCT code) FROM obs').fetchone()
        if not a or a[0] is None:
            raise ValueError('obs 테이블이 비어 있습니다')
        meta = dict(start=a[0], end=a[1], days=int(a[2]), html=int(a[3]), codes=int(a[4]))
        recs = con.execute("""
        SELECT d, market, COUNT(DISTINCT code)
        FROM obs
        WHERE market IN ('코스피', '코스닥')
        GROUP BY d,market ORDER BY d,market
        """).fetchall()
    finally:
        con.close()

    by_day = defaultdict(lambda: {'코스피': 0, '코스닥': 0})
    for d, market, n in recs:
        by_day[d][market] = n
    by_month = defaultdict(list)
    for d, c in by_day.items():
        by_month[d[:7]].append(c)
    monthly = []
    for ym in month_sequence(meta['start'], meta['end']):
        vals = by_month.get(ym, [])
        kp = [v['코스피'] for v in vals]
        kd = [v['코스닥'] for v in vals]
        monthly.append(dict(month=ym, days=len(vals),
            kospi_avg=mean(kp) if kp else None,
            kosdaq_avg=mean(kd) if kd else None,
            kospi_min=min(kp) if kp else None,
            kosdaq_min=min(kd) if kd else None,
            kospi_max=max(kp) if kp else None,
            kosdaq_max=max(kd) if kd else None))
    return monthly, meta


def load_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        missing = set(CSV_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f'CSV 필수 컬럼 없음: {sorted(missing)}')
        raw = list(reader)
    if not raw:
        raise ValueError('월별 CSV가 비어 있습니다')
    parsed=[]
    for row in raw:
        v=dict(month=row['month'], days=int(row['days']))
        for k in CSV_COLUMNS[2:]:
            s = (row[k] or '').strip()
            v[k] = float(s) if s else None
        parsed.append(v)
    if len({r['month'] for r in parsed}) != len(parsed):
        raise ValueError('월별 CSV에 중복 월 존재')
    meta = dict(VERIFIED)
    meta['days'] = sum(x['days'] for x in parsed)
    return parsed,meta


def save_csv(rows, path):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in rows:
            item=r.copy()
            for k in CSV_COLUMNS[2:]:
                if item[k] is not None:
                    item[k]=round(item[k],2)
            w.writerow(item)


def plot(rows,meta,outdir):
    font = get_korean_font()
    ko = bool(font)
    text = {
        'title': 'BANK:LAB | 1차 면담 · 종목구성 범위' if ko else 'BANK:LAB | Week 1 - Stock Coverage',
        'subtitle':'전체시장 데이터 / 관측 591일의 월별 종목 수 집계' if ko else 'Full market - monthly stock code counts over 591 observed dates',
        'kpi': ['자료 기간','관측 날짜','전체 HTML','고유 종목코드'] if ko else ['Date span','Observed dates','Total HTML','Distinct codes'],
        'main':'월별 코스피·코스닥 일평균 관측 종목코드 수' if ko else 'Monthly average observed codes (KOSPI / KOSDAQ)',
        'days':'월별 자료가 있는 날짜 수' if ko else 'Observed dates per month',
        'kp':'코스피' if ko else 'KOSPI', 'kd':'코스닥' if ko else 'KOSDAQ',
        'units':'종목코드 수' if ko else 'Number of codes',
        'july':'2025.07 누락 22거래일' if ko else 'Jul 2025: 22 missing trading days',
        'note1':'월평균은 관측된 날짜만으로 계산. 폴더가 없는 날은 0개로 처리하지 않음.' if ko else 'Monthly mean uses observed dates only; missing dates are not counted as zero.',
        'note2':'고유 종목코드에는 ETF·ETN 등 포함. 종목 수 증감은 실제 상장기업 수의 변화가 아님.' if ko else 'Counts include ETFs/ETNs and are not equivalent to listed company counts.'
    }

    rows=sorted(rows,key=lambda r:r['month'])
    months=[r['month'] for r in rows]
    assert months==list(month_sequence(meta['start'],meta['end'])), 'CSV 월 구간이 실제 기간을 모두 포함하지 않습니다.'
    if sum(r['days'] for r in rows) != meta['days']:
        raise ValueError('월별 관측일수 합계가 전체 날짜 수와 다름')

    fig=plt.figure(figsize=(17.0,9.6), facecolor='white')
    fig.text(.048,.953,text['title'],fontsize=22,fontweight='bold',color='#172B4D',va='top')
    fig.text(.048,.910,text['subtitle'],fontsize=10.5,color='#64748B')

    cards=[(text['kpi'][0],f"{meta['start']} ~ {meta['end']}"),
           (text['kpi'][1],f"{meta['days']:,}"),
           (text['kpi'][2],f"{meta['html']:,}"),
           (text['kpi'][3],f"{meta['codes']:,}")]
    for i,(label,val) in enumerate(cards):
        left=.048+i*.228
        shape=FancyBboxPatch((left,.800),.211,.084,transform=fig.transFigure,
            boxstyle='round,pad=0.005,rounding_size=0.010',linewidth=.7,
            facecolor='#F4F7FB',edgecolor='#E1E7EE')
        fig.add_artist(shape)
        fig.text(left+.012,.858,label,color='#64748B',fontsize=10,va='center')
        fig.text(left+.012,.826,val,color='#172B4D',fontsize=14.5,fontweight='bold',va='center')

    xs=list(range(len(months)))
    kp=[r['kospi_avg'] or 0 for r in rows]
    kd=[r['kosdaq_avg'] or 0 for r in rows]
    obs=[r['days'] for r in rows]
    ax=fig.add_axes([.062,.353,.91,.403])
    bar_width=.43
    ax.bar([x-bar_width/2 for x in xs],kp,width=bar_width,color='#2465A4',label=text['kp'])
    ax.bar([x+bar_width/2 for x in xs],kd,width=bar_width,color='#26A0A0',label=text['kd'])
    ax.set_title(text['main'],loc='left',fontsize=15,fontweight='bold',color='#172B4D',pad=20)
    ax.set_ylabel(text['units'],color='#334155',fontsize=10)
    ax.set_xticks(xs)
    ax.set_xticklabels([])
    ax.grid(axis='y',alpha=.22)
    ax.set_axisbelow(True)
    ax.legend(loc='upper left',ncol=2,frameon=False)
    for s in ('top','right'): ax.spines[s].set_visible(False)
    max_y=max(max(kp),max(kd),1)
    ax.set_ylim(0, max_y*1.19)

    bx=fig.add_axes([.062,.176,.91,.135],sharex=ax)
    bx.bar(xs,obs,width=.78,color='#A6B4C5',label=text['days'])
    bx.set_ylim(0,max(max(obs),1)*1.34)
    bx.set_title(text['days'],loc='left',fontsize=11,fontweight='bold',pad=11,color='#172B4D')
    bx.set_ylabel('일' if ko else 'Days',fontsize=10)
    bx.set_xticks(xs)
    bx.set_xticklabels([m.replace('-','.') for m in months],rotation=55,ha='right',fontsize=8)
    bx.grid(axis='y',alpha=.18)
    bx.set_axisbelow(True)
    for s in ('top','right'): bx.spines[s].set_visible(False)
    for x,n in enumerate(obs):
        if n<=2: bx.text(x,n+.45,str(n),fontsize=9,ha='center',weight='bold',color='#B45309')

    if '2025-07' in months:
        k=months.index('2025-07')
        ax.axvspan(k-.5,k+.5,facecolor='#FDE8DA',alpha=.5,zorder=0)
        bx.axvspan(k-.5,k+.5,facecolor='#FDE8DA',alpha=.5,zorder=0)
        ax.text(k,max_y*1.055,text['july'],fontsize=9,ha='center',color='#AD5827',weight='bold')
        bx.bar(k,obs[k],width=.78,color='#E68B47')

    fig.text(.062,.070,text['note1'],fontsize=9.5,color='#576678')
    fig.text(.062,.045,text['note2'],fontsize=9.5,color='#576678')
    fig.savefig(outdir/'04_종목범위_그림.png',dpi=180,bbox_inches='tight',facecolor='white')
    fig.savefig(outdir/'04_종목범위_그림.svg',bbox_inches='tight',facecolor='white')
    plt.close(fig)
    return font


def main():
    p=argparse.ArgumentParser(description='BANK:LAB 종목구성 1차 면담 그래프 (월별 전체기간)')
    p.add_argument('--db',type=Path,default=DEFAULT_DB,help='학교 서버의 SQLite 경로')
    p.add_argument('--csv',type=Path,default=None,help='기존 월별 CSV로 재생성(학교 서버 DB 없이 가능)')
    p.add_argument('--out',type=Path,default=Path.home()/'banklab_week1_market_counts'/'market_counts')
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True)
    if a.csv is not None:
        rows,meta=load_csv(a.csv)
        source='CSV'
    elif a.db.exists():
        rows,meta=extract_db(a.db)
        source='SQLite (read only)'
    else:
        csv_here=Path(__file__).resolve().parent/'근거_월별종목수.csv'
        if not csv_here.is_file():
            p.error('SQLite가 없고, 월별 CSV도 없습니다. --csv로 파일 경로를 지정하세요.')
        rows,meta=load_csv(csv_here)
        source=f'CSV ({csv_here})'
    save_csv(rows,a.out/'근거_월별종목수.csv')
    font=plot(rows,meta,a.out)
    print('=== BANK:LAB | 1차 면담 월별 종목구성 시각화 ===')
    print('집계 원천:',source)
    print('기간:',meta['start'],'~',meta['end'])
    print('날짜:',meta['days'],'HTML:',meta['html'],'고유 코드:',meta['codes'])
    print('관측일수 총합:',sum(x['days'] for x in rows))
    print('사용 글꼴:',font or 'Korean font unavailable - English labels used')
    print('2025.07 관측일 수:',next((r['days'] for r in rows if r['month']=='2025-07'),None))
    print('출력 폴더:',a.out)
    print('원본 HTML/SQLite 수정 없음')


if __name__=='__main__':
    main()