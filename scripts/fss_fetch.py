"""금감원 '외국인 증권투자 동향'(월간) 자동 수집 → data/manual/fss_foreign_holdings.json 에 빠진 달만 추가.

    python scripts/fss_fetch.py

- 출처: KDI 경제교육·정보센터 경제정책자료(eiec.kdi.re.kr)에 금감원 보도자료 요약이 매월 올라온다(보통 다음 달 중순).
  요약문에서 '상장주식 X조 Y억원을 순매수/순매도', '보유잔액 … N조원(시가총액의 P%)'를 읽는다.
- 시장별(코스피/코스닥) 순매수는 요약문에 없어 비워 둔다(기존 행은 보도 인용값 유지).
- 숫자를 못 읽으면 추가하지 않고 경고만 남긴다(추정값을 넣지 않음).
"""

from __future__ import annotations

import html
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "data" / "manual" / "fss_foreign_holdings.json"
BASE = "https://eiec.kdi.re.kr/policy/"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126"}


def text(h: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)))


def jo(s: str) -> float | None:
    """'4조 7,360억원' · '3,440억원' · '25.1조원' → 조원"""
    m = re.match(r"\s*(?:([\d,.]+)\s*조)?\s*(?:([\d,]+)\s*억)?", s)
    if not m or not (m.group(1) or m.group(2)):
        return None
    j = float(m.group(1).replace(",", "")) if m.group(1) else 0.0
    e = float(m.group(2).replace(",", "")) if m.group(2) else 0.0
    return round(j + e / 1e4, 3)


def parse(num: str) -> dict | None:
    r = httpx.get(BASE + f"materialView.do?num={num}", headers=UA, timeout=30)
    t = text(r.text)
    title = re.search(r"(\d{4})년 (\d{1,2})월 외국인 증권투자 동향", t)
    if not title:
        return None
    month = f"{title.group(1)}-{int(title.group(2)):02d}"
    # 문구가 달마다 조금씩 다르다: '상장주식 △49조 3,360억원을 순매도' · '상장주식 3,440억원을 순매수' · '상장주식을 47조 190억원 순매도'
    nb = re.search(r"상장주식\s*을?\s*[△▲\-]?\s*((?:[\d,.]+\s*조\s*)?(?:[\d,]+\s*억)?)\s*원?\s*을?\s*순(매수|매도)", t)
    # '2,908.6조원(시가총액의 36.4%)' · '보유잔액이 … 2,280.6조원(시가총액의 34.8%)' · 비중 없이 '상장주식 1,326.8조원'
    hold = (re.search(r"([\d,]+\.?\d*)\s*조원\s*\(\s*시가총액의\s*([\d.]+)\s*%\s*\)", t)
            or re.search(r"(?:말|현재)[^.]{0,40}?상장주식\s*([\d,]+\.\d)\s*조원()", t))
    pub = re.search(r"(\d{4})\.(\d{2})\.(\d{2})", t[t.find(title.group(0)):])
    if not (nb and hold):
        print(f"[fss] {month} 숫자 읽기 실패 — 수동 확인 필요 ({BASE}materialView.do?num={num})")
        return None
    v = jo(nb.group(1))
    return {"month": month, "holding_jo": float(hold.group(1).replace(",", "")), "share_pct": float(hold.group(2)) if hold.group(2) else None,
            "net_buy_jo": (v if nb.group(2) == "매수" else -v) if v is not None else None,
            "net_buy_kospi_jo": None, "net_buy_kosdaq_jo": None,
            "url": f"{BASE}materialView.do?num={num}", "published": "-".join(pub.groups()) if pub else None,
            "source": "금융감독원 '외국인 증권투자 동향' (KDI 경제정보센터 게재본, 자동 수집)"}


def main() -> int:
    d = json.loads(PATH.read_text(encoding="utf-8"))
    have = {r["month"] for r in d["rows"]}
    lst = httpx.get(BASE + "materialList.do", params={"search_txt": "외국인 증권투자 동향", "search_div": "1"}, headers=UA, timeout=30).text
    nums = list(dict.fromkeys(re.findall(r"materialView\.do\?num=(\d+)", lst)))[:12]
    added = []
    for n in nums:
        time.sleep(1)
        row = parse(n)
        if row and row["month"] in have:
            break  # 목록은 최신순 — 이미 있는 달을 만나면 그 뒤는 볼 필요 없음
        if row:
            d["rows"].append(row)
            have.add(row["month"])
            added.append(row)
    if added:
        d["rows"].sort(key=lambda r: r["month"])
        d["collected"] = date.today().isoformat()
        PATH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[fss] 추가 {len(added)}개: " + ", ".join(f"{r['month']} {r['holding_jo']}조 {r['share_pct']}% 순{r['net_buy_jo']}" for r in added) +
          f" · 최신 {max(have)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
