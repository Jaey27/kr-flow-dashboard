"""PPI(생산자물가) 세부 → data/ppi.json (경제지표 탭 'PPI 세부' 카드)

    python scripts/ppi_data.py

- 원천: BLS 플랫파일 wp.data.22.FD-ID (최종수요·중간수요, CPI와 같은 download.bls.gov). 연락처 담긴 User-Agent 필수.
- 파일 Last-Modified 가 캐시와 같으면 다시 받지 않는다(월 1회 발표, 매일 실행해도 부담 없음).
- MoM 은 계절조정(WPS…), YoY 는 원계열(WPU…) — BLS 보도자료와 같은 관례.
- 파이프라인 마지막 칸 'CPI 근원상품'은 cpi_dashboard/data/cpi.json 의 SACL1E YoY 를 그대로 쓴다.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "ppi.json"
CACHE = ROOT / "data" / "ppi_cache.txt"
URL = "https://download.bls.gov/pub/time.series/wp/wp.data.22.FD-ID"
UA = "cpi-dashboard (pjy0992@gmail.com)"  # cpi_dashboard/scripts/fetch.py 와 같은 연락처
MONTHS = 36

# (코드 뒷부분, 한국어 이름) — 앞에 WPS(계절조정)·WPU(원계열)를 붙인다
HEAD = [
    ("FD4", "최종수요 (헤드라인)"),
    ("FD49104", "식품·에너지 제외 (근원)"),
    ("FD49116", "식품·에너지·무역서비스 제외"),
    ("FD41", "최종수요 상품"),
    ("FD411", "  식품"),
    ("FD412", "  에너지"),
    ("FD413", "  식품·에너지 제외 상품"),
    ("FD42", "최종수요 서비스"),
    ("FD423", "  무역서비스(유통마진)"),
    ("FD422", "  운송·창고"),
    ("FD421", "  그 외 서비스"),
]
PIPE = [  # 원자재 → 중간재 → 최종재 → CPI
    ("ID622", "비식품 원자재(중간수요)"),
    ("ID61", "중간재 가공품"),
    ("ID611", "제조용 자재·부품"),
    ("FD41311", "최종 소비재(식품·에너지 제외)"),
]
MARGIN = [("FD423", "무역서비스 전체"), ("FD42311", "소비재 유통")]


def fetch() -> str:
    req = urllib.request.Request(URL, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as r:
        lm = r.headers.get("Last-Modified", "")
    if CACHE.exists() and CACHE.read_text(encoding="utf-8").startswith(lm + "\n") and lm:
        return CACHE.read_text(encoding="utf-8").split("\n", 1)[1]
    with urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": UA}), timeout=180) as r:
        body = r.read().decode("utf-8")
    CACHE.write_text(lm + "\n" + body, encoding="utf-8")
    return body


def main() -> int:
    raw = fetch()
    lm = CACHE.read_text(encoding="utf-8").split("\n", 1)[0]
    want = {"WPS" + c for c, _ in HEAD + PIPE + MARGIN} | {"WPU" + c for c, _ in HEAD + PIPE + MARGIN}
    S: dict[str, dict[str, float]] = {}
    for line in raw.splitlines()[1:]:
        p = [x.strip() for x in line.split("\t")]
        if len(p) < 4 or p[0] not in want or not p[2].startswith("M") or p[2] == "M13":
            continue
        try:
            S.setdefault(p[0], {})[f"{p[1]}-{p[2][1:]}"] = float(p[3])
        except ValueError:
            pass
    allm = sorted(set().union(*[v.keys() for v in S.values()]))
    months = allm[-MONTHS:]

    def mom(code, m):
        a = S.get("WPS" + code, {})
        i = allm.index(m)
        return round((a[m] / a[allm[i - 1]] - 1) * 100, 2) if i > 0 and m in a and allm[i - 1] in a else None

    def yoy(code, m):
        a = S.get("WPU" + code, {})
        y, mo = m.split("-")
        p = f"{int(y) - 1}-{mo}"
        return round((a[m] / a[p] - 1) * 100, 2) if m in a and p in a else None

    def ann3(code, m):
        a = S.get("WPS" + code, {})
        i = allm.index(m)
        return round(((a[m] / a[allm[i - 3]]) ** 4 - 1) * 100, 2) if i >= 3 and m in a and allm[i - 3] in a else None

    out = {"src": URL, "bls_last_modified": lm, "months": months, "latest": months[-1],
           "head": [{"code": c, "ko": k, "mom": [mom(c, m) for m in months], "yoy": [yoy(c, m) for m in months],
                     "ann3": [ann3(c, m) for m in months]} for c, k in HEAD],
           "pipe": [{"code": c, "ko": k, "yoy": [yoy(c, m) for m in months]} for c, k in PIPE],
           "margin": [{"code": c, "ko": k, "mom": [mom(c, m) for m in months]} for c, k in MARGIN]}
    # CPI 근원상품(SACL1E) YoY — cpi_dashboard 결과 재사용
    cp = ROOT / "cpi_dashboard" / "data" / "cpi.json"
    if cp.exists():
        c = json.loads(cp.read_text(encoding="utf-8"))
        cm = dict(zip(c["months"], c["series"]["SACL1E"]["yoy"]))
        out["pipe"].append({"code": "CPI SACL1E", "ko": "CPI 근원상품", "yoy": [round(cm[m], 2) if cm.get(m) is not None else None for m in months]})
    # 불변식: 헤드라인 최신 MoM 이 있어야 함
    h = out["head"][0]
    assert h["mom"][-1] is not None and h["yoy"][-1] is not None, "헤드라인 최신값 없음"
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[ppi] {months[-1]} 헤드라인 MoM {h['mom'][-1]}% YoY {h['yoy'][-1]}% · 근원 MoM {out['head'][1]['mom'][-1]}% · BLS {lm}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
