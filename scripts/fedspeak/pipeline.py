# -*- coding: utf-8 -*-
"""연준 발언 원장: raw/*.json 병합 → 인용 원문 대조 → ledger.json

  python -X utf8 pipeline.py merge     # raw/A*.json → ledger_raw.json (정규화·중복 제거)
  python -X utf8 pipeline.py verify    # source_url을 직접 받아 quote가 글자 그대로 있는지 대조 → ledger.json
  python -X utf8 pipeline.py report    # 인물별 건수·검증 상태 표

원칙: quote가 원문 페이지에 없으면(verify != exact/near) 지수·백테스트에서 뺀다. 빌드 게이트.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "data" / "fedspeak"  # 원장·덮어쓰기·요약(리포에 커밋)
REPO = Path(__file__).resolve().parents[2]
RAW = HERE / "raw"
CACHE = HERE / "cache"
START, END = "2026-01-01", "2026-11-23"

# 인물 명단. group: board/voter(2026 투표) /nonvoter /political /investor /sellside
# v26·v27 = 그해 FOMC 투표권. 지역 연은 로테이션은 수집 에이전트가 각 은행 사이트에서 재확인한 뒤 고친다.
ROSTER = {
    "warsh": dict(name="Kevin Warsh", kr="워시", role="의장", group="board", v26=1, v27=1),
    "jefferson": dict(name="Philip Jefferson", kr="제퍼슨", role="부의장", group="board", v26=1, v27=1),
    "bowman": dict(name="Michelle Bowman", kr="보우먼", role="감독 부의장", group="board", v26=1, v27=1),
    "waller": dict(name="Christopher Waller", kr="월러", role="이사", group="board", v26=1, v27=1),
    "barr": dict(name="Michael Barr", kr="바", role="이사", group="board", v26=1, v27=1),
    "cook": dict(name="Lisa Cook", kr="쿡", role="이사", group="board", v26=1, v27=1),
    "powell": dict(name="Jerome Powell", kr="파월", role="이사(전 의장)", group="board", v26=1, v27=1),
    "williams": dict(name="John Williams", kr="윌리엄스", role="뉴욕", group="voter", v26=1, v27=1),
    "hammack": dict(name="Beth Hammack", kr="해맥", role="클리블랜드", group="voter", v26=1, v27=0),
    "paulson": dict(name="Anna Paulson", kr="폴슨", role="필라델피아", group="voter", v26=1, v27=0),
    "logan": dict(name="Lorie Logan", kr="로건", role="댈러스", group="voter", v26=1, v27=0),
    "kashkari": dict(name="Neel Kashkari", kr="카시카리", role="미니애폴리스", group="voter", v26=1, v27=0),
    "goolsbee": dict(name="Austan Goolsbee", kr="굴스비", role="시카고", group="nonvoter", v26=0, v27=1),
    "barkin": dict(name="Tom Barkin", kr="바킨", role="리치먼드", group="nonvoter", v26=0, v27=1),
    "daly": dict(name="Mary Daly", kr="데일리", role="샌프란시스코", group="nonvoter", v26=0, v27=1),
    "collins": dict(name="Susan Collins", kr="콜린스", role="보스턴", group="nonvoter", v26=0, v27=0),
    "musalem": dict(name="Alberto Musalem", kr="무살렘", role="세인트루이스", group="nonvoter", v26=0, v27=0),
    "schmid": dict(name="Jeffrey Schmid", kr="슈미드", role="캔자스시티", group="nonvoter", v26=0, v27=0),
    "trump": dict(name="Donald Trump", kr="트럼프", role="대통령", group="political", v26=0, v27=0),
    "bessent": dict(name="Scott Bessent", kr="베센트", role="재무장관", group="political", v26=0, v27=0),
}
ROSTER_EXTRA = HERE / "roster_extra.json"  # 수집 뒤 확인된 인물(애틀랜타 총재 등)을 여기에 추가
if ROSTER_EXTRA.exists():
    ROSTER.update(json.loads(ROSTER_EXTRA.read_text(encoding="utf-8")))


def key_of(speaker: str) -> str:
    s = re.sub(r"[^a-z ]", "", speaker.lower())
    for k, v in ROSTER.items():
        last = v["name"].split()[-1].lower()
        if re.search(rf"\b{last}\b", s):
            return k
    return re.sub(r"\s+", "_", s.strip()) or "unknown"


def merge() -> None:
    items, unver, extra = [], [], {}
    for f in sorted(RAW.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8-sig"))
        except Exception as e:  # noqa: BLE001
            print(f"!! {f.name} JSON 오류: {e}")
            continue
        col = d.get("collector") or f.stem
        for it in d.get("items", []):
            it = dict(it)
            it["collector"] = col
            if "factba.se" in str(it.get("source_url", "")):  # 제3자 녹취 사이트는 '공식'이 아님
                it["source_tier"] = "full_interview_transcript"
            it["key"] = key_of(it.get("speaker", ""))
            r = ROSTER.get(it["key"])
            grp = r["group"] if r else ("sellside" if col in ("A10", "B10") else "investor")
            it["group"] = grp
            items.append(it)
        for u in d.get("unverified", []):
            unver.append(dict(u, collector=col))
        for k in ("fomc_meetings", "latest_calls", "coverage_notes", "blackouts", "blackout_periods"):
            if k in d:
                extra.setdefault(k, {})[col] = d[k]
    # 기간 밖·필수 칸 누락 제거(이유 기록)
    kept, dropped = [], []
    for it in items:
        why = None
        dt = str(it.get("date") or "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt):
            why = "날짜 형식"
        elif not (START <= dt <= END):
            why = "기간 밖"
        elif not it.get("source_url") or not it.get("quote"):
            why = "출처·인용 없음"
        elif it.get("score") not in (None, -2, -1, 0, 1, 2):
            why = f"점수 값 이상({it.get('score')})"
        (dropped if why else kept).append(dict(it, drop=why) if why else it)
    # 중복: 같은 인물·같은 날·같은 URL
    seen, out = set(), []
    for it in sorted(kept, key=lambda x: (x["date"], x["key"])):
        k = (it["key"], it["date"], it["source_url"].split("#")[0].rstrip("/"), norm(it["quote"])[:60])
        if k in seen:
            dropped.append(dict(it, drop="중복"))
            continue
        seen.add(k)
        it["id"] = hashlib.sha1("|".join(k).encode()).hexdigest()[:10]
        out.append(it)
    (HERE / "ledger_raw.json").write_text(json.dumps(dict(items=out, unverified=unver, dropped=dropped, extra=extra),
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"병합 {len(out)}건 · 미확인 {len(unver)}건 · 제외 {len(dropped)}건")


# ---- 인용 대조 ---------------------------------------------------------------
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def norm(s: str) -> str:
    s = html.unescape(s or "")
    s = s.replace(" ", " ")
    s = re.sub(r"[​‌‍⁠﻿­]", "", s)
    s = re.sub(r"[‘’‚′`]", "'", s)
    s = re.sub(r"[“”„″]", '"', s)
    s = re.sub(r"[‐-―−]", "-", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", norm(s))


def fetch(url: str) -> tuple[str | None, str]:
    """페이지 본문 텍스트. 캐시(cache/<sha1>.txt). 실패하면 (None, 이유)."""
    CACHE.mkdir(parents=True, exist_ok=True)  # 리포에서는 cache/ 가 무시 목록이라 처음엔 없음
    h = hashlib.sha1(url.encode()).hexdigest()[:16]
    cp = CACHE / f"{h}.txt"
    if cp.exists():
        return cp.read_text(encoding="utf-8"), "cache"
    binp = CACHE / f"{h}.bin"
    fp = CACHE / f"{h}.fail"
    if fp.exists():
        return None, fp.read_text(encoding="utf-8")
    try:
        r = subprocess.run(["curl", "-sS", "-L", "-m", "25", "-A", UA, "-H", "Accept-Language: en-US,en;q=0.9",
                            "-o", str(binp), "-w", "%{http_code} %{content_type}", url],
                           capture_output=True, text=True, timeout=35)
    except Exception as e:  # noqa: BLE001
        return None, f"curl 예외 {e}"
    meta = (r.stdout or "").strip()
    code = meta.split(" ")[0] if meta else "000"
    if not binp.exists() or code != "200":
        fp.write_text(f"http {code}", encoding="utf-8")
        return None, f"http {code}"
    raw = binp.read_bytes()
    if raw[:5] == b"%PDF-" or "pdf" in meta.lower():
        try:
            import fitz  # type: ignore
            doc = fitz.open(stream=raw, filetype="pdf")
            text = "\n".join(p.get_text() for p in doc)
        except Exception as e:  # noqa: BLE001
            return None, f"pdf 파싱 실패 {e}"
    else:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "html.parser")
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        text = soup.get_text(" ")
        # JSON-LD 등 스크립트 안 본문(일부 뉴스 사이트)도 살린다
        m = re.findall(rb'"articleBody"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        for b in m:
            try:
                text += "\n" + json.loads('"' + b.decode("utf-8", "ignore") + '"')
            except Exception:  # noqa: BLE001
                pass
        # 본문이 페이지 내장 데이터(스크립트 JSON) 안에만 있는 사이트(Fortune 녹취 등): 원시 HTML도 태그·이스케이프를 풀어 뒤에 붙인다
        rawtxt = raw.decode("utf-8", "ignore")
        rawtxt = re.sub(r"\\u([0-9a-fA-F]{4})", lambda mm: chr(int(mm.group(1), 16)), rawtxt)
        rawtxt = rawtxt.replace('\\"', '"').replace("\\n", " ").replace("\\/", "/")
        rawtxt = re.sub(r"<[^>]+>", " ", rawtxt)
        text += "\n\n[RAW]\n" + rawtxt
    binp.unlink(missing_ok=True)
    if len(text.strip()) < 200:
        return None, "본문 없음(차단·스크립트 렌더)"
    cp.write_text(text, encoding="utf-8")
    time.sleep(0.1)
    return text, "fetched"


def check(quote: str, text: str) -> tuple[str, float]:
    q, t = norm(quote), norm(text)
    q = q.strip(' "\'')
    if q and q in t:
        return "exact", 1.0
    qt, tt = toks(quote), toks(text)
    js = " ".join(tt)
    if qt and " ".join(qt) in js:
        return "exact", 1.0  # 문장부호만 다름
    n = 4
    if len(qt) < n + 1:
        return "miss", 0.0
    grams = [" ".join(qt[i:i + n]) for i in range(len(qt) - n + 1)]
    hit = sum(1 for g in grams if g in js) / len(grams)
    return ("near" if hit >= 0.8 else "miss"), round(hit, 2)


def verify() -> None:
    d = json.loads((HERE / "ledger_raw.json").read_text(encoding="utf-8"))
    CACHE.mkdir(exist_ok=True)
    stat: dict[str, int] = {}
    npath = CACHE / "notion_druck.md"  # Jae 노션 아카이브 사본(드러켄밀러 원장)
    ntext = re.sub(r"<[^>]+>", "", npath.read_text(encoding="utf-8")).replace("\\", "") if npath.exists() else None
    # 페이지 받기는 병렬로 먼저(차단 사이트 대기 시간이 겹치게)
    from concurrent.futures import ThreadPoolExecutor
    urls = sorted({u for it in d["items"] if it.get("source_tier") != "jae_notion" for u in (it["source_url"], it.get("ai_quote_url")) if u})
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(fetch, urls))
    print(f"  페이지 {len(urls)}개 받음", flush=True)
    for i, it in enumerate(d["items"]):
        if it.get("source_tier") == "jae_notion":
            if ntext is None:  # 노션 사본(Jae 비공개 노트)은 리포에 두지 않는다 → 처음 대조한 결과를 유지
                it["verify"], it["verify_note"] = "notion", "노션 사본 없음, 기존 대조 유지"
            else:
                st, sc = check(it["quote"], ntext)
                it["verify"], it["verify_note"] = ("notion" if st == "exact" else "miss"), f"노션 사본 대조 {sc}"
            stat[it["verify"]] = stat.get(it["verify"], 0) + 1
            continue
        text, how = fetch(it["source_url"])
        if text is None:
            it["verify"], it["verify_note"] = "fetch_fail", how
        else:
            st, sc = check(it["quote"], text)
            it["verify"], it["verify_note"] = st, f"{how} {sc}"
        if it.get("ai_quote"):
            t2 = text
            if it.get("ai_quote_url"):  # AI 인용이 다른 페이지에서 온 경우 그 페이지로 대조
                t2, _ = fetch(it["ai_quote_url"])
            it["ai_verify"] = check(it["ai_quote"], t2)[0] if t2 else "fetch_fail"
        stat[it["verify"]] = stat.get(it["verify"], 0) + 1
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(d['items'])} {stat}", flush=True)
    # 스크립트로 못 받은 페이지를 브라우저로 열어 인용을 직접 확인한 건(verify_manual.json: {id: "agent_ok"})
    mp = HERE / "verify_manual.json"
    if mp.exists():
        man = json.loads(mp.read_text(encoding="utf-8"))
        for it in d["items"]:
            if it["id"] in man and it["verify"] == "fetch_fail":
                stat[it["verify"]] -= 1
                it["verify"], it["verify_note"] = man[it["id"]], "브라우저로 원문 열어 확인"
                stat[it["verify"]] = stat.get(it["verify"], 0) + 1
    (HERE / "ledger.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("대조 결과", stat)


def report() -> None:
    d = json.loads((HERE / "ledger.json").read_text(encoding="utf-8"))
    rows: dict[str, dict] = {}
    for it in d["items"]:
        r = rows.setdefault(it["key"], dict(n=0, scored=0, exact=0, near=0, miss=0, fetch_fail=0, pending=0, grp=it["group"]))
        r["n"] += 1
        r["scored"] += it.get("score") is not None
        r[it.get("verify", "pending")] = r.get(it.get("verify", "pending"), 0) + 1
    print(f"{'인물':<22}{'그룹':<10}{'건':>4}{'점수':>5}{'일치':>5}{'근사':>5}{'불일치':>6}{'못받음':>6}{'재확인':>6}")
    for k, r in sorted(rows.items(), key=lambda x: (x[1]["grp"], -x[1]["n"])):
        print(f"{k:<22}{r['grp']:<10}{r['n']:>4}{r['scored']:>5}{r['exact']:>5}{r['near']:>5}{r['miss']:>6}{r['fetch_fail']:>6}{r.get('agent_ok', 0):>6}")
    print("합계", len(d["items"]), "· 미확인 목록", len(d["unverified"]), "· 제외", len(d["dropped"]))


if __name__ == "__main__":
    {"merge": merge, "verify": verify, "report": report}[sys.argv[1]]()
