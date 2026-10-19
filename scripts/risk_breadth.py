"""FINRA 공식 API(Public credential) — 회사채 시장 등락(Market Breadth) 최근 2년 → data/risk/breadth.json

    python scripts/risk_breadth.py

공식 API라 자동 수집이 약관상 허용된다(.env 의 FINRA_CLIENT·FINRA_SECRET). 채권별 가격은 Public 등급에 없다 — 집계만.
데이터셋: corporateMarketBreadth(공모) · corporate144AMarketBreadth(144A). 범주: all securities / investment grade / high yield / convertibles.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "risk" / "breadth.json"
SETS = {"pub": "corporateMarketBreadth", "a144": "corporate144AMarketBreadth"}


def env() -> dict:
    p = ROOT / ".env"
    return dict(l.split("=", 1) for l in p.read_text(encoding="utf-8").splitlines() if "=" in l and not l.startswith("#"))


def token() -> str:
    e = env()
    r = httpx.post("https://ews.fip.finra.org/fip/rest/ews/oauth2/access_token?grant_type=client_credentials",
                   auth=(e["FINRA_CLIENT"].strip(), e["FINRA_SECRET"].strip()), timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> int:
    H = {"Authorization": "Bearer " + token(), "Accept": "application/json", "Content-Type": "application/json"}
    start = date.today() - timedelta(days=731)
    out = {"start": str(start), "sets": {}}
    for k, name in SETS.items():
        rows, s = [], start
        while s <= date.today():  # 기간을 나눠 받기(한 번에 최대 5000행)
            e = min(s + timedelta(days=180), date.today())
            body = {"limit": 5000, "dateRangeFilters": [{"fieldName": "tradeReportDate", "startDate": str(s), "endDate": str(e)}]}
            r = httpx.post(f"https://api.finra.org/data/group/fixedIncomeMarket/name/{name}", headers=H, json=body, timeout=60)
            r.raise_for_status()
            rows += r.json() if r.text.strip() else []
            s = e + timedelta(days=1)
        by = {}
        for x in rows:
            by.setdefault(x["productCategory"], {})[x["tradeReportDate"]] = [x["advances"], x["declines"], x["unchanged"], x["fiftyTwoWeekHigh"], x["fiftyTwoWeekLow"], x["totalTrades"]]
        out["sets"][k] = {cat: sorted([[d] + v for d, v in m.items()]) for cat, m in by.items()}
        print(f"[breadth] {name}: {len(rows)}행, 최신 {max(x['tradeReportDate'] for x in rows)}")
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
