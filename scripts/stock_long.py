"""삼성전자·SK하이닉스 외국인 보유 5년 시계열 → data/stock_long.json (외국인 보유 탭의 '삼성전자·SK하이닉스 외국인 보유' 카드 전용)

    python scripts/stock_long.py            # 처음엔 5년치(약 1,250영업일) 받고, 이후엔 최근 분만 덧붙인다

- 외국인 보유율·종가: 네이버 모바일 API trend (5년 끊김 없음, 2026-10-20 확인). 캐시 data/stock_long_cache.json(gitignore).
- 외국인 보유 주식 수: 다음(KRX 기준, ledger daum_stock_*)이 있는 날은 그 값(정확), 없는 날(2년 이전)은
  보유율 × 상장주식 수. 상장주식 수 = 다음의 보유주식 수 ÷ 보유율 로 역산한 값 중 그날 이후 가장 가까운 값(소각 반영).
- 코스피: 다음 market_index (ledger daum_index 2년 + 그 이전은 API로 받아 캐시).
- 보유액 = 보유 주식 수 × 종가 (조원).
"""

from __future__ import annotations

import bisect
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "sources"))
from common import load_ledger  # noqa: E402
import daum as daum_src  # noqa: E402
import naver as naver_src  # noqa: E402

CODES = ("005930", "000660")
CACHE = ROOT / "data" / "stock_long_cache.json"
OUT = ROOT / "data" / "stock_long.json"
YEARS = 5


def main() -> int:
    today = dt.date.today()
    start = dt.date(today.year - YEARS, today.month, 1)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {"naver": {}, "kospi": {}}
    nv = naver_src.Naver()
    for c in CODES:
        rows = cache["naver"].setdefault(c, {})
        have = sorted(rows)
        frm = start if not have or have[0] > start.isoformat() else dt.date.fromisoformat(have[-1]) - dt.timedelta(days=14)
        pages = 25 if frm == start else 2
        got = nv.trend(c, frm, max_pages=pages)
        for d, r in got.items():
            rows[d] = {"hold": r.get("hold"), "close": r.get("close")}
        print(f"[stock_long] naver {c}: +{len(got)}행 · {min(rows)}~{max(rows)}")
    kos = cache.setdefault("kospi", {})
    if not kos or min(kos) > start.isoformat():
        got = daum_src.Daum().index("KOSPI", start)
        kos.update({d: v for d, v in got.items()})
        print(f"[stock_long] daum kospi: {len(got)}행")
    CACHE.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")

    # 코스피: ledger(최근 2년, 매일 갱신) 우선
    for d, r in load_ledger("daum_index")["rows"].items():
        if r.get("kospi"):
            kos[d] = r["kospi"]

    dates = sorted(d for d in set().union(*[cache["naver"][c].keys() for c in CODES]) if d >= start.isoformat())
    out = {"dates": dates, "start": start.isoformat(), "src": "네이버 증권(외국인 보유율·종가) · 다음(KRX 외국인 보유주식 수) · 다음(코스피)",
           "kospi": [kos.get(d) for d in dates]}
    for c in CODES:
        nvr = cache["naver"][c]
        dm = load_ledger(f"daum_stock_{c}")["rows"]
        # 상장주식 수 역산(다음 보유주식 수 ÷ 보유율) — 날짜순, 그날 이후 가장 가까운 값을 쓴다
        lst = sorted((d, r["fo_shares"] / (r["fo_rate"] / 100)) for d, r in dm.items() if r.get("fo_shares") and r.get("fo_rate"))
        lk = [x[0] for x in lst]
        rate, close, shares, val, exact = [], [], [], [], 0
        for d in dates:
            n = nvr.get(d, {})
            dr = dm.get(d, {})
            px = dr.get("close") or n.get("close")
            rt = dr.get("fo_rate") or n.get("hold")
            if dr.get("fo_shares"):
                sh = dr["fo_shares"]
                exact += 1
            elif rt is not None and lst:
                j = min(bisect.bisect_left(lk, d), len(lst) - 1)
                sh = round(rt / 100 * lst[j][1])
            else:
                sh = None
            rate.append(round(rt, 2) if rt is not None else None)
            close.append(px)
            shares.append(sh)
            val.append(round(sh * px / 1e12, 3) if sh and px else None)
        out[c] = {"rate": rate, "close": close, "shares": shares, "val": val}
        print(f"[stock_long] {c}: {len(dates)}일 · 보유주식 수 다음 실측 {exact}일, 나머지 보유율×상장주식 수 추정")
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[stock_long] {OUT} · {dates[0]}~{dates[-1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
