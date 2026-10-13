# -*- coding: utf-8 -*-
"""KRX 시총 원장(data/ledger/krx_mcap.json) 백필 — 다음 투자자 원장의 영업일 목록을 달력으로 쓴다.
usage: python scripts/backfill_krx.py [--from YYYY-MM-DD]
"""
import argparse, datetime as dt, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent / "sources"))
from common import load_ledger, save_ledger, log, now_kst
import krx as krx_src

ap = argparse.ArgumentParser(); ap.add_argument("--from", dest="start", default="2024-10-01"); a = ap.parse_args()
days = sorted(d for d in load_ledger("daum_investor_kospi")["rows"] if d >= a.start)
led = load_ledger("krx_mcap")
todo = [d for d in days if d not in led["rows"]]
log(f"KRX 백필 대상 {len(todo)}일 (전체 {len(days)})")
k = krx_src.KRX()
for i, d in enumerate(todo, 1):
    try:
        row = k.day(dt.date.fromisoformat(d))
    except Exception as e:
        log(f"[ERROR] {d}: {e}"); time.sleep(5); continue
    if row:
        led["rows"][d] = row
    if i % 20 == 0 or i == len(todo):
        led["fetched_at"] = now_kst().isoformat(timespec="seconds"); save_ledger("krx_mcap", led)
        log(f"{i}/{len(todo)} {d} kospi={row and row['kospi_mcap']}")
    time.sleep(0.3)
led["fetched_at"] = now_kst().isoformat(timespec="seconds"); save_ledger("krx_mcap", led)
log("완료")
