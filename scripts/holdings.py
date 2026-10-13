# -*- coding: utf-8 -*-
"""외국인 보유액·시총 비중·보유액 변화 분해 시리즈 (assemble 에서 호출). 단위: 억원 · %.

입력 원장
  freesis_kospi_market / freesis_kosdaq_market   금투협(KRX 원천) 일별 시가총액·외국인 보유 시가총액·외국인 비중 — 실측
  krx_mcap               KRX Open API 종목별 종가·시총·상장주식수 (D+1 08시)
  daum_stock_{code}      외국인 보유주식 수·지분율, 종가, 평균가
  naver_stock_{code}     개인·외국인·기관 순매수 수량
  data/manual/fss_foreign_holdings.json   금감원 월말(결제 기준) — 참고점

종목은 삼성전자 보통주(005930)·SK하이닉스(000660). 우선주는 넣지 않는다(사용자 지정).

보유액 변화 분해(종목, 정확한 항등식)
  H_t - H_{t-1} = (주식수_t - 주식수_{t-1}) × P_t   ← 매매 효과(보유주식 수 변화; 장외·DR 예탁 포함)
                + 주식수_{t-1} × (P_t - P_{t-1})       ← 주가 효과
시장 전체는 주식 수가 없으므로 매매 효과 = 다음 외국인 순매수(코스피+코스닥), 주가 효과 = 보유액 변화 - 순매수(잔차).
"""

from __future__ import annotations

import json

from common import DATA, load_ledger

STOCKS = ("005930", "000660")
FSS_PATH = DATA / "manual" / "fss_foreign_holdings.json"
MILLION_TO_EOK = 0.01   # 백만원 -> 억원


def load_fss() -> dict:
    if FSS_PATH.exists():
        return json.loads(FSS_PATH.read_text(encoding="utf-8"))
    return {"rows": []}


