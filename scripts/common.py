# -*- coding: utf-8 -*-
"""공통: 경로·KST 시각·HTTP 세션·영업일 계산·원장 입출력."""

from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LEDGER = DATA / "ledger"
KST = dt.timezone(dt.timedelta(hours=9))

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def now_kst() -> dt.datetime:
    return dt.datetime.now(KST)


def log(msg: str) -> None:
    print(f"[{now_kst():%H:%M:%S}] {msg}", flush=True)


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def session(referer: str | None = None) -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = UA
    if referer:
        s.headers["Referer"] = referer
    return s


def request_json(s: requests.Session, method: str, url: str, tries: int = 3, **kw):
    """JSON 응답을 돌려준다. 네트워크 오류·5xx·HTML 오류 페이지는 재시도 후 예외."""
    kw.setdefault("timeout", 30)
    last = None
    for i in range(tries):
        try:
            r = s.request(method, url, **kw)
            if r.status_code >= 500:
                raise RuntimeError(f"HTTP {r.status_code}")
            return r.json()
        except Exception as e:  # noqa: BLE001 - 재시도 대상 전부
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"{method} {url} 실패: {last!r}")


# --------------------------------------------------------------------------
# KRX 영업일 (data/holidays_kr.json = 자사주 대시보드와 같은 KRX 휴장일 원본)
# --------------------------------------------------------------------------
_HOL = json.loads((DATA / "holidays_kr.json").read_text(encoding="utf-8"))
HOLIDAYS = set(_HOL["holidays"])
SHORT_SESSIONS = {x["date"]: x for x in _HOL.get("short_sessions", [])}
HOLIDAY_COVER_TO = _HOL["covers"]["to"]


def is_bday(d: dt.date) -> bool:
    return d.weekday() < 5 and d.isoformat() not in HOLIDAYS


def prev_bday(d: dt.date) -> dt.date:
    d -= dt.timedelta(days=1)
    while not is_bday(d):
        d -= dt.timedelta(days=1)
    return d


def last_bday_on_or_before(d: dt.date) -> dt.date:
    while not is_bday(d):
        d -= dt.timedelta(days=1)
    return d


def market_close(d: dt.date) -> dt.time:
    """정규장 종료 시각. 수능일 등 순연일은 holidays_kr.json short_sessions 를 따른다."""
    ss = SHORT_SESSIONS.get(d.isoformat())
    hh, mm = (ss["close"] if ss else "15:30").split(":")
    return dt.time(int(hh), int(mm))


# --------------------------------------------------------------------------
# 원장: {"rows": {"YYYY-MM-DD": {field: value}}, "prov": [...], "fetched": {...}}
# --------------------------------------------------------------------------
def load_ledger(name: str) -> dict:
    p = LEDGER / f"{name}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"rows": {}, "prov": [], "fetched_at": None}


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def save_ledger(name: str, led: dict) -> None:
    led["rows"] = dict(sorted(led["rows"].items()))
    led["prov"] = sorted(set(led.get("prov", [])))
    save_json(LEDGER / f"{name}.json", led)


def merge_rows(led: dict, rows: dict[str, dict], prov_dates: set[str] = frozenset()) -> bool:
    """새로 받은 행을 원장에 덮어쓴다. 값이 하나라도 바뀌었으면 True.

    출처가 과거 값을 정정할 수 있으므로 받은 날짜는 항상 새 값으로 덮어쓴다.
    prov_dates 는 '잠정' 표시, 그 밖에 이번에 받은 날짜는 '확정'으로 전환한다.
    """
    changed = False
    prov = set(led.get("prov", []))
    for d, row in rows.items():
        if led["rows"].get(d) != row:
            led["rows"][d] = row
            changed = True
        want_prov = d in prov_dates
        if want_prov != (d in prov):
            changed = True
            (prov.add if want_prov else prov.discard)(d)
    led["prov"] = sorted(prov)
    return changed
