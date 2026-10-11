#!/usr/bin/env python3
"""
네이버(npay증권) 은행 11개 종목 일일 수집 (Windows용)

수집: 시세정보 / 투자정보 / 재무(종목분석) / 기업현황·주주현황 / 변화 감지 / 캔들 차트 / 종목 실종 경고
저장: 이 파일이 있는 폴더의 bank_data 폴더 (작업 스케줄러로 실행해도 위치가 바뀌지 않음)

처음 설정:  pip install requests pandas lxml schedule matplotlib
테스트:      test_now.bat 더블클릭   (주말/휴장이어도 강제 수집)
자동 실행:   register_task.bat 더블클릭 (평일 20:10 자동 실행 등록)
직접 실행:   python naver_bank_daily.py [--force | --daemon | --probe 006220 | --backfill]
--backfill:  놓친 거래일(PC가 꺼져 있었던 날)의 시가·고가·저가·종가·거래량을 일별 시세에서 채움
"""
import argparse
import json
import os
import smtplib
import socket
import sys
import time
from datetime import datetime, timedelta, timezone
from datetime import time as dtime
import mimetypes
from email.message import EmailMessage
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

for _stream in (sys.stdout, sys.stderr):  # 로그 파일로 리다이렉트해도 한글이 깨지지 않게
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ===================== CONFIG =====================
STOCKS = {
    "316140": "우리금융지주", "105560": "KB금융", "055550": "신한지주",
    "086790": "하나금융지주", "323410": "카카오뱅크", "024110": "기업은행",
    "138930": "BNK금융지주", "175330": "JB금융지주", "139130": "iM금융지주",
    "279570": "케이뱅크", "006220": "제주은행",
}
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "bank_data"   # 스크립트 옆 폴더 고정
# 화면의 시/고/저/거래량은 KRX+NXT 통합 → 애프터마켓(~20:00) 종료 후 수집하는 것을 권장
RUN_TIME = "20:10"
KST = timezone(timedelta(hours=9))        # 서버(GitHub 등)가 UTC여도 한국 시간 기준으로 판단
MARKET_DONE = dtime(20, 5)                # 애프터마켓(~20:00) 종료 후부터 '오늘 데이터'를 확정 저장
SAVE_RAW = os.getenv("SAVE_RAW", "1") != "0"   # 원본 JSON/HTML 보관 (GitHub 실행 시에는 0)
FAIL_WARN_DAYS = 3                       # 연속 N일 조회 실패 시 '사라짐 의심' 경고

# 매일 값이 달라지는 게 정상인 항목은 제외하고, '실제로 바뀌는 때'를 보고 싶은 항목
FUNDAMENTAL_KEYS = ["EPS", "BPS", "추정EPS", "추정PER", "주당배당금"]
# 그 외 투자정보(PER/PBR/시총 등)도 변화 로그(CSV)에는 모두 기록됨

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT") or 465)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
MAIL_TO = os.getenv("MAIL_TO", "")
# ==================================================

API = "https://m.stock.naver.com/api/stock"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Referer": "https://m.stock.naver.com/",
})

HIST = OUTPUT_DIR / "bank_history.csv"       # 종목×날짜 누적 (시세+투자정보)
FIN = OUTPUT_DIR / "bank_financials.csv"     # 재무 누적 (long format)
CHG = OUTPUT_DIR / "bank_changes.csv"        # 변화 로그
STATE = OUTPUT_DIR / "state.json"            # 연속 실패 횟수
COMP = OUTPUT_DIR / "bank_company.csv"       # 기업현황/통합JSON 최신값 (long format)
SHARE = OUTPUT_DIR / "bank_shareholders.csv" # 주주현황 누적

COMPANY_URL = "https://navercomp.wisereport.co.kr/v2/company/c1010001.aspx?cmp_cd={code}"
EXCLUDE_JSON_KEYS = {"totalInfos", "researches", "news", "newsTitle", "newsList"}  # 이미 열로 저장했거나 매일 바뀌는 목록
MAX_LIST = 5                                  # JSON 리스트는 앞 N개만


