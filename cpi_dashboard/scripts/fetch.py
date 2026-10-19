"""CPI 원자료 수집 — BLS 플랫파일, BLS 보도자료(가중치), 연은 보조지표, 트레이딩뷰 캘린더.

모든 결과는 data/raw/ 에 캐시한다. --offline 이면 캐시만 쓴다.
"""
import json
import re
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

# BLS는 연락처가 담긴 User-Agent를 요구한다
BLS_UA = "cpi-dashboard (pjy0992@gmail.com)"
WEB_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

BLS_FLAT = "https://download.bls.gov/pub/time.series/cu/cu.data.0.Current"
CLE_MEDIAN = "https://www.clevelandfed.org/-/media/files/webcharts/mediancpi/mcpi_revised.csv?sc_lang=en"
CLE_TRIM = "https://www.clevelandfed.org/-/media/files/webcharts/mediancpi/trim_revised.csv?sc_lang=en"
ATL_STICKY = "https://www.atlantafed.org/-/media/Project/Atlanta/FRBA/Documents/datafiles/research/inflationproject/stickprice/stickyprice.xlsx"
TV_CAL = "https://economic-calendar.tradingview.com/events"


def _get(url, ua=BLS_UA, headers=None, timeout=90, method="GET"):
    h = {"User-Agent": ua}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), dict(r.headers)


def _cached(name, url, ua=BLS_UA, offline=False, max_age_h=None):
    p = RAW / name
    if p.exists() and (offline or (max_age_h and time.time() - p.stat().st_mtime < max_age_h * 3600)):
        return p
    if offline:
        raise FileNotFoundError(p)
    body, _ = _get(url, ua=ua)
    p.write_bytes(body)
    return p


def bls_last_modified():
    """플랫파일 Last-Modified — 새 발표 여부를 값싸게 확인하는 용도."""
    _, h = _get(BLS_FLAT, method="HEAD", timeout=30)
    return h.get("Last-Modified")


def fetch_bls_flat(codes, offline=False):
    """cu.data.0.Current 에서 필요한 시리즈만 골라 data/raw/bls_series.json 으로 저장."""
    out = RAW / "bls_series.json"
    if offline:
        return json.loads(out.read_text(encoding="utf-8"))
    body, h = _get(BLS_FLAT, timeout=300)
    want = set()
    for c in codes:
        want.add("CUSR0000" + c)
        want.add("CUUR0000" + c)
    series = {}
    for line in body.decode("utf-8", "ignore").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        sid = parts[0].strip()
        if sid not in want:
            continue
        per = parts[2].strip()
        if not per.startswith("M") or per == "M13":
            continue
        try:
            v = float(parts[3])
        except ValueError:
            continue
        series.setdefault(sid, {})[f"{parts[1].strip()}-{per[1:]}"] = v
    data = {"last_modified": h.get("Last-Modified"), "series": series}
    out.write_text(json.dumps(data), encoding="utf-8")
    return data


# 매년 3월 발표문(1월 지수) 표1·표2에 '1월 상대중요도'가 실린다 → 그해 가중치 기준점
WEIGHT_RELEASES = {
    2021: "cpi_03102021.htm", 2022: "cpi_03102022.htm", 2023: "cpi_03142023.htm",
    2024: "cpi_03122024.htm", 2025: "cpi_03122025.htm", 2026: "cpi_03112026.htm",
}


def parse_release_weights(html_text):
    """보도자료 표1·표2에서 {항목명: 상대중요도} 추출 (첫 번째 숫자 열)."""
    out = {}
    # 표1·표2 행만 (th headers="cpipress1..." / "cpipress2..."), 요약표 A 등은 제외
    for m in re.finditer(r'<th headers="cpipress[12]\.[^"]*"[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>', html_text, re.S):
        name = re.sub(r'<span class="footnoteRefs">.*?</span>', "", m.group(1), flags=re.S)
        name = re.sub(r"<[^>]+>", "", name)
        name = name.replace("&#39;", "'").replace("&amp;", "&").strip()
        val = re.sub(r"<[^>]+>", "", m.group(2)).strip().replace(",", "")
        try:
            out.setdefault(name, float(val))
        except ValueError:
            pass
    out.setdefault("All items", 100.0)
    # 일부 연도 표2에 '가사 서비스' 행이 없음 → 상위 항목에서 차감
    if "Household operations" not in out and "Household furnishings and operations" in out:
        out["Household operations"] = round(out["Household furnishings and operations"]
                                            - out.get("Household furnishings and supplies", 0), 3)
    return out


