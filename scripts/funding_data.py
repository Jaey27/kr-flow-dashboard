"""빅테크 자금 조달 트래커 → data/funding.json (리스크 탭 ① 「빅테크 자금 조달」 카드, Jae 11/04)

    python scripts/funding_data.py          # 하루 1번(run_daily). SEC 원문은 data/funding/ 에 캐시

대상: META · MSFT · GOOGL · AMZN · ORCL · SPCX(SpaceX) · TSLA. 기간: 1Q25 이후 분기.

- 회사채 공모 = SEC 최종 설명서(424B2·424B5) 표지의 트랜치 합계. 외화채는 발행일 환율(Yahoo)로 달러 환산.
  사모(144A)·은행 대출은 SEC 공모 서류가 없어 여기 안 들어감 → 참고용으로 현금흐름표 「장기 차입 수령액」을 같이 둔다.
- 유상증자 = 10-Q·10-K 현금흐름표의 보통주·전환우선주·IPO 발행 수령액(ATM 판매 포함). 직원 주식(스톡옵션 행사 등)을
  빼려고 분기 $2B 미만은 0으로 본다. 10-Q가 아직 없는 분기는 최종 설명서(보통주 주식 수×공모가, 전환우선 예탁주×$50)로 채움.
- FCF = 영업활동 현금흐름 − Capex(회사별 자체 정의와 다를 수 있음, 예: AMZN 은 금융리스 차감 버전도 공시).
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
CTX = ROOT / "data" / "manual" / "funding_context.json"   # 건별 매수자·목적(뉴스·IR 조사, 출처 링크)
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
    ocf = flows(g, ["NetCashProvidedByUsedInOperatingActivities"], {})
    debt = flows(g, debt_t, base)
    eq = flows(g, eq_t, base, add=True) if eq_t else {}
    out = {}
    for e, (v, kind) in cap.items():
        dv = debt.get(e, (None, ""))[0]
        ev = eq.get(e, (0.0, ""))[0] if eq_t else 0.0
        ov = ocf.get(e, (None, ""))[0]
        out[e] = {"q": qlabel(e), "end": e, "capex": round(v / 1e9, 2), "debt_cf": None if dv is None else round(dv / 1e9, 2),
                  "ocf": None if ov is None else round(ov / 1e9, 2), "fcf": None if ov is None else round((ov - v) / 1e9, 2),
                  "eq_cf": round(ev / 1e9, 2) if ev >= EQ_MIN else 0.0, "span": kind}
    return out


# ---- SEC 공모 설명서 ------------------------------------------------------------------
CUR = r"(US\$|C\$|A\$|\$|€|£|CHF\s?|¥|JPY\s?)"
TR1 = re.compile(CUR + r"\s?([\d,]+(?:\.\d+)?)\s*(million|billion)?\s+(?:in\s+)?(?:aggregate principal amount of\s+)?(?:of\s+)?(?:its |our )?(floating rate|[\d.]+\s?%)\s+(?:senior\s+)?(?:notes|bonds|debentures)\s+due\s+(\d{4})", re.I)


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


USE_TAG = [(r"capital expenditure|data center|infrastructure", "설비투자·데이터센터"), (r"repay|refinanc|redeem|retire", "부채 상환"),
           (r"repurchase", "자사주"), (r"acquisition", "인수"), (r"dividend", "배당"), (r"working capital", "운전자본"),
           (r"general corporate purposes", "일반 운영 자금")]


def use_of_proceeds(text: str) -> dict | None:
    """설명서 「Use of Proceeds」 중 'to use the net proceeds' 문장 → 원문 짧게 + 한국어 태그(회사 공식 기재)"""
    m = re.search(r"([^.]{0,160}(?:intend|expect|plan|will|may) (?:to )?use (?:the |all or a portion of the |a portion of the )?(?:net )?proceeds[^.]{0,450}\.)", text, re.I)
    if not m:
        return None
    para = m.group(1).strip()
    return {"text": para[:420], "tags": [k for pat, k in USE_TAG if re.search(pat, para, re.I)]}


def price_table(text: str) -> tuple[float | None, float | None]:
    """증자 설명서 표지 'Price to Public' 표 → (주당 공모가, 총액 합계). Class A·C 처럼 줄이 여러 개면 Total 을 모두 더함"""
    m = re.search(r"Price to (?:the )?Public", text[:40000], re.I)
    if not m:
        return None, None
    seg = text[m.start():m.start() + 2500]
    per = re.search(r"Per (?:Share|Depositary Share)[^$]{0,60}\$\s?([\d,]+\.\d+)", seg, re.I)
    tots = [float(x.replace(",", "")) for x in re.findall(r"Total(?:\s*\(\d\))?\s*\$\s?([\d,]{7,})", seg)]
    return (float(per.group(1).replace(",", "")) if per else None), (sum(tots) if tots else None)


def spreads(text: str) -> list[str]:
    out = []
    for m in re.finditer(r"Spread to (?:Benchmark )?(Treasury|Bund|Gilt|Mid-Swap)[^:]{0,20}:\s*(.{0,400}?)(?=Yield|Benchmark|Re-offer|Interest|Optional|$)", text):
        pre = "T+" if m.group(1) == "Treasury" else ("Bund+" if m.group(1) == "Bund" else "+")
        out += [pre + x for x in re.findall(r"(?:T\s*\+\s*|\+\s*)(\d+(?:\.\d+)?)\s*(?:basis points|bps)?", m.group(2))]
        if m.group(1) == "Bund":
            break   # 유로채는 Bund 스프레드만(Mid-Swap 중복 제외)
    return out


def parse_pros(text: str) -> dict:
    prelim = bool(re.search(r"subject to completion", text[:8000], re.I))
    fwp = bool(re.search(r"pricing term sheet", text[:6000], re.I))
    cover = text[:40000]
    seen, tr = set(), []
    for g in TR1.finditer(cover[:6000] if fwp else cover):
        cur, amt, unit, cpn, yr = g.groups()
        v = float(amt.replace(",", ""))
        if unit:
            v *= 1e6 if unit.lower() == "million" else 1e9
        k = (cur.strip(), v, cpn.replace(" ", "").lower(), yr)
        if v < 1e7 or k in seen:
            continue
        seen.add(k)
        tr.append(k)
    if fwp and not tr:  # 표지에 트랜치별 금액이 없는 FWP(알파벳 유로채): 총액 1줄
        t = re.search(CUR + r"\s?([\d,]{10,})\s+(?:Alphabet|Meta|Amazon|Microsoft|Oracle)", text[:3000])
        if t:
            cps = re.findall(r"([\d.]+%) Notes due (\d{4})", text[:3000])
            tr.append((t.group(1).strip(), float(t.group(2).replace(",", "")), (cps[0][0] + "~" + cps[-1][0]) if cps else "", (cps[0][1] + "~" + cps[-1][1]) if cps else ""))
    eq = None
    if not tr:
        dep = re.search(r"([\d,]{6,})\s+(?:Series [A-Z] )?Depositary Shares", text[:1200], re.I)  # 표지 제목에 있을 때만(보통주 설명서 본문의 언급은 무시)
        com = re.search(r"(?:offering|offer)\s+([\d,]{6,})\s+shares of (?:our |its )?(?:Class [A-C] )?common stock", text[:12000], re.I) or \
            re.search(r"([\d,]{6,})\s+Shares\s+(?:of\s+)?(?:Class [A-C] )?Common Stock", text[:6000], re.I)
        upto = re.search(r"Up to \$([\d,]{9,})\s+(?:of\s+)?(?:Alphabet Inc\.\s+)?(?:Class [A-C] )?Common Stock", text[:3000], re.I)
        px = re.search(r"(?:public offering price|price to (?:the )?public|initial public offering price)[^$]{0,60}\$\s?([\d,]+(?:\.\d+)?)", text[:60000], re.I)
        per, tot = price_table(text)
        if upto:
            eq = {"kind": "ATM 한도", "usd": float(upto.group(1).replace(",", "")) / 1e9}
        elif dep:
            n = int(dep.group(1).replace(",", ""))
            p = per or (float(px.group(1).replace(",", "")) if px else 50.0)
            eq = {"kind": "전환우선주", "shares": n, "px": p, "usd": round((tot or n * p) / 1e9, 2)}
        elif com:
            n = int(com.group(1).replace(",", ""))
            two = re.search(r"and\s+([\d,]{6,})\s+shares of (?:our )?Class C", text[:3000], re.I)  # 알파벳 A주+C주 동시 공모
            if two:
                n += int(two.group(1).replace(",", ""))
            p = per or (float(px.group(1).replace(",", "")) if px else None)
            fwd = re.search(r"forward sale agreement", text[:6000], re.I)  # 선도매도: 돈은 정산 때 들어옴
            usd = tot if tot else (n * p if p else None)
            eq = {"kind": ("보통주(선도매도)" if fwd else "보통주") + (" A·C주" if two else ""), "shares": n, "px": p, "usd": round(usd / 1e9, 2) if usd else None}
        else:
            amt = re.search(r"\$([\d,]{10,})\s+(?:of\s+)?(?:Class [A-C] )?Common Stock", text[:3000], re.I)
            if amt:
                eq = {"kind": "보통주", "usd": float(amt.group(1).replace(",", "")) / 1e9}
    head = text[:4000]
    hint = "채권" if (tr or re.search(r"notes due|debentures due", head, re.I)) else ("증자" if (eq or re.search(r"common stock|depositary shares", head, re.I)) else "기타")
    return {"prelim": prelim, "fwp": fwp, "tranches": tr, "equity": eq, "hint": hint, "use": None if (prelim or fwp) else use_of_proceeds(text),
            "spreads": spreads(text) if fwp else []}


PARSE_VER = "5"   # parse_pros 가 바뀌면 올림 → 캐시된 설명서를 다시 읽음(원문은 data/funding/raw 에서, 다시 받지 않음)


def prospectuses(tk: str) -> list[dict]:
    cik = CO[tk][0]
    sub = json.loads(get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json"))["filings"]["recent"]
    out = []
    today = dt.date.today()
    for i, f in enumerate(sub["form"]):
        day = sub["filingDate"][i]
        if day < START or f not in ("424B2", "424B5", "424B4", "424B1", "FWP"):
            continue
        if f == "FWP" and (today - D(day)).days > 45:   # FWP(가격 확정 시트)는 최근 것만 → 최종 설명서가 곧 대체
            continue
        acc, doc = sub["accessionNumber"][i], sub["primaryDocument"][i]
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"
        p = CACHE / "pros" / f"{tk}_{acc}.json"
        raw_p = CACHE / "raw" / f"{tk}_{acc}.txt"
        if p.exists():
            r = json.loads(p.read_text(encoding="utf-8"))
            if r.get("ver") == PARSE_VER:
                if not (f == "FWP" and not r["fwp"]):
                    out.append(r)
                continue
        if raw_p.exists():
            text = raw_p.read_text(encoding="utf-8")
        else:
            try:
                raw = get(url, 90).decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001
                print(f"[funding] {tk} {acc} 받기 실패 {e}", flush=True)
                continue
            text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
            raw_p.parent.mkdir(parents=True, exist_ok=True)
            raw_p.write_text(text[:150000], encoding="utf-8")
        r = {"tk": tk, "date": day, "form": f, "url": url, "ver": PARSE_VER, **parse_pros(text)}
        r["tranches"] = [list(t) for t in r["tranches"]]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(r, ensure_ascii=False), encoding="utf-8")
        if f == "FWP" and not r["fwp"]:
            continue   # 가격 시트가 아닌 FWP(광고·발표 등)
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


def near(a: str, b: str, days: int) -> bool:
    return abs((D(a) - D(b)).days) <= days


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    today = dt.date.today()
    news = json.loads(NEWS.read_text(encoding="utf-8")) if NEWS.exists() else []
    ctx = json.loads(CTX.read_text(encoding="utf-8")) if CTX.exists() else []
    cos, recent, quarters = {}, [], set()
    cur_q = qlabel(today.isoformat())
    for tk in CO:
        try:
            q = xbrl(tk)
            pros = prospectuses(tk)
        except Exception as e:  # noqa: BLE001
            print(f"[funding] {tk} 실패 {e}", flush=True)
            continue
        ends = sorted(q)
        for r in pros:
            usd, tr = 0.0, []
            sp = r.get("spreads") or []
            for j, (cur, v, cpn, yr) in enumerate(r["tranches"]):
                u = to_usd(cur, v, r["date"])
                tr.append({"cur": cur, "amt": v, "cpn": cpn, "due": yr, "usd": None if u is None else round(u / 1e9, 2),
                           "spread": sp[j] if len(sp) == len(r["tranches"]) else None})
                usd += u or 0
            r["usd"] = round(usd / 1e9, 2) if tr else None
            r["tr"] = tr
            r["q"] = deal_quarter(tk, r["date"], ends)
            r["type"] = "채권" if tr else ("증자" if r["equity"] else r.get("hint", "기타"))
        finals = [r for r in pros if not r["prelim"] and not r["fwp"]]
        fwps = [r for r in pros if r["fwp"]]
        for r in pros:   # 예비 설명서 → 예정, FWP 가격 시트 → 가격 확정. 뒤에 최종본(같은 유형, 7일 안)이 나오면 대체됨
            if not r["prelim"] and not r["fwp"]:
                r["status"] = "확정"
                continue
            later = [f for f in finals + ([] if r["fwp"] else fwps) if f["type"] == r["type"] and 0 <= (D(f["date"]) - D(r["date"])).days <= 7]
            r["status"] = "대체됨" if later else ("가격 확정" if r["fwp"] else "예정")
            if r["status"] == "대체됨" and r["fwp"]:   # 스프레드는 FWP 에만 있음 → 최종본 트랜치에 옮김
                for t_f in later[0]["tr"]:
                    for t_w in r["tr"]:
                        if t_f["due"] == t_w["due"] and t_f["cpn"] == t_w["cpn"]:
                            t_f["spread"] = t_w["spread"]
        cells = {}
        for e, v in q.items():
            cells[v["q"]] = {**v, "bond": 0.0, "eq": v["eq_cf"], "eq_src": "현금흐름표", "deals": []}
        for qq in sorted(set([cur_q] + [r["q"] for r in pros])):
            if "2025Q1" <= qq <= cur_q and qq not in cells and (not ends or qq > qlabel(max(ends))):
                cells[qq] = {"q": qq, "capex": None, "fcf": None, "ocf": None, "debt_cf": None, "eq_cf": None, "eq": 0.0, "eq_src": "설명서", "bond": 0.0, "span": "q", "deals": []}
        for r in pros:
            if r["status"] not in ("확정", "가격 확정", "예정") or r["type"] == "기타" or r["q"] not in cells:
                continue
            c = cells[r["q"]]
            amt = r["usd"] if r["type"] == "채권" else (r["equity"] or {}).get("usd")
            atm = (r["equity"] or {}).get("kind") == "ATM 한도"
            if atm and any((d.get("eq") or {}).get("kind") == "ATM 한도" and (d.get("eq") or {}).get("usd") == r["equity"]["usd"] for d in c["deals"]):
                continue  # 같은 ATM 한도 보충 설명서
            if r["status"] == "확정":
                if r["type"] == "채권":
                    c["bond"] = round(c["bond"] + (amt or 0), 2)
                elif c["eq_src"] == "설명서" and not atm and amt:
                    c["eq"] = round(c["eq"] + amt, 2)
            elif r["status"] == "가격 확정" and amt:
                k = ("bond" if r["type"] == "채권" else "eq") + "_px"
                c[k] = round(c.get(k, 0.0) + amt, 2)
            c["deals"].append({"date": r["date"], "tk": tk, "type": r["type"], "status": r["status"], "usd": amt, "n": len(r["tr"]),
                               "kind": (r["equity"] or {}).get("kind"), "url": r["url"], "src": "SEC " + r["form"], "tr": r["tr"], "eq": r["equity"], "use": r.get("use")})
        quarters.update(cells)
        cos[tk] = {"name": CO[tk][1], "cells": cells, "last_10q": max(ends) if ends else None}
        print(f"[funding] {tk}: 분기 {len(cells)} · 설명서 {len(pros)}(최종 {len(finals)}·FWP {len(fwps)}) · 최근 10-Q {cos[tk]['last_10q']}", flush=True)
    # 뉴스: 같은 회사·유형의 SEC 서류(±3일)가 있으면 그 건에 맥락만 붙이고(금액은 SEC 우선), 없으면 뉴스 단독 건(가격 확정 → *_px, 추진 → *_plan)
    for n in news:
        st = str(n.get("status", ""))
        c = cos.get(n["tk"], {}).get("cells", {})
        hit = [d for cell in c.values() for d in cell["deals"] if d["type"] == n["type"] and near(d["date"], n["date"], 3) and d.get("src", "").startswith("SEC")]
        if n.get("separate"):   # 같은 날 SEC 건과 별개인 뉴스(예: META 유로 트랜치)
            hit = []
        if hit:
            for d in hit:
                d.setdefault("news", []).append({"note": n.get("note"), "url": n["url"], "src": n.get("src"), "notion": n.get("notion")})
                if d["status"] == "예정" and st.startswith("가격 확정") and n.get("usd"):   # SEC 는 예비 설명서뿐 → 뉴스가 가격을 먼저 확인
                    d["status"], d["usd"] = "가격 확정(뉴스)", n["usd"]
                    if n.get("eq"):
                        d["eq"] = n["eq"]
                    if n.get("tr") and not d["tr"]:
                        d["tr"] = n["tr"]
                    cell = next(cl for cl in c.values() if d in cl["deals"])
                    k = ("bond" if n["type"] == "채권" else "eq") + "_px"
                    cell[k] = round(cell.get(k, 0.0) + n["usd"], 2)
            continue
        q = deal_quarter(n["tk"], n["date"], sorted(e for e in [cos.get(n["tk"], {}).get("last_10q")] if e))
        if q not in c:
            continue
        if n.get("usd") and c[q]["capex"] is None and (st.startswith("가격 확정") or st.startswith("추진")):
            k = ("bond" if n["type"] == "채권" else "eq") + ("_px" if st.startswith("가격 확정") else "_plan")
            c[q][k] = round(c[q].get(k, 0.0) + n["usd"], 2)
        c[q]["deals"].append({"date": n["date"], "tk": n["tk"], "type": n["type"], "status": st, "usd": n.get("usd"), "n": len(n.get("tr") or []), "kind": "뉴스",
                              "url": n["url"], "src": n.get("src", "뉴스"), "tr": n.get("tr") or [], "eq": n.get("eq"), "note": n.get("note"), "notion": n.get("notion")})
    # 건별 매수자·목적(조사 파일 data/manual/funding_context.json): 같은 회사·유형·±3일 건에 붙임
    for x in ctx:
        for cell in cos.get(x["tk"], {}).get("cells", {}).values():
            for d in cell["deals"]:
                if d["type"] == x["type"] and near(d["date"], x["date"], 3):
                    d["ctx"] = {k: x.get(k) for k in ("buyers", "buyers_src", "purpose", "purpose_src", "amount_note")}
    for c in cos.values():
        for cell in c["cells"].values():
            for d in cell["deals"]:
                if (today - D(d["date"])).days <= 31 and (d.get("eq") or {}).get("kind") != "ATM 한도":
                    recent.append(d)
    recent.sort(key=lambda d: d["date"], reverse=True)
    qs = sorted(q for q in quarters if q >= "2025Q1")
    OUT.write_text(json.dumps({"fetched": today.isoformat(), "quarters": qs, "order": list(CO), "cos": cos, "recent": recent,
                               "notes": {"eq_min": EQ_MIN / 1e9}}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[funding] {OUT} · 분기 {qs[0] if qs else '-'}~{qs[-1] if qs else '-'} · 최근 30일 {len(recent)}건", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
