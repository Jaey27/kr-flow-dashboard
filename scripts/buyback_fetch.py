"""자사주 매입 대시보드(buyback-dashboard) 데이터 받기 → data/buyback.json (수급 탭 「자사주 매입」용)

    python scripts/buyback_fetch.py

- 원천: 공개 리포 Jaey27/buyback-dashboard 의 data/buyback.json (맥미니가 08:40·18:30·19:30·21:00 갱신·push).
  같은 머신에 리포가 있으면(BUYBACK_DIR 또는 ~/buyback-dashboard) 그 파일을 먼저 쓴다.
- 받기에 실패하면 기존 data/buyback.json 을 그대로 둔다(화면은 직전 값).
- 시즌: buyback.json 의 companies(현재 시즌) + archive(지난 시즌). 시즌 번호는 meta.season.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "buyback.json"
RAW = "https://raw.githubusercontent.com/Jaey27/buyback-dashboard/main/data/buyback.json"


def local_copy() -> Path | None:
    for d in [os.environ.get("BUYBACK_DIR"), str(Path.home() / "buyback-dashboard"), str(ROOT.parent / "buyback-dashboard")]:
        if d and (Path(d) / "data" / "buyback.json").exists():
            return Path(d) / "data" / "buyback.json"
    return None


def main() -> int:
    src, text = None, None
    p = local_copy()
    if p:
        src, text = str(p), p.read_text(encoding="utf-8")
    else:
        try:
            r = httpx.get(RAW, timeout=60, follow_redirects=True)
            r.raise_for_status()
            src, text = RAW, r.text
        except Exception as e:  # noqa: BLE001
            print(f"[buyback] 받기 실패 — 기존 파일 유지: {e}", file=sys.stderr)
            return 1
    d = json.loads(text)
    if not d.get("companies"):
        print("[buyback] companies 가 비어 있음 — 기존 파일 유지", file=sys.stderr)
        return 1
    OUT.write_text(text, encoding="utf-8")
    cos = d["companies"]
    print(f"[buyback] {src} · as_of {d.get('as_of')} · 현재 시즌 "
          + ", ".join(f"{c['meta']['name']} 시즌{c['meta'].get('season', 1)} {(c['derived'].get('progress_ratio') or 0) * 100:.1f}%" for c in cos.values())
          + f" · 지난 시즌 {sum(len(v) for v in (d.get('archive') or {}).values())}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