def get_json(path: str):
    r = SESSION.get(f"{API}/{path}", timeout=15)
    r.raise_for_status()
    return r.json()


def flatten_finance(code: str, freq: str, js: dict) -> list:
    fi = (js or {}).get("financeInfo", {})
    titles = {t.get("key"): t.get("title") for t in fi.get("trTitleList", [])}
    cons = {t.get("key"): t.get("isConsensus") for t in fi.get("trTitleList", [])}
    out = []
    for row in fi.get("rowList", []):
        for k, cell in (row.get("columns") or {}).items():
            out.append({"종목코드": code, "주기": freq, "기간": titles.get(k, k),
                        "컨센서스": cons.get(k), "항목": row.get("title"),
                        "값": (cell or {}).get("value")})
    return out


def walk_json(obj, path="", out=None):
    """JSON을 (경로, 값) 목록으로 펼침. 예: consensusInfo.priceTargetMean -> 12000"""
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in EXCLUDE_JSON_KEYS:
                continue
            walk_json(v, f"{path}.{k}" if path else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:MAX_LIST]):
            walk_json(v, f"{path}[{i}]", out)
    elif obj is not None and obj != "":
        out.append((path, obj))
    return out


def fetch_company_html(code: str) -> str:
    r = SESSION.get(COMPANY_URL.format(code=code), timeout=20,
                    headers={"Referer": "https://finance.naver.com/"})
    r.raise_for_status()
    try:
        return r.content.decode("utf-8")
    except UnicodeDecodeError:
        return r.content.decode("euc-kr", errors="replace")


def flat_cols(df: pd.DataFrame) -> list:
    cols = []
    for c in df.columns:
        parts = c if isinstance(c, tuple) else (c,)
        parts = [str(p) for p in parts if not str(p).startswith("Unnamed")]
        cols.append(" ".join(dict.fromkeys(parts)) or "항목")
    return cols


def tables_to_long(code: str, name: str, tables: list) -> tuple:
    """기업현황 페이지의 모든 표 -> long rows, 그리고 '주주/지분' 표는 따로 반환"""
    rows, share = [], []
    for i, t in enumerate(tables):
        t = t.copy()
        t.columns = flat_cols(t)
        t = t.dropna(how="all").dropna(how="all", axis=1)
        if t.empty:
            continue
        sec = f"t{i}:{t.columns[0]}"
        for _, r in t.iterrows():
            label = str(r.iloc[0])
            for col in t.columns[1:]:
                v = r[col]
                if pd.notna(v) and str(v).strip() != "":
                    rows.append({"종목코드": code, "종목명": name, "출처": "wisereport",
                                 "섹션": sec, "항목": f"{label}|{col}", "값": str(v)})
        blob = " ".join(map(str, t.columns)) + " " + " ".join(map(str, t.values.ravel()[:200]))
        if "주주" in blob or "지분" in blob:
            s = t.fillna("").astype(str)
            s.insert(0, "종목명", name)
            s.insert(0, "종목코드", code)
            s.insert(2, "표", sec)
            share.append(s)
    return rows, share


