#!/usr/bin/env python3
"""Safe, idempotent homepage enhancement for existing BANK:LAB v4 dashboard."""
from pathlib import Path
import shutil
import sys

START = '<!-- BANKLAB_KRX_RESEARCH_START -->'
END = '<!-- BANKLAB_KRX_RESEARCH_END -->'
STYLE_START = '/* BANKLAB_KRX_RESEARCH_CSS_START */'
STYLE_END = '/* BANKLAB_KRX_RESEARCH_CSS_END */'
CSS = r'''
/* BANKLAB_KRX_RESEARCH_CSS_START */
.research-highlight{margin:4px 0 28px;border:1px solid #dceae7;border-radius:14px;padding:24px 26px;background:linear-gradient(115deg,#f7fbfa 0%,#fff 72%)}
.research-highlight-head{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;flex-wrap:wrap}
.research-highlight h2{font-size:20px;letter-spacing:-.55px;margin:6px 0 8px;color:#173a41}
.research-highlight p{margin:0;color:#647883;font-size:13px;max-width:720px}
.research-eyebrow{font-size:10px;letter-spacing:1.8px;font-weight:800;color:#137c73}
.research-link{color:white;background:#176d6a;border-radius:8px;padding:11px 15px;text-decoration:none;font-size:12px;font-weight:750;display:inline-block;white-space:nowrap}
.research-link:focus-visible{outline:3px solid #88c6b9;outline-offset:3px}
.research-numbers{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:20px 0 13px}
.research-metric{background:white;border:1px solid #e7eded;border-radius:9px;padding:14px}
.research-metric strong{display:block;font-size:23px;line-height:1.3;color:#174c4f;font-weight:790}
.research-metric span{font-size:11px;color:#687b83}
.research-footnote{font-size:11px!important;line-height:1.7;color:#74818a!important}
@media(max-width:720px){.research-numbers{grid-template-columns:repeat(2,minmax(0,1fr))}.research-highlight{padding:19px}.research-highlight h2{font-size:18px}}
/* BANKLAB_KRX_RESEARCH_CSS_END */
'''
HTML = r'''
<!-- BANKLAB_KRX_RESEARCH_START -->
<aside class="research-highlight" aria-label="KRX 공식 데이터 연구 결과">
 <div class="research-highlight-head">
  <div><div class="research-eyebrow">VERIFIED RESEARCH · KRX CLOSE</div>
   <h2>은행주와 시장·금리·환율의 관계</h2>
   <p>KRX 공식 종가에 기반한 2024.01.02–2026.10.14 연구 결과. 아래 숫자는 로컬에서 실행해 저장한 HAC(5) 회귀분석 결과이며, 위·아래 일일 시세 탐색 데이터와는 표본 및 원천이 다릅니다.</p>
  </div>
  <a class="research-link" href="./research_krx.html">연구 보고서 전체 보기 ↗</a>
 </div>
 <div class="research-numbers">
  <div class="research-metric"><strong>6,750</strong><span>회귀분석 관측치 · 10개 종목</span></div>
  <div class="research-metric"><strong>10 / 10</strong><span>KOSPI 계수 유의 · BH-FDR 5%</span></div>
  <div class="research-metric"><strong>6 / 10</strong><span>환율 계수 유의 · BH-FDR 5%</span></div>
  <div class="research-metric"><strong>0 / 10</strong><span>금리 계수 유의 · BH-FDR 5%</span></div>
 </div>
 <p class="research-footnote">분석 기준: 공식 KRX 종가 가격수익률(배당 제외), KOSPI 수익률·국고채 3년 금리 변화(bp)·원/달러 환율 변동률(%), HAC Newey–West(5). 조건부 연관성만 해석하며 인과관계나 예측력을 주장하지 않습니다. KOSPI 및 ECOS 거시경제 입력은 별도 검증이 필요한 예비 데이터입니다.</p>
</aside>
<!-- BANKLAB_KRX_RESEARCH_END -->
'''

def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path.cwd()
    path = root / 'index.html'
    if not path.is_file():
        raise SystemExit('ERROR: index.html을 찾을 수 없습니다. naver-bank 저장소에서 실행하세요.')
    src = path.read_text(encoding='utf-8')
    if '<script' not in src or 'id="dataset"' not in src:
        raise SystemExit('ERROR: 현재 BANK:LAB 대시보드 구조와 다릅니다. 변경하지 않았습니다.')
    if START in src and END in src and STYLE_START in src and STYLE_END in src:
        print('이미 적용되어 있습니다. 추가 변경 없음.')
        return
    if any(tag in src for tag in (START,END,STYLE_START,STYLE_END)):
        raise SystemExit('ERROR: 일부 수정만 발견됐습니다. 수동 확인이 필요합니다. 변경하지 않았습니다.')
    target = '<nav class="tabs"'
    if src.count(target)!=1 or src.count('</style>')!=1:
        raise SystemExit('ERROR: 삽입 위치를 안전하게 확인할 수 없습니다. 변경하지 않았습니다.')
    backup = path.with_suffix('.html.before_krx_upgrade.bak')
    if not backup.exists():
        shutil.copy2(path,backup)
    src = src.replace('</style>', CSS+'\n</style>',1)
    src = src.replace(target, HTML+'\n'+target,1)
    path.write_text(src,encoding='utf-8')
    print('OK: 기존 index.html에 공식 KRX 연구 섹션 추가')
    print('백업:', backup)
    print('수정:', path)
    print('데이터셋, 수집 자동화, GitHub Actions 수정 없음')

if __name__=='__main__':
    main()