def fetch_weights(offline=False):
    """{연도: {항목명: 1월 상대중요도}} — 새 연도 3월 발표문은 날짜를 모르면 수동으로 추가."""
    res = {}
    for y, fn in WEIGHT_RELEASES.items():
        url = f"https://www.bls.gov/news.release/archives/{fn}"
        p = _cached(f"rel_{y}.htm", url, offline=offline, max_age_h=24 * 365)
        res[y] = parse_release_weights(p.read_text(encoding="utf-8", errors="ignore"))
    return res


def fetch_cleveland(offline=False):
    out = {}
    for key, url in (("median", CLE_MEDIAN), ("trim", CLE_TRIM)):
        p = _cached(f"cle_{key}.csv", url, ua=WEB_UA, offline=offline, max_age_h=6)
        rows = p.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]
        ser = {}
        for r in rows:
            f = r.split(",")
            if len(f) < 2 or not f[1].strip():
                continue
            m, d, y = f[0].strip().split("/")
            ser[f"{y}-{int(m):02d}"] = float(f[1])  # 전월비(소수)
        out[key] = ser
    return out


def fetch_sticky(offline=False):
    import openpyxl
    p = _cached("atl_sticky.xlsx", ATL_STICKY, ua=WEB_UA, offline=offline, max_age_h=6)
    wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
    ws = wb["Data"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = rows[0]
    # 열 위치: 'Sticky CPI (monthly)' 와 'Core Sticky CPI_ex shelter' 블록의 첫 열(전월비 소수)
    cols = {"sticky": hdr.index("Sticky CPI (monthly)"),
            "core_sticky_xs": hdr.index("Core Sticky CPI_ex shelter")}
    out = {k: {} for k in cols}
    for r in rows[1:]:
        if not isinstance(r[0], datetime):
            continue
        ym = f"{r[0].year}-{r[0].month:02d}"
        for k, c in cols.items():
            if isinstance(r[c], (int, float)):
                out[k][ym] = float(r[c])
    return out


def fetch_tv_calendar(start=date(2021, 1, 1), offline=False):
    """트레이딩뷰 경제 캘린더에서 CPI 4종 컨센서스·실제와 연준 금리 결정을 모은다."""
    p = RAW / "tv_calendar.json"
    if offline:
        return json.loads(p.read_text(encoding="utf-8"))
    keep = {"Inflation Rate MoM", "Inflation Rate YoY", "Core Inflation Rate MoM",
            "Core Inflation Rate YoY", "Fed Interest Rate Decision"}
    events = {}
    cur = start
    today = date.today() + timedelta(days=45)
    while cur < today:
        nxt = cur + timedelta(days=45)
        url = (f"{TV_CAL}?from={cur.isoformat()}T00:00:00.000Z&to={nxt.isoformat()}T00:00:00.000Z"
               f"&countries=US")
        body, _ = _get(url, ua=WEB_UA, headers={"Origin": "https://www.tradingview.com"}, timeout=40)
        for e in json.loads(body).get("result", []):
            if e.get("title") in keep:
                events[e["id"]] = {k: e.get(k) for k in
                                   ("title", "date", "actual", "forecast", "previous", "referenceDate")}
        cur = nxt
        time.sleep(0.4)
    data = sorted(events.values(), key=lambda e: e["date"])
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def fetch_schedule(offline=False):
    """BLS CPI 발표 일정 → ['YYYY-MM-DD', ...] (미 동부 8:30 발표)."""
    p = _cached("cpi_schedule.htm", "https://www.bls.gov/schedule/news_release/cpi.htm",
                offline=offline, max_age_h=24 * 7)
    s = p.read_text(encoding="utf-8", errors="ignore")
    out = []
    for m in re.finditer(r"<td>\s*([A-Z][a-z]{2})\.?\s+(\d{1,2}),\s+(\d{4})\s*</td>", s):
        try:
            d = datetime.strptime(f"{m.group(1)} {m.group(2)} {m.group(3)}", "%b %d %Y").date()
            out.append(d.isoformat())
        except ValueError:
            pass
    return sorted(set(out))
