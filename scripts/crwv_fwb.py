"""CoreWeave 9.75% 2031-10-01 — 프랑크푸르트(FWB) 시세로 FINRA 빈 날 메우기 (리스크 탭 CRWV 한정, Jae 10/26)

    python scripts/crwv_fwb.py          # 실행마다 1회 조회, data/risk/crwv_fwb.json 에 날짜별로 쌓음

- 같은 채권의 RegS판(ISIN USU2069EAC40, WKN A4EUCN). FINRA 가 쓰는 144A판(CUSIP 21873SAG3)과 조건이 같다.
- 원천: onvista 종목 스냅샷의 Frankfurt 마지막 가격(트레이딩뷰 FWB 와 같은 거래소). ★체결가가 아니라 호가 성격(거래량 0)이라
  FINRA 체결가와 1~2포인트 차이 날 수 있음. FINRA 에 그날 값이 들어오면 그쪽이 우선(risk_data.py).
- onvista 는 과거 시세 API 를 이용약관 위반으로 막는다(10/26 403) → 과거는 받지 않고 '오늘 스냅샷 1회'만. 403 이면 FWB_BLOCKED 를 남기고 멈춤.
- YTM 은 가격으로 직접 계산(반기 이자·30/360, 체결일 정산 근사). FINRA 10/22 80.375 → 15.58% 와 맞춰 확인.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RISK = ROOT / "data" / "risk"
OUT = RISK / "crwv_fwb.json"
BLOCK = RISK / "FWB_BLOCKED"
ISIN = "USU2069EAC40"
COUPON, MATURITY = 9.75, dt.date(2031, 10, 1)


def ytm(price: float, d: dt.date, cpn: float = COUPON, mat: dt.date = MATURITY) -> float:
    """깨끗한 가격(clean) → 반기 복리 만기수익률(%). 30/360 경과이자."""
    # 다음·직전 이자일(4/1, 10/1)
    nxt = dt.date(d.year, 4, 1) if d < dt.date(d.year, 4, 1) else dt.date(d.year, 10, 1) if d < dt.date(d.year, 10, 1) else dt.date(d.year + 1, 4, 1)
    prv = dt.date(nxt.year - 1, 10, 1) if nxt.month == 4 else dt.date(nxt.year, 4, 1)
    d360 = lambda a, b: (b.year - a.year) * 360 + (b.month - a.month) * 30 + (min(b.day, 30) - min(a.day, 30))  # noqa: E731
    acc = cpn / 2 * d360(prv, d) / 180
    frac = d360(d, nxt) / 180
    n = 0
    t = nxt
    while t <= mat:
        n += 1
        t = dt.date(t.year + (t.month == 10), 4 if t.month == 10 else 10, 1)
    dirty = price + acc

    def pv(y):
        r = y / 200
        return sum((cpn / 2 + (100 if k == n - 1 else 0)) / (1 + r) ** (frac + k) for k in range(n))
    lo, hi = 0.0, 80.0
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pv(mid) > dirty else (lo, mid)
    return round((lo + hi) / 2, 2)


def main() -> int:
    if BLOCK.exists():
        print(f"[fwb] 차단 표시 있음({BLOCK.read_text(encoding='utf-8').strip()}) — 건너뜀")
        return 0
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://api.onvista.de/api/v1/bonds/ISIN:{ISIN}/snapshot",
                                                           headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            BLOCK.write_text(f"{dt.datetime.now():%Y-%m-%d %H:%M} HTTP {e.code}", encoding="utf-8")
        print(f"[fwb] 실패 HTTP {e.code} — 멈춤")
        return 1
    q = next((x for x in d.get("quoteList", {}).get("list", []) if x.get("market", {}).get("codeMarket") == "_FRA"), None)
    if not q or not q.get("last") or not q.get("datetimeLast"):
        print("[fwb] Frankfurt 시세 없음")
        return 1
    day = q["datetimeLast"][:10]
    px = float(q["last"])
    led = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"isin": ISIN, "rows": {}}
    led["rows"][day] = [round(px, 3), ytm(px, dt.date.fromisoformat(day)), q["datetimeLast"]]
    led["fetched"] = dt.datetime.now().isoformat(timespec="minutes")
    OUT.write_text(json.dumps(led, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[fwb] CRWV 9.75% 2031 Frankfurt {day} {px} → YTM {led['rows'][day][1]}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
