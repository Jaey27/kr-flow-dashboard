"""리스크 아침 재수집(run_risk.sh)이 오늘 몫을 다 받았는지 판정한다 — 10:00 재시도 여부 결정용(10/23 Jae).

기준
  - DTCC CDS(cds_hist·cds_vol): 직전 미국 영업일(평일) 날짜가 들어 있어야 한다(09:15 KST 게시분).
  - FINRA 웹 채권: 오늘 받아 갔어야 한다(fetched 날짜 = 오늘). 데이터 자체가 영업일 1일+ 늦으므로 날짜로는 판정하지 않는다.
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


def finra_needed(today: dt.date) -> bool:
    if (RISK / "FINRA_BLOCKED").exists():
        return False
    return str(load("finra_eod_1y.json").get("fetched", ""))[:10] != str(today)


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
        why.append("FINRA 오늘 미수집")
    print("FRESH" if not why else "STALE " + ", ".join(why))
    return 0 if not why else 1


if __name__ == "__main__":
    sys.exit(main())
