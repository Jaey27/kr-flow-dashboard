# -*- coding: utf-8 -*-
"""섹터(네이버 업종 78개)별 투자자 수급 — KRX 종목별 원자료를 업종으로 묶는다.

원장 data/ledger/krx_sector_flow.json
  rows[date] = {"indiv"|"foreign"|"inst": {업종명: [매수억, 매도억]}}   (억원, 소수 1자리)
렌더 입력(assemble 에서 flows.json 에 붙임)
  sector.names          업종명 목록(최근 거래대금 큰 순)
  sector.net[inv][k]    날짜축(dates)에 정렬한 일별 순매수(억, 정수)
  sector.trade[k]       일별 업종 거래대금(3주체 매수+매도 합 ÷ 2, 억, 정수)
  sector.latest         최근일 '섹션별 수급'(거래액·순매수·순매도 상위 3업종 × 상위 3종목, 포스트 형식)
  sector.top[win][inv][업종] 기간(1·5·20·60일) 상위 순매수/순매도 종목 3개
"""

from __future__ import annotations

import json

from common import DATA, load_ledger, merge_rows, save_ledger
import krx_inv

SECTORS_PATH = DATA / "sectors_naver.json"
LEDGER = "krx_sector_flow"
WINDOWS = (1, 5, 10, 20, 60)
EOK = 1e8


def sectors() -> tuple[list[dict], dict[str, str], dict[str, str]]:
    doc = json.loads(SECTORS_PATH.read_text(encoding="utf-8"))
    code2sec, names = {}, {}
    for s in doc["sectors"]:
        for c in s["codes"]:
            code2sec[c] = s["name"]
        names.update(s.get("names", {}))
    return doc["sectors"], code2sec, names


def aggregate_day(raw: dict, code2sec: dict) -> dict:
    out = {}
    for inv, by_code in raw.items():
        agg: dict[str, list[float]] = {}
        for code, (buy, sell) in by_code.items():
            sec = code2sec.get(code)
            if not sec:
                continue                      # '기타'·코넥스 등 업종 밖 종목
            a = agg.setdefault(sec, [0.0, 0.0])
            a[0] += buy
            a[1] += sell
        out[inv] = {k: [round(v[0] / EOK, 1), round(v[1] / EOK, 1)] for k, v in agg.items()}
    return out


def rebuild_ledger(dates: list[str] | None = None) -> bool:
    """원자료(월별 gz)에서 업종 원장을 다시 만든다(업종 소속이 바뀌어도 다시 묶을 수 있게)."""
    _, code2sec, _ = sectors()
    led = load_ledger(LEDGER)
    rows = {}
    for p in sorted(krx_inv.RAW_DIR.glob("*.json.gz")):
        month = krx_inv.load_raw_month(p.name[:7])
        for d, raw in month.items():
            if dates is None or d in dates:
                rows[d] = aggregate_day(raw, code2sec)
    changed = merge_rows(led, rows)
    save_ledger(LEDGER, led)
    return changed


def build(dates: list[str]) -> dict | None:
    led = load_ledger(LEDGER)["rows"]
    if not led:
        return None
    secs, code2sec, names = sectors()
    have = [d for d in dates if d in led]
    last = have[-1]
    # 업종 순서: 최근 20일 거래대금 큰 순
    tv: dict[str, float] = {}
    for d in have[-20:]:
        for inv in krx_inv.INVESTORS:
            for k, (b, s) in led[d].get(inv, {}).items():
                tv[k] = tv.get(k, 0) + b + s
    order = sorted({s["name"] for s in secs}, key=lambda k: -tv.get(k, 0))

    net = {inv: {k: [None] * len(dates) for k in order} for inv in krx_inv.INVESTORS}
    trade = {k: [None] * len(dates) for k in order}
    for i, d in enumerate(dates):
        r = led.get(d)
        if not r:
            continue
        for k in order:
            t = 0.0
            for inv in krx_inv.INVESTORS:
                b, s = r.get(inv, {}).get(k, [0.0, 0.0])
                net[inv][k][i] = round(b - s)
                t += b + s
            trade[k][i] = round(t / 2)

    # ---- 종목 단위: 최근 60일 원자료로 기간별 상위 종목 + 최근일 섹션 ----------------------
    recent = have[-max(WINDOWS):]
    raw_by_day = {}
    for m in sorted({d[:7] for d in recent}):
        raw_by_day.update(krx_inv.load_raw_month(m))
    top = {}
    for w in WINDOWS:
        days = [d for d in recent[-w:] if d in raw_by_day]
        top[str(w)] = {}
        for inv in krx_inv.INVESTORS:
            acc: dict[str, list[float]] = {}
            for d in days:
                for code, (b, s) in raw_by_day[d].get(inv, {}).items():
                    if code in code2sec:
                        a = acc.setdefault(code, [0.0, 0.0])
                        a[0] += b
                        a[1] += s
            by_sec: dict[str, list] = {}
            for code, (b, s) in acc.items():
                by_sec.setdefault(code2sec[code], []).append((code, (b - s) / EOK, (b + s) / EOK))
            top[str(w)][inv] = {}
            for sec, v in by_sec.items():
                e = {"buy": [[names.get(c, c), c, round(n)] for c, n, _ in sorted(v, key=lambda x: -x[1])[:3] if n > 0],
                     "sell": [[names.get(c, c), c, round(n)] for c, n, _ in sorted(v, key=lambda x: x[1])[:3] if n < 0]}
                if w == 1:   # 거래액 상위 종목은 최근일 섹션에만 쓴다
                    e["trade"] = [[names.get(c, c), c, round(t)] for c, _, t in sorted(v, key=lambda x: -x[2])[:3]]
                top[str(w)][inv][sec] = e

    # 최근일 섹션 (포스트 형식): 주체별 거래액·순매수·순매도 상위 3업종, 업종 안 상위 3종목(비중 %)
    latest = {"date": last, "inv": {}}
    raw_last = raw_by_day.get(last, {})
    for inv in krx_inv.INVESTORS:
        r = led[last].get(inv, {})
        tot_b = sum(x[0] for x in raw_last.get(inv, {}).values()) / EOK
        tot_s = sum(x[1] for x in raw_last.get(inv, {}).values()) / EOK
        secs_t = sorted(r.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:3]
        secs_b = [kv for kv in sorted(r.items(), key=lambda kv: -(kv[1][0] - kv[1][1])) if kv[1][0] - kv[1][1] > 0][:3]
        secs_s = [kv for kv in sorted(r.items(), key=lambda kv: kv[1][0] - kv[1][1]) if kv[1][0] - kv[1][1] < 0][:3]
        t1 = top["1"][inv]

        def stocks(sec, kind, total):
            arr = t1.get(sec, {}).get(kind, [])[:3]
            return [[n, c, v, round(abs(v) / abs(total) * 100, 1) if total else None] for n, c, v in arr]
        latest["inv"][inv] = {
            "net": round(tot_b - tot_s), "trade": round(tot_b + tot_s),
            "trade_secs": [[k, round(v[0] + v[1]), stocks(k, "trade", v[0] + v[1])] for k, v in secs_t],
            "buy_secs": [[k, round(v[0] - v[1]), stocks(k, "buy", v[0] - v[1])] for k, v in secs_b],
            "sell_secs": [[k, round(v[0] - v[1]), stocks(k, "sell", v[0] - v[1])] for k, v in secs_s],
        }
    return {"names": order, "net": net, "trade": trade, "top": top, "latest": latest,
            "prov": load_ledger(LEDGER).get("prov", []),
            "first": have[0], "last": last, "n_sectors": len(order)}
