#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BANK:LAB | 1차 면담: 실제 월별 수집 공백 통계 시각화

출력물: 01_데이터범위_그림.png, 01_데이터범위_그림.svg
근거: 2024.03.27~2026.09.02 학교 서버에서 검증한 월별 집계 CSV

- 원본 학교 서버 HTML/SQLite는 열거나 수정하지 않습니다.
- 없는 거래일의 HTML 수를 0으로 대입하여 거짓 시계열을 그리지 않습니다.
- '폴더 없는 평일'에는 휴장일이 포함되고,
  'HTML < 3,000'은 결측 확정이 아닌 점검용 임시 기준입니다.

실행:
    python3 banklab_week1_scope_plot.py
    python3 banklab_week1_scope_plot.py --csv 근거_월별공백현황.csv --outdir .

사전 요구: matplotlib
    python3 -m pip install matplotlib
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch

BASE = Path(__file__).resolve().parent
DATA = BASE / '근거_월별공백현황.csv'

# 1차 면담 전 학교 서버 실행 출력값: 월별 CSV와 별도로 독립 확인한 숫자.
START = date(2024, 3, 27)
END = date(2026, 9, 2)
OBSERVED_DATES = 591
HTML_TOTAL = 2_403_074
UNIQUE_CODES = 4_813  # 주식 종목만이 아니라 ETF·ETN 등도 포함한 고유 코드 합집합
MISSING_WEEKDAYS = 45  # 휴장일 포함, '미수집 거래일'과 동일하지 않음
UNDER_3000_DATES = 14  # 임시 진단 기준
JUL_2025_MISSING = 22

# Palette: readable in print and distinct in grayscale.
NAVY = '#182B47'
BLUE = '#2669A8'
ORANGE = '#D77D44'
PALE = '#F6F9FC'
BORDER = '#D9E4EF'
MUTED = '#62748B'
LIGHT_GRID = '#E8EDF3'
DARK = '#243B56'


def set_fonts():
    available = {x.name for x in font_manager.fontManager.ttflist}
    for name in ('NanumSquare', 'NanumGothic', 'Noto Sans CJK KR',
                 'Malgun Gothic', 'AppleGothic', 'UnDotum'):
        if name in available:
            plt.rcParams['font.family'] = name
            break
    else:
        print('[주의] 사용 가능한 한글 폰트를 찾지 못했습니다. 그림에서 한글이 깨질 수 있습니다.')
    plt.rcParams.update({
        'axes.unicode_minus': False,
        'svg.fonttype': 'none',
        'pdf.fonttype': 42,
        'font.size': 11,
    })


def load_monthly(path: Path):
    if not path.is_file():
        raise SystemExit(f'[오류] 월별 근거 CSV가 없음: {path}')
    records = {}
    with path.open('r', encoding='utf-8-sig', newline='') as file:
        rd = csv.DictReader(file)
        required = {'년','월','폴더없는평일_휴장포함','HTML_진단기준미만일'}
        if not required.issubset(set(rd.fieldnames or [])):
            raise ValueError(f'CSV 필수 컬럼이 없습니다: {sorted(required-set(rd.fieldnames or []))}')
        for row in rd:
            y, m = int(row['년']), int(row['월'])
            a = int(row['폴더없는평일_휴장포함'])
            b = int(row['HTML_진단기준미만일'])
            if m < 1 or m > 12 or a < 0 or b < 0:
                raise ValueError(f'월 또는 집계 값이 잘못됨: {row}')
            key = (y,m)
            if key in records:
                raise ValueError(f'중복된 월: {key}')
            records[key] = (a,b)
    months=[]
    y,m=2024,3
    while (y,m) <= (2026,9):
        if (y,m) not in records:
            raise ValueError(f'연구 기간 중 누락된 월이 있음: {y}-{m:02d}')
        a,b=records.pop((y,m))
        months.append((y,m,a,b))
        if m==12:y,m=y+1,1
        else:m+=1
    if records:
        raise ValueError(f'연구 기간 밖의 월이 들어 있음: {sorted(records)[:5]}')
    if sum(x[2] for x in months)!=MISSING_WEEKDAYS:
        raise ValueError('폴더 없는 평일 합계가 학교 서버 검증값 45일과 불일치')
    if sum(x[3] for x in months)!=UNDER_3000_DATES:
        raise ValueError('HTML 3,000개 미만 합계가 학교 서버 검증값 14일과 불일치')
    july = next(x for x in months if x[0]==2025 and x[1]==7)
    if july[2] != JUL_2025_MISSING:
        raise ValueError('2025년 7월 누락값이 검증값 22일과 불일치')
    return months


