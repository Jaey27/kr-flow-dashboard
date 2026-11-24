# -*- coding: utf-8 -*-
"""시범 재채점(11단계) vs 기존 5단계 비교: 분포·천장 효과·백테스트(방향 적중·상관)

  python -X utf8 scripts/fedspeak/rescore_compare.py
"""
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from analyze import spearman

HERE = Path(__file__).resolve().parents[2] / "data" / "fedspeak"
a = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
new = {}
for f in sorted(glob.glob(str(HERE / "rescore" / "out_*.json"))):
    new.update(json.loads(Path(f).read_text(encoding="utf-8")))
items = [i for i in a["items"] if i["id"] in new]
print(f"재채점 {len(new)}건 · 원장과 매칭 {len(items)}건")

old = {i["id"]: i["score"] for i in items}            # 0/2.5/5/7.5/10
nw = {i["id"]: float(new[i["id"]]["s"]) for i in items}  # 0~10 정수
print("기존 분포", pd.Series(old).value_counts().sort_index().to_dict())
print("새 분포  ", pd.Series(nw).value_counts().sort_index().to_dict())
diff = pd.Series({k: nw[k] - old[k] for k in nw})
print("새−기존: 평균", round(diff.mean(), 2), "| 2점 넘게 벌어진 건", int((diff.abs() > 2).sum()))
pb = {k: v.get("path_bp") for k, v in new.items() if v.get("path_bp") is not None}
print("숫자(bp) 경로를 밝힌 발언", len(pb), "건")

grid = pd.DatetimeIndex(a["dates"])
mk = {k: pd.Series(a["market"][k], index=grid, dtype=float) for k in ("zq", "y2", "ndq")}
tdays = pd.DatetimeIndex(a["market_tdays"])
ev = {e["id"]: e for e in a["events"]}


def levels(score):
    sc = pd.DataFrame([dict(k=i["key"], d=pd.Timestamp(i["date"]), s=score[i["id"]]) for i in items])
    L = {}
    for k, g in sc.groupby("k"):
        s = g.groupby("d").s.mean().sort_index()
        vals = []
        for t in grid:
            p = s[s.index <= t]
            if p.empty:
                vals.append(np.nan)
                continue
            w = 0.5 ** (np.asarray((t - p.index).days, dtype=float) / 30)
            vals.append(float((p.values * w).sum() / w.sum()))
        L[k] = pd.Series(vals, index=grid)
    return pd.DataFrame(L)


def evaluate(score, tag):
    L = levels(score)
    rows = []
    for i in items:
        e = ev.get(i["id"])
        if not e or e.get("data_day") or (e.get("fomc_day") and i["key"] not in ("warsh", "powell")):
            continue
        prior = L[i["key"]].get(pd.Timestamp(i["date"]) - pd.Timedelta(days=1), np.nan)
        if np.isnan(prior):
            continue
        rows.append(dict(key=i["key"], grp=i["group"], surp=score[i["id"]] - prior, d_dec=e["d_dec"], d_y2=e["d_y2"]))
    E = pd.DataFrame(rows)
    out = {}
    for nm, sub in (("연준", E[E.grp != "political"]), ("트럼프·베센트", E[E.grp == "political"])):
        ok = sub.dropna(subset=["d_y2"])
        nz = ok[(ok.surp.abs() > 1e-9) & (ok.d_y2 != 0)]
        hit = (np.sign(nz.surp) == np.sign(nz.d_y2)).mean() * 100 if len(nz) else np.nan
        r1, p1 = spearman(ok.surp, ok.d_dec.fillna(0)) if len(ok) > 4 else (np.nan, np.nan)
        r2, p2 = spearman(ok.surp, ok.d_y2) if len(ok) > 4 else (np.nan, np.nan)
        out[nm] = dict(n=len(ok), 서프라이즈0아님=int((ok.surp.abs() > 1e-9).sum()), 방향적중=round(hit, 1), n_hit=len(nz),
                       rho_금리기대=round(r1, 3), p1=round(p1, 3), rho_2년물=round(r2, 3), p2=round(p2, 3))
    # 주간: 2026 투표권자 평균 변화 vs 금리 기대·나스닥
    v26 = [k for k, r in a["roster"].items() if r.get("v26") and k in L]
    idx = L[v26].mean(axis=1)
    wi = idx.resample("W-FRI").last().diff()
    for m in ("zq", "ndq"):
        wm = mk[m].resample("W-FRI").last()
        wm = wm.pct_change(fill_method=None) * 100 if m == "ndq" else wm.diff() * 100
        for lag in (0, -2):
            y = wm.shift(-lag)
            ok = wi.notna() & y.notna()
            r, p = spearman(wi[ok], y[ok])
            out[f"주간 투표권자 ↔ {m} (시차 {lag}주)"] = (round(r, 3), round(p, 3), int(ok.sum()))
    print(f"\n===== {tag}")
    for k, v in out.items():
        print(" ", k, v)
    return L


Lo = evaluate(old, "기존 5단계")
Ln = evaluate(nw, "새 11단계")
print("\n인물 현재 수준 (기존 → 새):")
for k in sorted(Ln.columns, key=lambda k: -(Ln[k].dropna().iloc[-1] if Ln[k].notna().any() else 0)):
    print(f"  {k:10} {Lo[k].dropna().iloc[-1]:.1f} → {Ln[k].dropna().iloc[-1]:.1f}")
