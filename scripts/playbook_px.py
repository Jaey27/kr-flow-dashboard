"""BLITZ AI 플레이북 이벤트 리스트 수익률(1D·5D)·타임라인 가격선용 일봉 종가 → px.json

    python scripts/playbook_px.py --out logs/playbook/px.json

- 플레이북 페이지가 같은 아티팩트에 함께 게시된 px.json 을 읽어 내장 주가(const PX)의 날짜·종가를 덮어쓴다.
  페이지 안의 이름·통화·계절성은 그대로 두고 dates·close 만 바꾼다(페이지 쪽 로더: playbook_imp/patch_px.py).
- 종목은 페이지 내장 PX 와 같은 8개. 늘리려면 페이지 PX(이름·통화)도 같이 넣어야 한다.
- Yahoo chart API 일봉(range=2y), adjclose 우선(없으면 close). 429면 query2로 바꿔 재시도.
- 하나라도 실패하면 그 종목은 빼고 meta.failed 에 적는다. 전부 실패하면 파일을 쓰지 않고 exit 1.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

SYMS = ["^IXIC", "^GSPC", "^KS11", "^KQ11", "NVDA", "005930.KS", "000660.KS", "^TNX"]
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
KST = timezone(timedelta(hours=9))


def fetch(sym: str, rng: str) -> dict:
    r = None
    for i, host in enumerate(["query1", "query2", "query1"]):  # 429(요청 과다)면 호스트 바꿔 최대 3번
        r = httpx.get(f"https://{host}.finance.yahoo.com/v8/finance/chart/{sym}",
                      params={"range": rng, "interval": "1d"}, headers=UA, timeout=30)
        if r.status_code != 429:
            break
        time.sleep(3 * (i + 1))
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    off = res["meta"].get("gmtoffset", 0)
    adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
    cl = res["indicators"]["quote"][0]["close"]
    vals = adj if adj and any(v is not None for v in adj) else cl
    out: dict[str, float] = {}
    for t, v in zip(res["timestamp"], vals):
        if v is None:
            continue
        d = datetime.fromtimestamp(t + off, tz=timezone.utc).date().isoformat()
        out[d] = round(float(v), 4)  # 같은 날 두 번 나오면 마지막 값
    ds = sorted(out)
    # 장중이면 오늘 봉은 미완성 → 뺀다(정규장 종료 30분 뒤부터 포함)
    reg = (res["meta"].get("currentTradingPeriod") or {}).get("regular") or {}
    if ds and reg.get("end") and time.time() < reg["end"] + 1800:
        today = datetime.fromtimestamp(reg["end"] + off, tz=timezone.utc).date().isoformat()
        if ds[-1] == today:
            ds = ds[:-1]
    if len(ds) < 50:
        raise ValueError(f"데이터 {len(ds)}일뿐")
    return {"dates": ds, "close": [out[d] for d in ds]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="logs/playbook/px.json")
    ap.add_argument("--range", default="2y", help="Yahoo range 값(2y = 페이지 내장 PX와 같은 길이)")
    a = ap.parse_args()
    series, failed = {}, []
    for s in SYMS:
        try:
            series[s] = fetch(s, a.range)
        except Exception as e:  # noqa: BLE001 — 종목 하나 실패는 건너뛰고 기록
            failed.append(f"{s}: {str(e)[:80]}")
        time.sleep(0.4)
    if not series:
        print("FAIL 전 종목 실패", failed, file=sys.stderr)
        return 1
    last = max(v["dates"][-1] for v in series.values())
    doc = {"meta": {"source": "Yahoo Finance chart API, 일봉 종가(adjclose 우선)",
                    "fetched": datetime.now(KST).strftime("%Y-%m-%dT%H:%M"), "last": last, "failed": failed},
           "series": series}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"PX {out} {len(series)}종목 마지막 {last} 실패 {len(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
