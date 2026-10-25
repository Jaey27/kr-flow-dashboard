"""고용 세부 → data/emp.json (경제지표 탭 '고용 세부' 카드)

    python scripts/emp_data.py

- 사업체 조사(CES): BLS 플랫파일 — 연락처 담긴 User-Agent 필수, Last-Modified 같으면 다시 받지 않음
    ce.data.01a.CurrentSeasAE                      비농업 고용·업종(계절조정, 천 명)
    ce.data.05b.TotalPrivate.AllEmployeeHoursAndEarnings  민간 시간당 임금·주당 근로시간
    ce.data.02b.AllRealEarningsAE                  실질 시간당 임금(1982-84 달러)
- 가계 조사(CPS): FRED(UA=curl) — 실업률 UNRATE · U-6 U6RATE · 참가율 CIVPART · 핵심연령(25~54) 고용률 LNS12300060
  (BLS 공개 API 는 'busy' 로 자주 막혀서 쓰지 않음, 10/25)
- 수정치: 직전 실행 값(data/emp_vintage.json)과 비교해 지난 두 달 고용 증감이 얼마나 고쳐졌는지 남긴다(BLS 는 매달 직전 2개월을 수정).
"""

from __future__ import annotations

import io
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "emp.json"
VIN = ROOT / "data" / "emp_vintage.json"
CACHE = ROOT / "data" / "emp_cache"
UA = "cpi-dashboard (pjy0992@gmail.com)"  # cpi_dashboard/scripts/fetch.py 와 같은 연락처
BLS = "https://download.bls.gov/pub/time.series/ce/"
FILES = ["ce.data.01a.CurrentSeasAE", "ce.data.05b.TotalPrivate.AllEmployeeHoursAndEarnings", "ce.data.02b.AllRealEarningsAE"]
MONTHS = 36

IND = [("CES0500000001", "민간 전체"), ("CES0600000001", "  재화 생산"), ("CES2000000001", "    건설"), ("CES3000000001", "    제조"),
       ("CES4200000001", "  소매"), ("CES4300000001", "  운송·창고"), ("CES5000000001", "  정보"), ("CES5500000001", "  금융"),
       ("CES6000000001", "  전문·사업서비스"), ("CES6056132001", "    임시직(temp help)"), ("CES6562000001", "  의료"),
       ("CES6500000001", "  교육·의료(사설)"), ("CES7000000001", "  여가·숙박·음식"), ("CES8000000001", "  기타 서비스"),
       ("CES9000000001", "정부"), ("CES9091000001", "  연방정부")]
FRED = {"ur": "UNRATE", "u6": "U6RATE", "lfpr": "CIVPART", "epop": "LNS12300060"}


def _get(url: str, ua: str, method: str = "GET"):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua}, method=method), timeout=180)


def bls_file(name: str) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    c = CACHE / name
    with _get(BLS + name, UA, "HEAD") as r:
        lm = r.headers.get("Last-Modified", "")
    if lm and c.exists() and c.read_text(encoding="utf-8").startswith(lm + "\n"):
        return c.read_text(encoding="utf-8").split("\n", 1)[1]
    with _get(BLS + name, UA) as r:
        body = r.read().decode("utf-8")
    c.write_text(lm + "\n" + body, encoding="utf-8")
    return body


def parse(text: str, want: set[str]) -> tuple[dict, dict]:
    S, prelim = {}, {}
    for line in text.splitlines()[1:]:
        p = [x.strip() for x in line.split("\t")]
        if len(p) < 4 or p[0] not in want or not p[2].startswith("M") or p[2] == "M13":
            continue
        m = f"{p[1]}-{p[2][1:]}"
        try:
            S.setdefault(p[0], {})[m] = float(p[3])
        except ValueError:
            continue
        if len(p) > 4 and "P" in p[4]:
            prelim.setdefault(p[0], set()).add(m)
    return S, prelim


