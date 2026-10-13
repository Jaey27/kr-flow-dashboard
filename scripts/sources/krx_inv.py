# -*- coding: utf-8 -*-
"""KRX 정보데이터시스템(로그인 필요) — 투자자별 전 종목 매수·매도 거래대금 (pykrx).

- pykrx.get_market_net_purchases_of_equities(D, D, "ALL", 투자자) 한 번에 그날 전 종목이 온다.
- 로그인: .env 의 KRX_ID / KRX_PW (사용자가 직접 넣는다). pykrx 는 import 시점에 환경변수를 읽으므로
  반드시 import 전에 os.environ 에 올린다.
- 원천 확정 시각은 KRX 투자자별 확정(18시경) — 그 이후에 받는다.
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import os

from common import DATA, ROOT, log

INVESTORS = {"indiv": "개인", "foreign": "외국인", "inst": "기관합계"}
RAW_DIR = DATA / "krx_inv"          # 종목별 원자료(월별 gz, git 제외)


def load_env() -> bool:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in ("KRX_ID", "KRX_PW") and v.strip():
                    os.environ.setdefault(k.strip(), v.strip())
    return bool(os.environ.get("KRX_ID") and os.environ.get("KRX_PW"))


_stock = None


def _api():
    global _stock
    if _stock is None:
        if not load_env():
            raise RuntimeError("KRX_ID/KRX_PW 가 .env 에 없다 — README '섹터 수급' 절 참고")
        from pykrx import stock  # noqa: PLC0415 - 환경변수 적재 후 import
        _stock = stock
    return _stock


def day(d: dt.date) -> dict[str, dict[str, list[int]]] | None:
    """{투자자키: {종목코드: [매수대금, 매도대금]}} (원). 휴장/미공개면 None."""
    st = _api()
    ymd = d.strftime("%Y%m%d")
    out = {}
    for key, name in INVESTORS.items():
        df = st.get_market_net_purchases_of_equities(ymd, ymd, "ALL", name)
        if df is None or df.empty:
            return None
        out[key] = {str(t): [int(r["매수거래대금"]), int(r["매도거래대금"])] for t, r in df.iterrows()}
    return out


def raw_path(d: str):
    return RAW_DIR / f"{d[:7]}.json.gz"


def load_raw_month(month: str) -> dict:
    p = RAW_DIR / f"{month}.json.gz"
    if p.exists():
        with gzip.open(p, "rt", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_raw_day(d: str, data: dict) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    m = load_raw_month(d[:7])
    m[d] = data
    p = raw_path(d)
    tmp = p.with_suffix(".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(m, f, separators=(",", ":"))
    os.replace(tmp, p)


def has_raw(d: str) -> bool:
    return d in load_raw_month(d[:7])


def login_check() -> str:
    """로그인 가능 여부를 값 노출 없이 점검."""
    if not load_env():
        return "KRX_ID/KRX_PW 없음"
    try:
        r = day(dt.date(2026, 10, 12))
        return "OK" if r else "로그인은 됐으나 데이터 없음"
    except Exception as e:  # noqa: BLE001
        log(f"KRX 로그인/조회 실패: {e!r}"[:300])
        return "실패"
