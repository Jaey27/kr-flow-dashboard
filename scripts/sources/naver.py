# -*- coding: utf-8 -*-
"""네이버 증권 모바일 API (m.stock.naver.com) — 종목별 투자자 순매수 수량.

`api/stock/{code}/trend?pageSize=60[&bizdate=YYYYMMDD]`
  - 개인·외국인·기관 순매수 '수량'(주), 외국인 보유율(%), 종가. 금액은 주지 않는다.
  - pageSize 는 60 까지(100 은 400). bizdate 를 주면 그 날짜 '이전' 60영업일이 온다 → 과거로 넘기며 받는다.
  - 구 finance.naver.com/sise/*.naver 페이지들은 '더 이상 제공되지 않습니다'로 막혔다(2026-10 확인).
"""

from __future__ import annotations

import datetime as dt

from common import request_json, session

API = "https://m.stock.naver.com/api/stock/{code}/trend"


def _num(s) -> float | None:
    if s in (None, "", "-"):
        return None
    return float(str(s).replace(",", "").replace("+", "").replace("%", ""))


class Naver:
    def __init__(self) -> None:
        self.s = session(referer="https://m.stock.naver.com/")

    def trend(self, code: str, start: dt.date, max_pages: int = 15) -> dict[str, dict]:
        out: dict[str, dict] = {}
        bizdate = None
        for _ in range(max_pages):
            params = {"pageSize": 60}
            if bizdate:
                params["bizdate"] = bizdate
            js = request_json(self.s, "GET", API.format(code=code), params=params)
            if not isinstance(js, list) or not js:
                break
            for x in js:
                b = x["bizdate"]
                d = f"{b[:4]}-{b[4:6]}-{b[6:]}"
                if d < start.isoformat():
                    return out
                out[d] = {
                    "indiv": _num(x.get("individualPureBuyQuant")),
                    "foreign": _num(x.get("foreignerPureBuyQuant")),
                    "organ": _num(x.get("organPureBuyQuant")),
                    "hold": _num(x.get("foreignerHoldRatio")),
                    "close": _num(x.get("closePrice")),
                }
            bizdate = js[-1]["bizdate"]
        return out
