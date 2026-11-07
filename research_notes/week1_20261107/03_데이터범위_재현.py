#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BANK:LAB 1차 면담: 월별 결측 분포 막대그래프 (matplotlib).

실제 학교 서버에서 검증된 월별 집계 CSV만 사용한다.
날짜별 시계열을 생성하거나 누락된 2025-07의 원자료를 보간하지 않는다.

사용:
  python3 -m pip install matplotlib   # 미설치인 경우에만
  python3 banklab_week1_bar_chart.py
  python3 banklab_week1_bar_chart.py --csv 근거_월별공백현황.csv --outdir 결과

기존 HTML, SQLite, 수집 결과는 읽지도/수정하지도 않는다.
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE / '근거_월별공백현황.csv'
QUESTION = '같은 업종에 속한 기업들의 주가는 서로 어떤 관계를 보이며, 특정 기업의 주가 움직임이 다른 기업보다 먼저 나타나는 현상이 존재할까?'
NAVY = '#152C4B'
TEXT = '#253B55'
BLUE = '#4879B8'
BLUE_LIGHT = '#98B9E0'
ORANGE = '#E0874E'
RED = '#CE5F3F'
BG = '#FFFFFF'
MUTED = '#61758C'


def read_counts(path: Path):
    if not path.is_file():
        raise SystemExit(f'입력 CSV가 없습니다: {path}')
    rows = []
    seen = set()
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            year, month = int(r['년']), int(r['월'])
            key = (year, month)
            if key in seen:
                raise ValueError(f'중복 월: {key}')
            seen.add(key)
            if not (1 <= month <= 12):
                raise ValueError(f'월 범위 이상: {key}')
            absent = int(r['폴더없는평일_휴장포함'])
            partial = int(r['HTML_진단기준미만일'])
            if min(absent, partial) < 0:
                raise ValueError(f'음수 일수 발견: {key}')
            rows.append({'year':year, 'month':month,'label':f'{year}.{month:02d}',
                         'absent':absent,'partial':partial})
    rows.sort(key=lambda d: (d['year'],d['month']))
    if not rows:
        raise ValueError('입력 월별 집계가 비어 있습니다.')
    return rows


def set_korean_font():
    from matplotlib import font_manager, rcParams
    available = {f.name for f in font_manager.fontManager.ttflist}
    for family in ('NanumBarunGothic','NanumGothic','Noto Sans CJK KR','Malgun Gothic','AppleGothic'):
        if family in available:
            rcParams['font.family'] = family
            break
    else:
        print('[주의] 한글 글꼴이 없어 한글이 깨질 수 있습니다.')
    rcParams.update({'axes.unicode_minus': False,'svg.fonttype':'none','font.size':12})


def plot_panel(ax, rows, field, color, standout=None, max_x=None):
    from matplotlib.ticker import MaxNLocator
    pairs = [r for r in rows if r[field] > 0]
    pairs.sort(key=lambda r:(-r[field],r['year'],r['month']))
    names = [r['label'] for r in pairs]
    vals = [r[field] for r in pairs]
    palette = [(RED if r['label'] == standout else color) for r in pairs]
    bars = ax.barh(names,vals,color=palette,height=.66,zorder=3)
    ax.invert_yaxis()
    ax.set_xlim(0,max_x or (max(vals,default=1)*1.15 + .8))
    ax.xaxis.set_major_locator(MaxNLocator(integer=True,nbins=6))
    ax.set_axisbelow(True)
    ax.grid(axis='x',color='#E6ECF2',lw=1,zorder=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis='both',length=0,labelcolor=TEXT,labelsize=11,pad=9)
    for b,v in zip(bars,vals):
        ax.text(v+.32,b.get_y()+b.get_height()/2,str(v),va='center',ha='left',
                color=RED if (standout and v == max(vals)) else TEXT,
                fontsize=12,fontweight='bold')
    ax.set_xlabel('일수 (일)',fontsize=10.5,color=MUTED,labelpad=12)
    return pairs


