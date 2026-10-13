# -*- coding: utf-8 -*-
"""네이버 업종 분류(79개, '기타' 제외 78개)와 업종별 소속 종목 → data/sectors_naver.json.

- 목록: m.stock.naver.com/api/stocks/industry?page=&pageSize=100  (pageSize 는 100 까지)
- 소속: m.stock.naver.com/api/stocks/industry/{no}?page=&pageSize=100
- 현재 소속만 준다(과거 편입 이력 없음) → 2년 전 날짜에도 '지금의' 업종으로 묶는다.
- '기타'(ETF·스팩 등 1,500여 종목)는 사용자 지정으로 뺀다.
"""

from __future__ import annotations

import time

from common import DATA, log, now_kst, request_json, save_json, session

API = "https://m.stock.naver.com/api/stocks/industry"
OUT = DATA / "sectors_naver.json"
EXCLUDE = {"기타"}


def fetch() -> dict:
    s = session(referer="https://m.stock.naver.com/")
    groups, page = [], 1
    while True:
        js = request_json(s, "GET", API, params={"page": page, "pageSize": 100})
        groups += js.get("groups", [])
        if len(js.get("groups", [])) < 100:
            break
        page += 1
    sectors = []
    for g in groups:
        if g["name"] in EXCLUDE:
            continue
        codes, page = [], 1
        names = {}
        while True:
            js = request_json(s, "GET", f"{API}/{g['no']}", params={"page": page, "pageSize": 100})
            st = js.get("stocks", [])
            codes += [x["itemCode"] for x in st]
            names.update({x["itemCode"]: x["stockName"] for x in st})
            if len(st) < 100:
                break
            page += 1
        sectors.append({"no": g["no"], "name": g["name"], "codes": codes, "names": names})
        time.sleep(0.15)
    doc = {"fetched_at": now_kst().isoformat(timespec="seconds"), "source": API, "sectors": sectors}
    save_json(OUT, doc)
    log(f"네이버 업종 {len(sectors)}개, 종목 {sum(len(x['codes']) for x in sectors)}개 → {OUT.name}")
    return doc


if __name__ == "__main__":
    import sys
    sys.exit(0 if fetch() else 1)
