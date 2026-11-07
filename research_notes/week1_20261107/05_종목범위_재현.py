#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BANK:LAB 1차 면담용 종목코드 수 비교 시각화.

- 검증된 학교 서버 실행 출력/정밀 진단 결과의 기준일별 종목코드 수를 입력한 CSV를 읽는다.
- ETF/ETN 등도 포함되며 실제 상장기업 수가 아님.
- 날짜별 시장 분할이 확인되지 않은 경우 임의의 값으로 채우지 않는다.
- 원본 학교 서버 HTML/SQLite는 변경하거나 읽지 않는다.

사용: python3 05_종목범위_재현.py
사전 요구: matplotlib
"""
from pathlib import Path
import csv
import argparse
import math

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Patch

BLUE = '#28649A'
TEAL = '#2F9B91'
ORANGE = '#CF7E4B'
NAVY = '#172943'
MUTED = '#64748B'
PALE = '#F4F7FB'
GRID = '#E3EAF2'


def load_csv(filename):
    with open(filename, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows: raise ValueError('CSV 비어 있음')
    required={'기준일','관측코드수','코스피코드수','코스닥코드수','비고'}
    if required - set(rows[0]): raise ValueError('필수 컬럼 누락')
    parsed=[]
    for row in rows:
        date=row['기준일']; total=int(row['관측코드수'])
        kp=int(row['코스피코드수']) if row['코스피코드수'].strip() else None
        kq=int(row['코스닥코드수']) if row['코스닥코드수'].strip() else None
        if (kp is None)!=(kq is None): raise ValueError(f'{date}: 시장별 값이 일부만 있음')
        if kp is not None and kp+kq!=total:raise ValueError(f'{date}: 시장별 합계 불일치')
        parsed.append((date,total,kp,kq,row['비고']))
    if [r[0] for r in parsed]!=sorted(r[0] for r in parsed):
        raise ValueError('날짜 오름차순이 아님')
    if len({r[0] for r in parsed}) != len(parsed):
        raise ValueError('중복 날짜')
    return parsed


def set_font():
    available={f.name for f in font_manager.fontManager.ttflist}
    for name in ('NanumSquare','NanumGothic','Noto Sans CJK KR','Malgun Gothic','AppleGothic','UnDotum'):
        if name in available:
            plt.rcParams['font.family']=name
            break
    plt.rcParams.update({'axes.unicode_minus':False,'svg.fonttype':'none','font.size':11})


def draw(rows,outdir):
    set_font()
    fig=plt.figure(figsize=(15,9),facecolor='white')
    fig.text(.055,.949,'BANK:LAB',color=NAVY,fontsize=24,weight='bold')
    fig.text(.24,.949,'1차 면담 | 종목 데이터 확보 범위',color=NAVY,fontsize=20,weight='bold')
    fig.text(.055,.913,'학교 서버 HTML / SQLite 진단 출력 기반 · 선택한 기준일의 관측 종목코드 비교',color=MUTED,fontsize=11)

    # cards
    summaries=[('전체 기간 고유 코드','4,813개','ETF·ETN 포함한 합집합'),
               ('초기 수집일','947개','2024.03.27'),
               ('마지막 관측일','4,307개','2026.09.02')]
    card_y=.761; gap=.018; left=.055; cw=(.89-2*gap)/3
    for i,(label,val,note) in enumerate(summaries):
        x=left+i*(cw+gap)
        box=FancyBboxPatch((x,card_y),cw,.114,transform=fig.transFigure,
            boxstyle='round,pad=0.007,rounding_size=0.012',linewidth=.9,
            edgecolor='#D9E4F0',facecolor=PALE)
        fig.add_artist(box)
        fig.text(x+.016,card_y+.083,label,color=MUTED,fontsize=10.5)
        fig.text(x+.016,card_y+.044,val,color=NAVY,fontsize=21,weight='bold')
        fig.text(x+.016,card_y+.018,note,color=MUTED,fontsize=9)

    # plot A horizontal bars (six selected, not falsely continuous)
    fig.text(.063,.710,'A. 기준일별 관측 코드 수',fontsize=16.5,color=NAVY,weight='bold')
    fig.text(.063,.682,'정상 수집 규모와 초기 947개 부분수집을 비교',fontsize=10.5,color=MUTED)
    ax=fig.add_axes([.205,.369,.715,.277])
    labels=[r[0].replace('-','.') for r in rows]
    values=[r[1] for r in rows]
    colors=[ORANGE if r[0]=='2024-03-27' else BLUE for r in rows]
    bars=ax.barh(list(range(len(rows))),values,color=colors,height=.67,edgecolor='white')
    ax.set_yticks(list(range(len(rows))),labels,fontsize=11,color=NAVY)
    ax.invert_yaxis()
    ax.set_xlim(0,5100)
    ax.set_xlabel('그날 관측된 종목코드 수 (개)',fontsize=10,color=NAVY)
    ax.grid(axis='x',color=GRID,linewidth=1)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():spine.set_visible(False)
    ax.tick_params(axis='both',length=0,pad=8)
    for bar,val in zip(bars,values):
        ax.text(val+60,bar.get_y()+bar.get_height()/2,f'{val:,}',va='center',ha='left',weight='bold',color=NAVY,fontsize=11)

    # plot B market shares exact values only
    fig.text(.063,.313,'B. 시장별 관측 종목 구성',fontsize=15.5,color=NAVY,weight='bold')
    fig.text(.063,.289,'시장별 실측 수치가 확인된 정상규모 기준일 4개',fontsize=10.2,color=MUTED)
    sub=[x for x in rows if x[2] is not None and x[0]!='2024-03-27']
    ax2=fig.add_axes([.10,.156,.82,.105])
    x=list(range(len(sub)))
    kp=[r[2] for r in sub]; kq=[r[3] for r in sub]
    ax2.bar(x,kp,width=.62,color=BLUE)
    ax2.bar(x,kq,bottom=kp,width=.62,color=TEAL)
    for i,row in enumerate(sub):
        ax2.text(i, row[1]+65,f'{row[1]:,}',ha='center',color=NAVY,weight='bold',fontsize=10)
        ax2.text(i,kp[i]*.5,f'{kp[i]:,}',ha='center',va='center',color='white',weight='bold',fontsize=10)
        ax2.text(i,kp[i]+kq[i]*.5,f'{kq[i]:,}',ha='center',va='center',color='white',weight='bold',fontsize=10)
    ax2.set_ylim(0,4900)
    ax2.set_yticks([0,2000,4000]);ax2.set_ylabel('코드 수',fontsize=9)
    ax2.set_xticks(x,[r[0].replace('-','.') for r in sub],fontsize=9.5)
    ax2.grid(axis='y',color=GRID)
    ax2.set_axisbelow(True)
    for spine in ax2.spines.values():spine.set_visible(False)
    ax2.tick_params(axis='both',length=0)
    fig.legend(handles=[Patch(facecolor=BLUE,label='코스피'),Patch(facecolor=TEAL,label='코스닥')],
               ncol=2,frameon=False,fontsize=9,loc='lower center',bbox_to_anchor=(.54,.100))
    fig.text(.056,.030,'주의: 4,813개는 전체 기간에 나타난 고유 코드의 합집합이며 실제 상장기업 수가 아님. ETF·ETN 등 포함.',color=MUTED,fontsize=9.4)
    fig.text(.056,.012,'선택한 기준일만 비교했으며 2026.09.02 시장별 분할은 미확인이라 B에서 제외. 초기 947개는 수집 범위 제한 정황.',color=MUTED,fontsize=9.2)

    outdir.mkdir(parents=True,exist_ok=True)
    result=[]
    for ext in ('png','svg'):
        path=outdir/f'04_종목범위_그림.{ext}'
        fig.savefig(path,dpi=190,facecolor='white')
        result.append(path)
    plt.close(fig)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--csv',type=Path,default=Path(__file__).parent/'근거_기준일별종목수.csv')
    p.add_argument('--outdir',type=Path,default=Path(__file__).parent)
    args=p.parse_args()
    rows=load_csv(args.csv)
    for path in draw(rows,args.outdir):print('[생성]',path)
    print('[원칙] DB/HTML 수정 없음; 확인된 기준일의 종목코드 수만 사용')

if __name__=='__main__':main()