def make_fig(rows,outdir):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    set_korean_font()
    missing = sum(r['absent'] for r in rows)
    low = sum(r['partial'] for r in rows)
    july = next((r['absent'] for r in rows if (r['year'],r['month']) == (2025,7)),None)
    print(f'[집계 검증] 폴더 없는 평일={missing} / HTML 3000개 미만={low} / 2025년 7월={july}')
    # 학교 서버에서 앞서 출력한 집계와 동일한지 사전에 검증. 다른 값이면 사용자에게 확인 요청.
    if (missing,low,july) != (45,14,22):
        raise SystemExit('기존 검증 기록(45, 14, 22)과 불일치: 저장하지 않고 중단합니다.')

    fig=plt.figure(figsize=(16,9),dpi=175,facecolor=BG)
    fig.text(.055,.945,'BANK:LAB',fontsize=22,fontweight='bold',color=NAVY)
    fig.text(.222,.946,'1차 면담 | 전체시장 데이터 수집 범위',fontsize=21,fontweight='bold',color=NAVY)
    fig.text(.055,.901,'2024.03.27 – 2026.09.02  |  학교 서버 HTML · SQLite 검증 집계',fontsize=11.5,color=MUTED)

    # 상단 지표 카드: 사용자 학교 서버 출력에서 직접 확인된 값.
    cards=[('자료가 있는 날짜','591일'),('전체 HTML','2,403,074개'),('고유 종목코드','4,813개'),('폴더 없는 평일','45일')]
    start=.055; space=.014; w=(.89-3*space)/4
    for i,(label,val) in enumerate(cards):
        x=start+i*(w+space)
        patch=FancyBboxPatch((x,.788),w,.087,boxstyle='round,pad=0.009,rounding_size=0.01',
                              transform=fig.transFigure,facecolor='#F5F8FC',edgecolor='#DCE6F0',lw=1)
        fig.patches.append(patch)
        fig.text(x+.018,.844,label,fontsize=10.4,color=MUTED)
        fig.text(x+.018,.806,val,fontsize=21,fontweight='bold',color=NAVY)

    fig.text(.060,.745,'A. 월별 날짜 폴더 공백',fontsize=16,fontweight='bold',color=NAVY)
    fig.text(.524,.745,'B. 월별 부분 수집 의심일',fontsize=16,fontweight='bold',color=NAVY)
    fig.text(.060,.711,'폴더가 없는 평일 수 · 휴장일 포함',fontsize=10.7,color=MUTED)
    fig.text(.524,.711,'HTML 3,000개 미만인 날짜 수 · 임시 진단 기준',fontsize=10.7,color=MUTED)

    ax1=fig.add_axes([.090,.265,.365,.405]); ax2=fig.add_axes([.555,.265,.365,.405])
    plot_panel(ax1,rows,'absent',BLUE,standout='2025.07',max_x=25.5)
    plot_panel(ax2,rows,'partial',ORANGE,max_x=9)

    # 설명 카드: 두 데이터 품질 지표를 명확히 구분.
    patch=FancyBboxPatch((.054,.095),.892,.108,boxstyle='round,pad=0.008,rounding_size=0.012',
                         transform=fig.transFigure,facecolor='#FFF8F3',edgecolor='#F4DFD2',lw=1)
    fig.patches.append(patch)
    fig.text(.075,.167,'핵심 공백 · 2025년 7월 2–31일',fontsize=12.5,fontweight='bold',color='#A64A2B')
    fig.text(.075,.138,'22거래일의 날짜 폴더 누락을 확인했으며, 해당 구간의 수익률 자료를 임의로 보간하지 않았음.',fontsize=11.3,color=TEXT)
    fig.text(.075,.107,'초기 8일은 동일한 947종목이 반복됐고, 3,000개 미만 날짜는 총 14일임.',fontsize=10.8,color=MUTED)
    fig.text(.056,.055,'해석 주의: “폴더 없는 평일”에는 공식 휴장일이 포함됨. 낮은 HTML 수는 진단 단서이지 곧바로 수집 실패·삭제 기준을 의미하지 않음.',
             fontsize=9.8,color=MUTED)
    fig.text(.056,.028,'자료: 학교 서버 읽기 전용 SQLite에서 검증한 월별 집계 CSV  |  재현: Python matplotlib',fontsize=9.2,color=MUTED)

    outdir.mkdir(parents=True,exist_ok=True)
    paths=[]
    for suffix in ('png','svg'):
        path=outdir/f'BANKLAB_1차면담_월별공백_막대그래프.{suffix}'
        fig.savefig(path,dpi=200,facecolor=BG,bbox_inches='tight',pad_inches=.16)
        paths.append(path)
    plt.close(fig)
    return paths


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--csv',type=Path,default=DEFAULT_CSV)
    p.add_argument('--outdir',type=Path,default=HERE)
    args=p.parse_args()
    rows=read_counts(args.csv)
    generated=make_fig(rows,args.outdir)
    print('[그림 생성 완료]')
    for path in generated:print(path)
    print('학교 서버의 원본 HTML/SQLite 및 기존 분석 결과 수정 없음.')

if __name__=='__main__':main()