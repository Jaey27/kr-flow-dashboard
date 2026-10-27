# -*- coding: utf-8 -*-
"""다음 금융 (finance.daum.net/api) — 투자자별 순매수·지수·코스피200 선물.

- Referer 만 맞으면 인증 없이 JSON 을 준다. 원천은 KRX/코스콤 시세이며 장중에는 잠정치가 들어온다.
- 투자자별 순매수(원): 개인/외국인/기관계 + details(금융투자·보험·투신·사모·은행·기타금융·연기금·기타법인·기타외국인).
- 선물 `future/{ISIN}/days` 의 foreign/institution/privateSettlement(계약)는 **월물별 값이 아니라
  코스피200 선물 전체 합계**다. 같은 날짜면 어느 월물을 조회해도 같은 값이 나온다
  (2026-09 롤오버 주간 근월·차월·원월 대조로 확인). 반면 unsettledVolume·accTradeVolume 은
  월물별 값이라 미결제약정은 상장 월물 전부를 더해야 한다.
"""

from __future__ import annotations

import datetime as dt

from common import log, request_json, session

API = "https://finance.daum.net/api"
REF_INVESTOR = "https://finance.daum.net/domestic/investors"
REF_FUTURES = "https://finance.daum.net/domestic/futures"

DETAIL_FIELDS = {
    "FINANCIAL_INVESTOR": "fin_invest",     # 금융투자
    "INSURANCE_COMPANIES": "insurance",     # 보험
    "MUTUAL_FUND": "trust",                 # 투신
    "PRIVATE_EQUITY_FUND": "private_fund",  # 사모
    "BANK": "bank",                         # 은행
    "ETC_FINANCIAL_INSTITUTION": "etc_fin", # 기타금융
    "PENSION_FUND": "pension",              # 연기금
    "ETC_CORPORATION": "etc_corp",          # 기타법인
    "ETC_FOREIGN": "etc_foreign",           # 기타외국인
}

EOK = 1e8  # 원 -> 억원


def _day(s: str) -> str:
    return s[:10]


def _pages(s, url: str, params: dict, start: dt.date, per: int = 250, max_pages: int = 20):
    """최신순 페이지를 start 이전 날짜가 나올 때까지 넘긴다."""
    for page in range(1, max_pages + 1):
        js = request_json(s, "GET", url, params={**params, "page": page, "perPage": per, "pagination": "true"})
        data = js.get("data") or []
        yield from data
        if not data or _day(data[-1]["date"]) < start.isoformat() or page >= (js.get("totalPages") or 1):
            return


class Daum:
    def __init__(self) -> None:
        self.s_inv = session(referer=REF_INVESTOR)
        self.s_fut = session(referer=REF_FUTURES)

    # ---- 현물 투자자별 순매수 ------------------------------------------------
    def investor(self, market: str, start: dt.date) -> dict[str, dict]:
        out = {}
        for x in _pages(self.s_inv, f"{API}/investor/{market}/days", {"details": "true"}, start):
            d = _day(x["date"])
            if d < start.isoformat():
                break
            row = {
                "indiv": round(x["individualStraightPurchasePrice"] / EOK, 2),
                "foreign": round(x["foreignStraightPurchasePrice"] / EOK, 2),
                "inst": round(x["institutionStraightPurchasePrice"] / EOK, 2),
            }
            det = x.get("details") or {}
            for k, f in DETAIL_FIELDS.items():
                if k in det and det[k] is not None:
                    row[f] = round(det[k] / EOK, 2)
            out[d] = row
        return out

    # ---- 지수 종가 -------------------------------------------------------------
    def index(self, market: str, start: dt.date) -> dict[str, float]:
        out = {}
        for x in _pages(self.s_inv, f"{API}/market_index/days", {"market": market}, start):
            d = _day(x["date"])
            if d < start.isoformat():
                break
            out[d] = {"close": x["tradePrice"], "val": x.get("accTradePrice")}  # val 단위 백만원(10/27 코스피 16,417,010 = 16.4조)
        return out

    # ---- 종목별: 외국인 보유주식 수·지분율, 외국인/기관 순매수 수량, 종가·평균가 ----------
    def stock(self, code: str, start: dt.date) -> dict[str, dict]:
        """foreignOwnShares 는 그날 장 마감 기준 외국인 보유 주식 수(한도 없는 종목은 상장주식 대비 비율이 Rate)."""
        s = session(referer=f"https://finance.daum.net/quotes/A{code}")
        out = {}
        for x in _pages(s, f"{API}/investor/days", {"symbolCode": f"A{code}"}, start, per=300):
            d = _day(x["date"])
            if d < start.isoformat():
                break
            vol, val = x.get("accTradeVolume") or 0, x.get("accTradePrice") or 0
            out[d] = {
                "fo_shares": x.get("foreignOwnShares"),
                "fo_rate": round(x["foreignOwnSharesRate"] * 100, 4) if x.get("foreignOwnSharesRate") is not None else None,
                "f_net": x.get("foreignStraightPurchaseVolume"),
                "i_net": x.get("institutionStraightPurchaseVolume"),
                "close": x.get("tradePrice"),
                "vwap": round(val / vol, 1) if vol else x.get("tradePrice"),
            }
        return out

    # ---- 코스피200 선물 ----------------------------------------------------------
    def future_days(self, code: str, start: dt.date) -> dict[str, dict]:
        out = {}
        for x in _pages(self.s_fut, f"{API}/future/{code}/days", {}, start, per=300):
            d = _day(x["date"])
            if d < start.isoformat():
                break
            out[d] = {
                "foreign": x.get("foreignSettlement"),
                "inst": x.get("institutionSettlement"),
                "indiv": x.get("privateSettlement"),
                "oi": x.get("unsettledVolume") or 0,
                "vol": x.get("accTradeVolume") or 0,
                "price": x.get("tradePrice"),
            }
        return out