def fetch_stock(code: str, name: str, raw_dir: Path):
    """한 종목의 시세/투자정보 1행 + 재무 long rows"""
    basic = get_json(f"{code}/basic")
    integ = get_json(f"{code}/integration")
    fin_rows, raws = [], {"basic": basic, "integration": integ}
    for freq, ep in (("annual", "finance/annual"), ("quarter", "finance/quarter")):
        try:
            js = get_json(f"{code}/{ep}")
            raws[ep.replace("/", "_")] = js
            fin_rows += flatten_finance(code, freq, js)
        except Exception as e:  # 재무는 실패해도 시세 수집은 계속
            print(f"  (재무 {freq} 실패: {name} {e})", file=sys.stderr)

    # 원본 JSON 보관 (필드 구조가 바뀌어도 나중에 다시 파싱 가능)
    if SAVE_RAW:
        raw_dir.mkdir(parents=True, exist_ok=True)
        for k, v in raws.items():
            (raw_dir / f"{code}_{k}.json").write_text(json.dumps(v, ensure_ascii=False), encoding="utf-8")

    row = {
        "거래일": str(basic.get("localTradedAt", ""))[:10],
        "종목코드": code,
        "종목명": basic.get("stockName") or name,
        "현재가": basic.get("closePrice"),
        "전일대비": basic.get("compareToPreviousClosePrice"),
        "등락률(%)": basic.get("fluctuationsRatio"),
    }
    for it in integ.get("totalInfos", []):     # 시가/고가/저가/거래량/대금/PER/EPS/PBR/BPS ... 전부 열로
        row[it.get("key")] = it.get("value")

    # 통합 JSON의 나머지 필드(컨센서스·업종비교·투자자 동향 등)를 long 형태로
    comp_rows = [{"종목코드": code, "종목명": row["종목명"], "출처": "integration",
                  "섹션": p.split(".")[0], "항목": p, "값": str(v)} for p, v in walk_json(integ)]

    # 기업현황 페이지(시세현황·주주현황·기업개요 ...)
    share_tables, soft = [], []
    try:
        html = fetch_company_html(code)
        if SAVE_RAW:
            (raw_dir / f"{code}_company.html").write_text(html, encoding="utf-8")
        tables = pd.read_html(StringIO(html))
        rows_c, share_tables = tables_to_long(code, row["종목명"], tables)
        comp_rows += rows_c
    except Exception as e:  # 기업현황 실패해도 시세 수집은 계속
        soft.append(f"{name}({code}) 기업현황/주주현황: {e}")
    return row, fin_rows, comp_rows, share_tables, soft


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"fail": {}}


def detect_changes(today_df: pd.DataFrame, hist: pd.DataFrame, trade_date: str) -> list:
    """직전 저장일 대비 투자정보 항목이 바뀐 내역"""
    out = []
    skip = {"거래일", "종목코드", "종목명", "현재가", "전일대비", "등락률(%)"}
    for _, r in today_df.iterrows():
        prev = hist[(hist["종목코드"] == r["종목코드"]) & (hist["거래일"] < trade_date)]
        if prev.empty:
            continue
        p = prev.sort_values("거래일").iloc[-1]
        for col in today_df.columns:
            if col in skip or col not in p.index:
                continue
            a, b = str(p[col]), str(r[col])
            if a != b and b != "nan" and a != "nan":
                out.append({"거래일": trade_date, "종목코드": r["종목코드"], "종목명": r["종목명"],
                            "구분": "투자정보", "항목": col, "이전값": a, "새값": b, "이전기준일": p["거래일"]})
    return out


def detect_fin_changes(new: pd.DataFrame, old: pd.DataFrame, trade_date: str) -> list:
    if old.empty or new.empty:
        return []
    key = ["종목코드", "주기", "기간", "항목"]
    m = old.merge(new, on=key, suffixes=("_old", "_new"))
    m = m[m["값_old"].astype(str) != m["값_new"].astype(str)]
    names = {c: n for c, n in STOCKS.items()}
    return [{"거래일": trade_date, "종목코드": r["종목코드"], "종목명": names.get(r["종목코드"], ""),
             "구분": f"재무({r['주기']})", "항목": f"{r['기간']} {r['항목']}",
             "이전값": r["값_old"], "새값": r["값_new"], "이전기준일": ""} for _, r in m.iterrows()]


