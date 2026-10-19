"""data/cpi.json + Chart.js → cpi.html (외부 요청 없는 단일 파일)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    tpl = (ROOT / "scripts" / "template.html").read_text(encoding="utf-8")
    data = (ROOT / "data" / "cpi.json").read_text(encoding="utf-8")
    chart = (ROOT / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8")
    html = tpl.replace("/*__CHARTJS__*/", chart).replace("/*__DATA__*/", data)
    (ROOT / "cpi.html").write_text(html, encoding="utf-8")
    print("cpi.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
