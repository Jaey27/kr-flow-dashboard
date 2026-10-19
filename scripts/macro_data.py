"""매크로 탭 데이터 수집 → data/macro.json

미 금리(2·5·10·30Y, 실질·BEI) · 텀프리미엄(NY Fed ACM) · 원/달러 · Brent · 연준 확률(Kalshi) · 금리분해 판정.
전부 무료·무인증. 실패한 출처는 캐시(data/macro_cache/)로 대신하고 asof 에 'cache' 를 남긴다.

    python scripts/macro_data.py            # 수집 + 금리분해 재계산 + docs/rates.html
    python scripts/macro_data.py --offline  # 캐시만으로 다시 계산

소스별 갱신 시각(KST, 경험칙):
- 재무부 명목·실질 커브: 미 영업일 당일 저녁(ET) 게시 → KST 다음 날 아침이면 전일분 있음
- NY Fed ACM: 1영업일 지연(10/17 아침 기준 10/15까지)
- CNBC 시세(Tradeweb·ICE): 실시간. 비공식 엔드포인트라 '오늘 값' 칸에만 쓰고 시계열은 공식 소스로 만든다
- Kalshi: 24시간
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = DATA / "macro_cache"
OUT = DATA / "macro.json"
RATES_DIR = ROOT / "rates"
KST = timezone(timedelta(hours=9))
START = date(2025, 1, 1)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

TREASURY_URL = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                "daily-treasury-rates.csv/{year}/all?type={kind}&field_tdr_date_value={year}&page&_format=csv")
ACM_URL = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls"
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
CNBC_URL = "https://quote.cnbc.com/quote-html-webservice/restQuote/symbolType/symbol"
CNBC_SYMS = {"US2Y": "y2", "US5Y": "y5", "US10Y": "y10", "US30Y": "y30", "US10YTIP": "real10",
             "@LCO.1": "brent", "KRW=": "usdkrw"}
FED_OUTCOMES = [("C26", "인하 >25bp"), ("C25", "인하 25bp"), ("H0", "동결"), ("H25", "인상 25bp"), ("H26", "인상 >25bp")]
FED_MEETINGS = 3   # 가까운 회의 몇 개를 볼지


def log(msg: str) -> None:
    print(f"[macro] {msg}", flush=True)


def cached(name: str, fetch, offline: bool):
    """fetch() 결과(DataFrame/dict)를 캐시에 저장. 실패하거나 offline 이면 캐시를 읽는다. (값, 'live'|'cache')"""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}.pkl"
    if not offline:
        try:
            v = fetch()
            pd.to_pickle(v, path)
            return v, "live"
        except Exception as e:  # noqa: BLE001
            log(f"{name} 수집 실패 → 캐시: {e}")
    if path.exists():
        return pd.read_pickle(path), "cache"
    return None, "none"


# ---- 출처별 ---------------------------------------------------------------
def fetch_treasury() -> pd.DataFrame:
    nom, real = [], []
    for y in range(START.year, datetime.now(KST).year + 1):
        for kind, bucket in (("daily_treasury_yield_curve", nom), ("daily_treasury_real_yield_curve", real)):
            r = httpx.get(TREASURY_URL.format(year=y, kind=kind), headers=UA, timeout=40, follow_redirects=True)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
            bucket.append(df.set_index("Date"))
    n = pd.concat(nom)[["2 Yr", "5 Yr", "10 Yr", "30 Yr"]]
    n.columns = ["y2", "y5", "y10", "y30"]
    rl = pd.concat(real)[["5 YR", "10 YR", "30 YR"]]
    rl.columns = ["real5", "real10", "real30"]
    df = n.join(rl, how="left").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df["bei5"] = df["y5"] - df["real5"]
    df["bei10"] = df["y10"] - df["real10"]
    df["s2s10"] = (df["y10"] - df["y2"]) * 100
    df["s10s30"] = (df["y30"] - df["y10"]) * 100
    return df[df.index >= pd.Timestamp(START)]


def fetch_acm() -> pd.DataFrame:
    r = httpx.get(ACM_URL, headers=UA, timeout=120, follow_redirects=True)
    r.raise_for_status()
    df = pd.read_excel(io.BytesIO(r.content), sheet_name="ACM Daily")
    df["DATE"] = pd.to_datetime(df["DATE"], format="%d-%b-%Y")
    df = df.set_index("DATE")[["ACMY10", "ACMTP10", "ACMRNY10", "ACMTP05", "ACMTP02"]]
    df.columns = ["acmy10", "tp10", "rny10", "tp5", "tp2"]
    return df[df.index >= pd.Timestamp(START)]


def fetch_yahoo(symbol: str) -> pd.Series:
    p1 = int(datetime(START.year, START.month, START.day, tzinfo=timezone.utc).timestamp())
    r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
                  params={"period1": p1, "period2": int(time.time()), "interval": "1d"}, headers=UA, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    off = res["meta"].get("gmtoffset", 0)
    idx = [pd.Timestamp(datetime.fromtimestamp(t + off, tz=timezone.utc).date()) for t in res["timestamp"]]
    s = pd.Series(res["indicators"]["quote"][0]["close"], index=idx, dtype="float64").dropna()
    return s[~s.index.duplicated(keep="last")]


def fetch_cnbc() -> dict:
    r = httpx.get(CNBC_URL, params={"symbols": "|".join(CNBC_SYMS), "requestMethod": "itv", "noform": 1,
                                    "partnerId": 2, "fund": 1, "exthrs": 1, "output": "json", "events": 1},
                  headers=UA, timeout=20)
    r.raise_for_status()
    out = {}
    for q in r.json()["FormattedQuoteResult"]["FormattedQuote"]:
        k = CNBC_SYMS.get(q.get("symbol"))
        if not k or q.get("last") in (None, ""):
            continue
        num = lambda s: float(str(s).replace("%", "").replace(",", "").replace("+", "")) if s not in (None, "", "UNCH") else None  # noqa: E731
        out[k] = {"last": num(q["last"]), "prev": num(q.get("previous_day_closing")), "time": q.get("last_time"),
                  "name": q.get("name"), "src": q.get("exchange")}
    return out


def fetch_fed() -> dict:
    ms = httpx.get(f"{KALSHI}/markets", params={"series_ticker": "KXFEDDECISION", "status": "open", "limit": 200},
                   timeout=30).json()["markets"]
    by_ev: dict[str, list] = {}
    for m in ms:
        by_ev.setdefault(m["event_ticker"], []).append(m)
    # 회의일 = 마켓 close_time(ET 결정일 14:00 직전) 의 날짜
    evs = sorted(by_ev, key=lambda e: min(m["close_time"] for m in by_ev[e]))[:FED_MEETINGS]
    now = int(time.time())
    meetings = []
    for ev in evs:
        mk = {m["ticker"].rsplit("-", 1)[1]: m for m in by_ev[ev]}
        close = min(m["close_time"] for m in by_ev[ev])
        outs, hist = [], {}
        for code, label in FED_OUTCOMES:
            m = mk.get(code)
            if not m:
                continue
            bid, ask = float(m.get("yes_bid_dollars") or 0), float(m.get("yes_ask_dollars") or 0)
            last = float(m.get("last_price_dollars") or 0)
            p = (bid + ask) / 2 if ask > 0 else last
            outs.append({"code": code, "label": label, "p": round(p * 100, 1), "last": round(last * 100, 1),
                         "prev": round(float(m.get("previous_price_dollars") or 0) * 100, 1)})
            try:
                c = httpx.get(f"{KALSHI}/series/KXFEDDECISION/markets/{m['ticker']}/candlesticks",
                              params={"start_ts": now - 86400 * 200, "end_ts": now, "period_interval": 1440},
                              timeout=30).json().get("candlesticks", [])
                for x in c:
                    d = datetime.fromtimestamp(x["end_period_ts"], tz=timezone(timedelta(hours=-5))).date().isoformat()
                    v = x["price"].get("close_dollars")
                    if v is None:
                        b, a = x["yes_bid"].get("close_dollars"), x["yes_ask"].get("close_dollars")
                        v = (float(b) + float(a)) / 2 if b and a else None
                    if v is not None:
                        hist.setdefault(d, {})[code] = round(float(v) * 100, 1)
            except Exception as e:  # noqa: BLE001
                log(f"kalshi 캔들 실패 {m['ticker']}: {e}")
        meetings.append({"event": ev, "date": close[:10], "outcomes": outs, "hist": hist})
    return {"meetings": meetings, "fetched": datetime.now(KST).isoformat(timespec="minutes")}


def run_decompose(offline: bool) -> dict | None:
    """rates/decompose.py 를 그대로 돌려 일별 판정·기여도와 docs/rates.html 을 만든다."""
    sys.path.insert(0, str(RATES_DIR))
    try:
        import decompose  # type: ignore
        r = decompose.run(offline=offline)
    except Exception as e:  # noqa: BLE001
        log(f"금리분해 실패: {e}")
        return None
    finally:
        sys.path.pop(0)
    docs = ROOT / "docs" / "rates.html"
    docs.parent.mkdir(exist_ok=True)
    docs.write_text(Path(r["html_path"]).read_text(encoding="utf-8"), encoding="utf-8")
    df = r["df"]
    rows = []
    for ts, row in df.tail(60).iterrows():
        g = lambda k: (None if pd.isna(row.get(k)) else round(float(row[k]), 2))  # noqa: E731
        rows.append({"date": ts.date().isoformat(), "tag": row["tag"], "subtag": row.get("subtag") or "",
                     "d_y10": g("d_y10"), "d_real10": g("d_real10"), "d_bei10": g("d_bei10"),
                     "d_y2": g("d_y2"), "d_y30": g("d_y30"), "r_brent": g("r_brent"), "r_ai_rel": g("r_ai_rel"),
                     "c": {k: g("c_" + k) for k in ("inflation", "oil", "ai", "ai_fund", "fed", "other")}})
    return {"rows": rows, "text": r["text"]}


def releases() -> list[dict]:
    """경제지표 탭 발표 일정 — rates/config.py 의 공식 일정(BLS·BEA·연준)을 그대로 쓴다."""
    sys.path.insert(0, str(RATES_DIR))
    try:
        import config as rc  # type: ignore
    finally:
        sys.path.pop(0)
    out = []
    for t, ds in (("CPI", rc.CPI_DATES), ("PPI", rc.PPI_DATES), ("PCE", rc.PCE_DATES), ("NFP", rc.NFP_DATES), ("FOMC", rc.FOMC_DATES), ("RETAIL", getattr(rc, "RETAIL_DATES", []))):
        out += [{"type": t, "date": d} for d in ds]
    return out



# ---- CME FedWatch 방식(연방기금 선물 ZQ) ------------------------------------
# CME 사이트는 스크립트에 403 → 같은 방법론을 연방기금 선물(Yahoo ZQ 월물, 지연시세)과 NY Fed EFFR로 직접 계산한다.
# 월물 평균금리 = 100 − 가격. 회의가 있는 달: 평균 = (d/N)·회의 전 금리 + ((N−d)/N)·회의 후 금리 → 회의 후 금리를 역산.
# 회의 후 예상 금리와 현재 EFFR 차이(누적 bp)를 25bp 단위 두 결과에 선형 배분(FedWatch와 같은 방식, 근사).
MCODE = "FGHJKMNQUVXZ"


def zq_symbol(y: int, m: int) -> str:
    return f"ZQ{MCODE[m-1]}{str(y)[-2:]}.CBT"


def fetch_fedwatch() -> dict:
    sys.path.insert(0, str(RATES_DIR))
    try:
        import config as rc  # type: ignore
    finally:
        sys.path.pop(0)
    import calendar
    ef = httpx.get("https://markets.newyorkfed.org/api/rates/unsecured/effr/last/400.json", timeout=30).json()["refRates"]
    effr = pd.Series({pd.Timestamp(r["effectiveDate"]): r["percentRate"] for r in ef}).sort_index()
    tgt = (ef[0]["targetRateFrom"], ef[0]["targetRateTo"])
    today = pd.Timestamp(datetime.now(KST).date())
    meets = [pd.Timestamp(d) for d in rc.FOMC_DATES if pd.Timestamp(d) >= today - pd.Timedelta(days=1)][:4]
    months = sorted({(m.year, m.month) for m in meets} | {((m + pd.offsets.MonthBegin(1)).year, (m + pd.offsets.MonthBegin(1)).month) for m in meets}
                    | {((m - pd.offsets.MonthBegin(1)).year, (m - pd.offsets.MonthBegin(1)).month) for m in meets})
    zq = {}
    for y, m in months:
        try:
            s = fetch_yahoo(zq_symbol(y, m))
            zq[(y, m)] = 100 - s
        except Exception as e:  # noqa: BLE001
            log(f"ZQ {y}-{m} 실패: {e}")
    if not zq:
        raise RuntimeError("ZQ 월물 없음")
    dates = sorted(set().union(*[set(v.index) for v in zq.values()]))
    dates = [d for d in dates if d >= today - pd.Timedelta(days=200)]

    def on(d):
        out, r0 = [], effr[effr.index <= d].iloc[-1] if (effr.index <= d).any() else None
        if r0 is None:
            return None
        cur = r0
        for mt in meets:
            if mt < d:
                continue
            y, m = mt.year, mt.month
            N = calendar.monthrange(y, m)[1]
            dd = mt.day  # 결정일 다음 날부터 새 금리 → 결정일까지 dd 일은 이전 금리
            avg = zq.get((y, m))
            nxt = zq.get(((mt + pd.offsets.MonthBegin(1)).year, (mt + pd.offsets.MonthBegin(1)).month))
            a = avg.get(d) if avg is not None else None
            b = nxt.get(d) if nxt is not None else None
            if b is not None and not pd.isna(b):
                post = float(b)  # 다음 달에 회의가 없으면 다음 달 평균 = 회의 후 금리 (더 깨끗)
                if any(x.year == (mt + pd.offsets.MonthBegin(1)).year and x.month == (mt + pd.offsets.MonthBegin(1)).month for x in meets):
                    post = None
            else:
                post = None
            if post is None and a is not None and not pd.isna(a):
                post = (float(a) - cur * dd / N) / ((N - dd) / N)
            if post is None:
                break
            out.append({"date": mt.date().isoformat(), "post": round(post, 3), "chg_bp": round((post - r0) * 100, 1)})
            cur = post
        return out

    hist = {}
    for d in dates:
        r = on(d)
        if r:
            hist[d.date().isoformat()] = r
    last = hist[max(hist)] if hist else []

    def dist(chg):  # 누적 변화 bp → 25bp 단위 두 결과 확률
        lo = math.floor(chg / 25) * 25
        w = (chg - lo) / 25
        return {lo: round((1 - w) * 100, 1), lo + 25: round(w * 100, 1)}

    meetings = [{"date": x["date"], "post": x["post"], "chg_bp": x["chg_bp"], "dist": {str(k): v for k, v in dist(x["chg_bp"]).items() if v > 0}} for x in last]
    return {"asof": max(hist) if hist else None, "effr": float(effr.iloc[-1]), "effr_date": effr.index[-1].date().isoformat(), "target": tgt,
            "meetings": meetings, "hist": hist, "fetched": datetime.now(KST).isoformat(timespec="minutes")}

# ---- 조립 -----------------------------------------------------------------
def kospi_from_flows() -> pd.Series:
    f = json.loads((DATA / "flows.json").read_text(encoding="utf-8"))
    return pd.Series(f["series"]["idx_kospi"], index=pd.to_datetime(f["dates"]), dtype="float64").dropna()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    a = ap.parse_args()

    tr, s_tr = cached("treasury", fetch_treasury, a.offline)
    if tr is None:
        log("재무부 금리 없음 — 중단")
        return 1
    acm, s_acm = cached("acm", fetch_acm, a.offline)
    brent, s_br = cached("brent", lambda: fetch_yahoo("BZ=F"), a.offline)
    krw, s_krw = cached("usdkrw", lambda: fetch_yahoo("KRW=X"), a.offline)
    live, s_live = cached("cnbc", fetch_cnbc, a.offline)
    fed, s_fed = cached("fed", fetch_fed, a.offline)
    dec = run_decompose(a.offline)
    fw, s_fw = cached("fedwatch", fetch_fedwatch, a.offline)

    idx = tr.index  # 축 = 미 채권시장 영업일
    df = tr.copy()
    if acm is not None:
        df = df.join(acm, how="left")
    # Brent·원/달러는 거래일이 달라 '그 날짜 이전 마지막 값'으로 맞춘다
    for name, s in (("brent", brent), ("usdkrw", krw)):
        if s is not None:
            df[name] = s.reindex(idx.union(s.index)).ffill().reindex(idx)
    try:
        k = kospi_from_flows()
        df["kospi"] = k.reindex(idx.union(k.index)).ffill().reindex(idx)
    except Exception as e:  # noqa: BLE001
        log(f"flows.json 코스피 없음: {e}")
    fw_meets = []
    if fw:
        # FedWatch 누적 원장: 날짜별 {회의일: 누적 bp}. 실행할 때마다 합친다(지나간 회의도 보존 → 계속 쌓임)
        led_path = DATA / "fedwatch_ledger.json"
        led = json.loads(led_path.read_text(encoding="utf-8")) if led_path.exists() else {}
        for d, v in fw["hist"].items():
            led.setdefault(d, {}).update({x["date"]: x["chg_bp"] for x in v})
        led_path.write_text(json.dumps(dict(sorted(led.items())), separators=(",", ":")), encoding="utf-8")
        fw_meets = sorted({m for v in led.values() for m in v})
        for m in fw_meets:
            ss = pd.Series({pd.Timestamp(d): v[m] for d, v in led.items() if m in v}).sort_index()
            col = "fw_" + m.replace("-", "")
            df[col] = ss.reindex(idx.union(ss.index)).ffill().reindex(idx)
            df.loc[(df.index < ss.index.min()) | (df.index > ss.index.max()), col] = None
    if fed:
        for i, m in enumerate(fed["meetings"]):
            for code, _ in FED_OUTCOMES:
                col = f"fed{i}_{code}"
                h = {pd.Timestamp(d): v.get(code) for d, v in m["hist"].items() if code in v}
                if h:
                    s = pd.Series(h).sort_index()
                    df[col] = s.reindex(idx.union(s.index)).ffill().reindex(idx)
                    df.loc[df.index < s.index.min(), col] = None

    def lastdate(s):
        s = s.dropna() if s is not None else None
        return None if s is None or s.empty else s.index.max().date().isoformat()

    out = {
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "dates": [d.date().isoformat() for d in idx],
        "series": {c: [None if pd.isna(v) else round(float(v), 4) for v in df[c]] for c in df.columns},
        "asof": {
            "treasury": {"date": lastdate(tr["y10"]), "via": s_tr},
            "acm": {"date": lastdate(acm["tp10"]) if acm is not None else None, "via": s_acm},
            "brent": {"date": lastdate(brent), "via": s_br},
            "usdkrw": {"date": lastdate(krw), "via": s_krw},
            "fed": {"date": fed["fetched"] if fed else None, "via": s_fed},
            "fedwatch": {"date": fw["asof"] if fw else None, "via": s_fw},
            "live": {"via": s_live},
        },
        "live": live or {},
        "fed": [{k: m[k] for k in ("event", "date", "outcomes")} for m in (fed or {}).get("meetings", [])],
        "fedwatch": dict({k: fw[k] for k in ("asof", "effr", "effr_date", "target", "meetings", "fetched")}, ledger_meetings=fw_meets) if fw else None,
        "decomp": dec,
        "releases": releases(),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    log(f"{OUT} ({OUT.stat().st_size/1024:.0f} KB) · 재무부 {out['asof']['treasury']['date']} · ACM {out['asof']['acm']['date']}"
        f" · Brent {out['asof']['brent']['date']} · 원/달러 {out['asof']['usdkrw']['date']} · 연준 {len(out['fed'])}회의")
    return 0


if __name__ == "__main__":
    sys.exit(main())