def fred(sid: str, start: str) -> dict:
    with _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}", "curl/8.4.0") as r:
        rows = r.read().decode("utf-8").strip().splitlines()[1:]
    out = {}
    for row in rows:
        d, v = row.split(",")[:2]
        if v not in ("", "."):
            out[d[:7]] = float(v)
    return out


def main() -> int:
    want = {c for c, _ in IND} | {"CES0000000001", "CES0500000003", "CES0500000002", "CES0500000013"}
    S, prelim = {}, {}
    for f in FILES:
        a, b = parse(bls_file(f), want)
        S.update(a)
        for k, v in b.items():
            prelim.setdefault(k, set()).update(v)
    allm = sorted(S["CES0000000001"])
    months = allm[-MONTHS:]
    start = f"{int(months[0][:4]) - 1}-01-01"
    F = {k: fred(v, start) for k, v in FRED.items()}

    def chg(c, m):
        a, i = S.get(c, {}), allm.index(m)
        p = allm[i - 1] if i else None
        return round(a[m] - a[p], 1) if p and m in a and p in a else None

    def pct_mom(c, m):
        a, i = S.get(c, {}), allm.index(m)
        p = allm[i - 1] if i else None
        return round((a[m] / a[p] - 1) * 100, 2) if p and m in a and p in a else None

    def yoy(c, m):
        a, (y, mm) = S.get(c, {}), m.split("-")
        p = f"{int(y) - 1}-{mm}"
        return round((a[m] / a[p] - 1) * 100, 2) if m in a and p in a else None

    nfp = [chg("CES0000000001", m) for m in months]
    avg3 = [round(sum(nfp[i - 2:i + 1]) / 3, 1) if i >= 2 and None not in nfp[i - 2:i + 1] else None for i in range(len(nfp))]
    out = {"src": "BLS CES 플랫파일 · FRED(UNRATE·U6RATE·CIVPART·LNS12300060)", "months": months, "latest": months[-1], "fetched": date.today().isoformat(),
           "prelim": sorted(prelim.get("CES0000000001", set()) & set(months)),
           "nfp": nfp, "nfp_avg3": avg3, "private": [chg("CES0500000001", m) for m in months],
           "ahe_mom": [pct_mom("CES0500000003", m) for m in months], "ahe_yoy": [yoy("CES0500000003", m) for m in months],
           "real_yoy": [yoy("CES0500000013", m) for m in months], "hours": [S.get("CES0500000002", {}).get(m) for m in months],
           "cps": {k: [v.get(m) for m in months] for k, v in F.items()},
           "ind": [{"code": c, "ko": k, "chg": [chg(c, m) for m in months], "lvl": S.get(c, {}).get(months[-1])} for c, k in IND if c in S]}
    old = json.loads(VIN.read_text(encoding="utf-8")) if VIN.exists() else {}
    if old.get("latest") and old["latest"] != months[-1]:
        rows = []
        for m in months[-3:-1]:
            o, n = (old.get("nfp") or {}).get(m), chg("CES0000000001", m)
            if o is not None and n is not None:
                rows.append({"month": m, "prev": o, "now": n, "diff": round(n - o, 1)})
        out["revision"] = {"vs": old["latest"], "rows": rows, "sum": round(sum(r["diff"] for r in rows), 1)}
    elif old.get("revision"):
        out["revision"] = old["revision"]
    VIN.write_text(json.dumps({"latest": months[-1], "nfp": {m: chg("CES0000000001", m) for m in months}, "revision": out.get("revision")}, ensure_ascii=False), encoding="utf-8")
    assert nfp[-1] is not None and out["cps"]["ur"][-1] is not None, "최신 고용·실업률 없음"
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[emp] {months[-1]} 비농업 {nfp[-1]:+.0f}천 (3개월 평균 {avg3[-1]:+.0f}) · 실업률 {out['cps']['ur'][-1]}% · 시간당 임금 MoM {out['ahe_mom'][-1]}% YoY {out['ahe_yoy'][-1]}% · 실질 YoY {out['real_yoy'][-1]}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
