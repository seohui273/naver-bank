#!/usr/bin/env python3
"""BANK:LAB 독립 과거 주가 수집기. 기존 bank_data를 수정하지 않습니다.

주의: pykrx의 KRX 가격은 네이버 KRX+NXT 통합 시세와 기준이 다를 수 있습니다.
실행: pip install pykrx pandas requests
      python scripts/collect_history.py --start 2024-01-01 --end 2026-10-14
검증 전에는 --dry-run 으로 수집/검사만 수행합니다.
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "historical_data"
STOCKS = {
    "316140": "우리금융지주", "105560": "KB금융", "055550": "신한지주",
    "086790": "하나금융지주", "323410": "카카오뱅크", "024110": "기업은행",
    "138930": "BNK금융지주", "175330": "JB금융지주", "139130": "iM금융지주",
    "279570": "케이뱅크", "006220": "제주은행",
}
KST = timezone(timedelta(hours=9))
FIELDS = ["거래일", "종목코드", "종목명", "시가", "고가", "저가", "종가", "거래량", "거래대금", "등락률", "출처", "수정주가"]


def fetch_one(code: str, name: str, start: str, end: str, adjusted: bool) -> pd.DataFrame:
    from pykrx import stock
    data = stock.get_market_ohlcv_by_date(start, end, code, adjusted=adjusted)
    if data is None or data.empty:
        raise ValueError("데이터 없음 (상장일·종목코드·제공처 상태 확인 필요)")
    needed = ["시가", "고가", "저가", "종가", "거래량"]
    missing = [x for x in needed if x not in data.columns]
    if missing:
        raise ValueError(f"필수 열 누락: {missing} / 반환 열={list(data.columns)}")
    result = pd.DataFrame({"거래일": pd.to_datetime(data.index).strftime("%Y-%m-%d"),
                           "종목코드": code, "종목명": name})
    # pykrx DataFrame index alignment 문제를 피하기 위해 위치 배열로 할당
    for k in ["시가", "고가", "저가", "종가", "거래량", "거래대금", "등락률"]:
        result[k] = pd.to_numeric(data[k], errors="coerce").to_numpy() if k in data else pd.NA
    result["출처"] = "pykrx/KRX"
    result["수정주가"] = bool(adjusted)
    return result[FIELDS]


def validate(df: pd.DataFrame, start: str, end: str) -> list[str]:
    issues = []
    if df.empty:
        return ["빈 데이터"]
    if df.duplicated(["종목코드", "거래일"]).any():
        issues.append("종목코드+거래일 중복")
    dt = pd.to_datetime(df["거래일"], errors="coerce")
    if dt.isna().any() or (dt < pd.to_datetime(start)).any() or (dt > pd.to_datetime(end)).any():
        issues.append("거래일 파싱 실패 또는 기간 범위 이탈")
    for field in ("시가", "고가", "저가", "종가"):
        if df[field].isna().any() or (df[field] <= 0).any():
            issues.append(f"{field} 결측/0/음수")
    if df["거래량"].isna().any() or (df["거래량"] < 0).any():
        issues.append("거래량 결측/음수")
    if ((df["고가"] < df["저가"]) | (df["고가"] < df[["시가", "종가"]].max(axis=1)) |
        (df["저가"] > df[["시가", "종가"]].min(axis=1))).any():
        issues.append("OHLC 일관성 위반: 수정주가 시기별 조정 방식도 확인")
    return issues


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2024-01-01", help="YYYY-MM-DD")
    p.add_argument("--end", default=datetime.now(KST).strftime("%Y-%m-%d"), help="YYYY-MM-DD")
    p.add_argument("--dry-run", action="store_true", help="검증만 수행, 파일 저장 안 함")
    p.add_argument("--unadjusted", action="store_true", help="미수정주가 사용 (기본값: 수정주가)")
    p.add_argument("--sleep", type=float, default=1.0, help="종목 간 요청 간격(초)")
    a = p.parse_args()
    try:
        start = pd.Timestamp(a.start).strftime("%Y%m%d")
        end = pd.Timestamp(a.end).strftime("%Y%m%d")
        if start > end: raise ValueError("시작일이 종료일 이후입니다")
        if a.sleep < 0: raise ValueError("--sleep은 음수가 될 수 없습니다")
    except Exception as exc:
        p.error(str(exc))
    frames, records, failures = [], [], []
    for code, name in STOCKS.items():
        try:
            df = fetch_one(code, name, start, end, adjusted=not a.unadjusted)
            issues = validate(df, start, end)
            status = "ok" if not issues else "review"
            records.append({"종목코드": code, "종목명": name, "상태": status,
                            "행수": len(df), "시작일": df["거래일"].min(), "종료일": df["거래일"].max(),
                            "문제": "; ".join(issues)})
            print(f"{code} {name}: {len(df)}행 ({status})")
            if issues:
                failures.append(f"{code}: {'; '.join(issues)}")
            else:
                frames.append(df)
        except Exception as exc:
            msg = f"{code} {name}: {type(exc).__name__}: {exc}"
            print("오류:", msg, file=sys.stderr)
            records.append({"종목코드": code, "종목명": name, "상태": "failed", "행수": 0,
                            "시작일": "", "종료일": "", "문제": str(exc)})
            failures.append(msg)
        time.sleep(a.sleep)
    if a.dry_run:
        print(json.dumps({"결과": records, "문제": failures}, ensure_ascii=False, indent=2))
        return 1 if failures else 0
    # 부분 성공을 전체 성공으로 저장하지 않는다. 누락 종목이 있으면 다음 재시도.
    if failures:
        print("일부 종목 수집/검증 실패. 기존 파일을 보존하며 아무것도 쓰지 않았습니다.", file=sys.stderr)
        print(json.dumps(records, ensure_ascii=False, indent=2))
        return 1
    combined = pd.concat(frames, ignore_index=True).sort_values(["거래일", "종목코드"])
    if combined.duplicated(["거래일", "종목코드"]).any():
        print("중복 키 발생. 저장 취소", file=sys.stderr)
        return 1
    # 요청 범위별 신규 결과만 별도 저장. 기존 파일은 절대 덮어쓰지 않음.
    OUT.mkdir(exist_ok=True)
    stem = f"krx_{start}_{end}_{'adjusted' if not a.unadjusted else 'unadjusted'}"
    csv_path = OUT / f"{stem}.csv"
    manifest_path = OUT / f"{stem}.json"
    if csv_path.exists() or manifest_path.exists():
        print("동일 기간 결과가 이미 존재합니다. 기존 자료 보호를 위해 저장 취소.", file=sys.stderr)
        return 2
    metadata = {"수집시각_KST": datetime.now(KST).isoformat(), "시작일": a.start, "종료일": a.end,
                "출처": "pykrx/KRX", "수정주가": not a.unadjusted,
                "주의": "네이버 KRX+NXT 통합 시세와 정의가 다를 수 있음. 거래량 합산 금지. 수정주가/배당/상장시점 확인 필요.",
                "종목별점검": records}
    csv_path.write_text(combined.to_csv(index=False), encoding="utf-8-sig")
    manifest_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료: {csv_path} ({len(combined)}행), {manifest_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
