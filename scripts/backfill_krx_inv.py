# -*- coding: utf-8 -*-
"""KRX 종목별 투자자(개인·외국인·기관) 원자료 백필 → data/krx_inv/*.json.gz, 끝나면 업종 원장 재구성.
usage: python scripts/backfill_krx_inv.py [--from YYYY-MM-DD]   (KRX_ID/KRX_PW 필요, 하루 3회 호출)
"""
import argparse, datetime as dt, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent / "sources"))
from common import load_ledger, log
import krx_inv, sector_flow

ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="start", default="2024-10-01"); a = ap.parse_args()
days = sorted(d for d in load_ledger("daum_investor_kospi")["rows"] if d >= a.start)
todo = [d for d in days if not krx_inv.has_raw(d)]
log(f"KRX 종목별 투자자 백필 {len(todo)}일")
for i, d in enumerate(todo, 1):
    try:
        raw = krx_inv.day(dt.date.fromisoformat(d))
        if raw:
            krx_inv.save_raw_day(d, raw)
    except Exception as e:
        log(f"[ERROR] {d}: {e!r}"[:200]); time.sleep(5); continue
    if i % 20 == 0 or i == len(todo):
        log(f"{i}/{len(todo)} {d}")
    time.sleep(0.2)
sector_flow.rebuild_ledger()
log("완료")