def detect_long_changes(new: pd.DataFrame, old: pd.DataFrame, trade_date: str, label: str) -> list:
    if old.empty or new.empty:
        return []
    key = ["종목코드", "섹션", "항목"]
    a = old[old["출처"] == "wisereport"][key + ["값"]]
    b = new[new["출처"] == "wisereport"][key + ["종목명", "값"]]
    m = a.merge(b, on=key, suffixes=("_old", "_new"))
    m = m[m["값_old"].astype(str) != m["값_new"].astype(str)]
    return [{"거래일": trade_date, "종목코드": r["종목코드"], "종목명": r["종목명"], "구분": label,
             "항목": f"{r['섹션']} {r['항목']}", "이전값": r["값_old"], "새값": r["값_new"],
             "이전기준일": ""} for _, r in m.iterrows()]


def draw_charts(hist: pd.DataFrame, trade_date: str):
    """누적 시가/고가/저가/종가로 캔들 차트 (빨강=상승 양봉, 파랑=하락 음봉)"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib 미설치 → 차트 생략 (pip install matplotlib)")
        return None
    from matplotlib import font_manager
    avail = {f.name for f in font_manager.fontManager.ttflist}
    for fam in ("Malgun Gothic", "AppleGothic", "NanumGothic"):  # 설치된 한글 폰트 하나만 선택 (경고 방지)
        if fam in avail:
            plt.rcParams["font.family"] = fam
            break
    plt.rcParams["axes.unicode_minus"] = False
    num = lambda s: pd.to_numeric(s.astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")
    fig, axes = plt.subplots(3, 4, figsize=(16, 9))
    for ax, (code, name) in zip(axes.flat, STOCKS.items()):
        d = hist[hist["종목코드"] == code].sort_values("거래일").tail(60)
        o, h, l, c = (num(d[k]) for k in ("시가", "고가", "저가", "현재가"))
        for i, (oo, hh, ll, cc) in enumerate(zip(o, h, l, c)):
            if pd.isna(oo) or pd.isna(cc):
                continue
            color = "#d24f45" if cc >= oo else "#4b78e6"
            ax.vlines(i, ll, hh, color=color, linewidth=1)
            ax.bar(i, max(abs(cc - oo), (hh - ll) * 0.01), bottom=min(oo, cc), color=color, width=0.6)
        ax.set_title(f"{name} ({code})", fontsize=10)
        ax.set_xticks(range(len(d)))
        ax.set_xticklabels([x[5:] for x in d["거래일"]], rotation=90, fontsize=6)
    for ax in list(axes.flat)[len(STOCKS):]:
        ax.axis("off")
    fig.tight_layout()
    path = OUTPUT_DIR / f"chart_{trade_date}.png"
    fig.savefig(path, dpi=110)
    plt.close(fig)
    return path


def build_report(df, trade_date, changes, failed, warns) -> str:
    L = [f"[{trade_date}] 은행 11종목 일일 리포트 (수집 {len(df)}/{len(STOCKS)})", ""]
    for _, x in df.iterrows():
        L.append(f"{x['종목명']:<8} {x['현재가']}원  {x['전일대비']} ({x['등락률(%)']}%)  "
                 f"거래량 {x.get('거래량', '-')}  PER {x.get('PER', '-')}  PBR {x.get('PBR', '-')}")
    key = [c for c in changes if any(c["항목"] == k or k in c["항목"] for k in FUNDAMENTAL_KEYS)
           or c["구분"].startswith("재무") or c["구분"].startswith("기업")]
    L += ["", f"■ 주요 변화 감지 ({len(key)}건)"]
    L += [f"- {c['종목명']} {c['구분']} {c['항목']}: {c['이전값']} → {c['새값']}" for c in key[:20]] or ["- 없음"]
    if len(key) > 20:
        L.append(f"... 외 {len(key) - 20}건 (bank_changes.csv 참고)")
    if failed:
        L += ["", "■ 수집 실패"] + [f"- {f}" for f in failed]
    if warns:
        L += ["", "■ ⚠ 경고"] + [f"- {w}" for w in warns]
    return "\n".join(L)


def notify(text: str, subject: str, image: Path = None, attachments: list = None):
    """텔레그램(사진 포함) / 이메일(본문 + 차트 + 변화 CSV 첨부)로 리포트 전송"""
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        base = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
        requests.post(f"{base}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": text[:4000]}, timeout=15)
        if image:
            with open(image, "rb") as f:
                requests.post(f"{base}/sendPhoto", data={"chat_id": TELEGRAM_CHAT_ID},
                              files={"photo": f}, timeout=30)
    if SMTP_HOST and SMTP_USER and MAIL_TO:
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = subject, SMTP_USER, MAIL_TO
        msg.set_content(text)
        for p in ([image] if image else []) + list(attachments or []):
            p = Path(p)
            if not p.exists():
                continue
            ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
            maintype, subtype = ctype.split("/", 1)
            msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)
        if SMTP_PORT == 587:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
                s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)

def wait_for_network(host: str = "m.stock.naver.com", tries: int = 10, delay: int = 30) -> bool:
    """절전 해제 직후처럼 인터넷이 아직 안 붙었을 때 최대 tries*delay초 기다림"""
    for i in range(tries):
        try:
            socket.getaddrinfo(host, 443)
            return True
        except OSError:
            print(f"네트워크 연결 대기 중... ({i + 1}/{tries})")
            time.sleep(delay)
    return False


DAY_URL = "https://finance.naver.com/item/sise_day.naver?code={code}&page={page}"


def fetch_daily_rows(code: str, since: str) -> list:
    """일별 시세(최신순). since(YYYY-MM-DD)보다 오래된 날짜가 나올 때까지 페이지를 넘김"""
    out = []
    for page in range(1, 31):
        r = SESSION.get(DAY_URL.format(code=code, page=page), timeout=15,
                        headers={"Referer": "https://finance.naver.com/"})
        r.raise_for_status()
        r.encoding = "euc-kr"
        t = next((t for t in pd.read_html(StringIO(r.text)) if "날짜" in [str(c) for c in t.columns]), None)
        if t is None:
            break
        t = t.dropna(subset=["날짜"])
        if t.empty:
            break
        num = lambda v: pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")
        for _, x in t.iterrows():
            out.append({"날짜": str(x["날짜"]).replace(".", "-"), "종가": num(x["종가"]), "시가": num(x["시가"]),
                        "고가": num(x["고가"]), "저가": num(x["저가"]), "거래량": num(x["거래량"])})
        if out[-1]["날짜"] < since:
            break
        time.sleep(0.4)
    return out


def backfill():
    """bank_history.csv에서 빠진 거래일을 일별 시세로 채움 (시세만, PER/재무 등은 빈칸)"""
    if not HIST.exists():
        print("bank_history.csv가 아직 없습니다. 먼저 한 번 수집한 뒤 실행하세요.")
        return
    wait_for_network()
    hist = pd.read_csv(HIST, dtype=str)
    since = hist["거래일"].min()
    have = set(zip(hist["거래일"], hist["종목코드"]))
    fmt = lambda v: "" if pd.isna(v) else f"{int(v):,}"
    new = []
    for code, name in STOCKS.items():
        try:
            rows = fetch_daily_rows(code, since)
        except Exception as e:
            print(f"{name}({code}) 일별 시세 실패: {e}")
            continue
        for i, x in enumerate(rows):
            if x["날짜"] < since or (x["날짜"], code) in have:
                continue
            prev = rows[i + 1]["종가"] if i + 1 < len(rows) else float("nan")
            diff = x["종가"] - prev
            new.append({"거래일": x["날짜"], "종목코드": code, "종목명": name, "현재가": fmt(x["종가"]),
                        "전일대비": "" if pd.isna(diff) else f"{int(diff):,}",
                        "등락률(%)": "" if pd.isna(diff) or not prev else f"{diff / prev * 100:.2f}",
                        "시가": fmt(x["시가"]), "고가": fmt(x["고가"]), "저가": fmt(x["저가"]),
                        "거래량": fmt(x["거래량"]), "비고": "백필(KRX 일봉)"})
        time.sleep(0.5)
    if not new:
        print("채울 누락일이 없습니다.")
        return
    out = pd.concat([hist, pd.DataFrame(new)], ignore_index=True)
    out.sort_values(["거래일", "종목코드"]).to_csv(HIST, index=False, encoding="utf-8-sig")
    dates = sorted({r["거래일"] for r in new})
    print(f"백필 완료: {len(new)}행 추가, 날짜 {', '.join(dates)}")
    print("※ 백필 행은 시세(시가/고가/저가/종가/거래량)만 있고 PER·재무 등은 비어 있습니다. 거래량은 KRX 기준이라 통합 거래량과 다를 수 있습니다.")


def run_once(force: bool = False):
    now = datetime.now(KST)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    wait_for_network()
    state = load_state()
    rows, fin_rows, comp_rows, share_tabs, failed, warns = [], [], [], [], [], []

    for code, name in STOCKS.items():
        try:
            row, fr, cr, st, soft = fetch_stock(code, name, OUTPUT_DIR / "raw" / now.strftime("%Y-%m-%d"))
            rows.append(row)
            fin_rows += fr
            comp_rows += cr
            share_tabs += st
            failed += [f"[부분실패] {s}" for s in soft]
            state["fail"][code] = 0
        except Exception as e:
            state["fail"][code] = state["fail"].get(code, 0) + 1
            failed.append(f"{name}({code}): {e}")
            if state["fail"][code] >= FAIL_WARN_DAYS:
                warns.append(f"{name}({code}) 연속 {state['fail'][code]}회 조회 실패 → 상장폐지/종목코드 변경 가능성")
        time.sleep(0.5)
    if rows:  # 전 종목 실패(=인터넷 문제)는 '상장폐지 의심' 카운트에 넣지 않음
        STATE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")

    if not rows:
        msg = f"[{now:%Y-%m-%d}] 전 종목 수집 실패\n" + "\n".join(failed)
        print(msg)
        notify(msg, "[은행업종] 수집 실패")
        return 1   # 전 종목 실패 → 종료 코드 1 (GitHub Actions가 실패 메일을 보내도록)

    df = pd.DataFrame(rows)
    trade_date = df["거래일"].mode()[0]
    hist_old = pd.read_csv(HIST, dtype=str) if HIST.exists() else pd.DataFrame(columns=["거래일", "종목코드"])

    if not force:
        # 오늘 거래일인데 애프터마켓이 안 끝났으면 → 아직 확정 아님
        if trade_date == now.strftime("%Y-%m-%d") and now.time() < MARKET_DONE:
            print(f"{trade_date} 장/애프터마켓 진행 중({now:%H:%M}) → 20:05 이후 다시 시도, 건너뜀")
            return
        # 이미 저장된 거래일이면(공휴일·주말·중복 실행) 건너뜀. 아직 없는 거래일이면 '늦게라도' 저장
        if trade_date in set(hist_old["거래일"]):
            print(f"최신 거래일 {trade_date} 은(는) 이미 저장됨 (오늘 {now:%Y-%m-%d} 휴장/중복 실행) → 건너뜀")
            return
        if trade_date != now.strftime("%Y-%m-%d"):
            print(f"※ 늦은 저장: 최신 거래일 {trade_date} 데이터를 지금({now:%Y-%m-%d %H:%M}) 저장합니다.")

    # --- 저장 + 변화 감지 ---
    changes = detect_changes(df.astype(str), hist_old, trade_date) if not hist_old.empty else []

    fin_new = pd.DataFrame(fin_rows)
    fin_old = pd.read_csv(FIN, dtype=str) if FIN.exists() else pd.DataFrame()
    if not fin_new.empty:
        changes += detect_fin_changes(fin_new.astype(str), fin_old, trade_date)
        fin_all = pd.concat([fin_old, fin_new.astype(str)]).drop_duplicates(
            ["종목코드", "주기", "기간", "항목"], keep="last")
        fin_all.to_csv(FIN, index=False, encoding="utf-8-sig")

    comp_new = pd.DataFrame(comp_rows)
    if not comp_new.empty:
        comp_old = pd.read_csv(COMP, dtype=str) if COMP.exists() else pd.DataFrame()
        changes += detect_long_changes(comp_new, comp_old, trade_date, "기업현황/주주")
        comp_new.insert(0, "거래일", trade_date)
        pd.concat([comp_old, comp_new]).drop_duplicates(
            ["종목코드", "출처", "섹션", "항목"], keep="last").to_csv(COMP, index=False, encoding="utf-8-sig")
    if share_tabs:
        sh = pd.concat(share_tabs, ignore_index=True)
        sh.insert(0, "거래일", trade_date)
        sh_old = pd.read_csv(SHARE, dtype=str) if SHARE.exists() else pd.DataFrame()
        pd.concat([sh_old, sh]).drop_duplicates(keep="last").to_csv(SHARE, index=False, encoding="utf-8-sig")

    df.to_csv(OUTPUT_DIR / f"bank_{trade_date}.csv", index=False, encoding="utf-8-sig")
    hist = pd.concat([hist_old, df.astype(str)]).drop_duplicates(["거래일", "종목코드"], keep="last")
    hist.sort_values(["거래일", "종목코드"]).to_csv(HIST, index=False, encoding="utf-8-sig")

    day_changes = None
    if changes:
        cdf = pd.DataFrame(changes)
        cdf.to_csv(CHG, mode="a", index=False, encoding="utf-8-sig", header=not CHG.exists())
        day_changes = OUTPUT_DIR / f"changes_{trade_date}.csv"      # 그날의 변화 전체 (메일 첨부용)
        cdf.to_csv(day_changes, index=False, encoding="utf-8-sig")

    chart = draw_charts(hist, trade_date)
    report = build_report(df, trade_date, changes, failed, warns)
    (OUTPUT_DIR / f"report_{trade_date}.txt").write_text(report, encoding="utf-8")
    print(report)
    try:
        notify(report, f"[은행업종] {trade_date} 리포트 (변화 {len(changes)}건)", chart,
               [x for x in (day_changes, OUTPUT_DIR / f"bank_{trade_date}.csv") if x])
    except Exception as e:
        print(f"알림 전송 실패: {e}", file=sys.stderr)


def probe(code: str):
    """응답 구조 확인용: 저장하지 않고 화면에만 출력"""
    print(f"=== PROBE {code} ===")
    for ep in ["basic", "integration", "finance/annual", "finance/quarter"]:
        try:
            js = get_json(f"{code}/{ep}")
            print(f"[OK] {ep}: 최상위 키 = {list(js.keys()) if isinstance(js, dict) else type(js)}")
            leaves = walk_json(js)
            for p, v in leaves[:40]:
                print(f"     {p} = {str(v)[:60]}")
            if len(leaves) > 40:
                print(f"     ... 외 {len(leaves) - 40}개")
        except Exception as e:
            print(f"[FAIL] {ep}: {e}")
    try:
        tables = pd.read_html(StringIO(fetch_company_html(code)))
        print(f"[OK] 기업현황 페이지: 표 {len(tables)}개")
        for i, t in enumerate(tables):
            t = t.copy()
            t.columns = flat_cols(t)
            print(f"     t{i}: {t.shape}, 열={list(t.columns)[:6]}")
    except Exception as e:
        print(f"[FAIL] 기업현황 페이지: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daemon", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--probe", metavar="CODE", help="한 종목 응답 구조만 출력 (예: --probe 006220)")
    ap.add_argument("--backfill", action="store_true", help="누락된 거래일 시세 채우기")
    a = ap.parse_args()
    if a.probe:
        probe(a.probe)
        return
    if a.backfill:
        backfill()
        return
    if not a.daemon:
        sys.exit(run_once(a.force) or 0)
    import schedule
    schedule.every().day.at(RUN_TIME).do(run_once)
    print(f"매일 {RUN_TIME}에 실행 대기 중... (Ctrl+C로 종료)")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
