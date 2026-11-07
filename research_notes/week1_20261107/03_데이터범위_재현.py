#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BANK:LAB 1차 면담 자료 범위 도표 (기존 DB 읽기 전용 / 업종 분석 전).

기본 모드: 2026-11-07 학교 서버에서 확인한 범위 수치로 제출용 SVG 생성.
--db: 학교 서버 SQLite(daylog, obs)를 직접 읽어 월별 수치를 재계산하고 새 SVG 생성.
모든 출력은 새로운 경로에만 저장. 원본 DB/HTML은 수정하지 않음.
"""
import argparse, calendar, sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

START = date(2024, 3, 27)
END = date(2026, 9, 2)
THRESHOLD = 3000
QUESTION = '같은 업종에 속한 기업들의 주가는 서로 어떤 관계를 보이며, 특정 기업의 주가 움직임이 다른 기업보다 먼저 나타나는 현상이 존재할까?'
# 2026-11-07 학교 서버 범위 그림의 월별 표시값. (없는 평일/HTML < 3,000 일)
# 토·일 제외, 거래소 공식 휴장일은 아직 빼지 않았음.
SNAPSHOT = {
    (2024,3):(2,1), (2024,4):(3,7), (2024,7):(1,0),
    (2024,9):(1,1), (2024,10):(2,2), (2024,11):(0,2),
    (2025,5):(8,0), (2025,7):(22,0), (2025,8):(1,1), (2025,10):(3,0),
    (2026,5):(2,0),
}


def snapshot():
    return ({key: SNAPSHOT.get(key, (0,0)) for key in months()},
            {'days':591,'html':2403074,'codes':4813,'start':START,'end':END})


def months():
    return [(y,m) for y in range(2024,2027) for m in range(1,13)
            if (y,m)>=(START.year,START.month) and (y,m)<=(END.year,END.month)]


def from_db(db):
    p=Path(db).expanduser().resolve()
    uri=f'{p.as_uri()}?mode=ro'
    con=sqlite3.connect(uri,uri=True)
    con.execute('PRAGMA query_only=ON')
    try:
        rows=con.execute('SELECT d,html_count FROM daylog WHERE d>=? AND d<=?',
                         (START.isoformat(),END.isoformat())).fetchall()
        code_count=con.execute('SELECT COUNT(DISTINCT code) FROM obs WHERE d>=? AND d<=?',
                              (START.isoformat(),END.isoformat())).fetchone()[0]
    finally:
        con.close()
    dates={date.fromisoformat(d) for d,n in rows}
    monthly=defaultdict(lambda:[0,0])
    d=START
    while d<=END:
        if d.weekday()<5 and d not in dates:
            monthly[(d.year,d.month)][0]+=1
        d+=timedelta(days=1)
    for d,n in rows:
        if n<THRESHOLD:
            dt=date.fromisoformat(d)
            monthly[(dt.year,dt.month)][1]+=1
    return ({key:tuple(monthly[key]) for key in months()},
            {'days':len(rows),'html':sum(n for d,n in rows),'codes':code_count,'start':START,'end':END})


def svg(monthly, totals):
    def txt(x,y,s,size=16,color='#213149',weight=400,anchor='start'):
        return f'<text x="{x}" y="{y}" font-family="NanumSquare,UnDotum,Noto Sans KR,Malgun Gothic,Apple SD Gothic Neo,Arial,sans-serif" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{escape(str(s))}</text>'
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="830" viewBox="0 0 1440 830">',
           '<rect width="1440" height="830" fill="#f6f8fc"/>']
    parts.append(txt(78,71,'BANK:LAB  |  1차 면담 · 전체시장 데이터 범위',36,'#152742',750))
    parts.append(txt(80,104,'학교 서버 원본 HTML · 읽기 전용 집계  |  분석 전 데이터 검증',16,'#60718b'))
    cards=[('관측 폴더',f"{totals['days']:,}일"),('자료 기간','2024.03.27–2026.09.02'),
           ('HTML 원본',f"{totals['html']:,}개"),('서로 다른 종목코드',f"{totals['codes']:,}개"),
           ('폴더 없는 평일',f"{sum(a for a,b in monthly.values()):,}일")]
    widths=[205,308,234,257,250]
    x=70
    for (label,val),w in zip(cards,widths):
        parts.append(f'<rect x="{x}" y="144" width="{w}" height="103" rx="14" fill="white" stroke="#e2e8f0"/>')
        parts.append(txt(x+20,174,label,15,'#687992',550))
        parts.append(txt(x+20,216,val,23,'#172b48',730))
        x+=w+8
    parts.append(txt(82,296,'월별 수집 공백 및 부분 수집 현황',25,'#172b48',720))
    parts.append(txt(83,325,'각 칸: 폴더 없는 평일 / HTML 3,000개 미만 관측일',15,'#667892'))
    parts.append(txt(1297,325,'총 '+str(sum(b for a,b in monthly.values()))+'일 부분 수집 의심',14,'#ab5426',650,'end'))
    for m in range(1,13):
        parts.append(txt(225+ m*90,369,f'{m}월',15,'#677890',550,'middle'))
    for yi,y in enumerate((2024,2025,2026)):
        y0=393+yi*101
        parts.append(txt(91,y0+47,str(y),22,'#173251',700))
        for m in range(1,13):
            x0=179+m*90
            if (y,m)<(START.year,START.month) or (y,m)>(END.year,END.month):
                fill='#edf0f5'; letter='—'; font='#a4b0bf'; strong=False
            else:
                missing,low=monthly[(y,m)]
                fill=('#fde4d4' if missing>=10 else '#fff1e7' if missing>0 else
                      '#e4eafc' if low>0 else '#f0f4f8')
                letter=f'{missing} / {low}'
                font='#ad5028' if missing>0 else '#4a6092' if low>0 else '#90a1b5'
                strong=bool(missing or low)
            parts.append(f'<rect x="{x0}" y="{y0}" width="84" height="71" rx="9" fill="{fill}"/>')
            parts.append(txt(x0+42,y0+44,letter,17,font,700 if strong else 500,'middle'))
    parts.append('<rect x="72" y="704" width="1292" height="94" rx="13" fill="white" stroke="#e3e9f3"/>')
    parts.append(txt(95,739,'핵심 결함  |  2025년 7월: 거래일 22일의 폴더 누락 (네이버 API 복구 가능성 검증 기록)',17,'#233b5d',660))
    parts.append(txt(95,768,'해석 주의  |  폴더 없는 평일에는 거래소 휴장일 포함 · 3,000개는 진단용 임시 기준 · 고유코드에 ETF/ETN 등 포함',14,'#697b93'))
    parts.append('</svg>')
    return '\n'.join(parts)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--db',help='읽기 전용 SQLite 경로; 없으면 확인된 2026-11-07 요약 수치 사용')
    ap.add_argument('--out',default='01_데이터범위_그림.svg')
    args=ap.parse_args()
    monthly,totals=(from_db(args.db) if args.db else snapshot())
    print('관측일:',totals['days'],'HTML:',totals['html'],'고유코드:',totals['codes'])
    print('폴더 없는 평일:',sum(v[0] for v in monthly.values()),'HTML<3000:',sum(v[1] for v in monthly.values()))
    Path(args.out).write_text(svg(monthly,totals),encoding='utf-8')
    print('그림:',Path(args.out).resolve())
    print('원본 수정 없음')

if __name__=='__main__': main()