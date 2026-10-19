"""CPI 대시보드 데이터 빌드.

  python build_cpi.py            # 수집 + 계산 + data/cpi.json + data/cpi_data.xlsx
  python build_cpi.py --offline  # 캐시만 사용

계산 규칙
- 전월비(MoM): 계절조정(SA). 계절조정 시리즈가 없는 항목은 원계열(NSA).
- 전년비(YoY): 원계열(NSA).
- 3·6개월 연율: SA 지수 기준 ((I_t / I_t-3)^4 - 1).
- 가중치: 매년 1월 상대중요도(3월 발표문 표1·2)를 기준점으로, 월별 가격 변화로 갱신
    w_i,t = w_i,Jan × (I_i,t / I_i,Jan) / (I_all,t / I_all,Jan)   (NSA 지수)
- 기여도(전월비) = w_i,t-1 × MoM_i,t / 100        → 헤드라인 기준 %p
  근원 기준 = w_i,t-1 / w_core,t-1 × MoM_i,t
- 기여도(전년비) = w_i,t-12 × YoY_i,t / 100 (근사)
- 잔여 = 발표치 - 항목 합 → '기타(잔여)'로 표시해 합계를 발표치와 맞춘다.
"""
import json
import math
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import fetch
import items as I

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
START = "2020-01"          # 계산용 시작 (YoY·6개월 연율 확보)
VIEW_YEARS = 5             # 화면 기본 기간

OFFLINE = "--offline" in sys.argv


def months_between(a, b):
    y, m = map(int, a.split("-"))
    out = []
    while f"{y}-{m:02d}" <= b:
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def shift(ym, k):
    y, m = map(int, ym.split("-"))
    t = y * 12 + (m - 1) + k
    return f"{t // 12}-{t % 12 + 1:02d}"


def r(x, n=4):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(x, n)