# --------------------------------------------------------------------------
# 코스피200 선물 월물 ISIN
#   ~2025년 만기: KR4101 + 연도문자(V=2024, W=2025) + 월(3/6/9/C) + 000 + 검증숫자
#   2026년~ 만기: KR4A01 + 연도 끝자리       + 월(3/6/9/C) + 000 + 검증숫자
#   (2026-10 Daum futures/masters 와 실제 조회로 확인. 2030년 이후 체계는 미확인)
# --------------------------------------------------------------------------
OLD_YEAR = {2023: "T", 2024: "V", 2025: "W"}
MONTH = {3: "3", 6: "6", 9: "9", 12: "C"}


def isin_check(body: str) -> str:
    digits = "".join(str(int(c, 36)) for c in body)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        v = int(ch)
        if i % 2 == 0:
            v *= 2
            if v > 9:
                v -= 9
        total += v
    return str((10 - total % 10) % 10)


def future_code(year: int, month: int) -> str | None:
    if year <= 2025:
        if year not in OLD_YEAR:
            return None
        body = f"KR4101{OLD_YEAR[year]}{MONTH[month]}000"
    elif year <= 2029:
        body = f"KR4A01{year % 10}{MONTH[month]}000"
    else:
        return None
    return body + isin_check(body)


def expiry(year: int, month: int) -> dt.date:
    """둘째 목요일(휴장 시 앞당겨지지만 '만기 지났나' 판정용이라 여유를 두고 쓴다)."""
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(3 - d.weekday()) % 7)
    return d + dt.timedelta(days=7)


def contracts(start: dt.date, until: dt.date) -> list[tuple[int, int, str]]:
    """만기가 [start, until+3년] 사이인 분기 월물 (연, 월, ISIN)."""
    out = []
    for y in range(start.year, until.year + 4):
        for m in (3, 6, 9, 12):
            if expiry(y, m) < start:
                continue
            code = future_code(y, m)
            if code:
                out.append((y, m, code))
    return out


def aggregate_futures(per_contract: dict[str, dict[str, dict]]) -> tuple[dict[str, dict], int]:
    """월물별 일자 데이터 -> 일자별 {foreign, inst, indiv(전체 합계), oi(합), vol(합), price(최다 거래 월물)}.

    반환: (rows, 불일치 건수). 투자자 값이 월물마다 다르면 Daum 의 '전체 합계' 전제가 깨진 것이다.
    """
    by_day: dict[str, list[dict]] = {}
    for rows in per_contract.values():
        for d, r in rows.items():
            by_day.setdefault(d, []).append(r)
    out, mismatch = {}, 0
    for d, rs in sorted(by_day.items()):
        inv = {(r["foreign"], r["inst"], r["indiv"]) for r in rs if r["foreign"] is not None}
        if len(inv) > 1:
            mismatch += 1
            log(f"[WARN] 선물 투자자 값이 월물마다 다름 {d}: {sorted(inv)}")
        # 가장 많이 나온 조합을 쓴다(불일치 시에도 근월물 값이 다수결로 이긴다)
        best = max(inv, key=lambda t: sum(1 for r in rs if (r["foreign"], r["inst"], r["indiv"]) == t)) if inv else (None, None, None)
        front = max(rs, key=lambda r: r["vol"])
        out[d] = {
            "foreign": best[0], "inst": best[1], "indiv": best[2],
            "oi": sum(r["oi"] for r in rs),
            "vol": sum(r["vol"] for r in rs),
            "price": front["price"],
        }
    return out, mismatch
