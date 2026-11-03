"""빅테크 자금 조달 트래커 → data/funding.json (리스크 탭 ① 「빅테크 자금 조달」 카드, Jae 11/04)

    python scripts/funding_data.py          # 하루 1번(run_daily). SEC 원문은 data/funding/ 에 캐시

대상: META · MSFT · GOOGL · AMZN · ORCL · SPCX(SpaceX) · TSLA. 기간: 1Q25 이후 분기.

- 회사채 공모 = SEC 최종 설명서(424B2·424B5) 표지의 트랜치 합계. 외화채는 발행일 환율(Yahoo)로 달러 환산.
  사모(144A)·은행 대출은 SEC 공모 서류가 없어 여기 안 들어감 → 참고용으로 현금흐름표 「장기 차입 수령액」을 같이 둔다.
- 유상증자 = 10-Q·10-K 현금흐름표의 보통주·전환우선주·IPO 발행 수령액(ATM 판매 포함). 직원 주식(스톡옵션 행사 등)을
  빼려고 분기 $2B 미만은 0으로 본다. 10-Q가 아직 없는 분기는 최종 설명서(보통주 주식 수×공모가, 전환우선 예탁주×$50)로 채움.
- Capex = 현금흐름표 유형자산 취득(AMZN 은 PaymentsToAcquireProductiveAssets). 10-Q 는 연초 누적이라 직전 분기 누적을 빼서 분기값.
- 분기 이름: 회계분기가 끝나는 달 기준 달력 분기(ORCL 은 2·5·8·11월 끝 → 1Q·2Q·3Q·4Q).
- 최근 30일 목록: 최종 설명서 + 예비 설명서(최종본이 아직 없는 것 = 「예정」) + data/manual/funding_news.json(사모·추진 뉴스).
"""

from __future__ import annotations

import datetime as dt
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "funding.json"
CACHE = ROOT / "data" / "funding"
NEWS = ROOT / "data" / "manual" / "funding_news.json"
UA = {"User-Agent": "cpi-dashboard (pjy0992@gmail.com)"}  # SEC 는 연락처 있는 UA 필수(ppi_data·emp_data 와 같은 연락처)
START = "2025-01-01"

CO = {  # 티커: (CIK, 이름, capex 태그, 차입 태그들, 증자 태그들)
    "META": (1326801, "Meta", ["PaymentsToAcquirePropertyPlantAndEquipment"], ["ProceedsFromIssuanceOfLongTermDebt"],
             ["ProceedsFromIssuanceOfCommonStock", "ProceedsFromIssuanceOfConvertiblePreferredStock"]),
    "MSFT": (789019, "Microsoft", ["PaymentsToAcquirePropertyPlantAndEquipment"], ["ProceedsFromIssuanceOfLongTermDebt", "ProceedsFromDebtMaturingInMoreThanThreeMonths"],
             []),  # MSFT 보통주 발행 수령액 = 직원 주식 구매 → 증자 아님
    "GOOGL": (1652044, "Alphabet", ["PaymentsToAcquirePropertyPlantAndEquipment"], ["ProceedsFromDebtNetOfIssuanceCosts"],
              ["ProceedsFromIssuanceOfCommonStock", "ProceedsFromIssuanceOfConvertiblePreferredStock"]),
    "AMZN": (1018724, "Amazon", ["PaymentsToAcquireProductiveAssets"], ["ProceedsFromIssuanceOfLongTermDebt"],
             ["ProceedsFromIssuanceOfCommonStock", "ProceedsFromIssuanceOfConvertiblePreferredStock"]),
    "ORCL": (1341439, "Oracle", ["PaymentsToAcquirePropertyPlantAndEquipment"], ["ProceedsFromIssuanceOfSeniorLongTermDebt", "ProceedsFromIssuanceOfLongTermDebt"],
             ["ProceedsFromIssuanceOfCommonStock", "ProceedsFromIssuanceOfConvertiblePreferredStock"]),
    "SPCX": (1181412, "SpaceX", ["PaymentsToAcquirePropertyPlantAndEquipment"], ["ProceedsFromIssuanceOfLongTermDebt"],
             ["ProceedsFromIssuanceInitialPublicOffering", "ProceedsFromIssuanceOfCommonStock"]),
    "TSLA": (1318605, "Tesla", ["PaymentsToAcquirePropertyPlantAndEquipment"], ["ProceedsFromIssuanceOfDebt"], []),
}
EQ_MIN = 2e9   # 분기 증자 수령액이 이보다 작으면 직원 주식 등으로 보고 0
FX = {"$": None, "US$": None, "€": "EURUSD=X", "£": "GBPUSD=X", "C$": "CADUSD=X", "A$": "AUDUSD=X", "CHF": "CHFUSD=X", "¥": "JPYUSD=X", "JPY": "JPYUSD=X"}


