"""소매판매 세부 → data/retail.json (경제지표 탭 '소매판매 세부' 카드)

    python scripts/retail_data.py

- 원천: Census MARTS(월간 소매판매 속보) API — .env 의 CENSUS_KEY. 계절조정 판매액(SM, 백만달러). 키가 없으면 FRED 의 같은 시리즈.
- MoM·YoY·기여도는 판매액으로 직접 계산(보도자료 0.1% 반올림보다 자세함). YoY 도 계절조정 기준.
- 컨트롤그룹 = 전체(44X72) − 자동차·부품(441) − 건축자재(444) − 주유소(447) − 음식점(722)  (GDP 소비 계산에 쓰는 묶음)
- 주유소 물량 역산 = 주유소 판매액 MoM ÷ CPI 자동차 연료(SETB) MoM (cpi_dashboard/data/cpi.json). 편의점 상품이 섞여 있어 근사.
- 수정치: 직전 실행 때 값(data/retail_vintage.json)과 비교해 지난 두 달 MoM 이 얼마나 고쳐졌는지 남긴다.
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "retail.json"
VIN = ROOT / "data" / "retail_vintage.json"
API = "https://api.census.gov/data/timeseries/eits/marts"
MONTHS = 36

HEAD = [("44X72", "소매판매 (헤드라인)"), ("44Y72", "자동차 제외"), ("44Z72", "주유소 제외"), ("44W72", "자동차·주유소 제외"), ("CTRL", "컨트롤그룹")]
CATS = [("441", "자동차·부품"), ("447", "주유소"), ("722", "음식점·주점"), ("454", "무점포(온라인)"), ("452", "일반상품(백화점 등)"),
        ("445", "식료품점"), ("444", "건축자재·원예"), ("446", "건강·개인관리"), ("448", "의류"), ("443", "전자·가전"),
        ("442", "가구"), ("451", "스포츠·취미·서적"), ("453", "기타 소매")]


def key() -> str | None:
    env = ROOT / ".env"
    for line in (env.read_text(encoding="utf-8").splitlines() if env.exists() else []):
        if line.startswith("CENSUS_KEY="):
            return line.split("=", 1)[1].strip() or None
    return None


# 키가 없으면 FRED 로 같은 MARTS 숫자를 받는다(10/27 대조: 2026-09 17개 항목 Census 와 전부 일치). FRED 는 UA=curl 필요
FRED_ID = {"44X72": "RSAFS", "44Y72": "RSFSXMV", "44Z72": "MARTSSM44Z72USS", "44W72": "MARTSSM44W72USS", "441": "RSMVPD", "447": "RSGASS",
           "722": "RSFSDP", "454": "RSNSR", "452": "RSGMS", "445": "RSDBS", "444": "RSBMGESD", "446": "RSHPCS", "448": "RSCCAS",
           "443": "RSEAS", "442": "RSFHFS", "451": "RSSGHBMS", "453": "RSMSR"}


def fetch_fred(start: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for c, sid in FRED_ID.items():
        req = urllib.request.Request(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}-01", headers={"User-Agent": "curl/8.4.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            for line in r.read().decode("utf-8").splitlines()[1:]:
                d, _, v = line.partition(",")
                try:
                    out.setdefault(c, {})[d[:7]] = float(v)
                except ValueError:
                    pass
    return out


def fetch(start: str) -> dict[str, dict[str, float]]:
    k = key()
    if not k:
        print("[retail] .env 에 CENSUS_KEY 없음 → FRED 로 받음")
        return fetch_fred(start)
    q = urllib.parse.urlencode({"get": "cell_value,data_type_code,category_code,seasonally_adj", "time": f"from {start}", "key": k})
    with urllib.request.urlopen(urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "kr-flow-dashboard"}), timeout=120) as r:
        rows = json.loads(r.read().decode("utf-8"))
    h = rows[0]
    out: dict[str, dict[str, float]] = {}
    for x in rows[1:]:
        d = dict(zip(h, x))
        if d["data_type_code"] == "SM" and d["seasonally_adj"] == "yes":
            try:
                out.setdefault(d["category_code"], {})[d["time"]] = float(d["cell_value"])
            except ValueError:
                pass
    return out


def main() -> int:
    y = date.today().year
    S = fetch(f"{y - 4}-01")
    allm = sorted(S["44X72"])
    S["CTRL"] = {m: S["44X72"][m] - S["441"][m] - S["444"][m] - S["447"][m] - S["722"][m] for m in allm
                 if all(m in S[c] for c in ("441", "444", "447", "722"))}
    months = allm[-MONTHS:]

    def mom(c, m):
        a, i = S.get(c, {}), allm.index(m)
        p = allm[i - 1] if i else None
        return round((a[m] / a[p] - 1) * 100, 2) if p and m in a and p in a else None

    def yoy(c, m):
        a, (yy, mm) = S.get(c, {}), m.split("-")
        p = f"{int(yy) - 1}-{mm}"
        return round((a[m] / a[p] - 1) * 100, 2) if m in a and p in a else None

    def ann3(c, m):
        a, i = S.get(c, {}), allm.index(m)
        p = allm[i - 3] if i >= 3 else None
        return round(((a[m] / a[p]) ** 4 - 1) * 100, 2) if p and m in a and p in a else None

    def contrib(c, m):  # 전체 MoM 에 대한 기여(%p) = 업종 증가액 ÷ 전월 전체
        a, t, i = S.get(c, {}), S["44X72"], allm.index(m)
        p = allm[i - 1] if i else None
        return round((a[m] - a[p]) / t[p] * 100, 3) if p and m in a and p in a and p in t else None

    out = {"src": (API if key() else "FRED(Census MARTS 재게시)") + " (계절조정 판매액)", "months": months, "latest": months[-1], "fetched": date.today().isoformat(),
           "head": [{"code": c, "ko": k, "mom": [mom(c, m) for m in months], "yoy": [yoy(c, m) for m in months], "ann3": [ann3(c, m) for m in months]} for c, k in HEAD],
           "cats": [{"code": c, "ko": k, "mom": [mom(c, m) for m in months], "yoy": [yoy(c, m) for m in months],
                     "contrib": [contrib(c, m) for m in months], "share": round(S[c][months[-1]] / S["44X72"][months[-1]] * 100, 1)} for c, k in CATS if c in S]}
    # 주유소 물량 역산
    cp = ROOT / "cpi_dashboard" / "data" / "cpi.json"
    if cp.exists():
        c = json.loads(cp.read_text(encoding="utf-8"))
        cm = dict(zip(c["months"], c["series"]["SETB"]["mom"]))
        gas = [mom("447", m) for m in months]
        px = [cm.get(m) for m in months]
        out["gas"] = {"sales_mom": gas, "cpi_mom": [round(v, 2) if v is not None else None for v in px],
                      "vol_mom": [round(((1 + g / 100) / (1 + p / 100) - 1) * 100, 2) if g is not None and p is not None else None for g, p in zip(gas, px)]}
    # 수정치: 직전 실행 값과 비교
    old = json.loads(VIN.read_text(encoding="utf-8")) if VIN.exists() else {}
    rev = []
    if old.get("latest") and old["latest"] != months[-1]:
        for m in months[-3:-1]:
            o = (old.get("mom") or {}).get(m)
            n = mom("44X72", m)
            if o is not None and n is not None:
                rev.append({"month": m, "prev": o, "now": n, "diff": round(n - o, 2)})
        out["revision"] = {"vs": old["latest"], "rows": rev}
    elif old.get("revision"):
        out["revision"] = old["revision"]
    VIN.write_text(json.dumps({"latest": months[-1], "mom": {m: mom("44X72", m) for m in months}, "revision": out.get("revision")}, ensure_ascii=False), encoding="utf-8")
    h = out["head"]
    assert h[0]["mom"][-1] is not None, "헤드라인 최신값 없음"
    tot = sum(c["contrib"][-1] or 0 for c in out["cats"])
    assert abs(tot - h[0]["mom"][-1]) < 0.02, f"업종 기여 합 {tot:.3f} ≠ 헤드라인 {h[0]['mom'][-1]}"  # 13개 업종 = 소매판매 전체
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[retail] {months[-1]} 헤드라인 {h[0]['mom'][-1]}% · 주유소 제외 {h[2]['mom'][-1]}% · 컨트롤그룹 {h[4]['mom'][-1]}%"
          + (f" · 주유소 물량 {out['gas']['vol_mom'][-1]}%" if out.get("gas") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
