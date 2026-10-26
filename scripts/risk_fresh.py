"""리스크 아침 재수집(run_risk.sh)이 오늘 몫을 다 받았는지 판정한다 — 10:00 재시도 여부 결정용(10/23 Jae).

기준
  - DTCC CDS(cds_hist·cds_vol): 직전 미국 영업일(평일) 날짜가 들어 있어야 한다(09:15 KST 게시분).
  - FINRA 웹 채권: 오늘 받았고(fetched = 오늘) 직전 미국 영업일 체결이 들어 있어야 한다(10/26: 금요일분은 주말에 안 올라오고 월요일 미국 시간에 처리됨 → 날짜로도 판정).
    FINRA_BLOCKED 가 있으면 재시도 대상 아님(우회 금지).
출력: 마지막 줄 FRESH  또는  STALE <이유들>.  `--need finra` 는 FINRA 재수집이 필요하면 exit 0, 아니면 1.
종료코드(기본): FRESH 0, STALE 1.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

RISK = Path(__file__).resolve().parent.parent / "data" / "risk"


def prev_weekday(d: dt.date) -> dt.date:
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def load(name: str) -> dict:
    try:
        return json.loads((RISK / name).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def finra_last(f: dict) -> str:
    """받아 둔 채권들 중 가장 최근 체결일(거래 없는 채권이 있어 '최대'로 본다)"""
    return max((b["eod"][-1][0] for b in (f.get("bonds") or {}).values() if b.get("eod")), default="")


def finra_needed(today: dt.date) -> bool:
    """오늘 아직 안 받았거나(09:30), 받았어도 직전 미국 영업일 체결이 없으면(10/26 Jae: 날짜 기준 재시도 — 10:00·19:00) 다시 받는다."""
    if (RISK / "FINRA_BLOCKED").exists():
        return False
    f = load("finra_eod_1y.json")
    if str(f.get("fetched", ""))[:10] != str(today):
        return True
    return finra_last(f) < str(prev_weekday(today))


def main() -> int:
    today = dt.date.today()
    if sys.argv[1:3] == ["--need", "finra"]:
        return 0 if finra_needed(today) else 1
    want = str(prev_weekday(today))
    why = []
    for f, label in (("cds_hist.json", "CDS"), ("cds_vol.json", "CDS거래량")):
        days = load(f).get("days") or {}
        last = max(days) if days else "-"
        if last < want:
            why.append(f"{label} {last}<{want}")
    if finra_needed(today):
        why.append(f"FINRA 최신 {finra_last(load('finra_eod_1y.json')) or '-'}<{want} 또는 오늘 미수집")
    print("FRESH" if not why else "STALE " + ", ".join(why))
    return 0 if not why else 1


if __name__ == "__main__":
    sys.exit(main())