def draw_kpi(fig, left, top, width, label, value, note=None):
    # Figure coordinates; render directly via Matplotlib, not image generation.
    card=FancyBboxPatch((left,top-0.104), width,0.104,
                        transform=fig.transFigure, boxstyle='round,pad=0.007,rounding_size=0.010',
                        facecolor=PALE, edgecolor=BORDER, linewidth=1.05)
    fig.add_artist(card)
    fig.text(left+0.016,top-0.029,label, fontsize=11.8, color=MUTED, weight='medium')
    fig.text(left+0.016,top-0.069,value, fontsize=(16.5 if ' – ' in value else (22 if note is None else 21)),
             color=NAVY, weight='bold')
    if note:
        fig.text(left+0.016,top-0.094,note,fontsize=8.8,color=MUTED)


def create_plot(months, outdir: Path):
    set_fonts()
    fig=plt.figure(figsize=(17.2,9.6),facecolor='white')
    fig.text(.050,.944,'BANK:LAB',weight='bold',fontsize=26,color=NAVY)
    fig.text(.206,.945,'1차 면담 | 읽어 들인 전체시장 데이터 범위',weight='bold',fontsize=22,color=NAVY)
    fig.text(.051,.904,'원본 HTML · 읽기 전용 SQLite 검증 집계    |    2024년 3월 ~ 2026년 9월',fontsize=11.8,color=MUTED)

    cards=[
        ('자료 기간', '2024.03.27 – 2026.09.02', None),
        ('자료가 있는 날짜',f'{OBSERVED_DATES:,}일',None),
        ('원본 HTML 총수',f'{HTML_TOTAL:,}개',None),
        ('고유 종목코드',f'{UNIQUE_CODES:,}개','ETF·ETN 등 포함'),
    ]
    card_left=.05; gap=.016; card_w=(.90-gap*3)/4
    for i,(label,val,note) in enumerate(cards):
        draw_kpi(fig,card_left+i*(card_w+gap), .861,card_w,label,val,note)

    fig.text(.056,.694,'월별 결측 및 부분 수집 분포',fontsize=19,color=NAVY,weight='bold')
    fig.text(.056,.660,'월별 두 지표를 동시에 비교 · 빈 날짜를 임의로 채우거나 연결하지 않음',fontsize=11,color=MUTED)
    # Main chart
    ax=fig.add_axes([.067,.263,.883,.354])
    positions=list(range(len(months)))
    missing=[x[2] for x in months]
    partial=[x[3] for x in months]
    width=.38

    # Distinct year backgrounds and one special highlight.
    year_ranges=[(2024,0,9),(2025,10,21),(2026,22,30)]
    for year,a,b in year_ranges:
        if year == 2025:
            ax.axvspan(a-.57,b+.53,facecolor='#F8FAFD',zorder=-2)
        ax.text((a+b)/2,24.2,str(year),ha='center',va='bottom',weight='bold',fontsize=13,color=MUTED)
    for k in [9.5,21.5]:
        ax.axvline(k,color='#D1DBE7',linestyle='--',lw=1.1,zorder=-1)
    jul_index=next(i for i,x in enumerate(months) if x[0]==2025 and x[1]==7)
    ax.axvspan(jul_index-.51,jul_index+.53,facecolor='#FFF0E6',zorder=-1)

    bars1=ax.bar([x-width/2 for x in positions],missing,width=width,
                 color=BLUE, label='폴더 없는 평일 (휴장 포함)',zorder=3)
    bars2=ax.bar([x+width/2 for x in positions],partial,width=width,
                 color=ORANGE,label='HTML 3,000개 미만 (진단)',zorder=3)
    # Numeric labels for non-zero bars; 2025.07 emphasized.
    for i,(bar,val) in enumerate(zip(bars1,missing)):
        if val>0:
            ax.text(bar.get_x()+bar.get_width()/2,val+0.5,str(val),
                    ha='center',va='bottom',fontsize=9.5,
                    weight='bold' if i==jul_index else 'normal',color=BLUE)
    for bar,val in zip(bars2,partial):
        if val>0:
            ax.text(bar.get_x()+bar.get_width()/2,val+.5,str(val),
                    ha='center',va='bottom',fontsize=9.5,color='#AF5830')
    ax.annotate('2025년 7월\n날짜 폴더 22거래일 누락',
                xy=(jul_index-width/2,22.0),xycoords='data',
                xytext=(jul_index-5,19.3),textcoords='data',
                fontsize=10,weight='bold',color='#A94D26',
                arrowprops=dict(arrowstyle='->',color='#B95C31',lw=1.6),
                bbox=dict(boxstyle='round,pad=.38',facecolor='#FFF6F0',edgecolor='#F0C3A6'))
    ax.set_ylim(0,26.5)
    ax.set_xlim(-.8,len(months)-.2)
    ax.set_ylabel('일수 (일)',fontsize=11.5,color=DARK,labelpad=15)
    ax.set_xticks(positions)
    ax.set_xticklabels([f'{m:02d}' for y,m,a,b in months],fontsize=9,color=DARK)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(5))
    ax.grid(axis='y',color=LIGHT_GRID,zorder=0)
    for s in ax.spines.values():s.set_visible(False)
    ax.tick_params(axis='both',length=0,pad=8,labelcolor=DARK)
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(facecolor=BLUE, label='폴더 없는 평일 (휴장 포함)'),
                        Patch(facecolor=ORANGE,label='HTML 3,000개 미만 (진단)')],
               frameon=False,ncol=2,loc='center',bbox_to_anchor=(.52,.223),
               fontsize=11.5,columnspacing=3)

    # Bottom evidence summary - avoids claiming all holidays are missing observations.
    footer=FancyBboxPatch((.048,.079),.904,.095,
                 transform=fig.transFigure,boxstyle='round,pad=0.008,rounding_size=0.012',
                 facecolor=PALE,edgecolor=BORDER,linewidth=1.0)
    fig.add_artist(footer)
    fig.text(.066,.139,'폴더 없는 평일',fontsize=10.7,color=MUTED)
    fig.text(.066,.104,'45일',fontsize=18,weight='bold',color=NAVY)
    fig.text(.25,.139,'HTML 3,000개 미만',fontsize=10.7,color=MUTED)
    fig.text(.25,.104,'14일',fontsize=18,weight='bold',color=NAVY)
    fig.text(.46,.139,'확인된 긴 공백',fontsize=10.7,color=MUTED)
    fig.text(.46,.106,'2025.07.02~07.31 · 22거래일',fontsize=14,weight='bold',color='#A94D26')
    fig.text(.058,.049,'해석 주의: 평일 폴더 부재에는 공식 휴장일이 포함됨. 3,000개는 부분 수집 의심일을 찾기 위한 임시 기준임.',
             fontsize=10,color=MUTED)
    fig.text(.058,.027,'고유 종목코드는 전체 기간의 합집합(일반주 이외 상품 포함). 원본 HTML·SQLite 수정 및 누락 구간 보간 없음.',
             fontsize=9.7,color=MUTED)

    outdir.mkdir(parents=True,exist_ok=True)
    results=[]
    for ext in ('png','svg'):
        p=outdir/f'01_데이터범위_그림.{ext}'
        fig.savefig(p,dpi=200,facecolor='white')
        results.append(p)
    plt.close(fig)
    return results


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--csv',type=Path,default=DATA,help='학교 서버 월별 검증 집계 CSV')
    p.add_argument('--outdir',type=Path,default=BASE,help='그림 저장 폴더')
    args=p.parse_args()
    months=load_monthly(args.csv)
    outputs=create_plot(months,args.outdir)
    print('[완료] 실제 월별 검증값으로 1차 면담 그림 생성')
    for p in outputs:print(p)
    print(f'[검증] 관측 날짜 {OBSERVED_DATES}일 / HTML {HTML_TOTAL:,}개 / 고유 코드 {UNIQUE_CODES:,}개')
    print(f'[검증] 폴더 없는 평일 {MISSING_WEEKDAYS}일(휴장 포함) / HTML 3,000개 미만 {UNDER_3000_DATES}일')
    print('[원칙] HTML·기존 SQLite 수정 없음, 일별 수치 임의 보간 없음')

if __name__ == '__main__': main()