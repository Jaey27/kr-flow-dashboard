"""PCE 추정(브릿지) + 실제값 대조 → data/pce.json (경제지표 탭 'PCE' 카드)

    python scripts/pce_data.py      # cpi_dashboard(cpi.json)·ppi_data.py(ppi_cache.txt) 다음에 실행

- 실제 PCE: FRED PCEPI(헤드라인)·PCEPILFE(근원) 월 지수(BEA, UA=curl). MoM·YoY 는 지수로 계산.
- 추정(브릿지 회귀, 계절조정 MoM %):
    근원 PCE ~ CPI 근원상품(SACL1E) + CPI 주거비(SAH1) + CPI 슈퍼코어(SUPERCORE)
               + PPI 소비자 서비스(운송·유통 제외, WPSFD42111: 의료·금융자문 등 PCE가 PPI로 재는 항목) + PPI 여객운송(WPSFD42211: 항공료)
    헤드라인 PCE ~ 위 + CPI 식품(SAF1) + CPI 에너지(SA0E)
  PCE 는 CPI 보다 주거 비중이 작고 의료·금융 서비스를 PPI 로 잰다 → 그 차이를 회귀가 계수로 흡수한다(가중치 표를 직접 쓰는 방식보다 단순, 대신 오차가 큼).
- 대조: 지난 12개월은 '그달 직전까지의 데이터로만' 다시 맞춘 1개월 앞 예측(실시간에 가까운 백테스트)과 실제값을 비교 → 평균 절대 오차(MAE).
- 기록: 아직 실제값이 없는 달의 추정치를 data/pce_nowcast_log.json 에 처음 낸 날과 함께 남기고, 실제값이 나오면 오차를 채운다.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "pce.json"
LOG = ROOT / "data" / "pce_nowcast_log.json"
START = "2021-01"   # 회귀 표본 시작(팬데믹 직후 왜곡 구간 제외)
MONTHS = 36
CPI_CORE = ["SACL1E", "SAH1", "SUPERCORE"]
CPI_HEAD = CPI_CORE + ["SAF1", "SA0E"]
PPI_X = ["WPSFD42111", "WPSFD42211"]
KO = {"SACL1E": "CPI 근원상품", "SAH1": "CPI 주거비", "SUPERCORE": "CPI 슈퍼코어", "SAF1": "CPI 식품", "SA0E": "CPI 에너지",
      "WPSFD42111": "PPI 소비자 서비스(의료·금융 등)", "WPSFD42211": "PPI 여객운송(항공료)"}


def fred(sid: str) -> dict[str, float]:
    with urllib.request.urlopen(urllib.request.Request(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd=2019-01-01",
                                                       headers={"User-Agent": "curl/8.4.0"}), timeout=120) as r:
        rows = r.read().decode("utf-8").strip().splitlines()[1:]
    return {d[:7]: float(v) for d, v in (x.split(",")[:2] for x in rows) if v not in ("", ".")}


def mom_of(lv: dict[str, float]) -> dict[str, float]:
    ks = sorted(lv)
    return {k: (lv[k] / lv[p] - 1) * 100 for p, k in zip(ks, ks[1:])}


def ppi_mom() -> dict[str, dict[str, float]]:
    raw = (ROOT / "data" / "ppi_cache.txt").read_text(encoding="utf-8").split("\n", 1)[1]
    lv: dict[str, dict[str, float]] = {}
    for line in raw.splitlines()[1:]:
        p = [x.strip() for x in line.split("\t")]
        if len(p) >= 4 and p[0] in PPI_X and p[2].startswith("M") and p[2] != "M13":
            try:
                lv.setdefault(p[0], {})[f"{p[1]}-{p[2][1:]}"] = float(p[3])
            except ValueError:
                pass
    return {k: mom_of(v) for k, v in lv.items()}


def fit(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    return np.linalg.lstsq(A, y, rcond=None)[0]


def pred(b: np.ndarray, x: np.ndarray) -> float:
    return float(b[0] + x @ b[1:])


def main() -> int:
    c = json.loads((ROOT / "cpi_dashboard" / "data" / "cpi.json").read_text(encoding="utf-8"))
    cpi = {k: {m: v for m, v in zip(c["months"], c["series"][k]["mom"]) if v is not None} for k in set(CPI_HEAD)}
    ppi = ppi_mom()
    lvl = {"core": fred("PCEPILFE"), "head": fred("PCEPI")}
    act = {k: mom_of(v) for k, v in lvl.items()}
    srcs = {**cpi, **ppi}
    allm = sorted(set(c["months"]) | set(act["core"]))
    last_act = max(act["core"])
    res = {}
    for key, xs in (("core", CPI_CORE + PPI_X), ("head", CPI_HEAD + PPI_X)):
        row = lambda m: [srcs[x].get(m) for x in xs]  # noqa: E731
        ok = lambda m: all(v is not None for v in row(m))  # noqa: E731
        train = [m for m in allm if START <= m <= last_act and m in act[key] and ok(m)]
        X = np.array([row(m) for m in train]); y = np.array([act[key][m] for m in train])
        b = fit(X, y)
        fitted = {m: pred(b, np.array(row(m))) for m in train}
        r2 = 1 - np.sum((y - X @ b[1:] - b[0]) ** 2) / np.sum((y - y.mean()) ** 2)
        # 1개월 앞 백테스트: 그달 직전까지로만 맞춰 그달 예측
        bt = {}
        for m in train[-12:]:
            tr = [t for t in train if t < m]
            bb = fit(np.array([row(t) for t in tr]), np.array([act[key][t] for t in tr]))
            bt[m] = pred(bb, np.array(row(m)))
        mae = float(np.mean([abs(bt[m] - act[key][m]) for m in bt]))
        # 실제값이 아직 없는 달 추정
        now = {m: pred(b, np.array(row(m))) for m in allm if m > last_act and ok(m)}
        # 추정 YoY: 마지막 실제 지수에서 추정 MoM 을 이어 붙임
        lv = dict(lvl[key]); nyoy = {}
        for m in sorted(now):
            p = max(k for k in lv if k < m); lv[m] = lv[p] * (1 + now[m] / 100)
            y0 = f"{int(m[:4]) - 1}-{m[5:]}"
            nyoy[m] = (lv[m] / lv[y0] - 1) * 100 if y0 in lv else None
        nowx = {m: {x: round(v, 3) for x, v in zip(xs, row(m))} for m in now}
        res[key] = {"nowx": nowx, "coef": {"const": round(float(b[0]), 4), **{x: round(float(v), 4) for x, v in zip(xs, b[1:])}},
                    "r2": round(float(r2), 3), "n": len(train), "bt_mae": round(mae, 3), "fitted": fitted, "bt": bt, "now": now, "now_yoy": nyoy}
    months = [m for m in allm if m >= START][-MONTHS:]
    yoy = {k: {m: (lvl[k][m] / lvl[k][f"{int(m[:4]) - 1}-{m[5:]}"] - 1) * 100 for m in lvl[k] if f"{int(m[:4]) - 1}-{m[5:]}" in lvl[k]} for k in lvl}
    r = lambda d, m, n=3: round(d[m], n) if m in d and d[m] is not None else None  # noqa: E731
    out = {"src": "FRED PCEPI·PCEPILFE(BEA) · CPI(cpi_dashboard) · PPI(BLS FD-ID)", "months": months, "last_actual": last_act,
           "fetched": date.today().isoformat(), "start": START, "ko": KO}
    for k in ("core", "head"):
        R = res[k]
        out[k] = {"act_mom": [r(act[k], m) for m in months], "act_yoy": [r(yoy[k], m, 2) for m in months],
                  "fit_mom": [r(R["fitted"], m) for m in months], "bt_mom": [r(R["bt"], m) for m in months],
                  "now_mom": [r(R["now"], m) for m in months], "now_yoy": [r(R["now_yoy"], m, 2) for m in months],
                  "coef": R["coef"], "r2": R["r2"], "n": R["n"], "bt_mae": R["bt_mae"], "nowx": R["nowx"]}
    # 추정 기록(처음 낸 값 유지) + 실제값 나오면 오차
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {}
    for k in ("core", "head"):
        for m, v in res[k]["now"].items():
            log.setdefault(m, {}).setdefault(k, {"first": round(v, 3), "made": date.today().isoformat()})
            log[m][k]["latest"] = round(v, 3)
    for m, e in log.items():
        for k, x in e.items():
            if m in act[k]:
                x["actual"] = round(act[k][m], 3)
                x["err_first"] = round(x["first"] - act[k][m], 3)
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
    out["log"] = log
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    nm = sorted(res["core"]["now"])
    print(f"[pce] 실제 {last_act} 근원 MoM {act['core'][last_act]:.3f}% · 추정 " + ", ".join(f"{m} 근원 {res['core']['now'][m]:.2f}% (YoY {res['core']['now_yoy'][m]:.2f}%)" for m in nm)
          + f" · R² {res['core']['r2']} · 1개월 앞 MAE {res['core']['bt_mae']}%p (최근 12개월)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
