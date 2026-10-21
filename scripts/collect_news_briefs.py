#!/usr/bin/env python3
"""Collect evidence-linked news excerpts for BANK:LAB. No fake AI summaries or causal claims.
Public RSS may be rate limited; failure preserves the last verified snapshot.
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import unescape

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'bank_data'/'news_briefs.json'
STOCKS={
'105560':'KB금융','055550':'신한지주','086790':'하나금융지주',
'316140':'우리금융지주','024110':'기업은행','138930':'BNK금융지주',
'175330':'JB금융지주','139130':'iM금융지주','006220':'제주은행',
'323410':'카카오뱅크','279570':'케이뱅크'}
KST=timezone(timedelta(hours=9))
def clean(s):
    s=re.sub(r'<[^>]+>',' ',unescape(s or ''))
    return re.sub(r'\s+',' ',s).strip()
def scrape():
    all_items=[]
    today=datetime.now(KST)
    for code,name in STOCKS.items():
        query=urllib.parse.quote(f'"{name}" 은행 주가 when:7d',safe='')
        url=f'https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko'
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'BANK-LAB-Research/1.0 (educational project)'})
            with urllib.request.urlopen(request,timeout=14) as response:
                doc=ET.fromstring(response.read(300000))
            count=0
            for item in doc.findall('./channel/item'):
                title=clean(item.findtext('title'))
                excerpt=clean(item.findtext('description'))
                link=(item.findtext('link') or '').strip()
                source=clean(item.findtext('source'))
                date=(item.findtext('pubDate') or '').strip()
                try:
                    from email.utils import parsedate_to_datetime
                    published=parsedate_to_datetime(date).astimezone(KST)
                except (ValueError,TypeError):
                    continue
                if (today-published).days>7 or name.replace('금융지주','') not in title+excerpt or not link.startswith('https://'):
                    continue
                # RSS description often contains links/repeated titles, not article body.
                # No deceptive "AI summary": only verified title and visible snippet.
                summary=excerpt
                if summary.startswith(title):summary=summary[len(title):].strip(' -')
                if len(summary)<25:summary='기사 본문이 제공되지 않아 제목과 출처만 표시합니다.'
                all_items.append({'code':code,'date':published.strftime('%Y-%m-%d'),
                                  'title':title[:180],'source':source[:90],
                                  'summary':summary[:500],'url':link})
                count+=1
                if count>=4:break
        except (OSError,ET.ParseError,ValueError) as e:
            print(f'NEWS_WARNING {code} {name}: {e}')
    return {'updated_at':today.isoformat(),'articles':all_items,
            'method':'Public RSS metadata only, not full-text AI summarization. No price-move causal inference.'}
def main():
    news=scrape()
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    # Do not overwrite a verified snapshot with empty data on API blockage.
    if not news['articles'] and TARGET.exists():
        print('NEWS_WARNING: no RSS articles returned; preserving previous file')
        return
    TARGET.write_text(json.dumps(news,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Saved',len(news['articles']),'source-linked RSS items')
if __name__=='__main__': main()
