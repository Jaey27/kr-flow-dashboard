"""금리 원인 분해

매일 미 10년물 금리 변화를 '물가지표 / 지정학·유가 / AI / 주식 전반 / 연준·고용 / 기타'로 나누고,
그날 AI 주식과 나머지 주식, 다음 날 코스피가 어떻게 반응했는지 같이 기록한다.

두 층으로 본다.
1) 사실: Δ10Y = Δ실질금리 + ΔBEI(기대인플레), 커브(2Y·30Y), 유가
2) 기여도: 최근 120영업일 회귀 Δ10Y ~ 브렌트% + (SMH−RSP)%p 로 '같이 움직인 몫'을 계산.
   설명 안 된 나머지는 그날 일정에 따라 배정: 물가지표 발표일 → '물가지표', FOMC·고용 → '연준·고용',
   AI 대형 회사채 발행일 → 'AI(조달)', 그 외 → '기타(텀프리미엄·수급·재정 등)'.
   → 인과가 아니라 '시장이 그날 금리를 무엇과 묶어서 움직였나'를 재는 것.
   (주식 전체 수익률은 요인에서 뺐다. 지금처럼 '금리↑ = 주식↓' 국면에서는 금리가 주식을 누른 몫이 섞여 해석이 꼬인다.)

사용법:
    python decompose.py            # 데이터 수집 → output/금리분해.html, 금리분해_일별.csv, 텔레그램 요약 출력
    python decompose.py --offline  # 캐시(data/)만으로 다시 계산
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import config
import data

BASE = Path(__file__).parent
OUT = BASE / "output"
KST = timezone(timedelta(hours=9))
WD = "월화수목금토일"
BUCKET_NAMES = {k: n for k, n, _, _ in config.BUCKETS}
BUCKET_SHORT = {k: s for k, _, s, _ in config.BUCKETS}

logger = logging.getLogger(__name__)


# ── 표 만들기 ──

def _aligned_returns(px: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """채권 영업일 사이 구간 수익률(%). 채권 휴장일에 주식이 열려도 같은 구간끼리 비교되게 맞춘다."""
    full = px.reindex(px.index.union(dates)).ffill()
    return full.reindex(dates).pct_change() * 100


def _next_day_return(px: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """미국 t일 이후 첫 한국 거래일의 수익률(%) = '익일 반응'."""
    ret = px.pct_change() * 100
    pos = px.index.searchsorted(dates, side="right")
    vals = [ret.iloc[p] if p < len(ret) else np.nan for p in pos]
    return pd.Series(vals, index=dates)


def build_table(rates: pd.DataFrame, series: dict[str, pd.Series]) -> pd.DataFrame:
    df = rates.copy()
    for c in ("y2", "y5", "y10", "y30", "real10", "bei10"):
        df[f"d_{c}"] = df[c].diff() * 100  # bp
    df["d_2s10s"] = df["d_y10"] - df["d_y2"]
    df["d_10s30s"] = df["d_y30"] - df["d_y10"]

    for key in ("brent", "smh", "rsp", "spy"):
        df[f"r_{key}"] = _aligned_returns(series[key], df.index)
    df["r_ai_rel"] = df["r_smh"] - df["r_rsp"]

    for key in ("kospi", "hynix", "samsung"):
        df[f"next_{key}"] = _next_day_return(series[key], df.index)

    def flag(dates):
        return df.index.isin(pd.to_datetime(dates))

    df["ev_cpi"] = flag(config.CPI_DATES)
    df["ev_ppi"] = flag(config.PPI_DATES)
    df["ev_pce"] = flag(config.PCE_DATES)
    df["ev_nfp"] = flag(config.NFP_DATES)
    df["ev_fomc"] = flag(config.FOMC_DATES)
    df["ev_ai_issue"] = flag(config.AI_ISSUANCE_DATES)
    df["ev_inflation"] = df["ev_cpi"] | df["ev_ppi"] | df["ev_pce"]
    df["ev_fed"] = df["ev_nfp"] | df["ev_fomc"]
    return df


def rolling_contributions(df: pd.DataFrame) -> pd.DataFrame:
    """t일 기여도 = (t-1까지 120일로 추정한 계수) × (t일 요인 값). 합은 정확히 Δ10Y."""
    xcols = ["r_brent", "r_ai_rel"]
    X = df[xcols].to_numpy()
    y = df["d_y10"].to_numpy()
    n = len(df)
    out = {k: np.full(n, np.nan) for k in ("oil", "ai", "resid", "b_oil", "b_ai", "r2")}
    for i in range(n):
        lo = max(0, i - config.REG_WINDOW)
        Xw, yw = X[lo:i], y[lo:i]
        ok = ~np.isnan(Xw).any(axis=1) & ~np.isnan(yw)
        if ok.sum() < config.REG_MIN or np.isnan(X[i]).any() or np.isnan(y[i]):
            continue
        A = np.column_stack([np.ones(ok.sum()), Xw[ok]])
        coef, *_ = np.linalg.lstsq(A, yw[ok], rcond=None)
        fitted = A @ coef
        ss_res = ((yw[ok] - fitted) ** 2).sum()
        ss_tot = ((yw[ok] - yw[ok].mean()) ** 2).sum()
        _, b_oil, b_ai = coef
        out["oil"][i] = b_oil * X[i, 0]
        out["ai"][i] = b_ai * X[i, 1]
        out["resid"][i] = y[i] - out["oil"][i] - out["ai"][i]  # 절편 포함
        out["b_oil"][i], out["b_ai"][i] = b_oil, b_ai
        out["r2"][i] = 1 - ss_res / ss_tot if ss_tot else np.nan
    for k, v in out.items():
        df[f"c_{k}" if k in ("oil", "ai", "resid") else k] = v

    # 설명 안 된 몫을 그날 일정에 따라 배정 (우선순위: 물가지표 > 연준·고용 > AI 조달 > 기타)
    infl, fed, fund = df["ev_inflation"], df["ev_fed"], df["ev_ai_issue"]
    df["c_inflation"] = np.where(infl, df["c_resid"], 0.0)
    df["c_fed"] = np.where(~infl & fed, df["c_resid"], 0.0)
    df["c_ai_fund"] = np.where(~infl & ~fed & fund, df["c_resid"], 0.0)
    df["c_other"] = np.where(~infl & ~fed & ~fund, df["c_resid"], 0.0)
    for c in ("c_inflation", "c_fed", "c_ai_fund", "c_other"):
        df.loc[df["c_resid"].isna(), c] = np.nan
    return df


def classify(row: pd.Series) -> tuple[str, str]:
    """하루 대표 라벨 (사용자 3갈래: 물가 / AI / 지정학 + 연준·텀프리미엄·기타). 임계값은 config.TH."""
    th = config.TH
    d10, d2, dbei = row["d_y10"], row["d_y2"], row["d_bei10"]
    oil, ai_rel, spy = row["r_brent"], row["r_ai_rel"], row["r_spy"]
    if any(pd.isna(v) for v in (d10, d2, dbei)):
        return "자료없음", ""
    if abs(d10) < th["flat_bp"]:
        return "횡보", ""
    sgn = np.sign(d10)

    if row["ev_inflation"] and (abs(d2) >= th["data_2y_bp"] or abs(dbei) >= th["data_bei_bp"]):
        names = [n for n, f in (("CPI", "ev_cpi"), ("PPI", "ev_ppi"), ("PCE", "ev_pce")) if row[f]]
        return "물가지표", "·".join(names) + (" → BEI" if abs(dbei) >= abs(d2) else " → 2Y(연준 경로)")

    if row["ev_fed"]:
        return "연준·고용", "FOMC" if row["ev_fomc"] else "고용지표"

    # 'AI 롱 / 채권 숏' 되감기: AI는 빠지고 나머지는 오르며 금리도 빠지는 날
    smh, rsp = row["r_smh"], row["r_rsp"]
    if d10 < 0 and not pd.isna(smh) and smh <= th["degross_smh_pct"] and rsp >= 0:
        return "AI 디그로싱", "AI↓·나머지↑·금리↓ ('AI 롱/채권 숏' 되감기)"

    if not pd.isna(oil) and abs(oil) >= th["oil_pct"]:
        if np.sign(oil) == sgn and (np.sign(dbei) == sgn or np.sign(d2) == sgn):
            return "지정학·유가", "BEI 경로" if abs(dbei) >= abs(d2) * 0.5 else "연준 경로(2Y)"
        if oil > 0 and d10 < 0 and not pd.isna(spy) and spy <= th["riskoff_spy_pct"]:
            return "지정학·안전자산", "유가↑·주식↓·금리↓"

    if row["ev_ai_issue"] and d10 > 0:
        return "AI 조달", "AI 대형 회사채 발행일"

    if d10 > 0 and not pd.isna(ai_rel) and ai_rel >= th["ai_rel_pct"]:
        return "AI 성장", "AI↑·금리↑ (성장·capex로 금리를 해석)"

    if d10 > 0 and (d10 - d2) >= th["steep_bp"] and abs(dbei) <= th["bei_flat_bp"]:
        return "텀프리미엄·수급", "베어 스티프너, BEI 보합 (조달·재정·글로벌 장기물 후보)"

    if abs(d2) >= abs(d10) * 0.9 and np.sign(d2) == sgn:
        return "연준 경로", "2Y 주도 (이벤트 없는 날)"
    return "기타·혼합", ""


def window_sums(df: pd.DataFrame, start: pd.Timestamp) -> dict:
    w = df[df.index >= start]
    out = {"from": start.strftime("%Y-%m-%d"), "days": int(len(w)), "d10": float(w["d_y10"].sum()),
           "real": float(w["d_real10"].sum()), "bei": float(w["d_bei10"].sum()),
           "d2": float(w["d_y2"].sum()), "d30": float(w["d_y30"].sum())}
    for k in BUCKET_NAMES:
        out[k] = float(w[f"c_{k}"].sum())
    out["tags"] = w["tag"].value_counts().to_dict()
    return out


def tag_stats(df: pd.DataFrame) -> list[dict]:
    rows = []
    for tag, g in df.groupby("tag"):
        if tag in ("자료없음",):
            continue
        rows.append({
            "tag": tag, "n": int(len(g)),
            "d10": float(g["d_y10"].mean()), "ai_rel": float(g["r_ai_rel"].mean()),
            "rsp": float(g["r_rsp"].mean()), "smh": float(g["r_smh"].mean()),
            "kospi": float(g["next_kospi"].mean()), "hynix": float(g["next_hynix"].mean()),
        })
    return sorted(rows, key=lambda r: -r["n"])


# ── 출력 ──

def _fmt_day(ts: pd.Timestamp) -> str:
    return f"{ts.month}/{ts.day}({WD[ts.weekday()]})"


def _s(v, nd=1, pct=False) -> str:
    if v is None or pd.isna(v):
        return "–"
    if round(v, nd) == 0:
        return "0"
    return f"{v:+.{nd}f}{'%' if pct else ''}"


def telegram_text(df: pd.DataFrame, leg: dict) -> str:
    r = df.dropna(subset=["d_y10"]).iloc[-1]
    d = r.name
    lines = [
        f"<b>금리 원인 분해 · 미국 {_fmt_day(d)}</b>",
        f"10Y {r['y10']:.2f}% ({_s(r['d_y10'])}bp) = 실질 {_s(r['d_real10'])} / BEI {_s(r['d_bei10'])}"
        f" · 2Y {_s(r['d_y2'])} · 30Y {_s(r['d_y30'])}",
        f"판정: <b>{r['tag']}</b>" + (f" — {r['subtag']}" if r["subtag"] else ""),
        "기여(bp): " + " | ".join(f"{BUCKET_SHORT[k]} {_s(r[f'c_{k}'])}" for k in BUCKET_SHORT if not pd.isna(r[f"c_{k}"])),
        f"반응: 브렌트 {_s(r['r_brent'], pct=True)} · SMH−RSP {_s(r['r_ai_rel'])}%p · 코스피 익일 {_s(r['next_kospi'], pct=True)}",
        f"{leg['from'][5:].replace('-', '/')} 이후 누적 10Y {_s(leg['d10'], 0)}bp = "
        + ", ".join(f"{BUCKET_SHORT[k]} {_s(leg[k], 0)}" for k in BUCKET_SHORT),
    ]
    return "\n".join(lines)


def render_html(df: pd.DataFrame, rep: pd.DataFrame, summaries: list[dict], stats: list[dict]) -> str:
    template = (BASE / "template_report.html").read_text(encoding="utf-8")

    def rows(frame: pd.DataFrame) -> list[dict]:
        out = []
        for ts, r in frame.iterrows():
            rec = {"date": ts.strftime("%Y-%m-%d"), "tag": r["tag"], "subtag": r["subtag"]}
            for c in ("y10", "d_y10", "d_y2", "d_y30", "d_real10", "d_bei10", "r_brent", "r_ai_rel", "r_smh",
                      "r_rsp", "r_spy", "next_kospi", "next_hynix", "b_oil", "b_ai", "r2"):
                rec[c] = None if pd.isna(r[c]) else round(float(r[c]), 3)
            for k in BUCKET_NAMES:
                v = r[f"c_{k}"]
                rec[f"c_{k}"] = None if pd.isna(v) else round(float(v), 3)
            ev = [n for n, f in (("CPI", "ev_cpi"), ("PPI", "ev_ppi"), ("PCE", "ev_pce"),
                                 ("고용", "ev_nfp"), ("FOMC", "ev_fomc"), ("AI채권", "ev_ai_issue")) if r[f]]
            rec["events"] = ev
            out.append(rec)
        return out

    payload = {
        "generated": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "buckets": [{"key": k, "name": n, "color": c} for k, n, _, c in config.BUCKETS],
        "rows": rows(rep),
        "summaries": summaries,
        "stats": stats,
        "th": config.TH,
        "regWindow": config.REG_WINDOW,
        "chartDays": config.CHART_DAYS,
    }
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return template.replace("/*__DATA__*/null", data_json)


def run(offline: bool = False) -> dict:
    if offline:
        rates = pd.read_csv(data.CACHE / "treasury.csv", index_col=0, parse_dates=True)
        series = {k: pd.read_csv(data.CACHE / f"{k}.csv", index_col=0, parse_dates=True).iloc[:, 0]
                  for k in config.TICKERS}
    else:
        rates, series = data.load_all()

    df = build_table(rates, series)
    df = rolling_contributions(df)
    tags = df.apply(classify, axis=1, result_type="expand")
    df["tag"], df["subtag"] = tags[0], tags[1]

    rep = df.dropna(subset=["d_y10"]).iloc[-config.REPORT_DAYS:]
    last = rep.index[-1]
    summaries = [
        window_sums(rep, rep.index[-5]) | {"label": "최근 5일"},
        window_sums(rep, rep.index[-20]) | {"label": "최근 20일"},
        window_sums(rep, rep.index[-60]) | {"label": "최근 60일"},
        window_sums(rep, pd.Timestamp(config.LEG_START)) | {"label": f"{config.LEG_START:%m/%d} 이후(이번 레그)"},
        window_sums(rep, rep.index[0]) | {"label": f"최근 {len(rep)}일(약 1년)"},
    ]
    stats = tag_stats(rep)

    OUT.mkdir(exist_ok=True)
    html_path = OUT / "금리분해.html"
    html_path.write_text(render_html(df, rep, summaries, stats), encoding="utf-8")

    cols = {
        "y10": "10Y(%)", "d_y10": "Δ10Y(bp)", "d_y2": "Δ2Y", "d_y30": "Δ30Y", "d_real10": "Δ실질10Y",
        "d_bei10": "ΔBEI10Y", "r_brent": "브렌트%", "r_ai_rel": "SMH−RSP(%p)", "r_spy": "SPY%",
        "next_kospi": "코스피 익일%", "next_hynix": "하이닉스 익일%", "tag": "판정", "subtag": "세부",
        **{f"c_{k}": f"기여_{n}" for k, n in BUCKET_NAMES.items()},
    }
    rep[list(cols)].rename(columns=cols).round(3).to_csv(OUT / "금리분해_일별.csv", encoding="utf-8-sig")

    return {"last": last, "html_path": html_path, "text": telegram_text(rep, summaries[3]), "df": rep}


def send_telegram(text: str, html_path: Path) -> None:
    """수급캘린더/.env의 봇 토큰·Chat ID로 요약과 HTML을 보낸다(작업 스케줄러용)."""
    import os

    import httpx
    from dotenv import load_dotenv

    load_dotenv(BASE.parent / "수급캘린더" / ".env")
    token, chat_id = os.getenv("TELEGRAM_BOT_TOKEN", ""), os.getenv("CHAT_ID", "")
    if not token or not chat_id:
        sys.exit("수급캘린더/.env에 TELEGRAM_BOT_TOKEN과 CHAT_ID를 넣어주세요.")
    api = f"https://api.telegram.org/bot{token}"
    with httpx.Client(timeout=30) as client:
        r = client.post(f"{api}/sendMessage", data={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                                                    "disable_web_page_preview": "true"})
        if not r.json().get("ok"):
            raise RuntimeError(r.text)
        with html_path.open("rb") as f:
            r = client.post(f"{api}/sendDocument", data={"chat_id": chat_id, "caption": "금리 원인 분해 (브라우저로 열기)"},
                            files={"document": (html_path.name, f, "text/html")})
        if not r.json().get("ok"):
            raise RuntimeError(r.text)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    parser = argparse.ArgumentParser(description="금리 원인 분해")
    parser.add_argument("--offline", action="store_true", help="캐시 데이터만 사용")
    parser.add_argument("--quiet", action="store_true", help="텔레그램 요약 텍스트만 출력(봇 연동용)")
    parser.add_argument("--send", action="store_true", help="텔레그램으로 전송")
    args = parser.parse_args()
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    result = run(offline=args.offline)
    if not args.quiet:
        print(f"HTML: {result['html_path']}")
        print("─" * 40)
    print(result["text"])
    if args.send:
        send_telegram(result["text"], result["html_path"])
        if not args.quiet:
            print("텔레그램 전송 완료")


if __name__ == "__main__":
    main()
