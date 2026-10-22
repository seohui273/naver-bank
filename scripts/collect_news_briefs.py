#!/usr/bin/env python3
"""BANK:LAB dated news archive.

Fetch Google News RSS by actual publication date windows, rather than only
"when:7d". Merge archives across refreshes; never invent article content.
A public RSS excerpt is not the full article body.
"""
import csv
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'bank_data'/'news_briefs.json'
HISTORY=ROOT/'bank_data'/'bank_history.csv'
KST=timezone(timedelta(hours=9))
STOCKS={
 '105560':'KB금융','055550':'신한지주','086790':'하나금융지주',
 '316140':'우리금융지주','024110':'기업은행','138930':'BNK금융지주',
 '175330':'JB금융지주','139130':'iM금융지주','006220':'제주은행',
 '323410':'카카오뱅크','279570':'케이뱅크'}
BANK_ALIASES={'105560':['KB금융','KB금융지주'],'055550':['신한지주','신한금융'],
'086790':['하나금융','하나금융지주'],'316140':['우리금융','우리금융지주'],
'024110':['기업은행','IBK기업은행'],'138930':['BNK금융','부산은행','경남은행'],
'175330':['JB금융','전북은행','광주은행'],'139130':['iM금융','DGB금융'],
'006220':['제주은행'],'323410':['카카오뱅크'],'279570':['케이뱅크']}
HEADLINE_WORDS=('주가','주식','상승','하락','급등','급락','실적','증권','투자','금리',
 '배당','자사주','공시','대출','연체','환율','순이익','영업이익','지주','은행','목표주가',
 '건전성','자본','대손','유상증자','매수','매도','금융당국','규제','보통주자본')
def clean(s):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',unescape(s or ''))).strip()
def available_dates():
    if not HISTORY.exists():
        return [date.today()]
    with HISTORY.open(encoding='utf-8-sig',newline='') as f:
        dates=sorted({r['거래일'] for r in csv.DictReader(f) if re.fullmatch(r'\d{4}-\d{2}-\d{2}',r.get('거래일',''))})
    return [date.fromisoformat(d) for d in dates]
def windows(earliest,now):
    earliest=max(earliest,date(2026,10,1)) # original daily collection begins Oct 2026
    start=earliest-timedelta(days=3)
    end=now+timedelta(days=1)
    while start<end:
        stop=min(start+timedelta(days=7),end)
        yield start,stop
        start=stop
def rss(code,name,start,stop):
    # Date constraints apply to publication date; avoid "when:7d" recency gate.
    query=f'"{name}" after:{start.isoformat()} before:{stop.isoformat()}'
    uri='https://news.google.com/rss/search?'+urllib.parse.urlencode({'q':query,'hl':'ko','gl':'KR','ceid':'KR:ko'})
    request=urllib.request.Request(uri,headers={'User-Agent':'Mozilla/5.0 (compatible; BANKLAB/2.0 educational research)'})
    with urllib.request.urlopen(request,timeout=12) as response:
        xml=response.read(550000)
    root=ET.fromstring(xml)
    output=[]
    for item in root.findall('./channel/item'):
        title=clean(item.findtext('title'))
        link=(item.findtext('link') or '').strip()
        source=clean(item.findtext('source'))
        raw=clean(item.findtext('description'))
        if not (title and link.startswith('https://')):continue
        try: pub=parsedate_to_datetime(item.findtext('pubDate') or '').astimezone(KST)
        except (ValueError,TypeError):continue
        d=pub.date()
        if not(start<=d<stop):continue
        aliases=BANK_ALIASES[code]
        if not any(a.lower() in (title+' '+raw).lower() for a in aliases):continue
        if not any(w in title for w in HEADLINE_WORDS):continue
        short_title=title.rsplit(' - ',1)[0] if title.endswith(' - '+source) else title
        # Google RSS often repeats the headline as its description, so do NOT
        # misrepresent a headline as a full-text AI summary.
        raw=re.sub(r'\s+',' ',raw)
        if raw.startswith(short_title):raw=raw[len(short_title):].strip(' -')
        if raw in (source,title,short_title) or len(raw)<35 or raw.startswith(source):raw=''
        short_title=short_title.strip()
        score=sum(2 if w in short_title else 0 for w in ('주가','실적','순이익','금리','배당','자사주','목표주가','연체','규제','환율'))
        score+=1 if '은행' in short_title else 0
        output.append({'code':code,'date':d.isoformat(),'title':short_title[:200],
                       'source':source[:90],'summary':raw[:500],
                       'summary_basis':'RSS 공개 설명' if raw else '제목만 확인',
                       'url':link,'score':score})
    return output
def load_existing():
    try:
        x=json.loads(TARGET.read_text(encoding='utf-8'))
        return x if isinstance(x,dict) else {}
    except (OSError,ValueError):
        return {}
def key(a):
    return (a.get('code'),a.get('date'),re.sub(r'\s+','',a.get('title','')).lower())
def main():
    previous=load_existing()
    rows={key(a):a for a in previous.get('articles',[]) if a.get('code') and a.get('date') and a.get('title')}
    succeeded=set(previous.get('fetched_windows',[]))
    today=datetime.now(KST).date()
    dates=available_dates()
    if not dates:raise SystemExit('No valid observation dates')
    intervals=list(windows(min(dates),today))
    attempted=0
    for start,stop in intervals:
        is_recent=stop>=today-timedelta(days=6)
        for code,name in STOCKS.items():
            wk=f'{code}|{start.isoformat()}|{stop.isoformat()}'
            if wk in succeeded and not is_recent:continue
            attempted+=1
            try:
                items=rss(code,name,start,stop)
                succeeded.add(wk)
                for a in items:
                    k=key(a)
                    if k not in rows or (not rows[k].get('summary') and a.get('summary')):rows[k]=a
                print(f'NEWS {name} {start}..{stop}: {len(items)} items')
            except (OSError,ET.ParseError,ValueError) as e:
                print(f'NEWS_WARNING {name} {start}: {e}')
            time.sleep(0.15)
    # 12 most relevant distinct headlines per stock/date, archiving all selected dates.
    by_date={}
    for a in rows.values():
        k=(a['code'],a['date'])
        by_date.setdefault(k,[]).append(a)
    final=[]
    for items in by_date.values():
        items.sort(key=lambda a:(-int(a.get('score',0)),a['title']))
        for a in items[:12]:
            final.append(a)
    final.sort(key=lambda a:(a['code'],a['date'],-int(a.get('score',0))))
    result={'updated_at':datetime.now(KST).isoformat(),'articles':final,
            'fetched_windows':sorted(succeeded),
            'method':'Date-scoped RSS searches and persistent archive. Publication date verified. Summaries are RSS excerpts, not generated full-text article summaries. Not causal claims.'}
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    TARGET.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'NEWS_DONE {len(final)} archived articles / {attempted} queries / {len(succeeded)} windows')
if __name__=='__main__':main()
