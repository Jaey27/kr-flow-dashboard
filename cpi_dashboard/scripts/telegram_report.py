"""CPI 발표 후 텔레그램 간략 보고서.

  python telegram_report.py            # .env 의 TELEGRAM_BOT_TOKEN·CHAT_ID 로 발송
  python telegram_report.py --dry-run  # 발송 없이 메시지만 출력

.env (cpi_dashboard 루트 또는 상위 저장소 루트):
  TELEGRAM_BOT_TOKEN=...
  CHAT_ID=...
  CPI_DASHBOARD_URL=https://jaey27.github.io/kr-flow-dashboard/cpi.html
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    for p in (ROOT / ".env", ROOT.parent / ".env"):
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_message(d):
    M = d["months"]
    k = M.index(d["latest"])
    S, C, F = d["series"], d["contrib"], d["flags"]
    meta = {m["code"]: m for m in d["meta"]}
    cons = d["consensus"].get(d["latest"], {})
    y, mo = d["latest"].split("-")

    def v(c, key):
        x = S[c][key][k]
        return None if x is None else x

    def vs(key, val):
        o = cons.get(key) or {}
        if o.get("f") is None or val is None:
            return ""
        a = round(val, 1)
        diff = a - o["f"]
        tag = "상회" if diff >= 0.05 else "하회" if diff <= -0.05 else "부합"
        return f" (예상 {o['f']:.1f}, {tag})"

    def p(x, n=1):
        return "–" if x is None else f"{x:+.{n}f}"

    lines = [f"<b>📊 미국 CPI {int(y)}년 {int(mo)}월</b>"]
    hm, hy, cm, cy = v("SA0", "mom"), v("SA0", "yoy"), v("SA0L1E", "mom"), v("SA0L1E", "yoy")
    lines.append(f"헤드라인 전월비 {p(hm)}%{vs('h_mom', hm)} · 전년비 {hy:.1f}%{vs('h_yoy', hy)}")
    lines.append(f"근원 전월비 {p(cm)}%{vs('c_mom', cm)} · 전년비 {cy:.1f}%{vs('c_yoy', cy)}")
    lines.append(f"근원 3개월 연율 {v('SA0L1E', 'ann3'):.1f}% · 6개월 {v('SA0L1E', 'ann6'):.1f}% · "
                 f"슈퍼코어 전월비 {p(v('SUPERCORE', 'mom'), 2)}%")

    # 근원 기여도 상위·하위
    core = [(c, x["mom_c"][k]) for c, x in C.items() if x["mom_c"][k] is not None]
    core.sort(key=lambda t: t[1], reverse=True)
    lines.append("")
    lines.append("<b>🔺 근원 상승 기여 상위</b> (근원 전월비 기준 %p)")
    for c, x in core[:3]:
        lines.append(f"· {esc(meta[c]['ko'])} {x:+.3f} (전월비 {p(S[c]['mom'][k], 2)}%)")
    neg = [t for t in core if t[1] < 0][-2:][::-1]
    if neg:
        lines.append("<b>🔻 끌어내린 항목</b>")
        for c, x in neg:
            lines.append(f"· {esc(meta[c]['ko'])} {x:+.3f} (전월비 {p(S[c]['mom'][k], 2)}%)")

    # 헤드라인 최대 기여 (식품·에너지 포함)
    head = max(((c, x["mom_h"][k]) for c, x in C.items() if x["mom_h"][k] is not None), key=lambda t: abs(t[1]))
    lines.append(f"헤드라인 최대 기여: {esc(meta[head[0]]['ko'])} {head[1]:+.3f}%p")

    # 일회성 신호
    lab = {"spike_up": "급등", "spike_down": "급락", "revert": "되돌림(일회성 가능성)", "persist": "지속(추세 가능성)"}
    sig = []
    for c, f in F.items():
        s = f["st"][k]
        if s and c in meta and meta[c]["type"] in ("item", "child", "derived"):
            sig.append((abs(f["z"][k] or 0), f"{esc(meta[c]['ko'])} {lab[s]}"))
    if sig:
        sig.sort(reverse=True)
        lines.append("")
        lines.append("<b>⚠️ 일회성 점검</b> " + " · ".join(t for _, t in sig[:5]))

    url = os.environ.get("CPI_DASHBOARD_URL", "https://jaey27.github.io/kr-flow-dashboard/cpi.html")
    lines.append("")
    lines.append(f'<a href="{url}">대시보드 열기</a>')
    return "\n".join(lines)


def send(text):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("CHAT_ID")
    if not token or not chat:
        raise SystemExit("TELEGRAM_BOT_TOKEN / CHAT_ID 가 .env 에 없습니다.")
    body = urllib.parse.urlencode({"chat_id": chat, "text": text, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=body, timeout=30) as r:
        return json.load(r).get("ok")


def main():
    load_env()
    d = json.loads((ROOT / "data" / "cpi.json").read_text(encoding="utf-8"))
    msg = build_message(d)
    if "--dry-run" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8")
        print(msg)
        return
    print("sent:", send(msg))


if __name__ == "__main__":
    main()