def get(url: str, timeout: int = 60) -> bytes:
    time.sleep(0.15)  # SEC 초당 10건 제한
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def D(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def qlabel(end: str) -> str:
    d = D(end)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


# ---- XBRL 현금흐름 → 분기값 ---------------------------------------------------------
def flows(gaap: dict, tags: list[str], frame_rows: dict, add: bool = False) -> dict[str, tuple[float, str]]:
    """여러 태그를 (start,end) 단위로 합친 뒤 분기값으로. add=False 는 같은 뜻의 다른 이름(앞 태그 우선), True 는 구성요소(합산:
    보통주+전환우선주). 같은 10-Q 에 줄이 없으면 0(그 분기 발행 없음). 반환 {분기 끝: (값, 'q' 분기값 | 'h' 앞 분기와 합산)}"""
    rows: dict[tuple, float] = {}
    for t in tags:
        one: dict[tuple, float] = {}
        for u in (gaap.get(t, {}).get("units", {}).get("USD", [])):
            if "start" not in u or u["form"] not in ("10-Q", "10-K", "10-Q/A", "10-K/A"):
                continue
            one.setdefault((u["start"], u["end"]), u["val"])
        for k, v in one.items():
            rows[k] = rows.get(k, 0.0) + v if add else rows.get(k, v)
    for k in frame_rows:          # capex 줄이 있는 기간인데 이 태그가 없으면 0
        rows.setdefault(k, 0.0)
    out = {}
    for s, e in sorted({k for k in rows}, key=lambda k: k[1]):
        if e < START:
            continue
        n = (D(e) - D(s)).days
        if 80 <= n <= 100:
            out.setdefault(e, (rows[(s, e)], "q"))
    for s, e in sorted(rows, key=lambda k: k[1]):
        if e < START or e in out:
            continue
        prev = [e2 for (s2, e2) in rows if s2 == s and e2 < e]
        if prev:
            e2 = max(prev)
            if 80 <= (D(e) - D(e2)).days <= 100:
                out[e] = (rows[(s, e)] - rows[(s, e2)], "q")
            else:
                out[e] = (rows[(s, e)] - rows[(s, e2)], "h")
        else:
            out[e] = (rows[(s, e)], "h")  # 누적만 있음(상장 전 분기 등)
    return out


def xbrl(tk: str) -> dict:
    cik, _, cap_t, debt_t, eq_t = CO[tk]
    p = CACHE / f"facts_{tk}.json"
    if not p.exists() or time.time() - p.stat().st_mtime > 20 * 3600:
        p.write_bytes(get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", 120))
    g = json.loads(p.read_text(encoding="utf-8"))["facts"]["us-gaap"]
    base = {}
    for t in cap_t:
        for u in g.get(t, {}).get("units", {}).get("USD", []):
            if "start" in u and u["form"].startswith("10-"):
                base[(u["start"], u["end"])] = 1
    cap = flows(g, cap_t, {})
    debt = flows(g, debt_t, base)
    eq = flows(g, eq_t, base, add=True) if eq_t else {}
    out = {}
    for e, (v, kind) in cap.items():
        dv = debt.get(e, (None, ""))[0]
        ev = eq.get(e, (0.0, ""))[0] if eq_t else 0.0
        out[e] = {"q": qlabel(e), "end": e, "capex": round(v / 1e9, 2), "debt_cf": None if dv is None else round(dv / 1e9, 2),
                  "eq_cf": round(ev / 1e9, 2) if ev >= EQ_MIN else 0.0, "span": kind}
    return out


# ---- SEC 공모 설명서 ------------------------------------------------------------------
CUR = r"(US\$|C\$|A\$|\$|€|£|CHF\s?|¥|JPY\s?)"
TR1 = re.compile(CUR + r"\s?([\d,]+(?:\.\d+)?)\s*(million|billion)?\s+(?:in\s+)?(?:aggregate principal amount of\s+)?(?:its |our )?(floating rate|[\d.]+\s?%)\s+(?:senior\s+)?(?:notes|bonds|debentures)\s+due\s+(\d{4})", re.I)


def fx_series(sym: str) -> dict[str, float]:
    p = CACHE / f"fx_{sym.replace('=', '_')}.json"
    if p.exists() and time.time() - p.stat().st_mtime < 20 * 3600:
        return json.loads(p.read_text(encoding="utf-8"))
    p1 = int(dt.datetime(2024, 12, 1).timestamp())
    r = json.loads(urllib.request.urlopen(urllib.request.Request(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?period1={p1}&period2={int(time.time())}&interval=1d",
        headers={"User-Agent": "Mozilla/5.0"}), timeout=30).read())["chart"]["result"][0]
    m = {dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat(): c for t, c in zip(r["timestamp"], r["indicators"]["quote"][0]["close"]) if c}
    p.write_text(json.dumps(m), encoding="utf-8")
    return m


def to_usd(cur: str, v: float, day: str) -> float | None:
    sym = FX.get(cur.strip())
    if sym is None:
        return v if cur.strip() in ("$", "US$") else None
    s = fx_series(sym)
    ks = [k for k in s if k <= day]
    return v * s[max(ks)] if ks else None


def parse_pros(text: str) -> dict:
    prelim = bool(re.search(r"subject to completion", text[:8000], re.I))
    cover = text[:40000]
    seen, tr = set(), []
    for g in TR1.finditer(cover):
        cur, amt, unit, cpn, yr = g.groups()
        v = float(amt.replace(",", ""))
        if unit:
            v *= 1e6 if unit.lower() == "million" else 1e9
        k = (cur.strip(), v, cpn.replace(" ", "").lower(), yr)
        if v < 1e7 or k in seen:
            continue
        seen.add(k)
        tr.append(k)
    eq = None
    if not tr:
        dep = re.search(r"([\d,]{6,})\s+(?:Series [A-Z] )?Depositary Shares", text[:6000], re.I)
        com = re.search(r"(?:offering|offer)\s+([\d,]{6,})\s+shares of (?:our |its )?(?:Class [A-C] )?common stock", text[:12000], re.I) or \
            re.search(r"([\d,]{6,})\s+Shares\s+(?:of\s+)?(?:Class [A-C] )?Common Stock", text[:6000], re.I)
        upto = re.search(r"Up to \$([\d,]{9,})\s+(?:of\s+)?(?:Alphabet Inc\.\s+)?(?:Class [A-C] )?Common Stock", text[:3000], re.I)
        px = re.search(r"(?:public offering price|price to (?:the )?public|initial public offering price)[^$]{0,60}\$\s?([\d,]+(?:\.\d+)?)", text[:60000], re.I)
        if upto:
            eq = {"kind": "ATM 한도", "usd": float(upto.group(1).replace(",", "")) / 1e9}
        elif dep:
            n = int(dep.group(1).replace(",", ""))
            p = float(px.group(1).replace(",", "")) if px else 50.0
            eq = {"kind": "전환우선주", "shares": n, "px": p, "usd": round(n * p / 1e9, 2)}
        elif com:
            n = int(com.group(1).replace(",", ""))
            p = float(px.group(1).replace(",", "")) if px else None
            fwd = re.search(r"forward sale agreement", text[:6000], re.I)  # 선도매도: 돈은 정산 때 들어옴
            eq = {"kind": "보통주(선도매도)" if fwd else "보통주", "shares": n, "px": p, "usd": round(n * p / 1e9, 2) if p else None}
        else:
            amt = re.search(r"\$([\d,]{10,})\s+(?:of\s+)?(?:Class [A-C] )?Common Stock", text[:3000], re.I)
            if amt:
                eq = {"kind": "보통주", "usd": float(amt.group(1).replace(",", "")) / 1e9}
    head = text[:4000]
    hint = "채권" if (tr or re.search(r"notes due|debentures due", head, re.I)) else ("증자" if (eq or re.search(r"common stock|depositary shares", head, re.I)) else "기타")
    return {"prelim": prelim, "tranches": tr, "equity": eq, "hint": hint}


def prospectuses(tk: str) -> list[dict]:
    cik = CO[tk][0]
    sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))["filings"]["recent"]
    out = []
    for i, f in enumerate(sub["form"]):
        day = sub["filingDate"][i]
        if day < START or f not in ("424B2", "424B5", "424B4", "424B1"):
            continue
        acc, doc = sub["accessionNumber"][i], sub["primaryDocument"][i]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"
        p = CACHE / "pros" / f"{tk}_{acc}.json"
        if p.exists():
            out.append(json.loads(p.read_text(encoding="utf-8")))
            continue
        try:
            raw = get(url, 90).decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            print(f"[funding] {tk} {acc} 받기 실패 {e}", flush=True)
            continue
        text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
        r = {"tk": tk, "date": day, "form": f, "url": url, **parse_pros(text)}
        r["tranches"] = [list(t) for t in r["tranches"]]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        out.append(r)
    return out


