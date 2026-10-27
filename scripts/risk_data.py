"""리스크 탭 데이터 → data/risk.json

v1 = 스냅샷. 2026-10-17 조사(통합대시보드\리스크_소스조사.md)에서 받은 risk_seed.json + FINRA 일별 가격(finra_eod.json)을
data/risk/ 에 두고 조립만 한다. 일별 자동 수집은 FINRA 약관(개인·비상업, 자동수집 금지) 판단 후에 붙인다.

    python scripts/risk_data.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "risk"
OUT = ROOT / "data" / "risk.json"
KST = timezone(timedelta(hours=9))

ISSUERS = ["CRWV", "NBIS", "SBG", "ORCL", "SPCX", "HUT", "META", "AMZN", "GOOGL", "MSFT"]
EOD_KEY = {"SBG": "SFTBY"}
GROUPS = [("네오클라우드", ["CRWV", "NBIS", "HUT"]), ("하이퍼스케일러", ["ORCL", "META", "AMZN", "GOOGL", "MSFT"]),
          ("SpaceX·SBG", ["SPCX", "SBG"]),
          ("전체", ["CRWV", "NBIS", "HUT", "ORCL", "META", "AMZN", "GOOGL", "MSFT", "SPCX", "SBG"])]


def bond_terms(iss: dict, cusip: str) -> dict:
    for b in iss.get("bonds") or iss.get("bonds_usd_finra") or []:
        if b.get("cusip") == cusip:
            return b
    return {}


def cds_of(cds: dict, tk: str) -> dict | None:
    c = (cds.get("levels_bp") or {}).get(tk)
    if not c:
        return None
    q, rng = c.get("quoted"), c.get("implied_range")
    if isinstance(q, list):
        txt, val = f"{q[0]:g}~{q[1]:g}", (q[0] + q[1]) / 2
    elif q is not None:
        txt, val = f"{q:g}", q
    elif rng:
        txt, val = f"~{rng[0]:g}~{rng[1]:g}(역산)", (rng[0] + rng[1]) / 2
    else:
        return {"txt": "미확인", "val": None, "asof": None, "news": c.get("note")}
    return {"txt": txt, "val": val, "asof": c.get("asof"), "news": c.get("news"), "ccy": c.get("ccy")}


def eod_series(eod: dict, key: str) -> list:
    """1년치(finra_eod_1y.json, [날짜, 가격, YTM]) 가 있으면 그걸, 없으면 10/17 스냅샷(finra_eod.json) 을 쓴다."""
    rows = (eod.get(key) or {}).get("eod") or []
    if rows and isinstance(rows[0], list):
        return [[d, round(px, 3), y] for d, px, y in rows if px]
    return [[r["tradeDate"], round(r["lastSalePrice"], 3), r.get("lastSaleYield")] for r in rows if r.get("lastSalePrice")]


# DC 본드 → 비교 기준 백커(임차·보증 주체). Beacon Point 는 임차인 비공개라 스폰서(Hut 8) 기준.
DC_SRC = {  # 기존 6종 출처(리스크_소스조사 §4)
    "DC_BEIGNET": ["https://www.ifre.com/ifr-awards/2327933/financing-package-blue-owl-capitalbeignet-investors-us27.3bn-23.6-year-bond"],
    "DC_SOPAIPILLA": ["https://www.globaldatacenterhub.com/p/blackrock-launches-123-billion-bond"],
    "DC_BEACONPT": ["https://www.sec.gov/Archives/edgar/data/1964789/000110465926070393/", "https://www.benzinga.com/node/53020821"],
    "HUT": ["https://www.sec.gov/Archives/edgar/data/0001964789/000110465926053247/tm2613163d1_8k.htm"],
    "DC_QTS_FAYETTEVILLE": ["https://www.paulhastings.com/news/paul-hastings-advises-the-initial-purchasers-on-qts-data-centers-usd4-6-billion-notes-offering"],
    "DC_RDMICH": ["https://www.kbra.com/publications/BNwvzDzR", "https://www.paulhastings.com/news/paul-hastings-advises-initial-purchasers-on-related-digitals-14-billion-project-bond-issuance-for-oracle-data-center-campus"],
}
DC_BACKER = {"DC_BEIGNET": "META", "DC_SOPAIPILLA": "META", "DC_RDMICH": "ORCL", "DC_QTS_FAYETTEVILLE": "MSFT", "HUT": "GOOGL", "DC_BEACONPT": "HUT"}


DC_GROUP = {"META": "Meta", "ORCL": "Oracle·MSFT", "MSFT": "Oracle·MSFT", "GOOGL": "Google backstop", "AMZN": "Amazon", "CRWV": "CoreWeave 임차"}


def norm_backer(t):
    """'NVDA(추정)' · 'CRWV / Alibaba' · '미확인(...)' → 첫 티커만, 미확인은 None"""
    if not t or str(t).startswith("미확인"):
        return None
    import re as _re
    m = _re.match(r"[A-Z]{2,5}", str(t))
    return m.group(0) if m else None


def _share(tk: str) -> dict | None:
    """최고 YTM 채권 발행액 ÷ 회사 총 부채(회사채+장기차입) — data/manual/bond_share.json (출처 포함, 수동 조사)"""
    p = ROOT / "data" / "manual" / "bond_share.json"
    if not p.exists():
        return None
    x = (json.loads(p.read_text(encoding="utf-8")).get("issuers") or {}).get(tk) or {}
    a, t = x.get("bond_amount_usd"), x.get("total_debt_usd")
    return {"amt": a, "total": t, "pct": round(a / t * 100, 1) if a and t else None,
            "basis": x.get("total_basis"), "src": x.get("total_src"), "note": x.get("note")}


def _cdsvol() -> dict | None:
    """하이퍼스케일러 CDS 일별 신규 체결 [건수, 명목 $M 하한, 상한 가림 건수] + 북미 IG CDX 5Y bp (risk_history.py cdsvol)"""
    p = SRC / "cds_vol.json"
    if not p.exists():
        return None
    v = json.loads(p.read_text(encoding="utf-8"))
    return {"names": v.get("names"), "fetched": v.get("fetched"),
            "days": [[d, x.get("vol") or {}, (x.get("cdxig") or {}).get("bp")] for d, x in sorted(v["days"].items())]}


def clean_cds(rows: list) -> list:
    """upfront 역산은 부호를 몰라 가끔 반대쪽 해가 섞인다 → 직전 5개 중앙값 대비 0.5배 미만·2배 초과 점은 뺀다."""
    out = []
    for r in rows:
        prev = sorted(x[1] for x in out[-5:])
        if len(prev) >= 3:
            m = prev[len(prev) // 2]
            if not (0.5 * m <= r[1] <= 2 * m):
                continue
        out.append(r)
    return out


def main() -> int:
    seed = json.loads((SRC / "risk_seed.json").read_text(encoding="utf-8"))
    f1y = SRC / "finra_eod_1y.json"
    eod = json.loads(f1y.read_text(encoding="utf-8"))["bonds"] if f1y.exists() else json.loads((SRC / "finra_eod.json").read_text(encoding="utf-8"))
    more = json.loads((SRC / "dc_more.json").read_text(encoding="utf-8")) if (SRC / "dc_more.json").exists() else {}
    backers = more.get("backers", {})
    ch = SRC / "cds_hist.json"
    cdsd = json.loads(ch.read_text(encoding="utf-8"))["days"] if ch.exists() else {}
    cds = seed.get("cds", {})
    issuers = []
    for tk in ISSUERS:
        iss = seed["issuers"].get(tk)
        if not iss:
            continue
        hb = iss.get("highest_yield_bond") or {}
        t = bond_terms(iss, hb.get("cusip"))
        r = iss.get("ratings") or {}
        issuers.append({
            "tk": tk, "name": iss.get("name", tk),
            "rating": {"m": r.get("moodys"), "sp": r.get("sp"), "f": r.get("fitch"), "act": r.get("latest_action"), "src": r.get("source"), "note": r.get("note")},
            "bond": {"cusip": hb.get("cusip"), "coupon": hb.get("coupon", t.get("coupon")), "maturity": hb.get("maturity", t.get("maturity")),
                     "amount": hb.get("amount_usd", t.get("amount_usd")), "price": hb.get("price_inst_median"), "ytm": hb.get("yield_inst_median"),
                     "g": hb.get("g_spread_bp_approx"), "asof": hb.get("asof"), "basis": hb.get("basis"), "note": hb.get("note"),
                     "is144a": t.get("is_144a"), "conv": tk == "NBIS"},
            "share": _share(tk),
            "cds": cds_of(cds, tk),
            "series": eod_series(eod, EOD_KEY.get(tk, tk)),
            "cds_series": clean_cds([[d, v[tk]["bp"], v[tk]["kind"][0]] for d, v in sorted(cdsd.items()) if tk in v]),
        })
    dc = []
    for b in seed["dc_project_bonds"]:
        lt = b.get("latest") or {}
        dc.append({"key": b["key"], "issuer": b["issuer"], "project": b.get("project"), "tenant": b.get("tenant_backer"),
                   "cusip": b.get("cusip_144a"), "coupon": b.get("coupon"), "maturity": b.get("maturity"), "amount": b.get("amount_usd"),
                   "rating": b.get("rating"), "price": lt.get("price_inst_median"), "ytm": lt.get("yield_inst_median"), "g": lt.get("g_spread_bp_approx"),
                   "asof": lt.get("asof"), "series": eod_series(eod, b["key"]), "backer": DC_BACKER.get(b["key"]), "src": DC_SRC.get(b["key"], [])})
    for b in more.get("bonds", []):
        if any(x["cusip"] == b.get("cusip") for x in dc):
            continue
        dc.append({"key": b["key"], "issuer": b.get("issuer"), "project": b.get("project"), "tenant": b.get("tenant"), "cusip": b.get("cusip"),
                   "coupon": b.get("coupon"), "maturity": b.get("maturity"), "amount": b.get("amount_usd"), "rating": b.get("rating"),
                   "price": b.get("price"), "ytm": b.get("yield"), "asof": b.get("asof"), "series": eod_series(eod, b["key"]),
                   "backer": norm_backer(b.get("backer_ticker")), "backer_raw": b.get("backer_ticker"), "added": True, "gpu": b.get("gpu_backed"),
                   "src": [u for u in (b.get("sources") or []) if str(u).startswith("http") and " " not in str(u)]})
    # ★ CRWV 한정(Jae 10/26): FINRA 일별이 아직 없는 날은 같은 채권 RegS판의 프랑크푸르트(FWB) 시세로 메운다(scripts/crwv_fwb.py).
    #   호가 성격이라 체결가와 1~2포인트 차이 가능 → 그날 FINRA 가 들어오면 FINRA 가 우선(FINRA 마지막 날 이후만 붙임).
    fwb = SRC / "crwv_fwb.json"
    FWB_DAYS: set = set()
    if fwb.exists():
        rows = json.loads(fwb.read_text(encoding="utf-8")).get("rows") or {}
        for i in issuers:
            if i["tk"] == "CRWV":
                last = i["series"][-1][0] if i["series"] else ""
                for d in sorted(rows):
                    if d > last:
                        i["series"].append([d, rows[d][0], rows[d][1]])
                        FWB_DAYS.add(d)
    # 표 값: 스냅샷(체결 중앙값)보다 FINRA 일별 종가가 더 최근이면 그걸로 바꾼다 → 매일 실행 시 표도 갱신
    def fresh(rec, ser):
        if ser and (not rec.get("asof") or ser[-1][0] > rec["asof"]):
            rec["asof"], rec["price"], rec["ytm"] = ser[-1][0], ser[-1][1], ser[-1][2]
            rec["basis"] = "FINRA 일별 종가(EOD)" if ser[-1][0] not in FWB_DAYS else "프랑크푸르트(FWB) 시세 — RegS판, 호가 성격(체결가 아님), FINRA 들어오면 교체"
            rec["fwb"] = ser[-1][0] in FWB_DAYS
    for i in issuers:
        fresh(i["bond"], i["series"])
    for d in dc:
        fresh(d, d["series"])
    # EOD(FINRA 일별)는 영업일 하루 더 늦다 → 표의 최신 체결 중앙값(asof)이 더 최근이면 선 끝에 이어 붙인다
    def tail(ser, asof, px, y):
        if asof and px and (not ser or ser[-1][0] < asof):
            ser.append([asof, round(px, 3), y])
    for i in issuers:
        tail(i["series"], i["bond"]["asof"], i["bond"]["price"], i["bond"]["ytm"])
    for d in dc:
        tail(d["series"], d.get("asof"), d.get("price"), d.get("ytm"))
    for d in dc:
        d["group"] = DC_GROUP.get(d.get("backer") or "", "기타·임차인 미확인")
        bk = backers.get(d.get("backer") or "") or {}
        tot = bk.get("total_debt_usd")
        d["backer_total"] = tot
        d["backer_pct"] = round(d["amount"] / tot * 100, 1) if tot and d.get("amount") else None
        d["backer_src"] = bk.get("concept", "") + (" " + bk.get("period_end", "") if bk.get("period_end") else "")
    hy = seed.get("hy_index", {})
    rec, cc = hy.get("recommended", {}), hy.get("cross_check", {})
    out = {
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "snapshot": seed.get("meta", {}).get("built"),
        "terms": seed.get("meta", {}).get("bond_data_terms"),
        "hy": {"hyg_oas": rec.get("value_bp"), "hyg_asof": rec.get("asof"), "hyg_ytm": (rec.get("also") or {}).get("avg_ytm_pct"),
               "jnk_oas": cc.get("JNK_OAS_bp"), "lqd_oas": cc.get("LQD_OAS_bp"), "lqd_asof": cc.get("LQD_asof"), "url": rec.get("url"), "jnk_url": cc.get("JNK_url")},
        "groups": GROUPS,
        "issuers": issuers,
        # 발행사 표에 없는 CDS 전용 종목(10/27): 차트에만
        "cds_more": {tk: clean_cds([[d, v[tk]["bp"], v[tk]["kind"][0]] for d, v in sorted(cdsd.items()) if tk in v]) for tk in ("AAPL", "TSLA", "NVDA", "AMD", "AVGO")},
        "dc": dc,
        "exposure": {k: {"sum_usd": v.get("sum_usd"), "sum_pct": v.get("sum_pct"), "n": len(v.get("bonds", [])),
                         "total": (backers.get(k) or {}).get("total_debt_usd"), "period": (backers.get(k) or {}).get("period_end"),
                         "off": (backers.get(k) or {}).get("off_balance")} for k, v in more.get("exposure", {}).items()},
        "dc_groups": ["Meta", "Oracle·MSFT", "Google backstop", "Amazon", "CoreWeave 임차", "기타·임차인 미확인"],
        "breadth": json.loads((SRC / "breadth.json").read_text(encoding="utf-8")) if (SRC / "breadth.json").exists() else None,
        "finra_blocked": (SRC / "FINRA_BLOCKED").read_text(encoding="utf-8").strip() if (SRC / "FINRA_BLOCKED").exists() else None,
        "stocks": json.loads((SRC / "stocks.json").read_text(encoding="utf-8")) if (SRC / "stocks.json").exists() else None,
        "fred": json.loads((SRC / "fred_credit.json").read_text(encoding="utf-8")) if (SRC / "fred_credit.json").exists() else None,
        "hysplit": json.loads((SRC / "hy_split_ledger.json").read_text(encoding="utf-8")) if (SRC / "hy_split_ledger.json").exists() else None,
        "debt": {k: {"fields": v["fields"], "rows": v["rows"]} for k, v in seed.get("neocloud_issuance", {}).items()},
        "cdsvol": _cdsvol(),
        "cds_src": cds.get("source"), "cds_method": cds.get("method"), "cds_caveat": cds.get("caveat"),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[risk] {OUT} ({OUT.stat().st_size/1024:.0f} KB) · 발행사 {len(issuers)} · DC 본드 {len(dc)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
