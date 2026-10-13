# -*- coding: utf-8 -*-
"""금융투자협회 FreeSIS (freesis.kofia.or.kr) — 신용공여 잔고·증시자금.

- 웹 화면이 쓰는 JSON 엔드포인트를 그대로 쓴다(인증 없음).
- ★ 세션 쿠키(WMONID/JSESSIONID)가 없으면 POST 가 HTML 오류 페이지를 돌려준다.
  화면 URL 을 한 번 GET 해 쿠키를 받은 뒤 POST 한다.
- 기준일 T 의 값은 T+1 영업일에 올라온다(장중 아님). 단위는 백만원.
"""

from __future__ import annotations

import datetime as dt

from common import request_json, session

BASE = "https://freesis.kofia.or.kr"
WARMUP = BASE + "/stat/FreeSIS.do?parentDivId=MSIS10000000000000&serviceId=STATSCU0100000060"
API = BASE + "/meta/getMetaDataList.do"

# OBJ_NM -> (원장 이름, {TMPVn: 필드})
TABLES = {
    # 신용공여 잔고 추이
    "STATSCU0100000070BO": ("freesis_credit", {
        "TMPV2": "credit_total",      # 신용거래융자 전체
        "TMPV3": "credit_kospi",      # 신용거래융자 유가증권
        "TMPV4": "credit_kosdaq",     # 신용거래융자 코스닥
        "TMPV5": "short_total",       # 신용거래대주 전체
        "TMPV8": "ipo_loan",          # 청약자금 대출
        "TMPV9": "collateral_loan",   # 예탁증권 담보융자
    }),
    # 증시자금 추이
    "STATSCU0100000060BO": ("freesis_funds", {
        "TMPV2": "deposit",           # 투자자예탁금(장내파생 거래예수금 제외)
        "TMPV3": "deriv_deposit",     # 장내파생상품 거래예수금
        "TMPV4": "rp_balance",        # 대고객 RP 매도잔고
        "TMPV5": "unpaid",            # 위탁매매 미수금
        "TMPV6": "forced_sale",       # 미수금 대비 실제 반대매매금액
        "TMPV7": "forced_ratio",      # 미수금 대비 반대매매비중(%)
    }),
}


class FreeSIS:
    def __init__(self) -> None:
        self.s = session(referer=WARMUP)
        self.s.get(WARMUP, timeout=30)

    def table(self, obj: str, start: dt.date, end: dt.date) -> dict[str, dict]:
        body = {"dmSearch": {"tmpV40": "1000000", "tmpV41": "1", "tmpV1": "D",
                             "tmpV45": start.strftime("%Y%m%d"), "tmpV46": end.strftime("%Y%m%d"),
                             "OBJ_NM": obj}}
        js = request_json(self.s, "POST", API, json=body)
        if "ds1" not in js:
            raise RuntimeError(f"FreeSIS {obj}: 예상 밖 응답 {str(js)[:200]}")
        fields = TABLES[obj][1]
        out = {}
        for r in js["ds1"]:
            d = r["TMPV1"]
            day = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            out[day] = {f: r.get(k) for k, f in fields.items()}
        return out

    def latest_date(self, obj: str, today: dt.date) -> str | None:
        rows = self.table(obj, today - dt.timedelta(days=20), today)
        return max(rows) if rows else None
