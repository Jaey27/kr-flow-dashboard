"""CPI 자동 업데이트 러너 — launchd 가 5분마다 불러도 할 일이 없으면 바로 끝난다.

  python run_cpi.py              # 자동 판정
  python run_cpi.py --force      # 판정 무시하고 빌드·렌더 (텔레그램 제외)
  python run_cpi.py --no-send    # 텔레그램 발송 안 함

판정 순서
1. BLS 발표일(미 동부) 08:30 이후 ~ 다음 날 12:00 사이에만 BLS 파일 Last-Modified 를 확인
   → 저장된 값과 다르면 빌드·렌더·텔레그램(한 지표월에 1회).
2. 연은 보조지표가 CPI 최신월보다 늦으면, 발표일 11:00 ET 이후 30분 간격으로 재빌드.
3. 매월 1일에는 발표일 목록을 새로 받는다(fetch_schedule 캐시 7일).
상태는 data/state.json.
"""
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import fetch

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "data" / "state.json"
ET = ZoneInfo("America/New_York")
PY = sys.executable


def load_state():
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(s):
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


def run(script, *args):
    r = subprocess.run([PY, str(ROOT / "scripts" / script), *args], cwd=ROOT / "scripts")
    if r.returncode != 0:
        raise SystemExit(f"{script} 실패 (code {r.returncode})")


def log(msg):
    print(datetime.now().strftime("%m-%d %H:%M"), msg, flush=True)


def build_and_render():
    run("build_cpi.py")
    run("render_cpi.py")
    d = json.loads((ROOT / "data" / "cpi.json").read_text(encoding="utf-8"))
    ext_latest = min((e["latest"] for e in d["ext"].values() if e.get("latest")), default=None)
    return d["latest"], ext_latest, d.get("bls_last_modified")


def main():
    st = load_state()
    send = "--no-send" not in sys.argv
    if "--force" in sys.argv:
        latest, ext_latest, lm = build_and_render()
        st.update(latest=latest, ext_latest=ext_latest, bls_last_modified=lm, built_at=time.time())
        save_state(st)
        log(f"강제 빌드 완료 {latest}")
        return 1  # 렌더함

    now = datetime.now(ET)
    try:
        sched = fetch.fetch_schedule()
    except Exception as ex:
        log(f"발표 일정 조회 실패: {ex}")
        sched = []
    # 발표가 끝나면 BLS 일정 페이지에서 그 날짜가 빠질 수 있어 본 날짜를 누적 보관
    sched = sorted(set(st.get("sched", [])) | set(sched))
    st["sched"] = [d for d in sched if d >= (now.date() - timedelta(days=60)).isoformat()]
    if not st.get("bls_last_modified"):   # 이관 직후: 동봉된 cpi.json 값으로 시작
        cj = ROOT / "data" / "cpi.json"
        if cj.exists():
            d0 = json.loads(cj.read_text(encoding="utf-8"))
            st.update(bls_last_modified=d0.get("bls_last_modified"), latest=d0.get("latest"), sent_for=d0.get("latest"),
                      ext_latest=min((e["latest"] for e in d0["ext"].values() if e.get("latest")), default=None))
    save_state(st)
    today = now.date().isoformat()
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    in_window = (today in sched and now.hour * 60 + now.minute >= 8 * 60 + 30) or \
                (yesterday in sched and now.hour < 12)
    did = False

    # 1) BLS 새 발표
    if in_window:
        try:
            lm = fetch.bls_last_modified()
        except Exception as ex:
            log(f"BLS HEAD 실패: {ex}")
            lm = None
        if lm and lm != st.get("bls_last_modified"):
            log(f"BLS 갱신 감지: {lm}")
            latest, ext_latest, lm2 = build_and_render()
            st.update(latest=latest, ext_latest=ext_latest, bls_last_modified=lm2 or lm, built_at=time.time())
            save_state(st)
            did = True
            if send and st.get("sent_for") != latest:
                run("telegram_report.py")
                st["sent_for"] = latest
                save_state(st)
                log(f"텔레그램 보고서 발송: {latest}")

    # 2) 연은 보조지표 따라잡기 (11:00 ET 이후, 30분 간격)
    latest, ext_latest = st.get("latest"), st.get("ext_latest")
    if not did and latest and (ext_latest or "") < latest and in_window and now.hour >= 11:
        if time.time() - st.get("ext_try", 0) >= 30 * 60:
            st["ext_try"] = time.time()
            save_state(st)
            log("연은 보조지표 재빌드")
            latest, ext_latest, lm = build_and_render()
            st.update(latest=latest, ext_latest=ext_latest, built_at=time.time())
            save_state(st)
            did = True
    return 1 if did else 0


if __name__ == "__main__":
    # 종료 코드 10 = 렌더함 (상위 run.sh 가 publish 여부 판단에 사용)
    sys.exit(10 if main() else 0)