def deal_quarter(tk: str, day: str, ends: list[str]) -> str:
    """발행일이 속한 회계분기 → 분기 이름. 10-Q 가 아직 없는 분기는 끝 달을 회사 주기로 늘려서 추정."""
    later = [e for e in ends if e >= day]
    if later:
        return qlabel(min(later))
    e = D(max(ends)) if ends else D(day)
    while e.isoformat() < day:
        m = e.month + 3
        y = e.year + (m - 1) // 12
        m = (m - 1) % 12 + 1
        last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
        e = dt.date(y, m, min(e.day if e.day < 28 else last, last))
    return qlabel(e.isoformat())


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    cos, deals, quarters = {}, [], set()
    for tk in CO:
        try:
            q = xbrl(tk)
            pros = prospectuses(tk)
        except Exception as e:  # noqa: BLE001
            print(f"[funding] {tk} 실패 {e}", flush=True)
            continue
        ends = sorted(q)
        finals = [r for r in pros if not r["prelim"]]
        for r in pros:
            usd = 0.0
            tr = []
            for cur, v, cpn, yr in r["tranches"]:
                u = to_usd(cur, v, r["date"])
                tr.append({"cur": cur, "amt": v, "cpn": cpn, "due": yr, "usd": None if u is None else round(u / 1e9, 2)})
                usd += u or 0
            r["usd"] = round(usd / 1e9, 2) if tr else None
            r["tr"] = tr
            r["q"] = deal_quarter(tk, r["date"], ends)
            r["type"] = "채권" if tr else ("증자" if r["equity"] else r.get("hint", "기타"))
        # 예비 설명서 중 최종본이 뒤따라 나온 것은 '예정'에서 뺌(같은 유형, 7일 안)
        for r in pros:
            r["status"] = "확정" if not r["prelim"] else (
                "대체됨" if any(f["type"] == r["type"] or (r["type"] == "기타" and f["type"] != "기타")
                                for f in finals if 0 <= (D(f["date"]) - D(r["date"])).days <= 7 and f["form"] == r["form"]) else "예정")
        cells = {}
        for e, v in q.items():
            cells[v["q"]] = {**v, "bond": 0.0, "eq": v["eq_cf"], "eq_src": "현금흐름표", "deals": []}
        for r in pros:
            if r["status"] != "확정" or r["type"] == "기타":
                continue
            c = cells.setdefault(r["q"], {"q": r["q"], "capex": None, "debt_cf": None, "eq_cf": None, "eq": 0.0, "eq_src": "설명서", "bond": 0.0, "span": "q", "deals": []})
            if r["type"] == "채권":
                c["bond"] = round(c["bond"] + (r["usd"] or 0), 2)
            elif c["eq_src"] == "설명서" and r["equity"] and r["equity"].get("kind") != "ATM 한도" and r["equity"].get("usd"):
                c["eq"] = round(c["eq"] + r["equity"]["usd"], 2)
            c["deals"].append({"date": r["date"], "type": r["type"], "usd": r["usd"] if r["type"] == "채권" else (r["equity"] or {}).get("usd"),
                               "n": len(r["tr"]), "kind": (r["equity"] or {}).get("kind"), "url": r["url"]})
        for k in cells:
            quarters.add(k)
        cos[tk] = {"name": CO[tk][1], "cells": cells, "last_10q": max(ends) if ends else None}
        for r in pros:
            if r["status"] == "대체됨" or r["type"] == "기타" or (today - D(r["date"])).days > 31:
                continue
            deals.append({"date": r["date"], "tk": tk, "type": r["type"], "status": r["status"], "usd": r["usd"] if r["type"] == "채권" else (r["equity"] or {}).get("usd"),
                          "tr": r["tr"], "eq": r["equity"], "src": "SEC " + r["form"], "url": r["url"]})
        print(f"[funding] {tk}: 분기 {len(cells)} · 설명서 {len(pros)}(최종 {len(finals)}) · 최근 10-Q {cos[tk]['last_10q']}", flush=True)
    news = json.loads(NEWS.read_text(encoding="utf-8")) if NEWS.exists() else []
    cur_q = qlabel(today.isoformat())
    quarters.add(cur_q)
    for tk, c in cos.items():       # 아직 10-Q 가 없는 분기(이번 분기 등)도 칸을 만든다
        for q in sorted(quarters):
            if q > (max(c["cells"]) if c["cells"] else q) or q not in c["cells"]:
                if q >= "2025Q1" and q <= cur_q and (not c["last_10q"] or q > qlabel(c["last_10q"])):
                    c["cells"].setdefault(q, {"q": q, "capex": None, "debt_cf": None, "eq_cf": None, "eq": 0.0, "eq_src": "설명서", "bond": 0.0, "span": "q", "deals": []})
    for n in news:                  # 가격이 확정된 뉴스(최종 설명서 전)는 그 분기 칸에 '뉴스'로 더함
        if not str(n.get("status", "")).startswith("가격 확정") or not n.get("usd"):
            continue
        c = cos.get(n["tk"], {}).get("cells", {})
        q = deal_quarter(n["tk"], n["date"], sorted(e for e in [cos[n["tk"]]["last_10q"]] if e))
        if q in c and c[q]["capex"] is None:
            c[q]["bond" if n["type"] == "채권" else "eq"] = round(c[q]["bond" if n["type"] == "채권" else "eq"] + n["usd"], 2)
            c[q]["deals"].append({"date": n["date"], "type": n["type"], "usd": n["usd"], "n": len(n.get("tr") or []), "kind": "뉴스", "url": n["url"]})
            if n["type"] != "채권":
                c[q]["eq_src"] = "뉴스"
    for n in news:
        if (today - D(n["date"])).days > 31:
            continue
        # 같은 회사·유형의 SEC 예비 설명서(±3일)가 있으면 뉴스 한 줄로 합침(뉴스가 가격·금액을 먼저 알려 줌)
        dup = [d for d in deals if d["status"] == "예정" and d["tk"] == n["tk"] and d["type"] == n["type"] and abs((D(d["date"]) - D(n["date"])).days) <= 3]
        for d in dup:
            deals.remove(d)
        deals.append({**n, "src": n.get("src", "뉴스"), "sec": dup[0]["url"] if dup else None})
    deals.sort(key=lambda d: d["date"], reverse=True)
    qs = sorted(q for q in quarters if q >= "2025Q1")
    OUT.write_text(json.dumps({"fetched": today.isoformat(), "quarters": qs, "order": list(CO), "cos": cos, "recent": deals,
                               "notes": {"eq_min": EQ_MIN / 1e9}}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[funding] {OUT} · 분기 {qs[0] if qs else '-'}~{qs[-1] if qs else '-'} · 최근 30일 {len(deals)}건", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
