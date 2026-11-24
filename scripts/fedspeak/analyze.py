# -*- coding: utf-8 -*-
"""연준 발언 원장 → 톤 지수 + 시장 가격과의 백테스트 → analysis.json

  python -X utf8 analyze.py

눈금(Jae 11/23): 10 = 매파, 5 = 중도, 0 = 비둘기파. 소수 첫째 자리.
  원장(ledger.json)의 점수는 −2~+2 다섯 단계 → 화면 점수 = 5 + 2.5 × 원장 점수 (0 / 2.5 / 5 / 7.5 / 10).
인물 수준 L_i(t): 그 인물의 발언 점수를 반감기 HALF일로 지수 가중 평균(마지막 발언 이후엔 그대로 유지).
위원회 지수: 그 시점 재임 중인 2026 투표권자 L_i의 단순 평균(의장 3배 가중판 병기).
시장: 연방기금 선물 2027년 1월물 내재 금리(= 12/9 회의 뒤 금리 기대, 1년치), kr-flow 대시보드 FedWatch 원장(4월~), 2년물, Kalshi.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import math


def _t_sf2(t: float, df: int) -> float:
    """t 분포 양측 p값(심프슨 적분). scipy 없이 돌리려고 직접 계산(맥미니 venv)."""
    t = abs(t)
    if t > 1e6:
        return 0.0
    f = lambda x: (1 + x * x / df) ** (-(df + 1) / 2)  # noqa: E731
    def simp(a, b, n=4000):
        h = (b - a) / n
        s = f(a) + f(b) + sum(f(a + i * h) * (4 if i % 2 else 2) for i in range(1, n))
        return s * h / 3
    tail, whole = simp(t, t + 400), simp(0, 400)
    return min(1.0, tail / whole)


def spearman(x, y):
    rx, ry = pd.Series(list(x)).rank(), pd.Series(list(y)).rank()
    r = float(rx.corr(ry))
    n = len(rx)
    if math.isnan(r):
        return r, 1.0
    if abs(r) >= 0.9999 or n < 3:
        return r, 0.0 if n >= 3 else 1.0
    return r, _t_sf2(r * math.sqrt((n - 2) / (1 - r * r)), n - 2)

from pipeline import ROSTER, START, END

HERE = Path(__file__).resolve().parents[2] / "data" / "fedspeak"  # 원장·덮어쓰기·요약(리포에 커밋)
REPO = Path(__file__).resolve().parents[2]
HALF = 30  # 일
OKV = ("exact", "near", "agent_ok", "notion")
DATA_REL = ("CPI", "NFP", "PCE", "PPI", "RETAIL")
CUTOFF = "15:00"  # 이 시각(ET) 이후 발언은 다음 거래일 반응으로 본다
MIN_N = 5
HAWK_T, DOVE_T = 6.25, 3.75  # 이 선 밖이면 매파 쪽 / 비둘기파 쪽으로 셈
FIRM_ALIAS = {"BofA Global Research": "Bank of America", "JPMorgan": "J.P. Morgan",
              "Goldman Sachs Global Banking & Markets (rates sales)": "Goldman Sachs (rates sales)"}
CHAIR_SWITCH = ("2026-05-15", "2026-05-22")  # 파월 의장 임기 끝 / 워시 취임


def disp(raw):
    return None if raw is None else 5 + 2.5 * raw


def g7(it) -> str:
    r = ROSTER.get(it["key"])
    if r is None:
        return it["group"]
    if r["group"] == "voter":
        return "v26"
    if r["group"] == "nonvoter":
        return "v27" if r.get("v27") else "nv"
    return r["group"]


def load_market():
    m = json.loads((REPO / "data" / "macro.json").read_text(encoding="utf-8"))
    df = pd.DataFrame(m["series"], index=pd.to_datetime(m["dates"]))
    ef = json.loads((HERE / "market" / "effr.json").read_text(encoding="utf-8"))["refRates"]
    effr = pd.Series({pd.Timestamp(r["effectiveDate"]): r["percentRate"] for r in ef}).sort_index()
    r0 = effr.reindex(df.index.union(effr.index)).ffill().reindex(df.index)
    out = pd.DataFrame(index=df.index)
    out["effr"] = r0
    out["dec_bp"] = pd.to_numeric(df.get("fw_20261209"), errors="coerce")
    out["dec_rate"] = r0 + out["dec_bp"] / 100  # kr-flow 방식: 12/9 회의 후 예상 금리(%), 4월~
    zp = HERE / "market" / "ZQF27.CBT.json"
    if zp.exists():
        z = json.loads(zp.read_text(encoding="utf-8"))["chart"]["result"][0]
        zs = pd.Series({pd.Timestamp(t, unit="s").normalize(): (100 - c) for t, c in zip(z["timestamp"], z["indicators"]["quote"][0]["close"]) if c})
        zs = zs[~zs.index.duplicated(keep="last")]
        out["zq"] = zs.reindex(out.index.union(zs.index)).ffill().reindex(out.index)
    else:
        out["zq"] = out["dec_rate"]
    for col, fn in (("spx", "GSPC.json"), ("ndq", "IXIC.json")):  # 주가지수(Yahoo 일봉 종가)
        fp = HERE / "market" / fn
        if fp.exists():
            z = json.loads(fp.read_text(encoding="utf-8"))["chart"]["result"][0]
            s = pd.Series({pd.Timestamp(t, unit="s").normalize(): c for t, c in zip(z["timestamp"], z["indicators"]["quote"][0]["close"]) if c})
            s = s[~s.index.duplicated(keep="last")]
            out[col] = s.reindex(out.index.union(s.index)).ffill().reindex(out.index)
    out["y2"] = pd.to_numeric(df["y2"], errors="coerce")
    out["y10"] = pd.to_numeric(df["y10"], errors="coerce")
    for i, mt in enumerate(m["fed"]):
        h = sum(pd.to_numeric(df.get(f"fed{i}_{c}"), errors="coerce").fillna(0) for c in ("H25", "H26"))
        c = sum(pd.to_numeric(df.get(f"fed{i}_{c}"), errors="coerce").fillna(0) for c in ("C25", "C26"))
        has = pd.to_numeric(df.get(f"fed{i}_H0"), errors="coerce").notna()
        out[f"k_hike_{mt['date']}"] = h.where(has)
        out[f"k_cut_{mt['date']}"] = c.where(has)
    out = out[(out.index >= pd.Timestamp(START) - pd.Timedelta(days=10)) & (out.index <= pd.Timestamp(END))]
    out["d_dec"] = out["zq"].diff() * 100  # bp, 금리 기대 변화
    out["d_y2"] = out["y2"].diff() * 100
    rel = {}
    for r in m["releases"]:
        rel.setdefault(r["date"], []).append(r["type"])
    return out, rel


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
YAHOO = {"ZQF27.CBT.json": "ZQF27.CBT", "GSPC.json": "%5EGSPC", "IXIC.json": "%5EIXIC"}  # ZQF27 = 27년 1월물(12/9 회의 뒤 금리). 27년 1월 회의가 지나면 다음 월물로 바꿀 것


def fetch_market() -> None:
    """EFFR(NY Fed)·연방기금 선물·S&P 500·나스닥 일봉을 market/ 에 받는다. 실패하면 직전 파일 유지."""
    import subprocess
    mk = HERE / "market"
    mk.mkdir(exist_ok=True)
    jobs = {"effr.json": "https://markets.newyorkfed.org/api/rates/unsecured/effr/last/400.json"}
    jobs.update({f: f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=2y&interval=1d" for f, s in YAHOO.items()})
    for fn, url in jobs.items():
        tmp = mk / (fn + ".tmp")
        r = subprocess.run(["curl", "-sS", "-m", "40", "-A", UA, "-o", str(tmp), "-w", "%{http_code}", url], capture_output=True, text=True)
        ok = r.stdout.strip() == "200" and tmp.exists() and tmp.stat().st_size > 1000
        if ok:
            try:
                json.loads(tmp.read_text(encoding="utf-8"))
                tmp.replace(mk / fn)
                continue
            except Exception:  # noqa: BLE001
                ok = False
        print(f"[WARN] {fn} 못 받음({r.stdout.strip()}), 직전 파일 유지")
        tmp.unlink(missing_ok=True)


def main() -> None:
    import sys
    if "--fetch" in sys.argv:
        fetch_market()
    led = json.loads((HERE / "ledger.json").read_text(encoding="utf-8"))
    items = [it for it in led["items"] if it.get("verify") in OKV]
    ovp = HERE / "overrides.json"  # 다시 본 결과: {id: {score(원장 눈금), drivers, drop, ai_side, note}}
    ov = json.loads(ovp.read_text(encoding="utf-8")) if ovp.exists() else {}
    kept = []
    for it in items:
        o = ov.get(it["id"])
        if o:
            if o.get("drop"):
                continue
            it.update({k: v for k, v in o.items() if k in ("score", "drivers", "date", "time_et", "ai_side")})
            it["override_note"] = o.get("note")
        it["raw_score"] = it.get("score")
        it["score"] = disp(it.get("score"))
        if it["group"] == "sellside" and it.get("firm"):  # 셀사이드는 사람이 아니라 하우스 단위로 묶는다
            f = FIRM_ALIAS.get(it["firm"], it["firm"])
            it["firm"] = f
            it["key"] = "ss_" + re.sub(r"[^a-z]+", "_", f.lower()).strip("_")
            it["disp"] = f
        # 화면에 쓰는 이름: 괄호 설명과 '이름 없음' 표기를 뗀다
        sp = re.sub(r"\s*\([^)]*\)", "", it.get("speaker") or "").strip()
        it["speaker"] = "" if re.search(r"unnamed|not named|economists$|analysts$|strategists$|research$|team$", sp, re.I) else sp
        it["g7"] = g7(it)
        kept.append(it)
    items = kept
    mk, rel = load_market()
    tdays = mk.index[mk.index >= pd.Timestamp(START)]
    grid = pd.date_range(START, END, freq="D")

    # ---- 인물 수준 ----
    sc = pd.DataFrame([dict(key=it["key"], date=pd.Timestamp(it["date"]), score=it["score"]) for it in items if it.get("score") is not None])
    lev = {}
    for k, g in sc.groupby("key"):
        s = g.groupby("date")["score"].mean().sort_index()
        vals = []
        for t in grid:
            past = s[s.index <= t]
            if past.empty:
                vals.append(np.nan)
                continue
            w = 0.5 ** (np.asarray((t - past.index).days, dtype=float) / HALF)
            vals.append(float((past.values * w).sum() / w.sum()))
        lev[k] = pd.Series(vals, index=grid)
    L = pd.DataFrame(lev)
    lev_last = {}
    for k, g in sc.groupby("key"):
        s = g.groupby("date")["score"].mean().sort_index()
        lev_last[k] = s.reindex(grid.union(s.index)).ffill().reindex(grid)
    L2 = pd.DataFrame(lev_last)[L.columns]
    grp_of = {}
    for it in items:
        grp_of.setdefault(it["key"], it["group"])

    # 재임 기간 밖은 지수에서 뺀다(수준 자체는 남김)
    Lm = L.copy()
    for k in Lm.columns:
        r = ROSTER.get(k)
        if not r:
            continue
        if r.get("since"):
            Lm.loc[Lm.index < pd.Timestamp(r["since"]), k] = np.nan
        if r.get("until"):
            Lm.loc[Lm.index > pd.Timestamp(r["until"]), k] = np.nan

    def members(pred):
        return [k for k in L.columns if k in ROSTER and pred(ROSTER[k])]

    v26, v27 = members(lambda r: r["v26"]), members(lambda r: r["v27"])
    nonv = members(lambda r: r["group"] == "nonvoter")
    pol = members(lambda r: r["group"] == "political")
    fed_all = members(lambda r: r["group"] in ("board", "voter", "nonvoter"))
    idx = pd.DataFrame(index=grid)
    idx["voter26"] = Lm[v26].mean(axis=1)
    chair = pd.Series(np.nan, index=grid)
    if "powell" in L:
        chair[grid <= pd.Timestamp(CHAIR_SWITCH[0])] = L["powell"][grid <= pd.Timestamp(CHAIR_SWITCH[0])]
    if "warsh" in L:
        chair[grid >= pd.Timestamp(CHAIR_SWITCH[1])] = L["warsh"][grid >= pd.Timestamp(CHAIR_SWITCH[1])]
    idx["chair"] = chair
    W = pd.DataFrame(1.0, index=grid, columns=v26)
    if "powell" in W:
        W.loc[grid <= pd.Timestamp(CHAIR_SWITCH[0]), "powell"] = 3.0
    if "warsh" in W:
        W.loc[grid >= pd.Timestamp(CHAIR_SWITCH[1]), "warsh"] = 3.0
    idx["voter26_cw"] = (Lm[v26] * W).sum(axis=1, min_count=1) / (Lm[v26].notna() * W).sum(axis=1).replace(0, np.nan)
    idx["voter27"] = Lm[v27].mean(axis=1)
    idx["nonvoter"] = Lm[nonv].mean(axis=1) if nonv else np.nan
    idx["political"] = L[pol].mean(axis=1) if pol else np.nan
    idx["fed_all"] = Lm[fed_all].mean(axis=1)
    idx["n_voter26"] = Lm[v26].notna().sum(axis=1)
    idx["n_hawk"] = (Lm[v26] > HAWK_T).sum(axis=1)
    idx["n_dove"] = (Lm[v26] < DOVE_T).sum(axis=1)
    idx["n_mid"] = idx["n_voter26"] - idx["n_hawk"] - idx["n_dove"]
    idx["n_voter27"] = Lm[v27].notna().sum(axis=1)
    idx["n_hawk27"] = (Lm[v27] > HAWK_T).sum(axis=1)
    idx["n_dove27"] = (Lm[v27] < DOVE_T).sum(axis=1)
    idx["n_mid27"] = idx["n_voter27"] - idx["n_hawk27"] - idx["n_dove27"]
    inv = [k for k in L.columns if grp_of.get(k) == "investor"]
    ssd = [k for k in L.columns if grp_of.get(k) == "sellside"]
    idx["investor"] = L[inv].mean(axis=1) if inv else np.nan
    idx["sellside"] = L[ssd].mean(axis=1) if ssd else np.nan
    # 같은 묶음을 '최근 발언만' 방식으로(재임 기간 마스크 동일)
    L2m = L2.where(Lm.notna() | L.isna(), np.nan)
    idx_last = pd.DataFrame(index=grid)
    idx_last["voter26"] = L2m[v26].mean(axis=1)
    idx_last["voter27"] = L2m[v27].mean(axis=1)
    ch2 = pd.Series(np.nan, index=grid)
    if "powell" in L2:
        ch2[grid <= pd.Timestamp(CHAIR_SWITCH[0])] = L2["powell"][grid <= pd.Timestamp(CHAIR_SWITCH[0])]
    if "warsh" in L2:
        ch2[grid >= pd.Timestamp(CHAIR_SWITCH[1])] = L2["warsh"][grid >= pd.Timestamp(CHAIR_SWITCH[1])]
    idx_last["chair"] = ch2
    idx_last["political"] = L2[pol].mean(axis=1) if pol else np.nan
    idx_last["investor"] = L2[inv].mean(axis=1) if inv else np.nan
    idx_last["sellside"] = L2[ssd].mean(axis=1) if ssd else np.nan

    # ---- 근거 태그 비중(연준 인사, 지난 30일) ----
    fed_items = [it for it in items if it["group"] in ("board", "voter", "nonvoter") and it.get("score") is not None]
    dd = pd.DataFrame([dict(date=pd.Timestamp(it["date"]),
                            fin=int("financial_stability_credit" in (it.get("drivers") or []) or it.get("ai_side") in ("watch", "crowding", "calm")),
                            ai=int(it.get("ai_side") in ("watch", "crowding")), infl=int("inflation" in (it.get("drivers") or [])),
                            labor=int(bool(set(it.get("drivers") or []) & {"labor", "growth"}))) for it in fed_items])
    drv_w = {}
    for wdays, minn in ((30, 5), (20, 4), (14, 3)):
        dw = pd.DataFrame(index=grid, columns=["fin", "ai", "infl", "labor", "n"], dtype=float)
        if not dd.empty:
            for t in grid:
                win = dd[(dd.date <= t) & (dd.date > t - pd.Timedelta(days=wdays))]
                if len(win) >= minn:
                    dw.loc[t] = [win.fin.mean() * 100, win.ai.mean() * 100, win.infl.mean() * 100, win.labor.mean() * 100, len(win)]
        drv_w[wdays] = dw
    drv = drv_w[30]
    # 대표 근거 구성비: 발언마다 근거 1~3순위에 3:2:1 가중(2개면 2:1, 1개면 전부) → 매 시점 합 100%
    CAT = {"inflation": "infl", "energy": "energy", "tariffs_supply": "tariff", "labor": "labor", "growth": "labor",
           "financial_stability_credit": "fin", "ai_financing": "fin"}
    cats = ["infl", "energy", "tariff", "labor", "fin", "other"]
    rows = []
    for it in fed_items:
        ds = [d for d in (it.get("drivers") or [])][:3]
        if not ds:
            continue
        wts = [3, 2, 1][:len(ds)]
        tot = sum(wts)
        row = dict.fromkeys(cats, 0.0)
        for d, w in zip(ds, wts):
            row[CAT.get(d, "other")] += w / tot
        row["date"] = pd.Timestamp(it["date"])
        rows.append(row)
    cd = pd.DataFrame(rows)
    comp_w = {}
    for wdays, minn in ((30, 5), (20, 4), (14, 3)):
        cw = pd.DataFrame(index=grid, columns=cats, dtype=float)
        if not cd.empty:
            for t in grid:
                win = cd[(cd.date <= t) & (cd.date > t - pd.Timedelta(days=wdays))]
                if len(win) >= minn:
                    s = win[cats].sum()
                    cw.loc[t] = (s / s.sum() * 100).values
        comp_w[wdays] = cw

    # ---- AI 발언 성격별 월 건수 ----
    ai_month = {}
    for it in items:
        if it.get("ai_side"):
            g = "fed" if it["group"] in ("board", "voter", "nonvoter") else ("political" if it["group"] == "political" else "street")
            ai_month.setdefault(g, {}).setdefault(it["date"][:7], {}).setdefault(it["ai_side"], 0)
            ai_month[g][it["date"][:7]][it["ai_side"]] += 1

    # ---- 이벤트 스터디 ----
    def tday(it):
        d = pd.Timestamp(it["date"])
        tm = it.get("time_et")
        if tm and str(tm) >= CUTOFF:
            d = d + pd.Timedelta(days=1)
        nxt = tdays[tdays >= d]
        return nxt[0] if len(nxt) else None

    ev = []
    for it in items:
        if it.get("score") is None:
            continue
        t0 = tday(it)
        if t0 is None or t0 not in mk.index:
            continue
        i = mk.index.get_loc(t0)
        prior = L[it["key"]].get(pd.Timestamp(it["date"]) - pd.Timedelta(days=1), np.nan) if it["key"] in L else np.nan
        row = dict(id=it["id"], key=it["key"], group=it["group"], g7=it["g7"], date=it["date"], t0=t0.date().isoformat(), score=it["score"],
                   surprise=(it["score"] - prior) if not np.isnan(prior) else np.nan,
                   d_dec=mk["d_dec"].iloc[i], d_y2=mk["d_y2"].iloc[i],
                   d_dec2=(mk["zq"].iloc[i + 1] - mk["zq"].iloc[i - 1]) * 100 if 0 < i < len(mk) - 1 else np.nan,
                   d_y22=(mk["y2"].iloc[i + 1] - mk["y2"].iloc[i - 1]) * 100 if 0 < i < len(mk) - 1 else np.nan,
                   rel=",".join(rel.get(t0.date().isoformat(), [])))
        row["data_day"] = any(x in DATA_REL for x in row["rel"].split(","))
        row["fomc_day"] = "FOMC" in row["rel"]
        ev.append(row)
    E = pd.DataFrame(ev)

    base = {c: float(mk.loc[tdays, c].abs().mean()) for c in ("d_dec", "d_y2")}

    def corr(x, y):
        ok = x.notna() & y.notna()
        x, y = x[ok], y[ok]
        if len(x) < MIN_N or x.nunique() < 2 or y.nunique() < 2:
            return None, None, int(len(x))
        r, p = spearman(x, y)
        return round(float(r), 2), round(float(p), 3), int(len(x))

    def hit(x, y):
        ok = x.notna() & y.notna() & (x != 0) & (y != 0)
        return (round(float((np.sign(x[ok]) == np.sign(y[ok])).mean() * 100), 0), int(ok.sum())) if ok.sum() >= MIN_N else (None, int(ok.sum()))

    table = []
    if not E.empty:
        for k, g in E.groupby("key"):
            clean = g[~g.data_day & ~(g.fomc_day & ~g.key.isin(["warsh", "powell"]))]
            r = dict(key=k, group=g.group.iloc[0], g7=g.g7.iloc[0], n=len(g), n_clean=len(clean), mean_score=round(float(g.score.mean()), 1))
            for tag, sub in (("all", g), ("clean", clean)):
                for mcol in ("d_dec", "d_y2"):
                    r[f"{tag}_score_{mcol}"] = corr(sub.score, sub[mcol])
                    r[f"{tag}_surp_{mcol}"] = corr(sub.surprise, sub[mcol])
                    r[f"{tag}_hit_{mcol}"] = hit(sub.surprise, sub[mcol])
                r[f"{tag}_surp_d_dec2"] = corr(sub.surprise, sub.d_dec2)
                r[f"{tag}_absmove_d_dec"] = round(float(sub.d_dec.abs().mean()), 2) if len(sub) else None
                r[f"{tag}_absmove_d_y2"] = round(float(sub.d_y2.abs().mean()), 2) if len(sub) else None
            table.append(r)

    # ---- 주간 선후행: 지수 변화 vs 금리 기대 변화 ----
    wk_m = mk["zq"].resample("W-FRI").last().diff() * 100
    wk_y = mk["y2"].resample("W-FRI").last().diff() * 100
    leadlag = {}
    for name in ("voter26", "voter26_cw", "chair", "fed_all", "nonvoter", "political"):
        wi = idx[name].resample("W-FRI").last().diff()
        row = {}
        for lag in range(-3, 4):  # lag>0: 톤이 lag주 먼저 움직임
            row[str(lag)] = corr(wi.shift(lag), wk_m)[:3]
        leadlag[name] = row
    sp_week = []
    for k in L.columns:
        wi = L[k].resample("W-FRI").last().diff()
        if (wi.fillna(0) != 0).sum() < MIN_N:
            continue
        sp_week.append(dict(key=k, same=corr(wi, wk_m), tone_leads_1w=corr(wi.shift(1), wk_m), market_leads_1w=corr(wi.shift(-1), wk_m),
                            same_y2=corr(wi, wk_y), n_moves=int((wi.fillna(0) != 0).sum())))

    # ---- 저장 ----
    def ser(s, nd=3):
        return [None if (v is None or (isinstance(v, float) and np.isnan(v))) else round(float(v), nd) for v in s]

    mkg = mk.reindex(grid.union(mk.index)).ffill().reindex(grid)
    out = dict(
        params=dict(start=START, end=END, half_life_days=HALF, cutoff_et=CUTOFF, min_n=MIN_N, baseline_absmove=base,
                    hawk_t=HAWK_T, dove_t=DOVE_T, chair_switch=CHAIR_SWITCH,
                    score_scale="10 = 매파, 5 = 중도, 0 = 비둘기파", n_items=len(led["items"]), n_usable=len(items),
                    n_scored=int(len(sc)), n_unverified=len(led["unverified"])),
        roster={k: v for k, v in ROSTER.items()},
        dates=[d.date().isoformat() for d in grid],
        levels={k: ser(L[k]) for k in L.columns},
        index={c: ser(idx[c]) for c in idx.columns},
        drivers={c: ser(drv[c], 1) for c in drv.columns},
        drivers_w={str(w): {c: ser(dw[c], 1) for c in dw.columns} for w, dw in drv_w.items()},
        comp_w={str(w): {c: ser(cw[c], 1) for c in cw.columns} for w, cw in comp_w.items()},
        index_last={c: ser(idx_last[c]) for c in idx_last.columns},
        market={c: ser(mkg[c]) for c in mkg.columns if not c.startswith("d_")},
        market_tdays=[d.date().isoformat() for d in tdays],
        events=json.loads(E.to_json(orient="records")) if not E.empty else [],
        speaker_table=table, speaker_weekly=sp_week, leadlag=leadlag,
        ai_month=ai_month, items=items, unverified=led["unverified"], extra=led.get("extra", {}),
        releases=rel,
    )
    (HERE / "analysis.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"사용 {len(items)}건(점수 {len(sc)}건) · 인물 {L.shape[1]}명 · 이벤트 {len(E)}건")
    last = idx.dropna(subset=["voter26"]).iloc[-1] if idx["voter26"].notna().any() else None
    if last is not None:
        print("최근 지수", {c: round(float(last[c]), 1) for c in ("voter26", "voter26_cw", "chair", "voter27", "nonvoter", "n_hawk", "n_mid", "n_dove")})


if __name__ == "__main__":
    main()
