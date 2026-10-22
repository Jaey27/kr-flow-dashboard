"""리스크 탭 1년 시계열 — 수동 실행 전용(개인 리서치). 자동 스케줄에 넣지 말 것(FINRA 약관: 개인·비상업, 자동수집 금지).

    python scripts/risk_history.py finra   # FINRA TRACE 일별 가격·YTM (최근 1년) → data/risk/finra_eod_1y.json
    python scripts/risk_history.py cds     # DTCC 공개 CDS 체결(5Y on-the-run) 일별 → data/risk/cds_hist.json (일자별 캐시)
    python scripts/risk_history.py cdsvol  # 하이퍼스케일러 CDS 거래 건수·명목(상한 가림 → 하한) + 북미 IG CDX 5Y 스프레드 → data/risk/cds_vol.json

CDS 5Y 기준 만기는 롤(3/20·9/20)에 맞춰 바꾼다: ~2026-03-19 → 2030-12-20, 2026-03-20~09-19 → 2031-06-20, 2026-09-20~ → 2031-12-20.
호가(Spread-Leg 1)가 찍힌 체결은 그대로, upfront 체결은 flat hazard(R=40%, r=3.7%)로 역산한다. upfront 부호가 없어서
쿠폰보다 스프레드가 높은 이름(CRWV·ORCL·SPCX·SBG·NBIS·HUT)은 '구매자 지급' 쪽 해만 쓰고, 나머지는 호가 체결만 쓴다.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import re
import statistics as st
import sys
import time
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RISK = ROOT / "data" / "risk"
START = dt.date.today() - dt.timedelta(days=731)  # 최근 2년(Jae 10/18)

# ---- FINRA ---------------------------------------------------------------
FB = "https://services-dynarep.ddwa.finra.org/"


def finra_client() -> httpx.Client:
    c = httpx.Client(headers={"User-Agent": "Mozilla/5.0", "Origin": "https://www.finra.org", "Referer": "https://www.finra.org/"}, timeout=40)
    c.get(FB + "public/reporting/v2/group/Firm/name/ActiveIndividual/dynamiclookup/examCode")
    c.headers.update({"Content-Type": "application/json", "Accept": "application/json", "X-XSRF-TOKEN": c.cookies.get("XSRF-TOKEN")})
    return c


def finra_eod(c: httpx.Client, cusip: str) -> list:
    body = {"fields": ["cusip", "lastSalePrice", "lastSaleYield", "tradeDate"],
            "orFilters": [{"compareFilters": [{"fieldName": "cusip", "fieldValue": cusip, "compareType": "EQUAL"}]}],
            "dateRangeFilters": [{"startDate": f"{START} 00:00:00", "endDate": f"{dt.date.today()} 23:59:59", "fieldName": "tradeDate"}],
            "sortFields": ["tradeDate"], "offset": 0, "limit": 5000}
    r = c.post(FB + "public/reporting/v2/data/group/FixedIncomeMarket/name/EndOfDayPriceYield", json=body)
    time.sleep(1.1)
    rb = r.json().get("returnBody", {})
    rows = json.loads(rb.get("data") or "[]")
    return sorted([[x["tradeDate"], x["lastSalePrice"], x.get("lastSaleYield")] for x in rows if x.get("lastSalePrice")])


def cusips() -> dict:
    seed = json.loads((RISK / "risk_seed.json").read_text(encoding="utf-8"))
    out = {tk: (v.get("highest_yield_bond") or {}).get("cusip") for tk, v in seed["issuers"].items()}
    out.update({b["key"]: b["cusip_144a"] for b in seed["dc_project_bonds"]})
    more = RISK / "dc_more.json"
    if more.exists():
        for b in json.loads(more.read_text(encoding="utf-8")).get("bonds", []):
            if b.get("cusip"):
                out[b["key"]] = b["cusip"]
    return {k: v for k, v in out.items() if v}


BLOCK = RISK / "FINRA_BLOCKED"


def run_finra() -> None:
    """FINRA 웹 데이터 — Jae 결정(10/19)으로 맥미니 매일 실행. 연속 실패(차단 의심)면 FINRA_BLOCKED 파일을 남기고 멈춘다(우회 시도 없음).
    파일이 있으면 다음 실행부터 건너뛴다 → Jae가 확인 후 파일을 지우면 재개."""
    if BLOCK.exists():
        print(f"[finra] 차단 표시 있음({BLOCK.read_text(encoding='utf-8').strip()}) — 건너뜀. 확인 후 파일 삭제하면 재개", flush=True)
        return
    old = json.loads((RISK / "finra_eod_1y.json").read_text(encoding="utf-8"))["bonds"] if (RISK / "finra_eod_1y.json").exists() else {}
    res, fails = {}, 0
    try:
        c = finra_client()
    except Exception as e:  # noqa: BLE001
        BLOCK.write_text(f"{dt.datetime.now():%Y-%m-%d %H:%M} 세션 실패 {e}", encoding="utf-8")
        print(f"[finra] 세션 실패 → 멈춤 {e}", flush=True)
        return
    for k, cu in cusips().items():
        try:
            res[k] = {"cusip": cu, "eod": finra_eod(c, cu)}
            print(f"[finra] {k} {cu} {len(res[k]['eod'])}행", flush=True)
            fails = 0
        except Exception as e:  # noqa: BLE001
            fails += 1
            print(f"[finra] {k} 실패 {e}", flush=True)
            if k in old:
                res[k] = old[k]
            if fails >= 3:
                BLOCK.write_text(f"{dt.datetime.now():%Y-%m-%d %H:%M} 연속 실패 {fails}회: {e}", encoding="utf-8")
                print("[finra] 연속 실패 → 차단 의심, 멈춤", flush=True)
                break
    for k, v in old.items():
        res.setdefault(k, v)
    (RISK / "finra_eod_1y.json").write_text(json.dumps({"start": str(START), "fetched": dt.datetime.now().isoformat(timespec="minutes"), "bonds": res}), encoding="utf-8")


# ---- DTCC CDS ------------------------------------------------------------
GROUPS = {"ORCL": r"ORACLE CORP|^Oracle Corp", "SPCX": r"SPACE EXPLORATION", "CRWV": r"^COREWEAVE", "GOOGL": r"ALPHABET",
          "META": r"META PLATFORMS", "AMZN": r"^AMAZON\.COM", "MSFT": r"MICROSOFT", "SBG": r"SOFTBANK GROUP", "NBIS": r"NEBIUS", "HUT": r"HUT 8"}
HIGH = {"CRWV", "ORCL", "SPCX", "SBG", "NBIS", "HUT"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0"}


def on_the_run(d: dt.date) -> str:
    if d < dt.date(2025, 9, 20):
        return "2030-06-20"
    if d < dt.date(2026, 3, 20):
        return "2030-12-20"
    if d < dt.date(2026, 9, 20):
        return "2031-06-20"
    return "2031-12-20"


def num(s):
    try:
        return float(str(s).replace(",", "").replace("+", ""))
    except Exception:  # noqa: BLE001
        return None


def rpv01(S, T, r=0.037, R=0.4):
    lam = S / (1 - R)
    return sum(0.25 * math.exp(-(r + lam) * 0.25 * (i + 1)) for i in range(int(round(T * 4))))


def implied(u, c, T):
    S = c
    for _ in range(60):
        S = c + u / rpv01(S, T)
    return S


def cds_day(d: dt.date) -> dict | None:
    cache = RISK / "cds_cache" / f"{d}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    r = httpx.get(f"https://kgc0418-tdw-data-0.s3.amazonaws.com/sec/eod/SEC_CUMULATIVE_CREDITS_{d:%Y_%m_%d}.zip", headers=UA, timeout=60)
    time.sleep(1.0)
    if r.status_code != 200:
        if d < dt.date.today() - dt.timedelta(days=3):  # 오래된 날 = 휴장일 → 빈 캐시
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("{}", encoding="utf-8")
        return None
    mat = otr5(d)  # 10/23: on_the_run 은 2025-03-20 이전 만기가 틀렸음(2030-06-20 → 실제 2029-12-20)
    got: dict[str, list] = {}
    z = zipfile.ZipFile(io.BytesIO(r.content))
    for n in z.namelist():
        for row in csv.DictReader(io.StringIO(z.read(n).decode("utf-8", "replace"))):
            nm = row.get("Underlying Asset Name", "")
            g = next((g for g, p in GROUPS.items() if re.search(p, nm, re.I)), None)
            if not g or row.get("Action type") != "NEWT" or row.get("Expiration Date") != mat:
                continue
            spr = num(row.get("Spread-Leg 1"))
            if spr is not None and spr > 0:
                # 단위가 체결마다 다르다: 0.0076(=76bp) · 0.000068(=68bp, 100배 작게 보고) · 76(bp)
                bp = spr * 1e6 if spr < 0.001 else (spr * 1e4 if spr < 1 else spr)
                got.setdefault(g, []).append(("q", round(bp, 1)))
                continue
            Ns = row.get("Notional amount-Leg 1", "")
            N, up, c = num(Ns), num(row.get("Other payment amount")), num(row.get("Fixed rate-Leg 1"))
            # ★ 10/23: 큰 체결은 명목이 '5,000,000+'로 가려진다. 예전엔 통째로 뺐는데, 그러면 작은 체결 1건이
            #   값을 정해 버렸다(META 10/21: 정정 붙은 2M 체결 1건 → 137bp, 가려진 11건은 97~116bp). 이제 상한 금액을 명목으로 넣는다
            #   (실제 명목이 더 크면 값이 쿠폰 쪽으로 조금 당겨지는 근사) → 중앙값이 한 체결에 끌려가지 않음.
            if not N or up is None or c is None:
                continue
            T = (dt.date.fromisoformat(mat) - d).days / 365.25
            hi, lo = implied(up / N, c, T) * 1e4, implied(-up / N, c, T) * 1e4
            got.setdefault(g, []).append(("i", round(hi, 0)) if g in HIGH else ("ig", (round(lo, 0), round(hi, 0))))
    out = {}
    for g, L in got.items():
        q = [v for t, v in L if t == "q"]
        use = q or [v for t, v in L if t == "i"]
        if use:
            out[g] = {"bp": round(st.median(use), 1), "n": len(use), "kind": "quoted" if q else "implied"}
        else:  # IG 이름 upfront: 부호를 몰라 두 해 (lo, hi) 를 남기고, run_cds 에서 직전 값에 가까운 쪽을 고른다
            out[g] = {"pairs": [v for t, v in L if t == "ig"], "kind": "implied2"}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


LAST: dict = {}


CDS_CACHE_VER = "2"  # 10/23: 상한 가림 체결 포함 + otr5 만기 → 예전 캐시는 한 번 지우고 다시 계산(맥미니 첫 실행 ~10분)


def run_cds() -> None:
    cd = RISK / "cds_cache"
    vf = cd / "VERSION"
    if cd.exists() and (not vf.exists() or vf.read_text().strip() != CDS_CACHE_VER):
        for f in cd.glob("*.json"):
            f.unlink()
        print(f"[cds] 캐시 버전 {CDS_CACHE_VER} — 예전 일자 캐시를 지우고 다시 계산", flush=True)
    cd.mkdir(parents=True, exist_ok=True)
    vf.write_text(CDS_CACHE_VER)
    d, res = START, {}
    while d <= dt.date.today():
        if d.weekday() < 5:
            try:
                x = cds_day(d)
                if x:
                    for g, v in list(x.items()):
                        if v.get("kind") == "implied2":
                            ref = LAST.get(g, 100.0)
                            picks = [min(p, key=lambda z: abs(z - ref)) for p in v["pairs"]]
                            x[g] = {"bp": round(st.median(picks), 1), "n": len(picks), "kind": "implied"}
                        LAST[g] = x[g]["bp"]
                    res[str(d)] = x
                    print(f"[cds] {d} {', '.join(f'{k} {v['bp']:g}' for k, v in x.items())}", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[cds] {d} 실패 {e}", flush=True)
        d += dt.timedelta(days=1)
    (RISK / "cds_hist.json").write_text(json.dumps({"start": str(START), "fetched": dt.datetime.now().isoformat(timespec="minutes"), "days": res}), encoding="utf-8")


# ---- CDS 거래량(하이퍼스케일러) + 북미 IG CDX ----------------------------------
# SEC(단일종목) 파일: 신규 체결(NEWT) 건수와 명목. 큰 거래는 '5,000,000+'처럼 상한으로 가려 공개된다 → 명목 합계는 '최소'(하한).
# CFTC(지수) 파일: CDX.NA.IG on-the-run 5Y 신규 체결 스프레드 중앙값(bp). 10/16 약 62bp(Bloomberg 차트 10월 수준과 일치 확인).
VOLG = ["ORCL", "META", "GOOGL", "AMZN", "MSFT", "CRWV"]
S3 = "https://kgc0418-tdw-data-0.s3.amazonaws.com"


def _rows(url: str):
    r = httpx.get(url, headers=UA, timeout=60)
    time.sleep(1.0)
    if r.status_code != 200:
        return None
    z = zipfile.ZipFile(io.BytesIO(r.content))
    out = []
    for n in z.namelist():
        out += list(csv.DictReader(io.StringIO(z.read(n).decode("utf-8", "replace"))))
    return out


def otr5(d: dt.date) -> str:
    """on-the-run 5Y 만기(롤 3/20·9/20): 9/20~3/19 거래 → (해+5 또는 +6)-12-20, 3/20~9/19 → (해+5)-06-20."""
    if d >= dt.date(d.year, 9, 20):
        return f"{d.year + 5}-12-20"
    if d >= dt.date(d.year, 3, 20):
        return f"{d.year + 5}-06-20"
    return f"{d.year + 4}-12-20"


def vol_day(d: dt.date) -> dict | None:
    cache = RISK / "cdsvol_cache" / f"{d}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    sec = _rows(f"{S3}/sec/eod/SEC_CUMULATIVE_CREDITS_{d:%Y_%m_%d}.zip")
    cftc = _rows(f"{S3}/cftc/eod/CFTC_CUMULATIVE_CREDITS_{d:%Y_%m_%d}.zip")
    if sec is None and cftc is None:
        if d < dt.date.today() - dt.timedelta(days=3):  # 오래된 날 = 휴장일 → 빈 캐시
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text("{}", encoding="utf-8")
        return None
    if sec is None or cftc is None:  # 한쪽만 올라온 날은 다음 실행에 다시
        return None
    vol = {}
    for row in sec:
        if row.get("Action type") != "NEWT" or row.get("Notional currency-Leg 1") != "USD":
            continue
        nm = row.get("Underlying Asset Name", "")
        g = next((g for g in VOLG if re.search(GROUPS[g], nm, re.I)), None)
        if not g:
            continue
        a = row.get("Notional amount-Leg 1", "")
        v = vol.setdefault(g, [0, 0.0, 0])
        v[0] += 1
        v[1] += num(a) or 0
        v[2] += 1 if a.endswith("+") else 0
    vol = {g: [v[0], round(v[1] / 1e6, 1), v[2]] for g, v in vol.items()}  # [건수, 명목 $M(하한), 상한 가림 건수]
    mat, sp, n_all = otr5(d), [], 0
    for row in cftc:
        if (row.get("UPI Underlier Name") or "") != "CDX.NA.IG" or row.get("Action type") != "NEWT":
            continue
        n_all += 1
        if row.get("Expiration Date") != mat:
            continue
        x = num(row.get("Spread-Leg 1"))
        if x is not None and x > 0:
            sp.append(x * 1e4 if x < 1 else x)
    out = {"vol": vol, "cdxig": {"bp": round(st.median(sp), 1), "n": len(sp), "all": n_all} if sp else None}
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out


def run_cdsvol() -> None:
    d, res = START, {}
    while d <= dt.date.today():
        if d.weekday() < 5:
            try:
                x = vol_day(d)
                if x:
                    res[str(d)] = x
                    c = x.get("cdxig") or {}
                    print(f"[cdsvol] {d} 건수 {sum(v[0] for v in x['vol'].values())} · IG CDX {c.get('bp')}bp", flush=True)
            except Exception as e:  # noqa: BLE001
                print(f"[cdsvol] {d} 실패 {e}", flush=True)
        d += dt.timedelta(days=1)
    (RISK / "cds_vol.json").write_text(json.dumps({"start": str(START), "fetched": dt.datetime.now().isoformat(timespec="minutes"),
                                                   "names": VOLG, "days": res}), encoding="utf-8")


# ---- 관련 회사 주가(Yahoo, 제한 없음) ------------------------------------
STOCKS = {"META": "META", "ORCL": "ORCL", "MSFT": "MSFT", "GOOGL": "GOOGL", "AMZN": "AMZN", "CRWV": "CRWV", "NBIS": "NBIS",
          "HUT": "HUT", "SPCX": "SPCX", "SBG": "9984.T", "NVDA": "NVDA", "WULF": "WULF", "CIFR": "CIFR", "APLD": "APLD", "GLXY": "GLXY", "CORZ": "CORZ", "CLSK": "CLSK"}


def run_stocks() -> None:
    out = {}
    p1 = int((dt.datetime.now() - dt.timedelta(days=740)).timestamp())
    for k, sym in STOCKS.items():
        try:
            r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", params={"period1": p1, "period2": int(time.time()), "interval": "1d"},
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=30).json()["chart"]["result"][0]
            off = r["meta"].get("gmtoffset", 0)
            out[k] = [[dt.datetime.fromtimestamp(t + off, tz=dt.timezone.utc).date().isoformat(), round(c, 2)]
                      for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c is not None]
            print(f"[stocks] {k} {sym} {len(out[k])}일 {out[k][-1]}", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"[stocks] {k} 실패 {e}", flush=True)
        time.sleep(0.5)
    (RISK / "stocks.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    {"finra": run_finra, "cds": run_cds, "cdsvol": run_cdsvol, "stocks": run_stocks}[sys.argv[1]]()