def build(dates: list[str], S: dict) -> dict:
    n = len(dates)
    krx = load_ledger("krx_mcap")["rows"]
    fm = {"kospi": load_ledger("freesis_kospi_market")["rows"], "kosdaq": load_ledger("freesis_kosdaq_market")["rows"]}
    meta: dict = {}
    none = lambda: [None] * n  # noqa: E731

    # ---- 시장: 시총·외국인 보유 시총 (금투협 실측 → 없으면 KRX 합 → 없으면 지수 비율 추정) ----------
    est_dates = []
    for mk in ("kospi", "kosdaq"):
        mcap, fo, fo_pct = none(), none(), none()
        last_i = None
        for i, d in enumerate(dates):
            r = fm[mk].get(d)
            k = krx.get(d) or {}
            if r and r.get("mcap"):
                mcap[i] = round(r["mcap"] * MILLION_TO_EOK, 1)
                if r.get("fo_mcap"):
                    fo[i] = round(r["fo_mcap"] * MILLION_TO_EOK, 1)
                    fo_pct[i] = r.get("fo_pct")
                last_i = i
            elif k.get(f"{mk}_mcap"):
                mcap[i] = k[f"{mk}_mcap"]
                last_i = i
            elif last_i is not None and S[f"idx_{mk}"][i] and S[f"idx_{mk}"][last_i]:
                mcap[i] = round(mcap[last_i] * S[f"idx_{mk}"][i] / S[f"idx_{mk}"][last_i], 1)
                if mk == "kospi":
                    est_dates.append(d)
        S[f"mcap_{mk}"], S[f"fo_{mk}"], S[f"fo_pct_{mk}"] = mcap, fo, fo_pct
    meta["mcap_est"] = est_dates

    def add(*arrs):
        return [None if any(a[i] is None for a in arrs) else round(sum(a[i] for a in arrs), 1) for i in range(n)]

    def pct(a, b):
        return [None if a[i] is None or not b[i] else round(a[i] / b[i] * 100, 2) for i in range(n)]

    S["mcap_total"] = add(S["mcap_kospi"], S["mcap_kosdaq"])
    S["fo_total"] = add(S["fo_kospi"], S["fo_kosdaq"])
    S["fo_pct_total"] = pct(S["fo_total"], S["mcap_total"])

    # ---- 종목별 -----------------------------------------------------------------
    for c in STOCKS:
        dr = load_ledger(f"daum_stock_{c}")["rows"]
        nr = load_ledger(f"naver_stock_{c}")["rows"]
        mcap, fo_val, fo_rate, fo_sh, px_arr = none(), none(), none(), none(), none()
        nf, ni, npv, nq = none(), none(), none(), none()
        last_shares = None
        for i, d in enumerate(dates):
            k, a, b = krx.get(d) or {}, dr.get(d), nr.get(d)
            if k.get(f"s{c}_shares"):
                last_shares = k[f"s{c}_shares"]
            close = k.get(f"s{c}_close") or (a or {}).get("close")
            px_arr[i] = close
            if k.get(f"s{c}_mcap"):
                mcap[i] = k[f"s{c}_mcap"]
            elif close and last_shares:
                mcap[i] = round(close * last_shares / 1e8, 1)
            if a and a.get("fo_shares") and close:
                fo_sh[i] = a["fo_shares"]
                fo_rate[i] = round(a["fo_rate"], 3)
                fo_val[i] = round(a["fo_shares"] * close / 1e8, 1)
            vw = (a or {}).get("vwap") or close
            if b and vw:
                for arr, f in ((nf, "foreign"), (ni, "organ"), (npv, "indiv")):
                    if b.get(f) is not None:
                        arr[i] = round(b[f] * vw / 1e8, 1)
                nq[i] = b.get("foreign")
        # 분해 (직전 값이 있는 날만)
        eff_t, eff_p, dh = none(), none(), none()
        prev = None
        for i in range(n):
            if fo_sh[i] is None or px_arr[i] is None:
                continue
            if prev is not None:
                eff_t[i] = round((fo_sh[i] - fo_sh[prev]) * px_arr[i] / 1e8, 1)
                eff_p[i] = round(fo_sh[prev] * (px_arr[i] - px_arr[prev]) / 1e8, 1)
                dh[i] = round(eff_t[i] + eff_p[i], 1)
            prev = i
        S.update({f"s{c}_mcap": mcap, f"s{c}_fo_val": fo_val, f"s{c}_fo_rate": fo_rate, f"s{c}_fo_shares": fo_sh,
                  f"s{c}_net_foreign": nf, f"s{c}_net_inst": ni, f"s{c}_net_indiv": npv, f"s{c}_net_foreign_qty": nq,
                  f"s{c}_eff_trade": eff_t, f"s{c}_eff_price": eff_p, f"s{c}_dH": dh})

    sh = STOCKS
    S["sh_mcap"] = add(*(S[f"s{c}_mcap"] for c in sh))
    S["sh_fo_val"] = add(*(S[f"s{c}_fo_val"] for c in sh))
    for f in ("net_foreign", "eff_trade", "eff_price", "dH"):
        S[f"sh_{f}"] = add(*(S[f"s{c}_{f}"] for c in sh))
    S["share_samsung"] = pct(S["s005930_mcap"], S["mcap_kospi"])
    S["share_hynix"] = pct(S["s000660_mcap"], S["mcap_kospi"])
    S["share_sh"] = pct(S["sh_mcap"], S["mcap_kospi"])
    S["sh_in_fo_kospi"] = pct(S["sh_fo_val"], S["fo_kospi"])
    S["mcap_kospi_rest"] = [None if S["mcap_kospi"][i] is None or S["sh_mcap"][i] is None
                            else round(S["mcap_kospi"][i] - S["sh_mcap"][i], 1) for i in range(n)]

    # ---- 시장 전체 보유액 변화 분해: 순매수(다음) vs 주가(잔차) ----------------------
    S["fo_net_total"] = [None if S["kospi_foreign"][i] is None
                         else round((S["kospi_foreign"][i] or 0) + (S["kosdaq_foreign"][i] or 0), 1) for i in range(n)]
    dH, price = none(), none()
    prev = None
    for i in range(n):
        if S["fo_total"][i] is None:
            continue
        if prev is not None and S["fo_net_total"][i] is not None:
            dH[i] = round(S["fo_total"][i] - S["fo_total"][prev], 1)
            price[i] = round(dH[i] - S["fo_net_total"][i], 1)
        prev = i
    S["fo_dH_total"], S["fo_eff_price_total"] = dH, price

    # ---- 금감원 월말(참고점) -------------------------------------------------------
    fss = load_fss()
    fss_val, fss_pct = none(), none()
    for r in fss.get("rows", []):
        idx = [i for i, d in enumerate(dates) if d[:7] == r["month"] and S["idx_kospi"][i] is not None]
        if idx:
            fss_val[idx[-1]] = round(r["holding_jo"] * 1e4, 1)
            fss_pct[idx[-1]] = r.get("share_pct")
    S["fo_total_fss"], S["fo_share_fss"] = fss_val, fss_pct
    meta["fss"] = [{k: r.get(k) for k in ("month", "holding_jo", "share_pct", "net_buy_jo", "net_buy_kospi_jo",
                                          "net_buy_kosdaq_jo", "url", "news", "published")} for r in fss.get("rows", [])]
    meta["fss_note"] = fss.get("note")
    return meta
