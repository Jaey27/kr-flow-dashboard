"""하이일드(HYG)를 AI 관련 / 비AI로 나눈 스프레드 + 투자등급(LQD) — 매일 스냅샷을 원장에 쌓는다.

    python scripts/hy_split.py        # → data/risk/hy_split_ledger.json (보유 기준일별 1행)

- 소스: iShares 공개 파일 latest-holdings.csv(채권별 가격·YTM·YTW·만기·시가) + 상품 페이지 OAS. 로그인·약관 제한 없음 → 맥미니 자동화 가능.
- 채권별 스프레드 = YTW(콜 있으면 최악 수익률) − 같은 잔존만기 미 국채 par 금리(재무부 커브 선형 보간). 시가 가중 평균.
  → 공식 OAS(옵션 조정)와 정의가 달라 수준은 다르다. AI·비AI·전체를 '같은 방식'으로 비교하는 용도.
- AI 분류(Jae 10/19, 좁게): CoreWeave + AI 데이터센터·컴퓨트 SPV(채굴→AI 코로케이션 포함) + SoftBank Group.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "risk" / "hy_split_ledger.json"
KST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
FUNDS = {"HYG": "https://www.ishares.com/us/products/239565/ishares-iboxx-high-yield-corporate-bond-etf",
         "LQD": "https://www.ishares.com/us/products/239566/ishares-iboxx-investment-grade-corporate-bond-etf"}
AI_PAT = re.compile(r"COREWEAVE|SOFTBANK GROUP|COMPUTE(CO)? |COMPUTE LLC|COMPUTECO|DATA ?CENTERS?|RNO PROPERTY OWNER|"
                    r"CORE SCIENTIFIC|GALAXY HELIOS|CSDC FINANCE|YONDR|ELK GROVE VILLAGE PROPERTY|BEIGNET|SOPAIPILLA|BEACON POINT DC|HUT 8 DC|"
                    r"NEBIUS|TERAWULF|CIPHER|APPLIED DIGITAL", re.I)
UST_COLS = [("1 Mo", 1/12), ("2 Mo", 2/12), ("3 Mo", .25), ("6 Mo", .5), ("1 Yr", 1), ("2 Yr", 2), ("3 Yr", 3), ("5 Yr", 5),
            ("7 Yr", 7), ("10 Yr", 10), ("20 Yr", 20), ("30 Yr", 30)]


def num(s):
    try:
        return float(str(s).replace(",", "").replace("%", ""))
    except Exception:  # noqa: BLE001
        return None


def holdings(url: str):
    t = httpx.get(url + "/latest-holdings.csv", headers=UA, timeout=60, follow_redirects=True).text
    lines = t.splitlines()
    asof = datetime.strptime(re.search(r'"([A-Z][a-z]{2} \d{2}, \d{4})"', lines[1]).group(1), "%b %d, %Y").date()
    hi = next(i for i, l in enumerate(lines) if l.startswith("Name,"))
    rows = [r for r in csv.DictReader(io.StringIO("\n".join(lines[hi:]))) if r.get("Asset Class") == "Fixed Income"]
    return asof, rows


def page_oas(url: str):
    t = httpx.get(url, headers=UA, timeout=60, follow_redirects=True).text
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
    m = re.search(r"Option Adjusted Spread.{0,200}?(-?\d+\.\d+)", txt)
    return float(m.group(1)) if m else None


def ust_curve(asof: date):
    u = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
         f"{asof.year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={asof.year}&page&_format=csv")
    rows = list(csv.DictReader(io.StringIO(httpx.get(u, headers=UA, timeout=40, follow_redirects=True).text)))
    rows = [r for r in rows if datetime.strptime(r["Date"], "%m/%d/%Y").date() <= asof]
    r = max(rows, key=lambda r: datetime.strptime(r["Date"], "%m/%d/%Y"))
    pts = [(y, num(r.get(c))) for c, y in UST_COLS if num(r.get(c)) is not None]
    return datetime.strptime(r["Date"], "%m/%d/%Y").date().isoformat(), pts


def interp(pts, x):
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1]


def bucket(rows, asof, pts):
    out = {"mv": 0.0, "w_g": 0.0, "w_y": 0.0, "w_d": 0.0, "n": 0}
    for r in rows:
        mv, y = num(r["Market Value"]), num(r.get("Yield to Worst (%)"))
        if y is None:
            y = num(r.get("YTM (%)"))
        try:
            mat = datetime.strptime(r["Maturity"], "%b %d, %Y").date()
        except Exception:  # noqa: BLE001
            continue
        if not mv or y is None:
            continue
        yrs = max((mat - asof).days / 365.25, 1 / 12)
        g = (y - interp(pts, yrs)) * 100
        out["mv"] += mv; out["w_g"] += mv * g; out["w_y"] += mv * y; out["w_d"] += mv * (num(r.get("Mod. Duration")) or 0); out["n"] += 1
    if not out["mv"]:
        return None
    return {"g_bp": round(out["w_g"] / out["mv"], 1), "ytw": round(out["w_y"] / out["mv"], 2), "dur": round(out["w_d"] / out["mv"], 2),
            "n": out["n"], "mv_bn": round(out["mv"] / 1e9, 2)}


FRED_IDS = {"hy": "BAMLH0A0HYM2", "ig": "BAMLC0A0CM", "bb": "BAMLH0A1HYBB", "b": "BAMLH0A2HYB", "ccc": "BAMLH0A3HYC"}


def fetch_fred() -> None:
    """ICE BofA OAS(공식 지수, FRED 무료) 최근 2년 → data/risk/fred_credit.json. 단위 % → bp 로 저장."""
    start = (date.today() - timedelta(days=731)).isoformat()
    out = {"fetched": datetime.now(KST).isoformat(timespec="minutes"), "series": {}}
    for k, sid in FRED_IDS.items():
        t = httpx.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}", headers={"User-Agent": "curl/8.4"}, timeout=40).text  # 브라우저 UA면 FRED가 응답 안 함
        rows = [r for r in csv.reader(io.StringIO(t))][1:]
        out["series"][k] = [[d, round(float(v) * 100, 1)] for d, v in rows if v not in (".", "")]
    (ROOT / "data" / "risk" / "fred_credit.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"[hy] FRED OAS {', '.join(f'{k} {v[-1]}' for k, v in out['series'].items())}")


def backfill_ai() -> None:
    """HYG 과거 보유종목은 공개되지 않는다 → AI 채권만 FINRA 채권별 일별 YTM(최근 2년)으로 복원.
    가중치 = 최신 HYG 시가(고정), 그날 값이 있는 채권만 재정규화(앞값 최대 5거래일 채움). 커버리지(가중치 %)도 남긴다.
    채권 대부분이 2025-10 이후 발행이라 초기 구간은 몇 개 채권만 반영된다 — 수준보다 방향용."""
    sys.path.insert(0, str(Path(__file__).parent))
    import risk_history as rh  # FINRA 웹 데이터(수동 실행 전용)
    led = json.loads(OUT.read_text(encoding="utf-8"))
    x = led[max(k for k in led if not k.startswith("_"))]
    eod_all = json.loads((ROOT / "data" / "risk" / "finra_eod_1y.json").read_text(encoding="utf-8"))["bonds"]
    by_cusip = {v["cusip"]: v["eod"] for v in eod_all.values()}
    c = None
    w_tot = sum(a["w"] or 0 for a in x["ai_top"])
    series = {}
    for a in x["ai_top"]:
        rows = by_cusip.get(a["cusip"])
        if rows is None:
            c = c or rh.finra_client()
            rows = rh.finra_eod(c, a["cusip"])
        series[a["cusip"]] = {r[0]: r[2] for r in rows if r[2] is not None}
    mats = {a["cusip"]: datetime.strptime(a["mat"], "%b %d, %Y").date() for a in x["ai_top"]}
    ws = {a["cusip"]: a["w"] or 0 for a in x["ai_top"]}
    # 국채 커브(2년치)
    curves = {}
    for y in sorted({date.today().year - 2, date.today().year - 1, date.today().year}):
        u = ("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/"
             f"{y}/all?type=daily_treasury_yield_curve&field_tdr_date_value={y}&page&_format=csv")
        for r in csv.DictReader(io.StringIO(httpx.get(u, headers=UA, timeout=40, follow_redirects=True).text)):
            curves[datetime.strptime(r["Date"], "%m/%d/%Y").date().isoformat()] = [(yy, num(r.get(cc))) for cc, yy in UST_COLS if num(r.get(cc)) is not None]
    days = sorted(d for d in curves if d >= (date.today() - timedelta(days=731)).isoformat())
    last, hist = {}, {}
    for d in days:
        num_, den, wy, wu = 0.0, 0.0, 0.0, 0.0
        for cu, s_ in series.items():
            if d in s_:
                last[cu] = (d, s_[d])
            if cu in last and (datetime.fromisoformat(d) - datetime.fromisoformat(last[cu][0])).days <= 7:
                yrs = max((mats[cu] - date.fromisoformat(d)).days / 365.25, 1 / 12)
                u = interp(curves[d], yrs)
                num_ += ws[cu] * (last[cu][1] - u) * 100
                wy += ws[cu] * last[cu][1]
                wu += ws[cu] * u
                den += ws[cu]
        if den:  # [스프레드 bp, 커버리지 %, AI 채권 수익률 %, 같은 만기 국채 금리 %]
            hist[d] = [round(num_ / den, 1), round(den / w_tot * 100, 1), round(wy / den, 3), round(wu / den, 3)]
    led["_ai_hist"] = hist
    OUT.write_text(json.dumps(dict(sorted(led.items())), ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"[hy] AI 복원 {len(hist)}일 · 최신 {max(hist)} {hist[max(hist)]}")


def main() -> int:
    led = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    asof, hy = holdings(FUNDS["HYG"])
    asof_ig, ig = holdings(FUNDS["LQD"])
    ust_d, pts = ust_curve(asof)
    ai = [r for r in hy if AI_PAT.search(r["Name"])]
    non = [r for r in hy if not AI_PAT.search(r["Name"])]
    tot_mv = sum(num(r["Market Value"]) or 0 for r in hy)
    rec = {
        "asof": asof.isoformat(), "ust_date": ust_d, "fetched": datetime.now(KST).isoformat(timespec="minutes"),
        "hy": bucket(hy, asof, pts), "hy_ai": bucket(ai, asof, pts), "hy_nonai": bucket(non, asof, pts),
        "ig": bucket(ig, asof_ig, pts), "ig_asof": asof_ig.isoformat(),
        "hyg_oas": page_oas(FUNDS["HYG"]), "lqd_oas": page_oas(FUNDS["LQD"]),
        "ai_weight_pct": round(sum(num(r["Market Value"]) or 0 for r in ai) / tot_mv * 100, 2),
        "ai_names": sorted({re.sub(r" 144A| REGS", "", r["Name"]) for r in ai}),
        "ai_top": sorted([{"name": re.sub(r" 144A| REGS", "", r["Name"]), "cusip": r["CUSIP"], "w": num(r["Weight (%)"]),
                           "px": num(r["Price"]), "ytw": num(r.get("Yield to Worst (%)")), "mat": r["Maturity"]} for r in ai],
                         key=lambda x: -(x["w"] or 0)),
    }
    led[rec["asof"]] = rec
    OUT.write_text(json.dumps(dict(sorted(led.items())), ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"[hy] {rec['asof']} HY G-spr {rec['hy']['g_bp']} (AI {rec['hy_ai']['g_bp']}, 비AI {rec['hy_nonai']['g_bp']}, AI 비중 {rec['ai_weight_pct']}%) · "
          f"IG {rec['ig']['g_bp']} · OAS HYG {rec['hyg_oas']} LQD {rec['lqd_oas']} · 원장 {len(led)}일")
    return 0


if __name__ == "__main__":
    if "--fred" in sys.argv:
        fetch_fred()
        sys.exit(0)
    if "--backfill-ai" in sys.argv:
        backfill_ai()
        sys.exit(0)
    sys.exit(main())
