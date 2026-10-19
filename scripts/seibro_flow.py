"""한국인 해외주식 결제(예탁결제원 SEIBro) → data/seibro.json

    python scripts/seibro_flow.py            # 미국 주식 일별 매수·매도 결제금액(2년) + 관심 종목 일별(최근 1년, 일자별 캐시)

- 출처: SEIBro 국제거래 > 외화증권예탁결제 > 시장별내역 / 종목별내역(주식TOP50). 단위 USD. 로그인 없음(세션 쿠키만).
- 기준일 = 한국시간 결제 처리일(미국 T+1 결제 → 대략 미국 매매일 다음 날). 공식 안내: 자료 인용 시 출처 "한국예탁결제원 증권정보포털(SEIBro)".
- 종목별은 그날 매수결제 상위 50위 안에 들 때만 값이 있다(빠진 날 = 50위 밖, 0이 아님).
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "seibro.json"
CACHE = ROOT / "data" / "seibro_cache"
KST = timezone(timedelta(hours=9))
URL = "https://seibro.or.kr/websquare/engine/proworks/callServletService.jsp"
PAGE = "https://seibro.or.kr/websquare/control.jsp?w2xPath=/IPORTAL/user/ovsSec/BIP_CNTS10013V.xml&menuNo=921"
WATCH = {"US25459W4583": "SOXL", "US5951121038": "MU", "US84615Q1031": "SPCX", "US25461A3876": "KORU", "US46090E1038": "QQQ"}
RE_TOP = re.compile(r'<ISIN value="([^"]*)"/><KOR_SECN_NM value="([^"]*)"/><SUM_FRSEC_BUY_AMT value="([^"]*)"/><SUM_FRSEC_SELL_AMT value="([^"]*)"/>'
                    r'<SUM_FRSEC_TOT_AMT value="([^"]*)"/><SUM_FRSEC_NET_BUY_AMT value="([^"]*)"')


def client() -> httpx.Client:
    c = httpx.Client(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126", "Referer": PAGE}, timeout=60)
    c.get(PAGE)
    return c


def post(c, body: str) -> str:
    r = c.post(URL, content=body.encode("utf-8"), headers={"Content-Type": 'application/xml; charset="UTF-8"'})
    time.sleep(1.0)
    return r.text


def us_daily(c, s: date, e: date) -> dict:
    b = ('<reqParam action="getNationsSettlementList" task="ksd.safe.bip.cnts.OvsSec.process.OvsSecIsinPTask"><MENU_NO value="862"/>'
         '<CMM_BTN_ABBR_NM value="total_search,openall,print,hwp,word,pdf,seach,xls,"/><W2XPATH value="/IPORTAL/user/ovsSec/BIP_CNTS10012V.xml"/>'
         f'<PG_START value="1"/><PG_END value="400"/><ic_start value="{s:%Y%m%d}"/><ic_end value="{e:%Y%m%d}"/><S_TYPE value="1"/><S_TYPE2 value="1"/>'
         '<GIGAN value="1"/><S_COUNTRY value="US"/></reqParam>')
    t = post(c, b)
    out = {}
    for m in re.finditer(r'<GIGAN value="(\d{8})"/>.*?<AA2 value="([^"]*)"/><AA3 value="[^"]*"/><AA4 value="([^"]*)"/>', t, re.S):
        d = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}"
        out[d] = [round(float(m.group(2)) / 1e6, 2), round(float(m.group(3)) / 1e6, 2)]  # 백만달러: 매수, 매도
    return out


def us_custody(c, s: date, e: date) -> dict:
    """미국 주식 보관금액(한국 투자자 보유 잔고, 종가 기준, USD) 일별 — 시장별내역 '보관금액'."""
    b = ('<reqParam action="getNationsSettlremaList" task="ksd.safe.bip.cnts.OvsSec.process.OvsSecIsinPTask"><MENU_NO value="862"/>'
         '<CMM_BTN_ABBR_NM value="total_search,openall,print,hwp,word,pdf,seach,xls,"/><W2XPATH value="/IPORTAL/user/ovsSec/BIP_CNTS10012V.xml"/>'
         f'<PG_START value="1"/><PG_END value="400"/><ic_start value="{s:%Y%m%d}"/><ic_end value="{e:%Y%m%d}"/><S_TYPE value="3"/><S_TYPE2 value="1"/>'
         '<GIGAN value="1"/><S_COUNTRY value="US"/></reqParam>')
    t = post(c, b)
    return {f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}": round(float(m.group(2)) / 1e6, 1)
            for m in re.finditer(r'<GIGAN value="(\d{8})"/>.*?<BB1 value="([^"]*)"/>', t, re.S)}


def top50(c, d: date) -> dict:
    f = CACHE / f"{d}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    b = ('<reqParam action="getImptFrcurStkSetlAmtList" task="ksd.safe.bip.cnts.OvsSec.process.OvsSecIsinPTask"><MENU_NO value="921"/>'
         '<CMM_BTN_ABBR_NM value="total_search,openall,print,hwp,word,pdf,seach,"/><W2XPATH value="/IPORTAL/user/ovsSec/BIP_CNTS10013V.xml"/>'
         f'<PG_START value="1"/><PG_END value="50"/><START_DT value="{d:%Y%m%d}"/><END_DT value="{d:%Y%m%d}"/><S_TYPE value="2"/>'
         '<S_COUNTRY value="US"/><D_TYPE value="1"/></reqParam>')
    rows = RE_TOP.findall(post(c, b))
    res = {isin: [round(float(buy) / 1e6, 2), round(float(sell) / 1e6, 2)] for isin, _n, buy, sell, _t, _net in rows}
    if rows and d < date.today():
        CACHE.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(res), encoding="utf-8")
    return res


# 종목 차트: ETF는 기초지수(Yahoo). KORU 기초지수(MSCI Korea 25/50)는 무료 일봉이 없어 같은 지수를 추종하는 EWY로 대신한다.
PRICE = {"SOXL": ("^SOX", "필라델피아 반도체지수(SOX)"), "MU": ("MU", "MU 주가"), "SPCX": ("SPCX", "SPCX 주가"),
         "KORU": ("EWY", "MSCI Korea 25/50(EWY로 대체)"), "QQQ": ("^NDX", "나스닥100")}


def prices() -> dict:
    out = {}
    p1 = int((datetime.now() - timedelta(days=740)).timestamp())
    for tk, (sym, name) in PRICE.items():
        try:
            r = httpx.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", params={"period1": p1, "period2": int(time.time()), "interval": "1d"},
                          headers={"User-Agent": "Mozilla/5.0"}, timeout=30).json()["chart"]["result"][0]
            off = r["meta"].get("gmtoffset", 0)
            cl = r["indicators"]["quote"][0]["close"]
            out[tk] = {"sym": sym, "name": name, "px": [[datetime.fromtimestamp(t + off, tz=timezone.utc).date().isoformat(), round(c, 2)]
                                                        for t, c in zip(r["timestamp"], cl) if c is not None]}
        except Exception as e:  # noqa: BLE001
            print(f"[seibro] 가격 실패 {tk} {sym}: {e}")
        time.sleep(0.5)
    return out


def main() -> int:
    c = client()
    us, cust = {}, {}
    s = date.today() - timedelta(days=731)
    while s <= date.today():
        e = min(s + timedelta(days=90), date.today())
        us.update(us_daily(c, s, e))
        cust.update(us_custody(c, s, e))
        s = e + timedelta(days=1)
    tick = {v: {} for v in WATCH.values()}
    d = date.today() - timedelta(days=366)
    days = sorted(k for k in us if k >= d.isoformat())
    for i, ds in enumerate(days):
        res = top50(c, date.fromisoformat(ds))
        for isin, tk in WATCH.items():
            if isin in res:
                tick[tk][ds] = res[isin]
        if i % 25 == 0:
            print(f"[seibro] {ds} ({i+1}/{len(days)})", flush=True)
    out = {"fetched": datetime.now(KST).isoformat(timespec="minutes"), "unit": "USD 백만달러",
           "us": [[k] + v for k, v in sorted(us.items())], "tick": {k: [[d] + v for d, v in sorted(m.items())] for k, m in tick.items()},
           "watch": WATCH, "prices": prices(), "custody": [[k, v] for k, v in sorted(cust.items())]}
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    last = out["us"][-1]
    print(f"[seibro] 미국 {len(out['us'])}일 · 최신 {last[0]} 매수 {last[1]} 매도 {last[2]} 순 {round(last[1]-last[2],1)} $M · " +
          ", ".join(f"{k} {len(v)}일" for k, v in out["tick"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
