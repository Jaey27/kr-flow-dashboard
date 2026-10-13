# -*- coding: utf-8 -*-
"""수집 -> 원장(data/ledger/*.json) 병합 -> 렌더 입력(data/flows.json).

모드
  --auto      (launchd 기본) 지금 새 데이터가 나올 차례인 출처만 조회한다. 할 일이 없으면 네트워크 0회.
  --full      모든 출처의 최근 --days 일을 다시 받는다(정정 반영용, 하루 1회 자동 실행).
  --backfill  원장을 HISTORY_START 부터 다시 채운다(최초 1회).

종료코드: 0 = 원장/flows.json 이 바뀜(렌더 필요) · 3 = 바뀐 것 없음 · 1 = 수집 실패
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "sources"))

from common import (DATA, HOLIDAY_COVER_TO, is_bday, last_bday_on_or_before, load_ledger, log,  # noqa: E402
                    market_close, merge_rows, now_kst, prev_bday, save_json, save_ledger)
import daum as daum_src  # noqa: E402
import freesis as freesis_src  # noqa: E402

# --------------------------------------------------------------------------
# 설정 — 갱신 시각 근거는 README.md '갱신 시각' 절
# --------------------------------------------------------------------------
HISTORY_START = dt.date(2024, 10, 1)   # 슬라이더로 볼 수 있는 가장 이른 날(기본 화면은 최근 1년)
CLOSE_GRACE_MIN = 10                    # 장 마감 후 이만큼 지나야 당일 수급을 '잠정'으로 받는다
FINAL_AT = dt.time(18, 30)              # 이 시각 이후 받은 당일 수급은 '확정'으로 본다(KRX 18시 확정)
FREESIS_FROM = dt.time(7, 0)            # 금투협 T+1 공표를 이 시각부터 폴링
RECENT_DAYS = 15                        # --auto/--full 에서 다시 받는 최근 일수(정정 반영)
RETRY_MIN = {"daum": 30, "freesis": 10}  # 공표 대기·누락 보충 시 재조회 최소 간격(분)

STATE_PATH = DATA / "state.json"
FLOWS_PATH = DATA / "flows.json"


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


# --------------------------------------------------------------------------
# 출처별 수집
# --------------------------------------------------------------------------
def daum_window_rows(rows: dict, now: dt.datetime) -> tuple[dict, set]:
    """장중(마감+유예 전) 당일 행은 버리고, FINAL_AT 전 당일 행은 잠정으로 표시."""
    today = now.date()
    close = dt.datetime.combine(today, market_close(today), now.tzinfo) + dt.timedelta(minutes=CLOSE_GRACE_MIN)
    t = today.isoformat()
    prov = set()
    if t in rows:
        if now < close:
            rows = {d: r for d, r in rows.items() if d != t}
        elif now.time() < FINAL_AT:
            prov.add(t)
    return rows, prov


def fetch_daum(start: dt.date, now: dt.datetime) -> bool:
    d = daum_src.Daum()
    changed = False
    for market in ("KOSPI", "KOSDAQ"):
        rows, prov = daum_window_rows(d.investor(market, start), now)
        led = load_ledger(f"daum_investor_{market.lower()}")
        if merge_rows(led, rows, prov):
            changed = True
        led["fetched_at"] = now.isoformat(timespec="seconds")
        save_ledger(f"daum_investor_{market.lower()}", led)
        log(f"daum investor {market}: {len(rows)}행 (잠정 {sorted(prov) or '-'})")

    idx_rows = {}
    for market in ("KOSPI", "KOSDAQ"):
        for day, v in d.index(market, start).items():
            idx_rows.setdefault(day, {})[market.lower()] = v
    idx_rows, prov = daum_window_rows(idx_rows, now)
    led = load_ledger("daum_index")
    changed |= merge_rows(led, idx_rows, prov)
    led["fetched_at"] = now.isoformat(timespec="seconds")
    save_ledger("daum_index", led)

    # 선물: 만기가 start 이후인 월물 전부(미결제약정 합산에 원월물까지 필요)
    raw_led = load_ledger("daum_futures_raw")
    per_contract = {}
    for y, m, code in daum_src.contracts(start, now.date()):
        rows = d.future_days(code, start)
        if rows:
            per_contract[code] = rows
    raw_rows: dict[str, dict] = {}
    for code, rows in per_contract.items():
        for day, r in rows.items():
            raw_rows.setdefault(day, {})[code] = r
    raw_rows, prov = daum_window_rows(raw_rows, now)
    merge_rows(raw_led, raw_rows, prov)
    raw_led["fetched_at"] = now.isoformat(timespec="seconds")
    save_ledger("daum_futures_raw", raw_led)

    # 원장 전체에서 다시 집계(증분 수집이어도 과거 날짜 집계가 흔들리지 않게)
    agg, mismatch = daum_src.aggregate_futures(_per_code_view(raw_led["rows"]))
    led = load_ledger("daum_futures")
    changed |= merge_rows(led, agg, set(raw_led.get("prov", [])))
    led["fetched_at"] = now.isoformat(timespec="seconds")
    led["contracts"] = sorted(per_contract)
    led["investor_mismatch_days"] = mismatch
    save_ledger("daum_futures", led)
    log(f"daum futures: 월물 {len(per_contract)}개, 집계 {len(agg)}일, 투자자값 불일치 {mismatch}일")
    return changed


def _per_code_view(raw_rows: dict[str, dict]) -> dict[str, dict[str, dict]]:
    """{day: {code: row}} -> {code: {day: row}}"""
    out: dict[str, dict[str, dict]] = {}
    for day, by_code in raw_rows.items():
        for code, r in by_code.items():
            out.setdefault(code, {})[day] = r
    return out


def fetch_freesis(start: dt.date, now: dt.datetime) -> bool:
    fs = freesis_src.FreeSIS()
    changed = False
    for obj, (name, _) in freesis_src.TABLES.items():
        rows = fs.table(obj, start, now.date())
        led = load_ledger(name)
        changed |= merge_rows(led, rows)
        led["fetched_at"] = now.isoformat(timespec="seconds")
        save_ledger(name, led)
        log(f"freesis {name}: {len(rows)}행, 최신 {max(rows) if rows else '-'}")
    return changed


# --------------------------------------------------------------------------
# --auto 판정: 지금 새 값이 나올 차례인가
# --------------------------------------------------------------------------
def daum_due(now: dt.datetime) -> str | None:
    today = now.date()
    led = load_ledger("daum_investor_kospi")
    if not led["rows"]:
        return "원장 비어 있음"
    rows, prov = led["rows"], set(led.get("prov", []))
    t = today.isoformat()
    if is_bday(today):
        close = dt.datetime.combine(today, market_close(today), now.tzinfo) + dt.timedelta(minutes=CLOSE_GRACE_MIN)
        if now >= close and t not in rows:
            return "당일 잠정치 수집"
        if t in prov and now.time() >= FINAL_AT:
            return "당일 확정치 수집"
    if any(d < t for d in prov):
        return f"이전 잠정치 확정 필요 {sorted(d for d in prov if d < t)}"
    last = (prev_bday(today) if is_bday(today) else last_bday_on_or_before(today)).isoformat()
    if max(rows) < last:
        return f"누락 영업일 보충(원장 최신 {max(rows)} < {last})"
    return None


def freesis_expected(today: dt.date) -> dt.date:
    """오늘까지 공표됐어야 하는 최신 기준일. T 의 값은 T+1 영업일에 올라온다."""
    if is_bday(today):
        return prev_bday(today)
    return prev_bday(last_bday_on_or_before(today))


def freesis_due(now: dt.datetime) -> str | None:
    led = load_ledger("freesis_credit")
    if not led["rows"]:
        return "원장 비어 있음"
    exp = freesis_expected(now.date()).isoformat()
    if max(led["rows"]) >= exp:
        return None
    if is_bday(now.date()) and now.time() < FREESIS_FROM:
        return None
    return f"T+1 공표 대기 (원장 최신 {max(led['rows'])} < 기대 {exp})"


# --------------------------------------------------------------------------
# 렌더 입력 조립
# --------------------------------------------------------------------------
def assemble(now: dt.datetime) -> dict:
    L = {n: load_ledger(n) for n in ("daum_investor_kospi", "daum_investor_kosdaq", "daum_index",
                                     "daum_futures", "freesis_credit", "freesis_funds")}
    start = HISTORY_START.isoformat()
    dates = sorted({d for led in L.values() for d in led["rows"] if d >= start})

    def col(ledger: str, field: str, scale: float = 1.0, nd: int | None = None):
        rows = L[ledger]["rows"]
        out = []
        for d in dates:
            v = rows.get(d, {}).get(field)
            if v is None:
                out.append(None)
            else:
                v = v * scale
                out.append(round(v, nd) if nd is not None else v)
        return out

    S: dict[str, list] = {}
    # 금투협 (백만원 -> 억원)
    for f in ("credit_total", "credit_kospi", "credit_kosdaq", "collateral_loan"):
        S[f] = col("freesis_credit", f, 0.01, 0)
    for f in ("deposit", "deriv_deposit", "rp_balance", "unpaid"):
        S[f] = col("freesis_funds", f, 0.01, 0)
    S["forced_sale"] = col("freesis_funds", "forced_sale", 0.01, 2)
    S["forced_ratio"] = col("freesis_funds", "forced_ratio")
    # 현물 투자자별 (억원)
    fields = ["indiv", "foreign", "inst"] + list(daum_src.DETAIL_FIELDS.values())
    for mk in ("kospi", "kosdaq"):
        for f in fields:
            S[f"{mk}_{f}"] = col(f"daum_investor_{mk}", f, 1, 1)
        S[f"idx_{mk}"] = col("daum_index", mk)
    # 선물 (계약)
    for f in ("foreign", "inst", "indiv", "oi", "price"):
        S[f"fut_{f}"] = col("daum_futures", f)

    asof = {}
    for key, ledger in (("credit", "freesis_credit"), ("funds", "freesis_funds"),
                        ("investor", "daum_investor_kospi"), ("futures", "daum_futures"),
                        ("index", "daum_index")):
        rows = L[ledger]["rows"]
        asof[key] = {"date": max(rows) if rows else None,
                     "prov": sorted(L[ledger].get("prov", [])),
                     "fetched_at": L[ledger].get("fetched_at")}

    return {
        "generated_at": now.isoformat(timespec="seconds"),
        "dates": dates,
        "series": S,
        "asof": asof,
        "expect": {
            "freesis": freesis_expected(now.date()).isoformat(),
            "daum": (now.date() if is_bday(now.date()) and now.time() >= FINAL_AT
                     else prev_bday(now.date()) if is_bday(now.date())
                     else last_bday_on_or_before(now.date())).isoformat(),
        },
        "futures_mismatch_days": L["daum_futures"].get("investor_mismatch_days", 0),
        "holiday_cover_to": HOLIDAY_COVER_TO,
    }


def strip_volatile(o: dict) -> dict:
    o = dict(o)
    o.pop("generated_at", None)
    o["asof"] = {k: {kk: vv for kk, vv in v.items() if kk != "fetched_at"} for k, v in o["asof"].items()}
    return o


# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--auto", action="store_true")
    g.add_argument("--full", action="store_true")
    g.add_argument("--backfill", action="store_true")
    ap.add_argument("--days", type=int, default=RECENT_DAYS)
    a = ap.parse_args()

    now = now_kst()
    state = load_state()
    recent = now.date() - dt.timedelta(days=a.days)

    jobs: list[tuple[str, dt.date, str]] = []
    if a.backfill:
        jobs = [("daum", HISTORY_START, "backfill"), ("freesis", HISTORY_START, "backfill")]
    elif a.full:
        jobs = [("daum", recent, "full"), ("freesis", recent, "full")]
    else:
        # 하루 첫 실행(07시 이후)은 전 출처 최근 구간을 다시 받아 정정분을 반영한다
        if state.get("last_full") != now.date().isoformat() and now.time() >= dt.time(7, 0):
            jobs = [("daum", recent, "일일 재수집"), ("freesis", recent, "일일 재수집")]
            state["last_full"] = now.date().isoformat()
        else:
            tries = state.setdefault("last_try", {})
            for name, fn in (("daum", daum_due), ("freesis", freesis_due)):
                why = fn(now)
                if not why:
                    continue
                # 같은 출처를 너무 자주 두드리지 않는다: 당일 수집은 매번, 그 밖의 대기·보충은 RETRY_MIN 간격
                urgent = why.startswith("당일") or why == "원장 비어 있음"
                last = tries.get(name)
                if not urgent and last and now - dt.datetime.fromisoformat(last) < dt.timedelta(minutes=RETRY_MIN[name]):
                    continue
                tries[name] = now.isoformat(timespec="seconds")
                jobs.append((name, HISTORY_START if why == "원장 비어 있음" else recent, why))

    if not jobs:
        save_json(STATE_PATH, state)
        return 3  # 조용히 종료(로그도 남기지 않는다 — run.sh 가 5분마다 부른다)

    if (dt.date.fromisoformat(HOLIDAY_COVER_TO) - now.date()).days < 45:
        log(f"[WARN] data/holidays_kr.json 휴장일 목록이 {HOLIDAY_COVER_TO} 까지만 있다 — 갱신 필요")

    changed = False
    failed = []
    for name, start, why in jobs:
        log(f"{name}: {why} (from {start})")
        try:
            changed |= (fetch_daum if name == "daum" else fetch_freesis)(start, now)
        except Exception:  # noqa: BLE001
            failed.append(name)
            log(f"[ERROR] {name} 수집 실패\n{traceback.format_exc()}")

    flows = assemble(now)
    old = json.loads(FLOWS_PATH.read_text(encoding="utf-8")) if FLOWS_PATH.exists() else None
    flows_changed = old is None or strip_volatile(old) != strip_volatile(flows)
    if flows_changed or changed:
        save_json(FLOWS_PATH, flows)
    state["last_run"] = now.isoformat(timespec="seconds")
    save_json(STATE_PATH, state)

    if failed and not (flows_changed or changed):
        return 1
    log(f"완료: 변경 {'있음' if (flows_changed or changed) else '없음'}"
        + (f" · 실패 {failed}" if failed else ""))
    return 0 if (flows_changed or changed) else 3


if __name__ == "__main__":
    sys.exit(main())
