# -*- coding: utf-8 -*-
"""KRX Open API (data-dbg.krx.co.kr) — 종목별 일별 시세·시가총액.

- 인증키: .env 의 KRX_API_KEY (헤더 AUTH_KEY). 서비스마다 이용신청이 따로 필요하다.
  2026-10-13 현재 승인: sto/stk_bydd_trd(유가증권), sto/ksq_bydd_trd(코스닥). idx·drv 는 401.
- 기준일 D 의 값은 D+1 오전(08시 전후)에 열린다. 당일 값은 빈 배열.
- 한 번 호출에 그날 시장 전 종목(코스피 ~950, 코스닥 ~1,800)이 온다 → 시장 시총 = MKTCAP 합.
"""

from __future__ import annotations

import datetime as dt
import os

from common import ROOT, request_json, session

API = "https://data-dbg.krx.co.kr/svc/apis/sto/{svc}"
IDX_API = "https://data-dbg.krx.co.kr/svc/apis/idx/drvprod_dd_trd"   # 파생상품지수 일별시세 (코스피200 변동성지수 포함)
SERVICES = {"kospi": "stk_bydd_trd", "kosdaq": "ksq_bydd_trd"}
WATCH = ("005930", "005935", "000660")   # 삼성전자, 삼성전자우, SK하이닉스
EOK = 1e8


def api_key() -> str:
    key = os.environ.get("KRX_API_KEY")
    if not key:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("KRX_API_KEY="):
                    key = line.split("=", 1)[1].strip()
    if not key:
        raise RuntimeError("KRX_API_KEY 가 없다 — .env 에 KRX_API_KEY=... 를 넣어라")
    return key


class KRX:
    def __init__(self) -> None:
        self.s = session()
        self.s.headers["AUTH_KEY"] = api_key()

    def day(self, d: dt.date) -> dict | None:
        """그날 코스피·코스닥 시총 합계와 관심 종목 행. 아직 안 열렸으면 None."""
        row: dict = {}
        for mk, svc in SERVICES.items():
            js = request_json(self.s, "GET", API.format(svc=svc), params={"basDd": d.strftime("%Y%m%d")})
            if "OutBlock_1" not in js:
                raise RuntimeError(f"KRX {svc} {d}: {str(js)[:160]}")
            items = js["OutBlock_1"]
            if not items:
                return None
            row[f"{mk}_mcap"] = round(sum(int(x["MKTCAP"]) for x in items) / EOK, 1)
            row[f"{mk}_n"] = len(items)
            for x in items:
                if x["ISU_CD"] in WATCH:
                    c = x["ISU_CD"]
                    row[f"s{c}_close"] = int(x["TDD_CLSPRC"])
                    row[f"s{c}_mcap"] = round(int(x["MKTCAP"]) / EOK, 1)
                    row[f"s{c}_shares"] = int(x["LIST_SHRS"])
        return row


class Unauthorized(RuntimeError):
    pass


def vkospi_day(k: "KRX", d: dt.date) -> float | None:
    """코스피200 변동성지수(VKOSPI) 종가. 서비스 미승인이면 Unauthorized."""
    js = request_json(k.s, "GET", IDX_API, params={"basDd": d.strftime("%Y%m%d")})
    if str(js.get("respCode")) == "401":
        raise Unauthorized("KRX Open API 파생상품지수 시세정보 미승인(401)")
    for x in js.get("OutBlock_1", []):
        name = x.get("IDX_NM", "")
        if "변동성" in name and "선물" not in name:
            for key, v in x.items():
                if key.startswith("CLSPRC") and v not in ("", "-", None):
                    return float(str(v).replace(",", ""))
    return None
