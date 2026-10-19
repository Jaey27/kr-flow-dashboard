"""무료 데이터 수집: 미 재무부 금리 CSV(명목·실질) + Yahoo 일봉

수집 결과는 data/ 폴더에 CSV로 캐시한다. 매번 전체를 다시 받지만 양이 작아 몇 초면 끝난다.
"""

import io
import logging
from datetime import date, datetime, timezone
from pathlib import Path

import httpx
import pandas as pd

import config

logger = logging.getLogger(__name__)
BASE = Path(__file__).parent
CACHE = BASE / "data"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
}
TREASURY_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all?type={kind}&field_tdr_date_value={year}&page&_format=csv"
)


def _treasury_year(year: int, kind: str) -> pd.DataFrame:
    r = httpx.get(TREASURY_URL.format(year=year, kind=kind), headers=HEADERS, timeout=30, follow_redirects=True)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df["Date"] = pd.to_datetime(df["Date"], format="%m/%d/%Y")
    return df


def treasury(start: date) -> pd.DataFrame:
    """명목 2·5·10·30년, 실질 10년 (%). 미 채권시장 영업일만 행이 있다."""
    frames_n, frames_r = [], []
    for year in range(start.year, datetime.now().year + 1):
        frames_n.append(_treasury_year(year, "daily_treasury_yield_curve"))
        frames_r.append(_treasury_year(year, "daily_treasury_real_yield_curve"))
    nom = pd.concat(frames_n).set_index("Date")[["2 Yr", "5 Yr", "10 Yr", "30 Yr"]]
    real = pd.concat(frames_r).set_index("Date")[["10 YR"]]
    df = nom.join(real, how="inner").sort_index()
    df.columns = ["y2", "y5", "y10", "y30", "real10"]
    df["bei10"] = df["y10"] - df["real10"]
    return df[df.index >= pd.Timestamp(start)]


def yahoo(symbol: str, start: date) -> pd.Series:
    """Yahoo chart API 일봉 종가(수정종가 우선). 인덱스는 거래소 현지 날짜."""
    period1 = int(datetime(start.year, start.month, start.day, tzinfo=timezone.utc).timestamp())
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    r = httpx.get(url, params={"period1": period1, "period2": int(datetime.now().timestamp()), "interval": "1d"},
                  headers=HEADERS, timeout=30)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    offset = res["meta"].get("gmtoffset", 0)
    close = res["indicators"]["quote"][0]["close"]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")
    values = adj if adj else close
    idx = [pd.Timestamp(datetime.fromtimestamp(t + offset, tz=timezone.utc).date()) for t in res["timestamp"]]
    s = pd.Series(values, index=idx, name=symbol, dtype="float64").dropna()
    return s[~s.index.duplicated(keep="last")]


def load_all(start: date = config.HISTORY_START, use_cache_on_error: bool = True) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """금리 표와 시장 시계열을 받아 캐시에 저장한다. 네트워크 실패 시 캐시를 쓴다."""
    CACHE.mkdir(exist_ok=True)
    try:
        rates = treasury(start)
        rates.to_csv(CACHE / "treasury.csv")
    except Exception as e:
        if not use_cache_on_error or not (CACHE / "treasury.csv").exists():
            raise
        logger.warning("재무부 금리 수집 실패, 캐시 사용: %s", e)
        rates = pd.read_csv(CACHE / "treasury.csv", index_col=0, parse_dates=True)

    series = {}
    for key, symbol in config.TICKERS.items():
        path = CACHE / f"{key}.csv"
        try:
            s = yahoo(symbol, start)
            s.to_csv(path)
        except Exception as e:
            if not use_cache_on_error or not path.exists():
                raise
            logger.warning("%s 수집 실패, 캐시 사용: %s", symbol, e)
            s = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
        series[key] = s
    return rates, series
