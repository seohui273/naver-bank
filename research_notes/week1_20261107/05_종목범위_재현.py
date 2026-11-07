#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BANK:LAB 1차 면담: CSV 기반 월별 종목구성 그래프 재현.

같은 폴더의 `근거_월별종목수.csv`와 `06_전체기간_월별종목수.py`를 이용해
`04_종목범위_그림.png`, `.svg`를 생성합니다.
학교 서버 SQLite나 원본 HTML에는 접근하지 않습니다.
"""
from pathlib import Path
import subprocess
import sys


def main():
    folder = Path(__file__).resolve().parent
    source = folder / '근거_월별종목수.csv'
    renderer = folder / '06_전체기간_월별종목수.py'
    missing = [p.name for p in (source, renderer) if not p.is_file()]
    if missing:
        raise SystemExit(f'재현에 필요한 파일이 없습니다: {", ".join(missing)}')
    subprocess.run([sys.executable, str(renderer), '--csv', str(source), '--out', str(folder)], check=True)


if __name__ == '__main__':
    main()