def main():
    t0 = datetime.now(timezone.utc)
    item_codes = [i["code"] for i in I.ITEMS if not i.get("derived")]
    child_codes = [c["code"] for c in I.CHILDREN]
    agg_codes = [a[0] for a in I.AGGREGATES]
    all_codes = agg_codes + item_codes + child_codes

    print("BLS 플랫파일 수집…")
    bls = fetch.fetch_bls_flat(all_codes, offline=OFFLINE)
    S = bls["series"]
    latest = max(k for k in S["CUUR0000SA0"])
    months = months_between(START, latest)

    def lv(prefix, code, ym):
        return S.get(prefix + code, {}).get(ym)

    sa_avail = {c: ("CUSR0000" + c) in S for c in all_codes}

    def sa(c, ym):
        return lv("CUSR0000" if sa_avail[c] else "CUUR0000", c, ym)

    def nsa(c, ym):
        return lv("CUUR0000", c, ym)

    # ---------- 가중치 ----------
    print("가중치…")
    W = fetch.fetch_weights(offline=OFFLINE)
    years = sorted(W)
    name_of = {a[0]: a[1] for a in I.AGGREGATES}
    name_of.update({i["code"]: i["t2"] for i in I.ITEMS if i.get("t2")})
    name_of.update({c["code"]: c["t2"] for c in I.CHILDREN})

    def anchor(code, y):
        """연도 y의 1월 상대중요도. 없으면 가까운 연도 값을 지수 비율로 환산."""
        yy = min(max(y, years[0]), years[-1])
        nm = name_of[code]
        if nm in W[yy]:
            return W[yy][nm], yy
        for d in range(1, 6):
            for cand in (yy - d, yy + d):
                if cand in W and nm in W[cand]:
                    return W[cand][nm], cand
        return None, None

    weight = {c: {} for c in all_codes}
    for c in all_codes:
        for ym in months:
            y = int(ym[:4])
            # t의 가중치는 그해 기준점에서. 12월은 다음 해 1월 변화의 기준이므로 계산 시 별도 처리
            a, ay = anchor(c, y)
            if a is None:
                continue
            base = f"{ay}-01" if ay == y else f"{ay}-01"
            i0, a0 = nsa(c, base), nsa("SA0", base)
            it, at = nsa(c, ym), nsa("SA0", ym)
            if None in (i0, a0, it, at):
                continue
            weight[c][ym] = a * (it / i0) / (at / a0)

    def w_at(c, ym, at):
        """ym이 속한 해의 1월 기준점으로 계산한 at 시점 가중치 (전월비 기여도·체인용)."""
        a, ay = anchor(c, int(ym[:4]))
        if a is None:
            return None
        base = f"{ay}-01"
        i0, a0 = nsa(c, base), nsa("SA0", base)
        it, at_ = nsa(c, at), nsa("SA0", at)
        if None in (i0, a0, it, at_):
            return None
        return a * (it / i0) / (at_ / a0)

    def w_prev(c, ym):
        return w_at(c, ym, shift(ym, -1))

    def prev_avail(ym):
        """직전 발표월 (2025-10 같은 결측월은 건너뜀)."""
        p = shift(ym, -1)
        return p if nsa("SA0", p) is not None else shift(ym, -2)

    # ---------- 기본 지표 ----------
    def pct(a, b):
        return None if a is None or b is None else (a / b - 1) * 100

    series = {}

    def sa_i(c, ym):
        """연율 계산용 SA 지수 — 결측월(2025-10)은 앞뒤 기하평균으로 보간."""
        v = sa(c, ym)
        if v is None:
            a, b = sa(c, shift(ym, -1)), sa(c, shift(ym, 1))
            v = None if None in (a, b) else (a * b) ** 0.5
        return v

    def base_metrics(c):
        out = {"mom": {}, "yoy": {}, "ann3": {}, "ann6": {}, "w": {}, "wp": {}}
        for ym in months:
            out["mom"][ym] = pct(sa(c, ym), sa(c, shift(ym, -1)))
            out["yoy"][ym] = pct(nsa(c, ym), nsa(c, shift(ym, -12)))
            a3, a6 = sa(c, ym), sa_i(c, shift(ym, -3))
            out["ann3"][ym] = None if None in (a3, a6) else ((a3 / a6) ** 4 - 1) * 100
            b6 = sa_i(c, shift(ym, -6))
            out["ann6"][ym] = None if None in (a3, b6) else ((a3 / b6) ** 2 - 1) * 100
            out["w"][ym] = weight[c].get(ym)
            out["wp"][ym] = w_prev(c, ym)
        return out

    for c in all_codes:
        series[c] = base_metrics(c)

    # ---------- 파생 시리즈 (가중치 차감) ----------
    def derive(code, base, minus):
        """base 에서 minus 항목들을 가중치로 차감한 시리즈. 결측월은 건너뛰어 체인을 잇는다."""
        out = {"mom": {}, "yoy": {}, "ann3": {}, "ann6": {}, "w": {}, "wp": {}}
        idx_sa, idx_nsa = {}, {}
        parts = [base] + minus
        for k, ym in enumerate(months):
            wc = [weight[c].get(ym) for c in parts]
            out["w"][ym] = None if None in wc else wc[0] - sum(wc[1:])
            if k == 0:
                idx_sa[ym] = idx_nsa[ym] = 100.0
                out["mom"][ym] = out["wp"][ym] = None
                continue
            for idx, fn, key in ((idx_sa, sa, "mom"), (idx_nsa, nsa, None)):
                # 구성 항목이 모두 있는 직전 월 (결측월 최대 3개월 건너뜀)
                p = next((q for q in (shift(ym, -j) for j in (1, 2, 3))
                          if idx.get(q) is not None and all(fn(c, q) is not None for c in parts)),
                         shift(ym, -1))
                ws = [w_at(c, ym, p) for c in parts]
                if key:
                    out["wp"][ym] = None if None in ws else ws[0] - sum(ws[1:])
                ch = [pct(fn(c, ym), fn(c, p)) for c in parts]
                if None in ch + ws or idx.get(p) is None:
                    idx[ym] = None
                    d = None
                else:
                    d = (ws[0] * ch[0] - sum(w * x for w, x in zip(ws[1:], ch[1:]))) / (ws[0] - sum(ws[1:]))
                    idx[ym] = idx[p] * (1 + d / 100)
                if key:
                    out["mom"][ym] = d if p == shift(ym, -1) else None
        for idx in (idx_sa, idx_nsa):   # 결측월 기하평균 보간 (연율·체인용)
            for ym in months[1:-1]:
                if idx.get(ym) is None and idx.get(shift(ym, -1)) and idx.get(shift(ym, 1)):
                    idx[ym] = (idx[shift(ym, -1)] * idx[shift(ym, 1)]) ** 0.5
        for ym in months:
            out["yoy"][ym] = pct(idx_nsa.get(ym), idx_nsa.get(shift(ym, -12))) if nsa("SA0", ym) else None
            a3, a6, b6 = idx_sa.get(ym), idx_sa.get(shift(ym, -3)), idx_sa.get(shift(ym, -6))
            out["ann3"][ym] = None if None in (a3, a6) else ((a3 / a6) ** 4 - 1) * 100
            out["ann6"][ym] = None if None in (a3, b6) else ((a3 / b6) ** 2 - 1) * 100
        return out

    for code, ko, base, minus, desc in I.DERIVED:
        series[code] = derive(code, base, minus)

    # ---------- 기여도 ----------
    core_items = [i for i in I.ITEMS if i["bucket"] not in ("food", "energy")]
    contrib = {}  # code -> {mom_h, mom_c, yoy_h, yoy_c}
    for it in I.ITEMS:
        c = it["code"]
        s = series[c]
        d = {"mom_h": {}, "mom_c": {}, "yoy_h": {}, "yoy_c": {}}
        is_core = it["bucket"] not in ("food", "energy")
        for ym in months:
            wp, m = s["wp"][ym], s["mom"][ym]
            wcore = series["SA0L1E"]["wp"][ym]
            d["mom_h"][ym] = None if None in (wp, m) else wp * m / 100
            d["mom_c"][ym] = None if (None in (wp, m, wcore) or not is_core) else wp / wcore * m
            w12, y12 = s["w"].get(shift(ym, -12)), s["yoy"][ym]
            wc12 = series["SA0L1E"]["w"].get(shift(ym, -12))
            d["yoy_h"][ym] = None if None in (w12, y12) else w12 * y12 / 100
            d["yoy_c"][ym] = None if (None in (w12, y12, wc12) or not is_core) else w12 / wc12 * y12
        contrib[c] = d

    # 잔여(발표치 - 항목 합)
    resid = {"mom_h": {}, "mom_c": {}, "yoy_h": {}, "yoy_c": {}}
    for ym in months:
        for key, tot_code, pool in (("mom_h", "SA0", I.ITEMS), ("mom_c", "SA0L1E", core_items),
                                    ("yoy_h", "SA0", I.ITEMS), ("yoy_c", "SA0L1E", core_items)):
            tot = series[tot_code]["mom" if key.startswith("mom") else "yoy"][ym]
            parts = [contrib[i["code"]][key][ym] for i in pool]
            # 결측 항목은 잔여에 흡수
            resid[key][ym] = None if tot is None else tot - sum(p for p in parts if p is not None)

    # ---------- 일회성 플래그 (전월비 z-score, 직전 12개월 기준) ----------
    def flags_for(mom):
        z, st = {}, {}
        for k, ym in enumerate(months):
            x = mom.get(ym)
            hist = [mom.get(shift(ym, -j)) for j in range(1, 13)]
            hist = [h for h in hist if h is not None]
            if x is None or len(hist) < 8:
                z[ym] = None
                continue
            mu = sum(hist) / len(hist)
            sd = (sum((h - mu) ** 2 for h in hist) / (len(hist) - 1)) ** 0.5 or 1e-9
            z[ym] = (x - mu) / sd
        for ym in months:
            zz, zp = z.get(ym), z.get(shift(ym, -1))
            s = None
            if zz is not None and abs(zz) >= 2:
                s = "spike_up" if zz > 0 else "spike_down"
            elif zp is not None and abs(zp) >= 2 and zz is not None:
                s = "persist" if (zz >= 1 if zp > 0 else zz <= -1) else "revert"
            st[ym] = s
        return z, st

    flags = {}
    for c in list(series):
        z, st = flags_for(series[c]["mom"])
        flags[c] = {"z": z, "st": st}

    # ---------- 확산도 (주요 근원 항목 기준) ----------
    diffusion = {"up": {}, "hot": {}}
    for ym in months:
        tot = up = hot = 0.0
        for it in core_items:
            s = series[it["code"]]
            w, m = s["wp"][ym], s["mom"][ym]
            if w is None or m is None:
                continue
            tot += w
            up += w if m > 0 else 0
            hot += w if m > 0.247 else 0   # 연율 3% 초과
        diffusion["up"][ym] = up / tot * 100 if tot else None
        diffusion["hot"][ym] = hot / tot * 100 if tot else None

    # ---------- 외부 보조 CPI ----------
    print("연은 보조지표…")
    ext = {}
    try:
        cle = fetch.fetch_cleveland(offline=OFFLINE)
        stk = fetch.fetch_sticky(offline=OFFLINE)
        raw_ext = {"median": ("클리블랜드 중위 CPI", cle["median"],
                              "https://www.clevelandfed.org/indicators-and-data/median-cpi"),
                   "trim": ("클리블랜드 16% 절사평균 CPI", cle["trim"],
                            "https://www.clevelandfed.org/indicators-and-data/median-cpi"),
                   "sticky": ("애틀랜타 끈적한(sticky) CPI", stk["sticky"],
                              "https://www.atlantafed.org/research-and-data/data/sticky-price-cpi"),
                   "core_sticky_xs": ("애틀랜타 근원 sticky CPI (주거 제외)", stk["core_sticky_xs"],
                                      "https://www.atlantafed.org/research-and-data/data/sticky-price-cpi")}
        for k, (ko, ser, url) in raw_ext.items():
            idx, prev = {}, None
            for ym in months_between("2018-01", latest):
                m = ser.get(ym)
                if prev is None:
                    idx[ym] = 100.0
                elif m is not None and idx.get(prev) is not None:
                    idx[ym] = idx[prev] * (1 + m)
                else:
                    idx[ym] = None
                prev = ym
            e = {"ko": ko, "url": url, "mom": {}, "yoy": {}, "ann3": {}, "ann6": {}}
            for ym in months:
                m = ser.get(ym)
                e["mom"][ym] = None if m is None else m * 100
                e["yoy"][ym] = pct(idx.get(ym), idx.get(shift(ym, -12)))
                a, b3, b6 = idx.get(ym), idx.get(shift(ym, -3)), idx.get(shift(ym, -6))
                e["ann3"][ym] = None if None in (a, b3) else ((a / b3) ** 4 - 1) * 100
                e["ann6"][ym] = None if None in (a, b6) else ((a / b6) ** 2 - 1) * 100
            e["latest"] = max((k2 for k2, v in ser.items() if v is not None), default=None)
            ext[k] = e
    except Exception as ex:  # 외부 지표 실패는 대시보드 전체를 막지 않는다
        print("  외부 지표 실패:", ex)

    # ---------- 컨센서스·FOMC ----------
    print("컨센서스·FOMC…")
    consensus, fomc = {}, []
    try:
        cal = fetch.fetch_tv_calendar(offline=OFFLINE)
        keymap = {"Inflation Rate MoM": "h_mom", "Inflation Rate YoY": "h_yoy",
                  "Core Inflation Rate MoM": "c_mom", "Core Inflation Rate YoY": "c_yoy"}
        for e in cal:
            if e["title"] in keymap:
                ref = (e.get("referenceDate") or "")[:7]
                if not ref:
                    continue
                consensus.setdefault(ref, {})[keymap[e["title"]]] = {
                    "f": e.get("forecast"), "a": e.get("actual"), "date": e["date"]}
            elif e["title"] == "Fed Interest Rate Decision" and e.get("actual") is not None:
                fomc.append({"date": e["date"][:10], "rate": e["actual"], "prev": e.get("previous")})
    except Exception as ex:
        print("  캘린더 실패:", ex)
    manual = DATA / "manual" / "consensus.json"   # 수동 보정(있으면 우선)
    if manual.exists():
        for ref, v in json.loads(manual.read_text(encoding="utf-8")).items():
            consensus.setdefault(ref, {}).update(v)

    # ---------- 발표 일정 ----------
    try:
        sched = fetch.fetch_schedule(offline=OFFLINE)
    except Exception:
        sched = []

    # ---------- 메타 + JSON ----------
    meta = []
    for code, ko, *_ in [(a[0], a[2]) for a in I.AGGREGATES]:
        meta.append({"code": code, "ko": ko, "type": "agg", "sa": sa_avail[code]})
    for code, ko, base, minus, desc in I.DERIVED:
        meta.append({"code": code, "ko": ko, "type": "derived", "desc": desc, "sa": True,
                     "formula": f"{base} − " + " − ".join(minus)})
    for it in I.ITEMS:
        meta.append({"code": it["code"], "ko": it["ko"], "en": it.get("t2"), "type": "item",
                     "bucket": it["bucket"], "kind": it["kind"], "desc": it["desc"],
                     "sa": sa_avail.get(it["code"], True), "derived": bool(it.get("derived"))})
    for ch in I.CHILDREN:
        meta.append({"code": ch["code"], "ko": ch["ko"], "en": ch["t2"], "type": "child",
                     "parent": ch["parent"], "desc": ch["desc"], "sa": sa_avail[ch["code"]]})

    def pack(d):
        return [r(d.get(ym)) for ym in months]

    out = {
        "generated_at": t0.isoformat(),
        "bls_last_modified": bls.get("last_modified"),
        "latest": latest,
        "months": months,
        "view_start": shift(latest, -VIEW_YEARS * 12 + 1),
        "meta": meta,
        "buckets": [{"key": k, "ko": ko, "color": col, "desc": I.BUCKET_DESC[k]} for k, ko, col in I.BUCKETS],
        "series": {c: {k: pack(v) for k, v in s.items() if k in ("mom", "yoy", "ann3", "ann6", "w")}
                   for c, s in series.items()},
        "contrib": {c: {k: pack(v) for k, v in d.items()} for c, d in contrib.items()},
        "resid": {k: pack(v) for k, v in resid.items()},
        "flags": {c: {"z": [r(f["z"].get(ym), 2) for ym in months], "st": [f["st"].get(ym) for ym in months]}
                  for c, f in flags.items()},
        "diffusion": {k: pack(v) for k, v in diffusion.items()},
        "ext": {k: {"ko": e["ko"], "url": e["url"], "latest": e["latest"],
                    **{m: pack(e[m]) for m in ("mom", "yoy", "ann3", "ann6")}} for k, e in ext.items()},
        "consensus": consensus,
        "fomc": [f for f in fomc if f["date"] >= START],
        "schedule": sched,
        "notes": [
            {"month": "2025-10", "text": "2025년 10월 CPI 미발표 (연방정부 셧다운으로 가격 미수집). 10월·11월 전월비와 10월 전년비가 없다."},
            {"month": "2026-04", "text": "2025년 10월에 조사 못 한 주거비 표본 그룹을 6개월 만에 재조사 → 셧다운 왜곡 해소 (BLS)."},
            {"month": "2026-10", "text": "같은 주거비 표본 그룹 재조사 시점. 2025년 10월 결측 영향이 다시 나타날 수 있다."},
        ],
    }
    (DATA / "cpi.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"cpi.json 저장: 최신 {latest}, {len(months)}개월")

    import excel
    excel.write(out, DATA / "cpi_data.xlsx")
    print("cpi_data.xlsx 저장")


if __name__ == "__main__":
    main()
