# BANK:LAB | 국내 은행업종 금융통계 대시보드

**전북대학교 2026년 2학기 「바이브 코딩과 금융통계」 프로젝트**  
네이버페이 증권 기반의 국내 은행 관련 11종목을 수집하고, 금융통계 분석 결과를 인터랙티브 대시보드와 자동 보고서로 제공합니다.

**[대시보드 열기](https://seohui273.github.io/naver-bank/)** · **[최신 금융통계 보고서](reports/latest.md)** · **[통계 결과 CSV](reports/stock_stats.csv)** · **[변경 이력](CHANGELOG.md)**

> 교육·통계 탐구용 프로젝트이며 투자 권유나 매매 신호를 제공하지 않습니다. 자료의 완전성·정확성을 보장하지 않습니다.

## 프로젝트 개요

- **분석 대상:** 우리금융지주(316140), KB금융(105560), 신한지주(055550), 하나금융지주(086790), 카카오뱅크(323410), 기업은행(024110), BNK금융지주(138930), JB금융지주(175330), iM금융지주(139130), 케이뱅크(279570), 제주은행(006220).
- **데이터 출처:** 네이버페이 증권 모바일 주식 API(`m.stock.naver.com`), 일부 재무·기업현황 정보는 WiseReport 기업 페이지, 백필은 네이버 금융 일별 시세 페이지.
- **수집 범위:** 일별 시세·거래량·투자정보, 주기별 재무·기업·주주 정보, 변화 로그 및 캔들 차트.
- **데이터 범위:** 2026-10-15 01:30 KST에 생성된 보고서 기준 **2026-10-02 ~ 2026-10-14, 7개 관측 거래일, 11종목, 77행**. 최신 현황은 [`reports/latest.md`](reports/latest.md) 확인.
- **배포:** GitHub Pages에 정적 HTML + Plotly 차트. 별도 서버가 필요하지 않습니다.

## 데이터 처리 흐름

```text
GitHub Actions (daily.yml; 예약/수동 실행)
  └─ naver_bank_daily.py
       └─ bank_data/ : 날짜별 시세, 누적 이력, 재무/기업/주주 정보
           └─ GitHub Actions (report.yml; 수집 워크플로 성공 후 또는 수동 실행)
                └─ scripts/build_dashboard.py
                     ├─ index.html : 수집 데이터 내장형 인터랙티브 대시보드
                     ├─ reports/latest.md : 기술통계와 자료 품질 보고서
                     └─ reports/stock_stats.csv : 종목별 통계 결과
                         └─ GitHub Pages 자동 배포
```

`daily.yml`은 수업 가이드의 `collect.yml`에 해당하는 수집 역할을 하며, 분석과 배포는 `report.yml`로 분리했습니다. 수집 시각은 GitHub Actions의 실제 시작 지연에 따라 달라질 수 있습니다.

## 주요 파일

| 경로 | 용도 |
|---|---|
| `.github/workflows/daily.yml` | 예약 수집, 재시도, 커밋 및 알림 |
| `.github/workflows/report.yml` | 분석 생성, 결과 커밋, Pages 배포 |
| `naver_bank_daily.py` | 종목별 데이터 수집 및 누락일 백필 |
| `scripts/build_dashboard.py` | 누적 CSV 기반 통계 및 HTML 갱신 |
| `bank_data/bank_YYYY-MM-DD.csv` | 일자별 시세·투자정보 스냅샷 |
| `bank_data/bank_history.csv` | 종목·거래일 기준 시세 누적 이력 |
| `bank_data/bank_financials.csv` | 최신 재무 항목 모음(과거 버전 전체 보존 아님) |
| `bank_data/bank_company.csv` | 기업정보 최신값(과거 버전 전체 보존 아님) |
| `bank_data/bank_shareholders.csv` | 주주 정보 변경 이력 |
| `bank_data/bank_changes.csv` | 관측된 필드 변경 사항 |
| `bank_data/chart_YYYY-MM-DD.png` | 날짜별 캔들 차트 |
| `reports/latest.md` | 최신 자동 생성 보고서 |
| `reports/stock_stats.csv` | 종목별 통계 CSV |
| `index.html` | BANK:LAB 미니멀 화이트 대시보드 |

## 분석과 시각화

- 11종목 주가 및 변동률 비교, 기간·종목 선택, 캔들·거래량 조회
- 누적수익률, 관측 구간별 평균 수익률, 수익률 표본표준편차, 종목 간 상관계수·히트맵
- 일자별 11종목 수집 완전성, 결측 자료, 백필 표시 확인
- 수익률은 인접한 **관측일**의 종가 비율로 계산하므로 중간 거래일 누락 여부에 유의해야 합니다.
- 변동성 표준편차는 별도 명시가 없는 한 **연율화하지 않은** 수익률의 표본표준편차입니다.
- 자료가 아직 짧아 금융시장 일반화 또는 예측용으로 활용해서는 안 됩니다.

## 데이터 품질 및 결측 처리

- 현재 공개된 자동 보고서 스냅샷(2026-10-15 생성)에서는 **7개 관측 날짜 모두 11개 종목 포함**, 종가·거래량 결측 0건으로 기록되어 있습니다.
- **2026-10-06은 백필 표시된 날짜**입니다. 백필 데이터는 KRX 일별 시세 기반이며 NXT를 포함하는 통합 시세와 거래량 집계 기준이 다를 수 있습니다.
- 별도 결측이 확인되면 `reports/latest.md`의 날짜별 수집 완전성을 참고하고, 원인·복구 범위·처리 일자를 CHANGELOG에 기록합니다.
- 11종목 충족은 **이미 관측된 날짜 내 종목 수**의 완전성을 의미합니다. 빠진 거래일 자체가 없는지 보장하지 않습니다.
- 원본 HTML·JSON은 항상 보존되는 구조가 아닙니다. 워크플로의 `SAVE_RAW` 설정을 확인하세요.

## 로컬 재생성

Python 3.12 기준으로 저장소 루트에서 실행:

```bash
python scripts/build_dashboard.py
```

위 스크립트는 `bank_data/bank_history.csv`에서 데이터를 읽어 `index.html`, `reports/latest.md`, `reports/stock_stats.csv`를 갱신합니다. 대시보드는 브라우저에서 JavaScript/Plotly를 사용하며, 차트 표시에는 네트워크 연결이 필요할 수 있습니다.

수집기는 다음처럼 별도로 실행할 수 있습니다.

```bash
pip install -r requirements.txt
python naver_bank_daily.py --backfill
```

`--backfill`은 기존 이력에서 누락된 과거 시세를 보완하며, 과거 PER·PBR·재무정보를 모두 복원하지는 않습니다. `--force`는 예외적인 수동 점검에만 사용하세요.

## 자동화 검증 및 운영 주의

1. `Actions → naver-bank-daily`에서 수집 단계와 새 `bank_data` 커밋 확인
2. `Actions → banklab-report-and-pages`에서 분석·배포 단계 성공 확인
3. `reports/latest.md` 관측 종료일과 `index.html` 대시보드의 최신 거래일 비교
4. 오류 발생 시 GitHub Actions 실행 로그와 `CHANGELOG.md`에 문제 및 대응 기록

GitHub Pages로 게시된 웹사이트는 공개 접근이 가능합니다. 실제 금융 데이터를 참고할 때 출처 표시와 이용 조건을 확인하세요.

## 향후 과제

- Quarto `.qmd` 학기말 보고서 작성과 자동 렌더링 연결
- 데이터 수집일·거래일 누락 판별 고도화 및 원본 응답 아카이빙 검토
- 분석 기간 증가에 따른 통계적 해석 확장

---

**제작:** 최서희 · 전북대학교 금융통계 수업 프로젝트
