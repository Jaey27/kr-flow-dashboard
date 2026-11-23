"""data/cpi.json + Chart.js → cpi.html (외부 요청 없는 단일 파일)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    tpl = (ROOT / "scripts" / "template.html").read_text(encoding="utf-8")
    # 다크/라이트 테마 + TV용 최소 글자 크기(kr-flow scripts/theme.py, 11/23) — 데이터·Chart.js 를 넣기 전에 화면 코드에만 적용
    sys.path.insert(0, str(ROOT.parent / "scripts"))
    import theme  # noqa: E402
    tpl = theme.legible(theme.themeify_cpi(tpl))
    data = (ROOT / "data" / "cpi.json").read_text(encoding="utf-8")
    chart = (ROOT / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8")
    html = tpl.replace("/*__CHARTJS__*/", chart).replace("/*__DATA__*/", data)
    (ROOT / "cpi.html").write_text(html, encoding="utf-8")
    print("cpi.html", len(html) // 1024, "KB")


if __name__ == "__main__":
    main()
