# -*- coding: utf-8 -*-
"""매크로 탭(미 금리·실질/BEI·텀프리미엄·원/달러·Brent·연준 확률·금리 판정) 조각.

render.py 가 index.html 을 구울 때 MACRO_CSS / MACRO_HTML / macro_script() 를 끼워 넣는다.
데이터는 data/macro.json(scripts/macro_data.py). 없으면 탭에 '데이터 없음'만 표시한다.
수급 탭과 날짜축이 달라(미 채권시장 영업일) 기간 바를 따로 쓴다.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MACRO_PATH = ROOT / "data" / "macro.json"

# 링크 서랍(기본 접힘). 공개 페이지라 claude.ai 아티팩트는 로그인한 본인만 열린다.
LINKS = [
    ("수급·자사주", [
        ("자사주 바이백 대시보드 (삼성전자·SK하이닉스)", "https://jaey27.github.io/buyback-dashboard/", "윈도우 수동 갱신 · 삼성 15조 완료(10/6)"),
        ("이격도 대시보드", None, "미배포(7/1 로컬 커밋만) · 예탁금·신용은 이 페이지 '시장 수급' 탭과 같음"),
        ("ETF 자금유출입 트래커", None, "텔레그램 평일 08:30 자동 발송(맥미니)"),
    ]),
    ("금리·국채", [
        ("MacroMicro — ACM 10Y 텀프리미엄", "https://en.macromicro.me/charts/45452/us-10-treasury-term-premium", "원천 = NY Fed ACM(이 탭과 같은 데이터)"),
        ("MacroMicro — 10Y 금리 구성(실질·BEI·TP)", "https://en.macromicro.me/charts/86836/us-10y-treasury-yield-composition", ""),
        ("MacroMicro — 10Y vs TIPS", "https://en.macromicro.me/search?q=10Y%20Treasury%20vs%20TIPS", ""),
        ("NY Fed ACM 원자료", "https://www.newyorkfed.org/research/data_indicators/term-premia-tabs", "1영업일 지연"),
        ("국채 숫자 눈금자", "https://claude.ai/artifact/1YVZ2tAs873qQ9x2hEqtME", "아티팩트(9/10)"),
        ("롱본드 수급 레이더", "https://claude.ai/code/artifact/f62274d4-dbae-4fce-a326-3bd1581c468e", "아티팩트"),
        ("롱본드 갈림길", "https://claude.ai/artifact/Ja9yTBJ3vSQEYkZBfG9Bbc", "아티팩트(9/3)"),
        ("미국채 수급 아티팩트집", "https://claude.ai/artifact/XPqaBcitVEqe26JN4gHwZf", "아티팩트(9/13)"),
        ("실질금리 vs AI 일별 분해", "https://claude.ai/artifact/TtmcWygLh8RdApWBscfxFy", "아티팩트(10/14)"),
    ]),
    ("정치·지정학", [
        ("블루스윕 반영도 점검", "https://claude.ai/artifact/Bc7p7WQ4yvgG6fBMGqeuBB", "아티팩트(10/14 기준)"),
        ("전쟁·금리 매크로 노트", "https://claude.ai/artifact/XgEXRAad4aUE1PSvLPj9L9", "아티팩트"),
        ("전쟁과 금리 케이스스터디", "https://claude.ai/artifact/QTU2SewAwbw4Gi7psr1629", "아티팩트"),
    ]),
]

MACRO_CSS = r"""
#tab-macro .card{margin-bottom:16px}
.mx-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.mx-bar .lbl{font-size:12px;color:var(--text-dim)}
.mx-bar label{font-size:12px;color:var(--text-dim);display:inline-flex;gap:6px;align-items:center;cursor:pointer}
.mx-bar .asof{margin-left:auto;font-size:11px;color:var(--text-muted)}
.mx-tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:16px}
@media (max-width:1100px){.mx-tiles{grid-template-columns:repeat(3,1fr)}}
@media (max-width:560px){.mx-tiles{grid-template-columns:1fr 1fr}}
.mx-t{background:var(--surface);border:1px solid rgba(151,252,228,.08);border-left:3px solid rgba(157,179,176,.45);border-radius:12px;padding:10px 12px;min-width:0}
.mx-t .k{font-size:11px;color:var(--text-muted);line-height:1.35}
.mx-t .v{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em;margin:2px 0}
.mx-t .d{font-size:11.5px;color:var(--text-dim);font-variant-numeric:tabular-nums;white-space:nowrap}
.mx-t .d b{font-weight:700}
.mx-t .pb{position:relative;height:4px;border-radius:2px;background:rgba(157,179,176,.15);margin:7px 0 3px}
.mx-t .pb i{position:absolute;top:-3px;width:2px;height:10px;background:#c9d6d4;border-radius:1px}
.mx-t .pl{font-size:10.5px;color:var(--text-muted);display:grid;grid-template-columns:1fr auto 1fr;gap:6px;font-variant-numeric:tabular-nums}.mx-t .pl span:last-child{text-align:right}
.mx-t .lv{font-size:10.5px;color:var(--text-muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mx-t[data-ch]{cursor:pointer}.mx-t[data-ch]:hover{border-color:rgba(151,252,228,.3)}.card.mx-flash{box-shadow:0 0 0 2px var(--hl-teal)}
.mx-up{color:var(--up)} .mx-dn{color:var(--down)}
.mx-verdict{font-size:14px;line-height:1.6}
.mx-verdict .tag{display:inline-block;padding:1px 9px;border-radius:999px;background:rgba(151,252,228,.12);color:var(--hl-teal);font-weight:700;margin-right:6px}
.mx-contrib{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.mx-contrib span{font-size:11.5px;padding:2px 8px;border-radius:6px;background:rgba(157,179,176,.10);color:var(--text-dim);font-variant-numeric:tabular-nums}
.mx-tbl{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums;margin-top:10px}
.mx-tbl th,.mx-tbl td{padding:5px 8px;border-bottom:1px solid rgba(151,252,228,.07);text-align:right;white-space:nowrap}
.mx-tbl th:first-child,.mx-tbl td:first-child,.mx-tbl td.l,.mx-tbl th.l{text-align:left}
.mx-tbl th{color:var(--text-muted);font-weight:600}
.mx-fed{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
@media (max-width:900px){.mx-fed{grid-template-columns:1fr}}
.mx-fed h4{font-size:12.5px;margin-bottom:4px;color:var(--text)}
.mx-fed .row{display:grid;grid-template-columns:78px 1fr 120px;gap:6px;align-items:center;font-size:11.5px;margin:3px 0;font-variant-numeric:tabular-nums}
.mx-fed .bar{height:8px;border-radius:4px;background:rgba(157,179,176,.12);overflow:hidden}
.mx-fed .bar i{display:block;height:100%;background:#9db3b0}
.mx-fed .row.top .bar i{background:var(--hl-teal-dim)}
.mx-fed .row .n{text-align:right;color:var(--text-dim)}
.mx-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:900px){.mx-grid{grid-template-columns:1fr}}
.mx-grid .card{margin-bottom:0}
.mx-box{position:relative;height:250px}
.mx-links{margin-top:16px}
.mx-links summary{cursor:pointer;font-size:13px;font-weight:700;color:var(--text-dim);padding:12px 16px;list-style:none}
.mx-links summary::-webkit-details-marker{display:none}
.mx-links summary::before{content:'▸ ';color:var(--hl-teal-dim)}
.mx-links[open] summary::before{content:'▾ '}
.mx-links .body{padding:0 16px 14px;display:grid;grid-template-columns:repeat(3,1fr);gap:14px}
@media (max-width:900px){.mx-links .body{grid-template-columns:1fr}}
.mx-links h5{font-size:11.5px;color:var(--text-muted);margin:4px 0 6px}
.mx-links li{list-style:none;font-size:12.5px;margin:5px 0;line-height:1.45}
.mx-links li a{color:var(--hl-teal)}
.mx-links li .n{display:block;font-size:11px;color:var(--text-muted)}
.mx-empty{padding:30px;text-align:center;color:var(--text-dim)}
.mx-note{font-size:12px;color:var(--text-dim);margin-top:10px;line-height:1.55;padding:8px 12px;border-left:3px solid rgba(151,252,228,.25);background:rgba(151,252,228,.04);border-radius:6px}
.mx-sum{display:flex;flex-wrap:wrap;gap:8px;margin:2px 0 8px}.mx-sum span{font-size:12.5px;padding:4px 10px;border-radius:8px;background:rgba(157,179,176,.10);font-variant-numeric:tabular-nums}
.ov-btn{padding:3px 10px;border-radius:999px;font-size:11.5px;color:var(--text-dim);background:rgba(151,252,228,.04);border:1px solid rgba(151,252,228,.12);cursor:pointer}.ov-btn.on{color:var(--bg-0);background:#9db3b0;border-color:#9db3b0;font-weight:700}
.rk-below{color:var(--down);font-size:10px;margin-right:3px}.rk-fit td,.rk-fit th{white-space:normal!important;vertical-align:top}.rk-fit .rk-wrap{min-width:160px;max-width:none}.rk-src{font-size:10.5px;color:var(--hl-teal);text-decoration:none;font-weight:500;white-space:nowrap}.rk-src:hover,.rk-name:hover{text-decoration:underline}.rk-name{color:var(--text);text-decoration:none}
.rk-grow td{background:rgba(151,252,228,.06);color:var(--hl-teal);font-weight:700;font-size:11.5px}.rk-sub{font-size:11px;color:var(--text-muted);font-weight:400}.rk-tag{font-size:10px;padding:0 5px;border-radius:4px;background:rgba(157,179,176,.15);color:var(--text-muted)}.rk-wrap{white-space:normal!important;min-width:180px;max-width:300px}.rk-hy{grid-template-columns:repeat(6,1fr)}@media (max-width:1100px){.rk-hy{grid-template-columns:repeat(3,1fr)}}#tab-risk .card-tools{max-width:100%;min-width:0;flex-wrap:wrap}#tab-risk .card-tools .seg{flex-wrap:wrap;border-radius:14px}#tab-risk .card-head > div:first-child{min-width:0}#rk-grp,#rk-ism,#rk-cg,#rk-dcm,#rk-dcg{max-width:100%;overflow-x:auto}@media (max-width:560px){.rk-hy{grid-template-columns:1fr 1fr}}
.ec-tbl td.next{color:var(--hl-teal);font-weight:700}

/* 전체화면(차트 카드) — iOS 는 요소 Fullscreen API 가 없어 CSS 오버레이로 처리 */
.fs-btn{padding:3px 9px;border-radius:999px;font-size:13px;line-height:1.2;color:var(--text-dim);background:rgba(151,252,228,.04);border:1px solid rgba(151,252,228,.12);cursor:pointer}
.fs-btn:hover{color:var(--hl-teal)}
.card.fs .cl-btn{display:none}
.card.fs{position:fixed!important;inset:0;z-index:1000;margin:0!important;border-radius:0;overflow:auto;background:#061E20;
  padding:max(12px,env(safe-area-inset-top)) max(12px,env(safe-area-inset-right)) max(12px,env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left))}
.card.fs .chart-box,.card.fs .mx-box,.card.fs .rank-box{height:calc(100dvh - 150px)!important;min-height:220px}
body.fs-lock{overflow:hidden}
.card.cl > :not(.card-head){display:none!important}.card.cl .card-head{margin-bottom:0}.card.cl .card-tools > :not(.cl-btn){display:none}
"""


def _links_html() -> str:
    cols = []
    for head, items in LINKS:
        lis = []
        for name, url, note in items:
            a = f'<a href="{url}" target="_blank" rel="noopener">{name} ↗</a>' if url else f"<span>{name}</span>"
            lis.append(f"<li>{a}{f'<span class=n>{note}</span>' if note else ''}</li>")
        cols.append(f"<div><h5>{head}</h5><ul>{''.join(lis)}</ul></div>")
    return "".join(cols)


MACRO_HTML = r"""
<div id="tab-macro" hidden>
<div class="mx-bar"><span class="lbl">기간</span><div class="seg" id="mx-presets"></div>
  <div class="range-dates"><input id="mx-d0" class="dinp" inputmode="numeric" aria-label="시작일 입력" title="날짜 입력 후 Enter (예: 2026-04-15, 260415, 4/15)"><span>~</span><input id="mx-d1" class="dinp" inputmode="numeric" aria-label="종료일 입력" title="날짜 입력 후 Enter"><span id="mx-rlab"></span></div>
  <span class="asof" id="mx-asof"></span></div>
<div class="mx-note" style="margin:0 0 10px">바 읽는 법: 흰 눈금 = 오늘 값이 최근 1년 범위에서 어디쯤인지, 가운데 %ile = 그 위치(0% = 1년 최저, 100% = 1년 최고). 왼쪽 끝 숫자 = 1년 최저, 오른쪽 끝 = 1년 최고. 카드를 누르면 해당 차트로 이동.</div>
<div class="rng" id="mx-rng" style="margin:-4px 0 14px"><canvas id="mx-ov-c" aria-hidden="true"></canvas><input type="range" id="mx-r0" min="0" step="1" aria-label="시작일"><input type="range" id="mx-r1" min="0" step="1" aria-label="종료일"></div>
<div class="mx-tiles" id="mx-tiles"></div>
<section class="card" id="mx-dec-card"><div class="card-head"><div><div class="card-title">10Y 상승은 무엇이었나 — 텀프리미엄 vs BEI</div>
  <div class="card-sub">위 기간 바 기준(기본 6M) · 왼쪽 = 기간 시작 대비 누적 bp · 오른쪽 = 10Y 금리 수준 %(같은 스케일, 흰 선 기준) · 코스피는 툴팁에 기간 시작 대비 % · ① 재무부: 10Y = 실질 + BEI ② NY Fed ACM: 10Y = 기대 단기금리 경로 + 텀프리미엄</div></div></div>
  <div id="mx-dec-sum"></div><div class="mx-box" style="height:300px"><canvas id="mx-dec"></canvas></div>
  <div id="mx-dec-exp" style="margin-top:12px"></div>
  <div class="mx-note"><b>관계 — 같은 10Y를 두 방식으로 쪼갠 것</b><br>① 재무부 기준: <b>10Y = 실질 + BEI</b> (시장 가격으로 바로 계산)<br>② NY Fed ACM 기준: <b>10Y = 기대경로 + 텀프리미엄</b> (모형 추정, 1영업일 늦음)<br>두 분해는 서로 다른 축이라 섞어 더하면 안 됨. ①은 '인플레이션이냐 아니냐', ②는 '연준 때문이냐 장기 보유 프리미엄 때문이냐'를 본다.</div>
  <div class="mx-note">체크포인트(Jae 프레임): 종전 등으로 유가·지정학 프리미엄이 빠지면 BEI·기대경로는 내려갈 수 있다. 그래도 10Y가 안 떨어지려면 <b>텀프리미엄이 유지</b>돼야 한다 → TP 선이 꺾이는지 본다.</div></section>
<section class="card"><div class="card-head"><div><div class="card-title">금리 판정 — 10Y는 왜 움직였나</div>
  <div class="card-sub">사실: Δ10Y = Δ실질 + ΔBEI · 기여: 120일 회귀(브렌트·SMH−RSP) + 발표일 배정 · 인과 아님 · <a href="rates.html" style="color:var(--hl-teal)">금리분해 상세 ↗</a></div></div></div>
  <div id="mx-verdict"></div></section>
<section class="card"><div class="card-head"><div><div class="card-title">연준 확률 — CME FedWatch 방식</div>
  <div class="card-sub" id="mx-fw-sub"></div></div></div><div class="mx-fed" id="mx-fw"></div>
  <details class="claim-sub"><summary>보조: Kalshi 예측시장</summary><div class="card-sub" id="mx-fed-sub" style="margin:4px 0 8px"></div><div class="mx-fed" id="mx-fed"></div></details></section>
<div class="mx-grid" id="mx-grid"></div>
<details class="card mx-links"><summary>링크 서랍 — 바이백·이격도·국채·정치 아티팩트 (매일 보는 것 아님)</summary>
  <div class="body">__LINKS__</div></details>
</div>
<div id="tab-econ" hidden>
<section class="card"><div class="card-head"><div><div class="card-title">발표 일정 — 발표 전후에만 본다</div>
  <div class="card-sub">미국 날짜 · 출처: BLS·BEA·연준 공식 일정(rates/config.py) · 매일 1장에는 넣지 않음</div></div></div><div id="ec-cal"></div></section>
<section class="card"><div class="card-head"><div><div class="card-title">CPI 세부 (근원 30항목 기여도 · 3/6개월 연율)</div>
  <div class="card-sub">BLS 원자료 · 월 1회 갱신 · <a href="cpi.html" target="_blank" rel="noopener" style="color:var(--hl-teal)">새 창 ↗</a></div></div></div>
  <iframe id="ec-cpi" title="CPI 세부" style="width:100%;height:1400px;border:0;border-radius:12px;background:#061E20"></iframe></section>
<section class="card" id="ec-ppi-card"><div class="card-head"><div><div class="card-title">PPI 세부 — 최종수요 · 원자재→중간재→최종재→CPI · 유통마진</div>
  <div class="card-sub" id="ec-ppi-sub">BLS 원자료 · 월 1회 갱신</div></div><div class="card-tools"><div class="seg" id="ec-ppi-v"></div></div></div>
  <div id="ec-ppi-tbl"></div><div class="mx-box" style="height:320px;margin-top:10px"><canvas id="ec-ppi-c"></canvas></div>
  <div class="mx-note" id="ec-ppi-note"></div></section>
<script>window.__PPI__ = __PPIDATA__;</script>
<section class="card" id="ec-rt-card"><div class="card-head"><div><div class="card-title">소매판매 세부 — 헤드라인·컨트롤그룹 · 업종 기여 · 주유소 가격 vs 물량</div>
  <div class="card-sub" id="ec-rt-sub">Census MARTS · 월 1회 갱신</div></div><div class="card-tools"><div class="seg" id="ec-rt-v"></div></div></div>
  <div id="ec-rt-tbl"></div><div class="mx-box" style="height:320px;margin-top:10px"><canvas id="ec-rt-c"></canvas></div>
  <div class="mx-note" id="ec-rt-note"></div></section>
<script>window.__RETAIL__ = __RETAILDATA__;</script>
<section class="card" id="ec-em-card"><div class="card-head"><div><div class="card-title">고용 세부 — 비농업 고용 · 실업률 · 임금 · 업종</div>
  <div class="card-sub" id="ec-em-sub">BLS · 월 1회 갱신</div></div><div class="card-tools"><div class="seg" id="ec-em-v"></div></div></div>
  <div id="ec-em-tbl"></div><div class="mx-box" style="height:320px;margin-top:10px"><canvas id="ec-em-c"></canvas></div>
  <div class="mx-note" id="ec-em-note"></div></section>
<script>window.__EMP__ = __EMPDATA__;</script>
<section class="card"><div class="card-title">PCE</div><div class="card-sub" style="margin-top:6px">다음 단계에서 추가 (CPI·PPI로 근원 PCE 추정 → 실제값과 대조)</div></section>
</div>
<div id="tab-risk" hidden>
<div class="mx-bar"><span class="lbl">기간</span><div class="seg" id="rk-presets"></div>
  <div class="range-dates"><input id="rk-d0" class="dinp" inputmode="numeric" aria-label="시작일 입력" title="날짜 입력 후 Enter (예: 2025-06-01, 250601, 6/1)"><span>~</span><input id="rk-d1" class="dinp" inputmode="numeric" aria-label="종료일 입력" title="날짜 입력 후 Enter"><span id="rk-rlab"></span></div>
  <span class="asof" id="rk-asof"></span></div>
<div class="rng" style="margin:-4px 0 14px"><div style="position:absolute;left:0;right:0;top:12px;height:6px;border-radius:3px;background:rgba(151,252,228,.12)"></div><input type="range" id="rk-r0" min="0" step="1" aria-label="시작일"><input type="range" id="rk-r1" min="0" step="1" aria-label="종료일"></div>
<section class="card" id="rk-iss-card"><div class="card-head"><div><div class="card-title">발행사별 최고 YTM 채권 가격</div>
  <div class="card-sub">FINRA TRACE 일별 종가(T-1) · 위 기간 바</div></div><div class="card-tools"><div class="seg" id="rk-grp"></div><div class="seg" id="rk-ism"></div></div></div>
  <div class="mx-box" style="height:300px"><canvas id="rk-iss"></canvas></div></section>
<section class="card"><div class="card-head"><div><div class="card-title">CDS 5Y 추이</div>
  <div class="card-sub" id="rk-cds-sub2">DTCC 공개 체결(on-the-run 5Y, 3·9월 롤) · '비교' = 체결일 값을 앞으로 채운 뒤 5거래일 중앙값·로그축(SoftBank·SpaceX는 범례 클릭으로 켬) · 그룹 보기 점 = 체결 있던 날. 호가 없는 날은 upfront 역산(R=40%) — 수준보다 방향을 볼 것. NBIS·HUT는 체결 없음</div></div><div class="card-tools"><div class="seg" id="rk-cg"></div></div></div>
  <div class="mx-box" style="height:300px"><canvas id="rk-cds"></canvas></div></section>
<section class="card" id="rk-vol-card"><div class="card-head"><div><div class="card-title">하이퍼스케일러 CDS 주간 거래 (DTCC 공개 체결)</div>
  <div class="card-sub" id="rk-vol-sub">신규 체결(NEWT) · 모든 만기 · 주간 합계 · 위 기간 바</div></div><div class="card-tools"><div class="seg" id="rk-vv"></div></div></div>
  <div class="mx-box" style="height:280px"><canvas id="rk-vol"></canvas></div>
  <div class="mx-note">공개 체결은 큰 거래를 '5,000,000+'처럼 상한으로 가려서 내보낸다 → 명목 합계는 <b>최소</b>(하한)이고, 추이는 <b>건수</b>가 더 깨끗하다. Morgan Stanley 집계(주간 수십억 달러)와 절대 수준은 다르다. 출처: DTCC SEC 단일종목 CDS 공개 체결.</div></section>
<section class="card" id="rk-hy-card"><div class="card-head"><div><div class="card-title">하이일드 스프레드 — AI vs 비AI + 국채</div>
  <div class="card-sub" id="rk-hy-sub"></div></div><div class="card-tools"><div class="seg" id="rk-hv"></div></div></div>
  <div class="mx-box" style="height:300px"><canvas id="rk-hyc"></canvas></div>
  <div class="mx-note" id="rk-hy-contrib"></div>
  <details class="claim-sub" id="rk-hy-ai"></details>
  <div class="mx-note"><b>등급 경계</b>: 투자등급(IG) = S&amp;P·Fitch AAA~<b>BBB-</b> / Moody's Aaa~<b>Baa3</b>. 하이일드(HY) = <b>BB+</b>~D / <b>Ba1</b>~C. BB+는 하이일드 맨 위 — 예: SoftBank BB+(HY 맨 위), Hut 8 River Bend BBB-(IG 맨 아래), CoreWeave B+(HY), Oracle BBB-(IG 경계). BBB-→BB+로 떨어지면(fallen angel) IG만 살 수 있는 기관의 강제 매도로 스프레드가 튄다.<br>
  <b>용어</b>: 스프레드 = 회사채가 같은 만기 미국 국채보다 더 주는 금리(가산금리, bp=0.01%p). 높을수록 시장이 부도 위험을 크게 본다는 뜻. 공식 지수 = ICE BofA 회사채 지수의 가산금리(조기상환 같은 옵션 효과를 뺀 값, FRED에서 받음).<br><b>HY 중 AI − 같은 만기 국채 (FINRA 복원)</b>: iShares 하이일드 ETF(HYG)가 들고 있는 AI 관련 채권 20개를 골라, 채권마다 FINRA에 찍힌 일별 수익률에서 같은 만기 국채 금리를 뺀 뒤 HYG 안 비중(오늘 기준 고정)으로 가중평균. 과거엔 이 채권들이 대부분 미발행이라, 그날 값이 있는 채권이 AI 묶음 비중의 40% 이상인 날만 그림.<br><b>맨 위 최신값(AI·비AI·투자등급)</b>: iShares HYG·LQD가 매일 공개하는 보유채권 파일에서 채권별 수익률 − 같은 만기 국채로 직접 계산. 비AI 선 = (하이일드 전체 − AI 비중×AI) ÷ (1 − AI 비중)으로 추정한 근사치.</div></section>

<section class="card"><div class="card-head"><div><div class="card-title">발행사 크레딧 한 장 — 최고 YTM 채권 · CDS</div>
  <div class="card-sub">▼ = 액면가(100) 아래 · 1M Δ = 21거래일 가격 변화 · G-spread = YTM − 같은 만기 국채(근사) · CDS = DTCC 공개 체결(5Y, 2031-12 만기) · 등급에 마우스를 올리면 원문</div></div></div>
  <div id="rk-tbl"></div>
  <div class="mx-note">가격 하락 상당 부분은 금리(10Y 5.09%, 30Y 5.43%) 몫이다. MSFT·GOOGL·AMZN의 '최고 YTM'은 초장기·저쿠폰 듀레이션 효과라 크레딧 신호가 아니다 → 크레딧만 보려면 G-spread·CDS 열을 본다. NBIS는 전환사채라 YTM이 전환옵션을 무시한 값.</div></section>
<section class="card"><div class="card-head"><div><div class="card-title">데이터센터 프로젝트 채권</div>
  <div class="card-sub">FINRA TRACE 일별 종가(T-1) · 위 기간 바 · 144A 라인 · 백커 대비 = 채권 규모 ÷ 임차·보증 주체 전체 회사채·장기차입</div></div><div class="card-tools"><div class="seg" id="rk-dcg"></div><div class="seg" id="rk-dcm"></div></div></div>
  <div class="mx-box" style="height:320px"><canvas id="rk-dc"></canvas></div><div id="rk-dc-tbl" style="margin-top:10px"></div></section>
<section class="card"><div class="card-head"><div><div class="card-title">백커 익스포저 — 데이터센터 SPV 채권 ÷ 백커 회사채·장기차입</div>
  <div class="card-sub">최신 10-Q·10-K(XBRL) 기준 · SPV 채권은 대부분 백커 장부 밖(공시로 확인된 것만 Fact) · 스폰서 비율이 100% 넘는 건 SPV 발행이 기준일 이후라서</div></div></div><div id="rk-exp"></div></section>
<section class="card" id="rk-breadth-card"><div class="card-head"><div><div class="card-title">회사채 시장 등락 (FINRA 공식 API)</div>
  <div class="card-sub">TRACE Market Breadth · 5거래일 평균 · 공모 vs 144A · 하이일드 하락 비율이 오르거나 52주 신저가가 신고가보다 많아지면 크레딧 스트레스</div></div><div class="card-tools"><div class="seg" id="rk-bv"></div></div></div>
  <div class="mx-box" style="height:280px"><canvas id="rk-br"></canvas></div></section>
<details class="card mx-links"><summary>부채 구조 (참고) — CRWV·NBIS·HUT 발행 이력, GPU 담보 여부 · SEC 공시 원문</summary>
  <div style="padding:0 16px 14px" id="rk-debt"></div></details>
</div>
"""

MACRO_JS = r"""
(function(){
'use strict';
var M=window.__MACRO__;
var root=document.getElementById('tab-macro');
if(!M){root.innerHTML='<section class="card mx-empty">매크로 데이터가 없습니다 — <code>python scripts/macro_data.py</code> 를 먼저 실행하세요.</section>';window.MACRO={show:function(){}};return;}
var D=M.dates,S=M.series,N=D.length;
var css=getComputedStyle(document.documentElement);function cv(n){return css.getPropertyValue(n).trim();}
var COL={text:cv('--text'),dim:cv('--text-dim'),muted:cv('--text-muted'),teal:cv('--hl-teal'),grid:'rgba(151,252,228,.13)',ov:'rgba(200,215,212,.75)'};
var P=['#3987e5','#d95926','#199e70','#c98500','#d55181','#9085e9'];
var WD=['일','월','화','수','목','금','토'];
function dl(s){var d=new Date(s+'T00:00:00');return (+s.slice(5,7))+'/'+(+s.slice(8,10))+'('+WD[d.getDay()]+')';}
function nf(v,d){return Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});}
function sgn(v,d,u){if(v==null||isNaN(v)) return '–';var s=(v>0?'+':v<0?'−':'±')+nf(Math.abs(v),d)+(u||'');return '<b class="'+(v>0?'mx-up':v<0?'mx-dn':'')+'">'+s+'</b>';}
function ls(k,v){try{if(v===undefined) return localStorage.getItem('krflow.mx.'+k);localStorage.setItem('krflow.mx.'+k,v);}catch(e){return null;}}
function lastI(a){for(var i=a.length-1;i>=0;i--) if(a[i]!=null) return i;return -1;}
function back(a,i,n){var j=i,c=0;while(j>0&&c<n){j--;if(a[j]!=null) c++;}return a[j];}

// ---- 타일: 값 · 1D · 20D · 1년 백분위 (색 없음 — 기준은 Jae가 정하면 켠다) ----
var TILES=[
  {k:'y2',n:'미 2Y',u:'%',dd:'bp',live:'y2',ch:'curve'},
  {k:'y10',n:'미 10Y',u:'%',dd:'bp',live:'y10',ch:'curve'},
  {k:'y30',n:'미 30Y',u:'%',dd:'bp',live:'y30',ch:'curve'},
  {k:'bei10',n:'10Y 명목−TIPS = 인플레이션(BEI)',u:'%',dd:'bp',live:'bei10',ch:'real'},
  {k:'tp10',n:'10Y 텀프리미엄 — 미국 재정우려 등 국채 장기 보유에 대한 프리미엄(ACM)',u:'%',dd:'bp',ch:'tp'},
  {k:'usdkrw',n:'원/달러',u:'원',dd:'pct',dec:1,live:'usdkrw',ch:'krw'},
  {k:'brent',n:'Brent($)',u:'',dd:'pct',dec:2,live:'brent',ch:'brent'}
];
// 실시간 BEI = CNBC 10Y − 10Y TIPS
if(M.live&&M.live.y10&&M.live.real10) M.live.bei10={last:M.live.y10.last-M.live.real10.last,time:M.live.y10.time};
function pctile(a,i,n){var v=a[i],xs=[];for(var j=Math.max(0,i-n+1);j<=i;j++) if(a[j]!=null) xs.push(a[j]);
  var lo=Math.min.apply(null,xs),hi=Math.max.apply(null,xs),below=xs.filter(function(x){return x<v;}).length;
  return {p:Math.round(below/Math.max(1,xs.length-1)*100),lo:lo,hi:hi};}
function delta(t,a,b){if(a==null||b==null) return null;if(t.dd==='bp') return (a-b)*100;if(t.dd==='bpl') return a-b;return (a/b-1)*100;}
function renderTiles(){
  var h=TILES.map(function(t){var a=S[t.k];if(!a) return '';var i=lastI(a);if(i<0) return '';
    var v=a[i],dec=t.dec!=null?t.dec:2,q=pctile(a,i,252),u=t.dd==='pct'?'%':'bp',ud=t.dd==='pct'?2:0;
    var d1=delta(t,v,back(a,i,1)),d20=delta(t,v,back(a,i,20));
    var lv='';if(t.live&&M.live[t.live]&&M.live[t.live].last!=null){var L=M.live[t.live];
      var tm=(L.time||'').slice(5,16).replace('T',' ');lv='실시간 '+nf(L.last,t.u==='%'?3:dec)+(t.u==='%'?'%':'')+' · '+tm+' 현지';}
    var vv=t.u==='bp'?nf(v,0)+'bp':nf(v,dec)+(t.u==='%'?'%':(t.u==='원'?'':''));
    return '<div class="mx-t" data-ch="'+(t.ch||'')+'" title="기준일 '+D[i]+' · 누르면 차트로 이동"><div class="k">'+t.n+' · '+dl(D[i])+'</div><div class="v">'+vv+'</div>'+
      '<div class="d">1D '+sgn(d1,ud,u)+' · 20D '+sgn(d20,ud,u)+'</div>'+
      '<div class="pb"><i style="left:calc('+q.p+'% - 1px)"></i></div>'+
      '<div class="pl"><span>'+nf(q.lo,t.u==='bp'?0:dec)+'</span><span>1년 '+q.p+'%ile</span><span>'+nf(q.hi,t.u==='bp'?0:dec)+'</span></div>'+
      (lv?'<div class="lv">'+lv+'</div>':'')+'</div>';});
  document.getElementById('mx-tiles').innerHTML=h.join('');
  Array.prototype.forEach.call(document.querySelectorAll('#mx-tiles .mx-t[data-ch]'),function(e){e.onclick=function(){var c=document.getElementById('mxc-'+e.dataset.ch);if(c){if(c.classList.contains('cl')) c.querySelector('.cl-btn').click();window.scrollTo(0,c.getBoundingClientRect().top+window.pageYOffset-12);c.classList.add('mx-flash');setTimeout(function(){c.classList.remove('mx-flash');},1200);}};});
}

// ---- 금리 판정 ------------------------------------------------------------
var BK=[['inflation','물가'],['oil','유가·지정학'],['ai','AI주가'],['ai_fund','AI조달'],['fed','연준·고용'],['other','기타(TP·수급)']];
function renderVerdict(){
  var el=document.getElementById('mx-verdict'),dec=M.decomp;
  if(!dec||!dec.rows||!dec.rows.length){el.innerHTML='<div class="card-sub">금리분해 결과 없음</div>';return;}
  var r=dec.rows[dec.rows.length-1];
  var h='<div class="mx-verdict"><span class="tag">'+r.tag+'</span>'+(r.subtag?'<span style="color:var(--text-dim)">'+r.subtag+'</span> · ':'')+
    '미국 '+dl(r.date)+' · 10Y '+sgn(r.d_y10,0,'bp')+' = 실질 '+sgn(r.d_real10,0)+' / BEI '+sgn(r.d_bei10,0)+
    ' · 2Y '+sgn(r.d_y2,0)+' · 30Y '+sgn(r.d_y30,0)+' · Brent '+sgn(r.r_brent,1,'%')+' · SMH−RSP '+sgn(r.r_ai_rel,1,'%p')+'</div>';
  h+='<div class="mx-contrib">'+BK.map(function(b){return '<span>'+b[1]+' '+(r.c[b[0]]==null?'–':(r.c[b[0]]>0?'+':'')+nf(r.c[b[0]],1))+'</span>';}).join('')+'</div>';
  var rows=dec.rows.slice(-10).reverse();
  h+='<div style="overflow-x:auto"><table class="mx-tbl"><thead><tr><th>미국 날짜</th><th class="l">판정</th><th>Δ10Y</th><th>실질</th><th>BEI</th><th>Δ2Y</th><th>Δ30Y</th><th>Brent</th><th>SMH−RSP</th></tr></thead><tbody>'+
    rows.map(function(x){return '<tr><td>'+dl(x.date)+'</td><td class="l">'+x.tag+(x.subtag?' <span style="color:var(--text-muted)">'+x.subtag+'</span>':'')+'</td><td>'+sgn(x.d_y10,0)+'</td><td>'+sgn(x.d_real10,0)+'</td><td>'+sgn(x.d_bei10,0)+'</td><td>'+sgn(x.d_y2,0)+'</td><td>'+sgn(x.d_y30,0)+'</td><td>'+sgn(x.r_brent,1,'%')+'</td><td>'+sgn(x.r_ai_rel,1)+'</td></tr>';}).join('')+'</tbody></table></div>';
  el.innerHTML=h;
}

// ---- 연준 확률 ------------------------------------------------------------
function renderFW(){
  var F=M.fedwatch,box=document.getElementById('mx-fw');
  if(!F||!F.meetings||!F.meetings.length){box.innerHTML='<div class="card-sub">FedWatch 계산 데이터 없음</div>';return;}
  var lo=F.target[0]*100,hi=F.target[1]*100;
  function rng(bp){return nf((lo+(+bp))/100,2)+'~'+nf((hi+(+bp))/100,2)+'%';}
  function lab(bp){bp=+bp;return bp===0?'동결':(bp>0?'인상 +'+bp+'bp':'인하 '+bp+'bp');}
  document.getElementById('mx-fw-sub').innerHTML='CME 사이트는 자동 조회가 막혀(403) 같은 방법론으로 직접 계산 — 연방기금 선물(ZQ, Yahoo 지연시세) + NY Fed EFFR '+nf(F.effr,2)+'%('+F.effr_date.slice(5)+') · 현재 목표 '+nf(F.target[0],2)+'~'+nf(F.target[1],2)+'% · 누적 기준(오늘 대비) · 선물 '+String(F.asof||'').slice(5)+' 종가 · <a href="https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html" target="_blank" rel="noopener" style="color:var(--hl-teal)">CME FedWatch ↗</a>';
  box.innerHTML=F.meetings.map(function(m){var ks=Object.keys(m.dist).sort(function(a,b){return a-b;}),mx=Math.max.apply(null,ks.map(function(k){return m.dist[k];}));
    return '<div><h4>'+dl(m.date)+' FOMC <span style="color:var(--text-muted);font-weight:400">예상 '+nf(m.post,2)+'% (누적 '+(m.chg_bp>0?'+':'')+nf(m.chg_bp,0)+'bp)</span></h4>'+ks.map(function(k){var p=m.dist[k];
      return '<div class="row'+(p===mx?' top':'')+'"><span>'+lab(k)+'</span><div class="bar"><i style="width:'+p+'%"></i></div><span class="n">'+nf(p,0)+'% <span style="color:var(--text-muted)">'+rng(k)+'</span></span></div>';}).join('')+'</div>';}).join('');
}
function renderFed(){
  var box=document.getElementById('mx-fed');
  if(!M.fed||!M.fed.length){box.innerHTML='<div class="card-sub">Kalshi 데이터 없음</div>';return;}
  document.getElementById('mx-fed-sub').innerHTML='KXFEDDECISION · 호가 중간값 · 괄호 = 전일 대비 %p · 조회 '+String(M.asof.fed.date||'').replace('T',' ').slice(0,16)+' KST · <a href="https://kalshi.com/markets/kxfeddecision" target="_blank" rel="noopener" style="color:var(--hl-teal)">Kalshi ↗</a>';
  box.innerHTML=M.fed.map(function(m){var mx=Math.max.apply(null,m.outcomes.map(function(o){return o.p;}));
    return '<div><h4>'+dl(m.date)+' FOMC</h4>'+m.outcomes.map(function(o){var ch=o.prev?o.p-o.prev:null;
      return '<div class="row'+(o.p===mx?' top':'')+'"><span>'+o.label+'</span><div class="bar"><i style="width:'+o.p+'%"></i></div><span class="n">'+nf(o.p,0)+'%'+(ch!=null&&Math.abs(ch)>=1?' ('+(ch>0?'+':'−')+nf(Math.abs(ch),0)+')':'')+'</span></div>';}).join('')+'</div>';}).join('');
}

// ---- 차트 -----------------------------------------------------------------
var W={i0:0,i1:N-1},CH=[];
var fwViews=(M.fedwatch&&(M.fedwatch.ledger_meetings||[]).length)?[{label:'FedWatch 누적 bp',u:'bp',zero:true,series:M.fedwatch.ledger_meetings.map(function(m){return ['fw_'+m.replace(/-/g,''),dl(m)+' 회의 후'];}).filter(function(x){return S[x[0]];})}]:[];
var fedViews=(M.fed||[]).map(function(m,i){return {label:dl(m.date),u:'pp',series:[['fed'+i+'_H0','동결'],['fed'+i+'_H25','인상 25bp'],['fed'+i+'_H26','인상 >25bp'],['fed'+i+'_C25','인하 25bp']]};});
var CHARTS=[
  {id:'curve',t:'미 국채 금리',sub:'재무부 고시(종가) · %',views:[
    {label:'2·5·10·30Y',u:'%',series:[['y2','2Y'],['y5','5Y'],['y10','10Y'],['y30','30Y']]},
    {label:'커브(bp)',u:'bp',series:[['s2s10','2s10s'],['s10s30','10s30s']],zero:true}]},
  {id:'real',t:'실질금리 vs BEI',sub:'재무부 명목 − 실질(TIPS) 커브 · %',views:[
    {label:'10Y',u:'%',series:[['real10','10Y 실질'],['bei10','10Y BEI']]},
    {label:'5Y',u:'%',series:[['real5','5Y 실질'],['bei5','5Y BEI']]},
    {label:'10Y 명목',u:'%',series:[['y10','10Y 명목'],['real10','10Y 실질']]}]},
  {id:'tp',t:'텀프리미엄 (NY Fed ACM)',sub:'1영업일 지연 · MacroMicro 차트와 같은 원천 · %',views:[
    {label:'10Y TP',u:'%',series:[['tp10','10Y TP']]},
    {label:'2·5·10Y TP',u:'%',series:[['tp2','2Y TP'],['tp5','5Y TP'],['tp10','10Y TP']]},
    {label:'10Y = 기대경로 + TP',u:'%',series:[['rny10','기대 단기금리 경로'],['tp10','TP']]}]},
  {id:'krw',t:'원/달러',sub:'Yahoo KRW=X 일봉(뉴욕 마감 기준) · 원',views:[{label:'원/달러',u:'원',series:[['usdkrw','원/달러']]}]},
  {id:'brent',t:'Brent 선물',sub:'Yahoo BZ=F 일봉 · $',views:[{label:'Brent',u:'$',series:[['brent','Brent']]}]},
  {id:'fed',t:'연준 기대 추이 — FedWatch 방식(앞) · Kalshi(뒤)',sub:'FedWatch: 회의 후 예상 금리 − 그날 EFFR(누적 bp), 실행할 때마다 원장(data/fedwatch_ledger.json)에 쌓음 · Kalshi: 회의별 결과 확률(%)',views:fwViews.concat(fedViews)}
];
function el(t,c,h){var e=document.createElement(t);if(c) e.className=c;if(h!=null) e.innerHTML=h;return e;}
function fmtU(u,v){if(v==null) return '–';if(u==='%') return nf(v,2)+'%';if(u==='bp') return nf(v,0)+'bp';if(u==='pp') return nf(v,0)+'%';if(u==='원') return nf(v,1);if(u==='$') return '$'+nf(v,2);return nf(v,2);}
function cfg(c){var v=c.p.views[c.v],L=D.slice(W.i0,W.i1+1);
  var ds=v.series.map(function(s,j){return {label:s[1],data:(S[s[0]]||[]).slice(W.i0,W.i1+1),borderColor:P[j],backgroundColor:P[j],borderWidth:2,pointRadius:0,pointHoverRadius:3,tension:0,spanGaps:true,yAxisID:'y'};});
  if(c.ov&&S.kospi) ds.push({label:'코스피',data:S.kospi.slice(W.i0,W.i1+1),borderColor:COL.ov,backgroundColor:COL.ov,borderWidth:1.2,pointRadius:0,tension:0,spanGaps:true,yAxisID:'y1',order:9});
  return {type:'line',data:{labels:L,datasets:ds},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{display:true,labels:{color:COL.dim,boxWidth:12,boxHeight:3,font:{size:12.5}}},
      tooltip:{backgroundColor:'rgba(6,30,32,.95)',borderColor:'rgba(151,252,228,.25)',borderWidth:1,titleColor:COL.text,bodyColor:COL.text,
        callbacks:{title:function(it){return it.length?'미국 '+it[0].label:'';},label:function(it){return ' '+it.dataset.label+'  '+(it.dataset.yAxisID==='y1'?nf(it.raw,2)+' (같은 날짜 이전 마지막 국내 종가)':fmtU(v.u,it.raw));}}}},
    scales:{x:{grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:7,font:{size:12},callback:function(x){var s=this.getLabelForValue(x);return s.slice(2,7).replace('-','.')+(W.i1-W.i0<70?'.'+s.slice(8):'');}}},
      y:{grid:{color:function(g){return v.zero&&g.tick&&g.tick.value===0?'rgba(151,252,228,.3)':COL.grid;}},border:{display:false},ticks:{color:COL.muted,font:{size:12},maxTicksLimit:6,callback:function(x){return fmtU(v.u,x);}}},
      y1:{display:c.ov&&!!S.kospi,position:'right',grid:{display:false},border:{display:false},ticks:{color:'#B4D6D1',font:{size:11},maxTicksLimit:5,callback:function(x){return nf(x,0);}}}}}};}
function draw(c){if(c.ch) c.ch.destroy();c.ch=new Chart(c.cv,cfg(c));
  if(c.seg) Array.prototype.forEach.call(c.seg.children,function(b,i){b.classList.toggle('on',i===c.v);});}
function build(){var g=document.getElementById('mx-grid');
  CHARTS.forEach(function(p){if(!p.views.length) return;var c={p:p,v:0,ov:ls('ov.'+p.id)!=='0'};var sv=parseInt(ls('v.'+p.id),10);if(sv>=0&&sv<p.views.length) c.v=sv;
    var r=el('section','card'),hd=el('div','card-head'),tt=el('div');r.id='mxc-'+p.id;tt.appendChild(el('div','card-title',p.t));tt.appendChild(el('div','card-sub',p.sub));hd.appendChild(tt);
    var tl=el('div','card-tools');hd.appendChild(tl);
    if(p.views.length>1){var sg=el('div','seg');p.views.forEach(function(v,i){var b=el('button',null,v.label);b.type='button';b.onclick=function(){c.v=i;ls('v.'+p.id,i);draw(c);};sg.appendChild(b);});
      tl.appendChild(sg);c.seg=sg;}
    var ob=el('button','ov-btn'+(c.ov?' on':''),'코스피');ob.type='button';ob.title='코스피를 회색 선(오른쪽 축)으로 겹치기';
    ob.onclick=function(){c.ov=!c.ov;ls('ov.'+p.id,c.ov?'1':'0');ob.classList.toggle('on',c.ov);draw(c);};tl.appendChild(ob);
    r.appendChild(hd);var bx=el('div','mx-box');c.cv=document.createElement('canvas');bx.appendChild(c.cv);r.appendChild(bx);g.appendChild(r);CH.push(c);});}
var PR=[['1M',1],['3M',3],['6M',6],['1Y',12],['전체',0]];
function setP(m,lab){var i0=0;if(m){var t=new Date(D[N-1]+'T00:00:00');t.setMonth(t.getMonth()-m);var s=t.toISOString().slice(0,10);for(var i=0;i<N;i++) if(D[i]>=s){i0=i;break;}}
  setW(i0,N-1,lab);}
// 기간: 프리셋 · 슬라이더 · 날짜 입력이 모두 이 함수로 모인다
var R0=document.getElementById('mx-r0'),R1=document.getElementById('mx-r1'),MINW=5,RAFW=0;R0.max=R1.max=N-1;
function setW(a,b,lab){W.i0=a;W.i1=b;R0.value=a;R1.value=b;ls('preset',lab||'');
  Array.prototype.forEach.call(document.getElementById('mx-presets').children,function(x){x.classList.toggle('on',x.textContent===lab);});
  document.getElementById('mx-d0').value=D[a].replace(/-/g,'.');document.getElementById('mx-d1').value=D[b].replace(/-/g,'.');
  document.getElementById('mx-rlab').textContent=(b-a+1)+'영업일';drawOv();
  if(SHOWN&&!RAFW){RAFW=1;setTimeout(function(){RAFW=0;CH.forEach(draw);drawDec();},60);}}
function onR(e){var a=+R0.value,b=+R1.value;if(b-a<MINW){if(e.target===R0) a=Math.max(0,b-MINW);else b=Math.min(N-1,a+MINW);}setW(a,b,null);}
R0.addEventListener('input',onR);R1.addEventListener('input',onR);
function pd(t){t=(t||'').trim().replace(/\s/g,'');var m,y,mo,d;
  if((m=t.match(/^(\d{2})(\d{2})(\d{2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{4})[-./]?(\d{1,2})[-./]?(\d{1,2})$/))){y=+m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{2})[-./](\d{1,2})[-./](\d{1,2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{1,2})[-./](\d{1,2})$/))){y=+D[N-1].slice(0,4);mo=+m[1];d=+m[2];var c=y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2);if(c>D[N-1]) y-=1;}
  else return null;
  if(mo<1||mo>12||d<1||d>31) return null;return y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2);}
['mx-d0','mx-d1'].forEach(function(id,k){var inp=document.getElementById(id);
  inp.addEventListener('keydown',function(e){if(e.key!=='Enter') return;var s=pd(inp.value);if(!s){inp.classList.add('bad');return;}inp.classList.remove('bad');
    var a=W.i0,b=W.i1,i;if(k===0){for(i=0;i<N;i++) if(D[i]>=s){a=i;break;}if(b-a<MINW) b=Math.min(N-1,a+MINW);}
    else{for(i=N-1;i>=0;i--) if(D[i]<=s){b=i;break;}if(b-a<MINW) a=Math.max(0,b-MINW);}
    setW(a,b,null);inp.blur();});
  inp.addEventListener('focus',function(){inp.select();});});
function drawOv(){var cv=document.getElementById('mx-ov-c'),w=cv.clientWidth,h=30,dpr=window.devicePixelRatio||1;if(!w) return;
  cv.width=w*dpr;cv.height=h*dpr;var c=cv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
  var a=S.y10,mn=Infinity,mx=-Infinity,i;for(i=0;i<N;i++) if(a[i]!=null){mn=Math.min(mn,a[i]);mx=Math.max(mx,a[i]);}
  var xs=function(i){return 6+(w-12)*i/(N-1);},ys=function(v){return h-3-(h-8)*(v-mn)/((mx-mn)||1);};
  c.fillStyle='rgba(151,252,228,.05)';c.fillRect(0,0,w,h);c.fillStyle='rgba(151,252,228,.15)';c.fillRect(xs(W.i0),0,Math.max(2,xs(W.i1)-xs(W.i0)),h);
  c.strokeStyle='rgba(151,252,228,.6)';c.lineWidth=1.2;c.beginPath();var st=false;for(i=0;i<N;i++){if(a[i]==null) continue;if(!st){c.moveTo(xs(i),ys(a[i]));st=true;}else c.lineTo(xs(i),ys(a[i]));}c.stroke();}
window.addEventListener('resize',drawOv);
var SHOWN=false;
var pb=document.getElementById('mx-presets');PR.forEach(function(p){var b=el('button',null,p[0]);b.type='button';b.onclick=function(){setP(p[1],p[0]);};pb.appendChild(b);});
var A=M.asof;function ad(x){return x&&x.date?String(x.date).slice(5,10).replace('-','/')+(x.via==='cache'?'(캐시)':''):'–';}
document.getElementById('mx-asof').textContent='기준 · 재무부 '+ad(A.treasury)+' · ACM '+ad(A.acm)+' · Brent '+ad(A.brent)+' · 원/달러 '+ad(A.usdkrw)+' · 생성 '+M.generated_at.slice(5,16).replace('T',' ');
// ---- 기간 분해: 10Y = 실질+BEI (재무부) / 기대경로+TP (ACM) ----
var DEC=null,DECOV=ls('ov.dec')!=='0',DECM='cum';
function fNN(a,i,j){for(var k=i;k<=j;k++) if(a[k]!=null) return k;return -1;}
function lNN(a,i,j){for(var k=j;k>=i;k--) if(a[k]!=null) return k;return -1;}
function rel(k){var a=S[k]||[],b=fNN(a,W.i0,W.i1);return a.slice(W.i0,W.i1+1).map(function(v){return (v==null||b<0)?null:Math.round((v-a[b])*1000)/10;});}
function chg(k){var a=S[k]||[],b=fNN(a,W.i0,W.i1),e=lNN(a,W.i0,W.i1);return (b<0||e<0)?null:{v:(a[e]-a[b])*100,d0:D[b],d1:D[e]};}
function drawDec(){
  var y=chg('y10'),r=chg('real10'),be=chg('bei10'),tp=chg('tp10'),rn=chg('rny10'),ay=chg('acmy10');
  function sp(n,x){return '<span>'+n+' '+(x?sgn(x.v,0,'bp'):'–')+'</span>';}
  document.getElementById('mx-dec-sum').innerHTML=
    '<div class="mx-sum"><span style="background:rgba(151,252,228,.12)"><b>재무부 '+(y?dl(y.d0)+'→'+dl(y.d1):'')+'</b></span>'+sp('10Y',y)+sp('= 실질',r)+sp('+ BEI',be)+'</div>'+
    '<div class="mx-sum"><span style="background:rgba(151,252,228,.12)"><b>ACM '+(ay?dl(ay.d0)+'→'+dl(ay.d1):'')+'</b></span>'+sp('10Y(모형)',ay)+sp('= 기대경로',rn)+sp('+ 텀프리미엄',tp)+'</div>';
  var EX=[['10Y 명목','시장에서 보는 10년 국채금리',y],['실질 (TIPS)','인플레이션을 뺀 금리. 돈을 빌리는 진짜 비용',r],['BEI','명목 − 실질. 시장이 예상하는 향후 10년 평균 인플레이션',be],
    ['기대경로 (ACM)','앞으로 10년간 연준 정책금리가 평균 어디쯤일지에 대한 예상',rn],['텀프리미엄 (ACM)','장기채를 들고 있는 대가로 더 받는 몫(재정적자·국채 공급·불확실성)',tp]];
  document.getElementById('mx-dec-exp').innerHTML='<div style="overflow-x:auto"><table class="mx-tbl"><thead><tr><th class="l">지표</th><th class="l">뜻</th><th>기간 변화'+(y?' ('+dl(y.d0)+'→'+dl(y.d1)+')':'')+'</th><th>최신 수준</th></tr></thead><tbody>'+
    EX.map(function(e,j){var k=['y10','real10','bei10','rny10','tp10'][j],a=S[k]||[],li=lNN(a,W.i0,W.i1);return '<tr><td class="l"><b>'+e[0]+'</b></td><td class="l rk-wrap" style="max-width:none">'+e[1]+'</td><td>'+(e[2]?sgn(e[2].v,0,'bp'):'–')+'</td><td>'+(li>=0?nf(a[li],2)+'%':'–')+'</td></tr>';}).join('')+'</tbody></table></div>';
  var L=D.slice(W.i0,W.i1+1);
  var SR=[['y10','10Y 명목',COL.text,2,null],['real10','실질',P[0],1.8,null],['bei10','BEI',P[1],1.8,null],['tp10','텀프리미엄(ACM)',P[2],2.8,null],['rny10','기대경로(ACM)',P[3],1.8,[5,4]]];
  var LV=DECM==='lvl';
  var ds=SR.map(function(x){var o={label:x[1],data:LV?(S[x[0]]||[]).slice(W.i0,W.i1+1):rel(x[0]),borderColor:x[2],backgroundColor:x[2],borderWidth:x[3],pointRadius:0,pointHoverRadius:3,tension:0,spanGaps:true,yAxisID:'y'};if(x[4]) o.borderDash=x[4];return o;});
  var kb=S.kospi?S.kospi[fNN(S.kospi,W.i0,W.i1)]:null;
  if(DECOV&&S.kospi) ds.push({label:'코스피(기간 시작 대비 %)',data:S.kospi.slice(W.i0,W.i1+1).map(function(v){return (v==null||!kb)?null:Math.round((v/kb-1)*1000)/10;}),borderColor:COL.ov,backgroundColor:COL.ov,borderWidth:1.2,pointRadius:0,tension:0,spanGaps:true,yAxisID:'y1',order:9});
  // 오른쪽 축 = 10Y 금리 수준(%). 왼쪽 누적 bp와 같은 스케일(100bp = 1%p)이 되도록 범위를 맞춘다 → 흰 10Y 선은 양쪽 축 모두로 읽힘
  var lo=0,hi=0;ds.forEach(function(d){if(d.yAxisID!=='y') return;d.data.forEach(function(v){if(v!=null){lo=Math.min(lo,v);hi=Math.max(hi,v);}});});
  lo=Math.floor((lo-5)/25)*25;hi=Math.ceil((hi+5)/25)*25;
  var a10=S.y10||[],b10=fNN(a10,W.i0,W.i1),s10=b10>=0?a10[b10]:null;
  ds.forEach(function(d){if(d.yAxisID==='y1') d.yAxisID='y2';});
  if(DEC) DEC.destroy();
  DEC=new Chart(document.getElementById('mx-dec'),{type:'line',data:{labels:L,datasets:ds},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{color:COL.dim,boxWidth:12,boxHeight:3,font:{size:12.5}}},tooltip:{backgroundColor:'rgba(6,30,32,.95)',borderColor:'rgba(151,252,228,.25)',borderWidth:1,titleColor:COL.text,bodyColor:COL.text,
      callbacks:{title:function(it){return it.length?'미국 '+it[0].label:'';},label:function(it){return ' '+it.dataset.label+'  '+(it.dataset.yAxisID==='y2'?(it.raw>0?'+':'')+nf(it.raw,1)+'%':(LV?nf(it.raw,2)+'%':(it.raw>0?'+':'')+nf(it.raw,0)+'bp'));}}}},
    scales:{x:{grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:7,font:{size:12},callback:function(x){var s=this.getLabelForValue(x);return s.slice(2,7).replace('-','.')+(W.i1-W.i0<70?'.'+s.slice(8):'');}}},
      y:{min:lo,max:hi,grid:{color:function(g){return g.tick&&g.tick.value===0?'rgba(151,252,228,.3)':COL.grid;}},border:{display:false},title:{display:true,text:LV?'금리 %':'기간 시작 대비 bp',color:COL.muted,font:{size:11}},ticks:{color:COL.muted,font:{size:12},maxTicksLimit:7,callback:function(x){return LV?nf(x,1)+'%':(x>0?'+':'')+nf(x,0)+'bp';}}},
      y1:{display:s10!=null,position:'right',min:s10!=null?s10+lo/100:0,max:s10!=null?s10+hi/100:1,grid:{display:false},border:{display:false},title:{display:true,text:'10Y 금리 %'+(b10>=0?' ('+dl(D[b10])+' '+nf(s10,2)+'% = 0bp)':''),color:'#F2FFFC',font:{size:11}},ticks:{color:'#F2FFFC',font:{size:12},maxTicksLimit:7,callback:function(x){return nf(x,2)+'%';}}},
      y2:{display:false}}}});
}
(function(){var hd=document.querySelector('#mx-dec-card .card-head'),tl=el('div','card-tools');var ob=el('button','ov-btn'+(DECOV?' on':''),'코스피');ob.type='button';ob.title='코스피를 회색 선(오른쪽 축)으로 겹치기';
  ob.onclick=function(){DECOV=!DECOV;ls('ov.dec',DECOV?'1':'0');ob.classList.toggle('on',DECOV);drawDec();};tl.appendChild(ob);hd.appendChild(tl);})();

renderTiles();renderVerdict();renderFW();renderFed();build();
var pre=ls('preset');var pp=PR.filter(function(p){return p[0]===pre;})[0]||PR[2];setP(pp[1],pp[0]);
window.MACRO={show:function(){drawOv();if(!SHOWN){SHOWN=true;CH.forEach(draw);drawDec();}else CH.forEach(function(c){c.ch&&c.ch.resize();});}};
if(!root.hidden) window.MACRO.show();  // 앱 스크립트가 먼저 매크로 탭을 열었을 때
})();
"""


FS_JS = r"""
(function(){
'use strict';
// 차트가 있는 모든 카드에 ⛶ 버튼. 섹터 탭처럼 나중에 그려지는 카드도 잡으려고 MutationObserver 로 다시 훑는다.
var SEL='.chart-box,.mx-box,.rank-box,.heat-box';
function close(c){c.classList.remove('fs');document.body.classList.remove('fs-lock');var b=c.querySelector('.fs-btn:not(.cl-btn)');if(b){b.textContent='⛶';b.title='전체화면';}
  setTimeout(function(){window.dispatchEvent(new Event('resize'));},30);}
function open(c){var o=document.querySelector('.card.fs');if(o) close(o);c.classList.add('fs');document.body.classList.add('fs-lock');
  var b=c.querySelector('.fs-btn:not(.cl-btn)');if(b){b.textContent='✕';b.title='닫기 (Esc)';}c.scrollTop=0;
  setTimeout(function(){window.dispatchEvent(new Event('resize'));},30);}
function scan(){Array.prototype.forEach.call(document.querySelectorAll('section.card'),function(c){
  if(c.dataset.fs||!c.querySelector(SEL)) return;var hd=c.querySelector('.card-head');if(!hd) return;c.dataset.fs='1';
  var tl=hd.querySelector(':scope > .card-tools');if(!tl){tl=document.createElement('div');tl.className='card-tools';hd.appendChild(tl);}
  var b=document.createElement('button');b.type='button';b.className='fs-btn';b.textContent='⛶';b.title='전체화면';b.setAttribute('aria-label','차트 전체화면');
  b.onclick=function(){c.classList.contains('fs')?close(c):open(c);};tl.appendChild(b);});}
// 카드 접기: 머리글 오른쪽 ▾ 버튼. 상태는 카드 제목별로 기억
var DEFCL=['rk-breadth-card','card-samsung','card-hynix','card-shhold','card-share','card-futures','card-kospi','card-kosdaq','card-inst','card-index'];  // 기본 접힘(Jae 10/18)
function ckey(c){var t=c.querySelector('.card-title');return 'krflow.cl.'+(c.id||(t?t.textContent.slice(0,40):''));}
function cl(c,on){c.classList.toggle('cl',on);var b=c.querySelector('.cl-btn');if(b){b.textContent=on?'▸':'▾';b.title=on?'펼치기':'접기';}try{localStorage.setItem(ckey(c),on?'1':'0');}catch(e){}
  if(!on) setTimeout(function(){window.dispatchEvent(new Event('resize'));},30);}
function scanCl(){Array.prototype.forEach.call(document.querySelectorAll('section.card'),function(c){
  if(c.dataset.cl) return;var hd=c.querySelector(':scope > .card-head');if(!hd) return;c.dataset.cl='1';
  var tl=hd.querySelector(':scope > .card-tools');if(!tl){tl=document.createElement('div');tl.className='card-tools';hd.appendChild(tl);}
  var b=document.createElement('button');b.type='button';b.className='fs-btn cl-btn';b.textContent='▾';b.title='접기';b.onclick=function(){if(c.classList.contains('fs')){close(c);return;}cl(c,!c.classList.contains('cl'));};tl.appendChild(b);
  var on=null;try{on=localStorage.getItem(ckey(c));}catch(e){}if(on===null) on=DEFCL.indexOf(c.id)>=0?'1':'0';if(on==='1') cl(c,true);});}
scanCl();new MutationObserver(function(){setTimeout(scanCl,120);}).observe(document.body,{childList:true,subtree:true});
document.addEventListener('keydown',function(e){if(e.key==='Escape'){var o=document.querySelector('.card.fs');if(o) close(o);}});
scan();
var t=0;new MutationObserver(function(){if(t) return;t=setTimeout(function(){t=0;scan();},100);}).observe(document.body,{childList:true,subtree:true});
})();
"""

ECON_JS = r"""
(function(){
'use strict';
var M=window.__MACRO__||{},R=M.releases||[];
var WD=['일','월','화','수','목','금','토'];
function dl(s){var d=new Date(s+'T00:00:00');return s.slice(2).replace(/-/g,'.')+'('+WD[d.getDay()]+')';}
var today=new Date(Date.now()+9*3600e3-14*3600e3).toISOString().slice(0,10); // KST 기준 미국 날짜(대략)
var by={};R.forEach(function(x){(by[x.type]=by[x.type]||[]).push(x.date);});
var ORDER=[['CPI','CPI'],['PPI','PPI'],['PCE','PCE(개인소비지출)'],['NFP','고용(NFP)'],['FOMC','FOMC 결정'],['RETAIL','소매판매']];
var h='<div style="overflow-x:auto"><table class="mx-tbl ec-tbl"><thead><tr><th class="l">지표</th><th>직전 발표</th><th>다음 발표</th><th>그다음</th></tr></thead><tbody>';
ORDER.forEach(function(o){var ds=(by[o[0]]||[]).slice().sort(),prev=null,nx=[];
  ds.forEach(function(d){if(d<today) prev=d;else nx.push(d);});
  h+='<tr><td class="l">'+o[1]+'</td><td>'+(prev?dl(prev):'–')+'</td><td class="next">'+(nx[0]?dl(nx[0]):(ds.length?'–':'일정 미입력'))+'</td><td>'+(nx[1]?dl(nx[1]):'–')+'</td></tr>';});
h+='</tbody></table></div>';
document.getElementById('ec-cal').innerHTML=h;
var fr=document.getElementById('ec-cpi'),loaded=false;
fr.addEventListener('load',function(){try{var b=fr.contentDocument.documentElement;fr.style.height=Math.max(600,b.scrollHeight+20)+'px';}catch(e){}});
// ---- PPI 세부 (scripts/ppi_data.py → data/ppi.json) ----
var P=window.__PPI__,PV=0,PCH=null;try{PV=+(localStorage.getItem('krflow.ec.ppiv')||0);}catch(e){}
function pf(v,d){if(v==null) return '–';var t=Number(v).toFixed(d==null?2:d);if(/^-0\.0+$/.test(t)) t=t.slice(1);return (+t>0?'+':'')+t+'%';}
function ppiTable(){var i=P.months.length-1,h='<div style="overflow-x:auto"><table class="mx-tbl ec-tbl"><thead><tr><th class="l">'+P.latest+' (계절조정 MoM · 원계열 YoY)</th><th>MoM</th><th>직전 MoM</th><th>YoY</th><th>3개월 연율</th></tr></thead><tbody>';
  P.head.forEach(function(r){var sub=/^ /.test(r.ko);h+='<tr><td class="l" style="'+(sub?'padding-left:22px;color:var(--text-dim)':'font-weight:700')+'">'+r.ko.trim()+'</td><td><b>'+pf(r.mom[i])+'</b></td><td>'+pf(r.mom[i-1])+'</td><td>'+pf(r.yoy[i],1)+'</td><td>'+pf(r.ann3[i],1)+'</td></tr>';});
  document.getElementById('ec-ppi-tbl').innerHTML=h+'</tbody></table></div>';}
function ppiDraw(){if(!P) return;var css=getComputedStyle(document.documentElement),cv=function(n){return css.getPropertyValue(n).trim();};
  var C={dim:cv('--text-dim'),muted:cv('--text-muted'),grid:'rgba(151,252,228,.13)'},L=P.months.slice(-24),n=L.length,cut=function(a){return a.slice(-n);};
  var sb=document.getElementById('ec-ppi-v');sb.innerHTML='';[['MoM·YoY 추이',0],['파이프라인 YoY',1],['유통마진 MoM',2]].forEach(function(x){var b=document.createElement('button');b.type='button';b.textContent=x[0];if(x[1]===PV) b.className='on';b.onclick=function(){PV=x[1];try{localStorage.setItem('krflow.ec.ppiv',PV);}catch(e){}ppiDraw();};sb.appendChild(b);});
  var ds,y2=false,note;
  if(PV===0){var H=P.head[0],K=P.head[1];y2=true;
    ds=[{type:'bar',label:'헤드라인 MoM',data:cut(H.mom),backgroundColor:'rgba(232,130,58,.7)',yAxisID:'y'},{type:'bar',label:'근원(식품·에너지 제외) MoM',data:cut(K.mom),backgroundColor:'rgba(57,135,229,.7)',yAxisID:'y'},
        {type:'line',label:'헤드라인 YoY',data:cut(H.yoy),borderColor:'#e8823a',pointRadius:0,borderWidth:2,yAxisID:'y2'},{type:'line',label:'근원 YoY',data:cut(K.yoy),borderColor:'#3987e5',pointRadius:0,borderWidth:2,yAxisID:'y2'}];
    note='막대 = 전월 대비(계절조정, 왼쪽 축) · 선 = 전년 대비(원계열, 오른쪽 축). 근원 = 최종수요에서 식품·에너지 제외(WPSFD49104).';}
  else if(PV===1){var col=['#d55181','#e8823a','#d4a72c','#2aa58a','#F2FFFC'];
    ds=P.pipe.map(function(r,j){return {type:'line',label:r.ko,data:cut(r.yoy),borderColor:col[j%col.length],backgroundColor:col[j%col.length],pointRadius:0,borderWidth:j===P.pipe.length-1?2.6:1.8};});
    note='원자재 → 중간재 → 최종재 → 소비자물가 순서로 YoY. 위 단계가 오르고 아래 단계가 따라오지 않으면 「아직 전이 안 됨」(기업이 떠안거나 시차). 마지막 선 = CPI 근원상품(SACL1E).';}
  else{ds=P.margin.map(function(r,j){return {type:'bar',label:r.ko,data:cut(r.mom),backgroundColor:j?'rgba(42,165,138,.7)':'rgba(212,167,44,.75)'};});
    note='무역서비스 PPI = 도·소매 유통마진(판매가 − 매입가). 오르면 유통업체가 마진을 넓힌 것(물가 전가), 내리면 떠안은 것.';}
  document.getElementById('ec-ppi-sub').textContent='BLS wp.data.22.FD-ID · 기준월 '+P.latest+' · 원자료 갱신 '+(P.bls_last_modified||'').replace(' GMT','').slice(5,16);
  document.getElementById('ec-ppi-note').textContent=note;
  if(PCH) PCH.destroy();
  PCH=new Chart(document.getElementById('ec-ppi-c'),{type:'bar',data:{labels:L.map(function(m){return m.slice(2).replace('-','.');}),datasets:ds},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{color:C.dim,boxWidth:12,boxHeight:6}},tooltip:{callbacks:{label:function(it){return ' '+it.dataset.label+'  '+pf(it.raw);}}}},
    scales:{x:{grid:{display:false},ticks:{color:C.muted,maxRotation:0,autoSkip:true,maxTicksLimit:12}},y:{grid:{color:C.grid},ticks:{color:C.muted,callback:function(v){return v+'%';}}},
      y2:{display:y2,position:'right',grid:{display:false},ticks:{color:C.muted,callback:function(v){return v+'%';}}}}}});}
if(P){ppiTable();}else{document.getElementById('ec-ppi-tbl').innerHTML='<div class="card-sub">PPI 데이터 없음 — scripts/ppi_data.py 실행 필요</div>';}
// ---- 소매판매 세부 (scripts/retail_data.py → data/retail.json) ----
var RT=window.__RETAIL__,RV=0,RCH=null;try{RV=+(localStorage.getItem('krflow.ec.rtv')||0);}catch(e){}
function rtTable(){var i=RT.months.length-1,h='<div style="overflow-x:auto"><table class="mx-tbl ec-tbl"><thead><tr><th class="l">'+RT.latest+' (계절조정 판매액 기준)</th><th>MoM</th><th>직전 MoM</th><th>YoY</th><th>3개월 연율</th></tr></thead><tbody>';
  RT.head.forEach(function(r,j){h+='<tr><td class="l" style="'+(j===0||j===4?'font-weight:700':'padding-left:22px;color:var(--text-dim)')+'">'+r.ko+(j===4?' <span class="rk-sub">(전체 − 자동차·건축자재·주유소·음식점)</span>':'')+'</td><td><b>'+pf(r.mom[i])+'</b></td><td>'+pf(r.mom[i-1])+'</td><td>'+pf(r.yoy[i],1)+'</td><td>'+pf(r.ann3[i],1)+'</td></tr>';});
  var rv=RT.revision&&RT.revision.rows&&RT.revision.rows.length?'수정: '+RT.revision.rows.map(function(x){return x.month.slice(2).replace('-','.')+' '+pf(x.prev)+' → '+pf(x.now);}).join(', '):'';
  document.getElementById('ec-rt-tbl').innerHTML=h+'</tbody></table></div>'+(rv?'<div class="card-sub" style="margin-top:4px">'+rv+'</div>':'');}
function rtDraw(){if(!RT) return;var css=getComputedStyle(document.documentElement),cv=function(n){return css.getPropertyValue(n).trim();};
  var C={dim:cv('--text-dim'),muted:cv('--text-muted'),grid:'rgba(151,252,228,.13)'},n=24,L=RT.months.slice(-n),cut=function(a){return a.slice(-n);},i=RT.months.length-1;
  var sb=document.getElementById('ec-rt-v');sb.innerHTML='';[['MoM 추이',0],['업종 기여(최근월)',1],['주유소 가격 vs 물량',2]].forEach(function(x){var b=document.createElement('button');b.type='button';b.textContent=x[0];if(x[1]===RV) b.className='on';b.onclick=function(){RV=x[1];try{localStorage.setItem('krflow.ec.rtv',RV);}catch(e){}rtDraw();};sb.appendChild(b);});
  var type='bar',labels=L.map(function(m){return m.slice(2).replace('-','.');}),ds,idx='x',note;
  if(RV===0){ds=[{label:'헤드라인',data:cut(RT.head[0].mom),backgroundColor:'rgba(232,130,58,.7)'},{label:'컨트롤그룹',data:cut(RT.head[4].mom),backgroundColor:'rgba(57,135,229,.75)'},{type:'line',label:'주유소 제외',data:cut(RT.head[2].mom),borderColor:'#2aa58a',pointRadius:2,borderWidth:1.6}];
    note='헤드라인과 컨트롤그룹(GDP 소비 계산에 들어가는 묶음)이 갈리면 자동차·주유소·음식점 같은 변동 큰 항목이 헤드라인을 끌고 간 것.';}
  else if(RV===1){var cs=RT.cats.slice().sort(function(a,b){return (b.contrib[i]||0)-(a.contrib[i]||0);});idx='y';labels=cs.map(function(c){return c.ko+' ('+c.share+'%)';});
    ds=[{label:RT.latest+' 전체 MoM 기여(%p)',data:cs.map(function(c){return c.contrib[i];}),backgroundColor:cs.map(function(c){return (c.contrib[i]||0)>=0?'rgba(240,117,106,.75)':'rgba(120,170,255,.75)';})}];
    note='막대 = 업종 증가액 ÷ 전월 전체 판매액(%p). 13개 업종 합 = 헤드라인 MoM '+pf(RT.head[0].mom[i])+'. 괄호 = 전체에서 차지하는 비중.';}
  else{var G=RT.gas||{};type='line';ds=[{type:'bar',label:'주유소 판매액 MoM',data:cut(G.sales_mom||[]),backgroundColor:'rgba(212,167,44,.7)'},{label:'CPI 자동차 연료 MoM(가격)',data:cut(G.cpi_mom||[]),borderColor:'#d55181',pointRadius:2,borderWidth:1.8},{label:'물량 역산 MoM',data:cut(G.vol_mom||[]),borderColor:'#F2FFFC',pointRadius:2,borderWidth:2.2}];
    note='물량 역산 = 판매액 ÷ 기름값. 판매액이 늘어도 물량이 줄면 「기름값이 끌어올린 매출」. 주유소 매출엔 편의점 상품이 섞여 있어 근사(EIA 휘발유 공급량과 교차 확인 필요).';}
  document.getElementById('ec-rt-sub').textContent='Census MARTS 계절조정 · 기준월 '+RT.latest+' · 받은 날 '+RT.fetched;
  document.getElementById('ec-rt-note').textContent=note;
  if(RCH) RCH.destroy();
  RCH=new Chart(document.getElementById('ec-rt-c'),{type:type,data:{labels:labels,datasets:ds},options:{indexAxis:idx,responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{color:C.dim,boxWidth:12,boxHeight:6}},tooltip:{callbacks:{label:function(it){return ' '+it.dataset.label+'  '+(RV===1?(it.raw>0?'+':'')+Number(it.raw).toFixed(2)+'%p':pf(it.raw));}}}},
    scales:{x:{grid:{display:idx==='y',color:C.grid},ticks:{color:C.muted,maxRotation:0,autoSkip:idx==='x',maxTicksLimit:12}},y:{grid:{color:C.grid,display:idx==='x'},ticks:{color:C.muted,autoSkip:false}}}}});}
if(RT){rtTable();}else{document.getElementById('ec-rt-tbl').innerHTML='<div class="card-sub">소매판매 데이터 없음 — scripts/retail_data.py 실행 필요(.env CENSUS_KEY)</div>';}
// ---- 고용 세부 (scripts/emp_data.py → data/emp.json) ----
var EM=window.__EMP__,EV=0,ECH=null;try{EV=+(localStorage.getItem('krflow.ec.emv')||0);}catch(e){}
function man(v){return v==null?'–':(v>0?'+':v<0?'−':'')+(Math.abs(v)/10).toFixed(1)+'만';}
function emTable(){var i=EM.months.length-1,c=EM.cps,pr=EM.prelim.indexOf(EM.latest)>=0?' <span class="prov-tag">잠정</span>':'';
  var row=function(k,a,b,cc,dd,bold){return '<tr><td class="l" style="'+(bold?'font-weight:700':'padding-left:22px;color:var(--text-dim)')+'">'+k+'</td><td><b>'+a+'</b></td><td>'+b+'</td><td>'+cc+'</td><td>'+dd+'</td></tr>';};
  var lv=function(a,d){return a[i]==null?'–':Number(a[i]).toFixed(d==null?1:d)+'%';},lp=function(a,d){return a[i-1]==null?'–':Number(a[i-1]).toFixed(d==null?1:d)+'%';},dl=function(a){return a[i]==null||a[i-1]==null?'–':((a[i]-a[i-1])>0?'+':'')+(a[i]-a[i-1]).toFixed(1)+'%p';};
  var h='<div style="overflow-x:auto"><table class="mx-tbl ec-tbl"><thead><tr><th class="l">'+EM.latest+pr+'</th><th>이번 달</th><th>직전 달</th><th>3개월 평균 / 변화</th><th>비고</th></tr></thead><tbody>';
  var rv=EM.revision&&EM.revision.rows&&EM.revision.rows.length?'직전 2개월 수정 '+man(EM.revision.sum)+' 명':'수정치: 다음 발표부터 기록';
  h+=row('비농업 고용 증감',man(EM.nfp[i])+' 명',man(EM.nfp[i-1])+' 명',man(EM.nfp_avg3[i])+' 명',rv,true);
  h+=row('민간 고용 증감',man(EM.private[i])+' 명',man(EM.private[i-1])+' 명','','',false);
  h+=row('실업률',lv(c.ur),lp(c.ur),dl(c.ur),'U-6(광의) '+lv(c.u6)+' ('+dl(c.u6)+')',true);
  h+=row('경제활동참가율',lv(c.lfpr),lp(c.lfpr),dl(c.lfpr),'',false);
  h+=row('핵심연령(25~54) 고용률',lv(c.epop),lp(c.epop),dl(c.epop),'실업률보다 노동시장 체력을 덜 왜곡',false);
  h+=row('시간당 임금 MoM',pf(EM.ahe_mom[i]),pf(EM.ahe_mom[i-1]),'YoY '+pf(EM.ahe_yoy[i],1),'',true);
  h+=row('실질 시간당 임금 YoY',pf(EM.real_yoy[i],1),pf(EM.real_yoy[i-1],1),'','명목 임금 − 물가(1982-84 달러)',false);
  h+=row('주당 근로시간',EM.hours[i]==null?'–':EM.hours[i].toFixed(1)+'시간',EM.hours[i-1]==null?'–':EM.hours[i-1].toFixed(1)+'시간','','',false);
  document.getElementById('ec-em-tbl').innerHTML=h+'</tbody></table></div>';}
function emDraw(){if(!EM) return;var css=getComputedStyle(document.documentElement),cv=function(n){return css.getPropertyValue(n).trim();};
  var C={dim:cv('--text-dim'),muted:cv('--text-muted'),grid:'rgba(151,252,228,.13)'},n=24,L=EM.months.slice(-n),cut=function(a){return a.slice(-n);},i=EM.months.length-1;
  var sb=document.getElementById('ec-em-v');sb.innerHTML='';[['고용 증감',0],['실업률·U-6',1],['임금 YoY',2],['업종별(최근월)',3]].forEach(function(x){var b=document.createElement('button');b.type='button';b.textContent=x[0];if(x[1]===EV) b.className='on';b.onclick=function(){EV=x[1];try{localStorage.setItem('krflow.ec.emv',EV);}catch(e){}emDraw();};sb.appendChild(b);});
  var type='bar',labels=L.map(function(m){return m.slice(2).replace('-','.');}),ds,idx='x',note,fmt=function(v){return man(v)+' 명';},y2=false;
  if(EV===0){ds=[{label:'비농업 고용 증감',data:cut(EM.nfp),backgroundColor:cut(EM.nfp).map(function(v){return (v||0)>=0?'rgba(42,165,138,.75)':'rgba(240,117,106,.75)';})},{type:'line',label:'3개월 평균',data:cut(EM.nfp_avg3),borderColor:'#F2FFFC',pointRadius:0,borderWidth:2},{type:'line',label:'민간',data:cut(EM.private),borderColor:'#3987e5',pointRadius:2,borderWidth:1.4}];
    note='막대 = 전월 대비 고용 증감(천 명 → 만 명 표시). 최근 두 달은 잠정이라 다음 두 번의 발표에서 수정된다.';}
  else if(EV===1){type='line';fmt=function(v){return v==null?'–':v.toFixed(1)+'%';};y2=true;
    ds=[{label:'실업률',data:cut(EM.cps.ur),borderColor:'#e8823a',pointRadius:2,borderWidth:2.2,yAxisID:'y'},{label:'U-6(광의 실업률)',data:cut(EM.cps.u6),borderColor:'#d55181',pointRadius:0,borderWidth:1.6,yAxisID:'y2'},{label:'핵심연령 고용률',data:cut(EM.cps.epop),borderColor:'#2aa58a',pointRadius:0,borderWidth:1.6,yAxisID:'y2',hidden:true}];
    note='왼쪽 축 = 실업률, 오른쪽 축 = U-6(시간제 원하는 사람·구직 단념자 포함)·핵심연령 고용률(범례로 켬). 출처 FRED(BLS 가계조사).';}
  else if(EV===2){type='line';fmt=function(v){return pf(v,2);};
    ds=[{label:'시간당 임금 YoY(명목)',data:cut(EM.ahe_yoy),borderColor:'#e8823a',pointRadius:0,borderWidth:2},{label:'실질 시간당 임금 YoY',data:cut(EM.real_yoy),borderColor:'#F2FFFC',pointRadius:0,borderWidth:2},{type:'bar',label:'시간당 임금 MoM',data:cut(EM.ahe_mom),backgroundColor:'rgba(57,135,229,.5)'}];
    note='실질 임금 YoY가 0 아래로 내려가면 물가가 임금보다 빨리 올라 실질 구매력이 줄어드는 것 → 소비 둔화 경로.';}
  else{var is=EM.ind.filter(function(r){return r.code!=='CES0500000001';});idx='y';labels=is.map(function(r){return r.ko.trim();});
    ds=[{label:EM.latest+' 증감',data:is.map(function(r){return r.chg[i];}),backgroundColor:is.map(function(r){return (r.chg[i]||0)>=0?'rgba(42,165,138,.75)':'rgba(240,117,106,.75)';})},{label:'3개월 평균',data:is.map(function(r){var a=r.chg.slice(-3);return a.indexOf(null)>=0?null:Math.round((a[0]+a[1]+a[2])/3*10)/10;}),backgroundColor:'rgba(157,179,176,.45)'}];
    note='업종별 고용 증감(계절조정). 임시직(temp help)은 경기 선행 성격 — 줄면 기업이 먼저 사람을 덜 쓰기 시작한 것.';}
  document.getElementById('ec-em-sub').textContent='BLS 사업체조사(CES) + FRED 가계조사 · 기준월 '+EM.latest+(EM.prelim.length?' (잠정 '+EM.prelim.map(function(m){return m.slice(5);}).join('·')+'월)':'')+' · 받은 날 '+EM.fetched;
  document.getElementById('ec-em-note').textContent=note;
  if(ECH) ECH.destroy();
  ECH=new Chart(document.getElementById('ec-em-c'),{type:type,data:{labels:labels,datasets:ds},options:{indexAxis:idx,responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{color:C.dim,boxWidth:12,boxHeight:6}},tooltip:{callbacks:{label:function(it){return ' '+it.dataset.label+'  '+fmt(it.raw);}}}},
    scales:{x:{grid:{display:idx==='y',color:C.grid},ticks:{color:C.muted,maxRotation:0,autoSkip:idx==='x',maxTicksLimit:12}},y:{grid:{color:C.grid,display:idx==='x'},ticks:{color:C.muted,autoSkip:false}},
      y2:{display:y2,position:'right',grid:{display:false},ticks:{color:C.muted}}}}});}
if(EM){emTable();}else{document.getElementById('ec-em-tbl').innerHTML='<div class="card-sub">고용 데이터 없음 — scripts/emp_data.py 실행 필요</div>';}
window.ECON={show:function(){if(!loaded){loaded=true;fr.src='cpi.html';}if(P) setTimeout(ppiDraw,30);if(RT) setTimeout(rtDraw,40);if(EM) setTimeout(emDraw,50);}};
if(!document.getElementById('tab-econ').hidden) window.ECON.show();
})();

"""

RISK_JS = r"""
(function(){
'use strict';
var R=window.__RISK__,root=document.getElementById('tab-risk');
if(!R){root.innerHTML='<section class="card mx-empty">리스크 데이터가 없습니다 — <code>python scripts/risk_data.py</code></section>';window.RISK={show:function(){}};return;}
var css=getComputedStyle(document.documentElement);function cv(n){return css.getPropertyValue(n).trim();}
var COL={text:cv('--text'),dim:cv('--text-dim'),muted:cv('--text-muted'),grid:'rgba(151,252,228,.13)'};
var SC=['#c8d6d4','#f0c987','#9fd0ff','#e7a3c5','#b8e0a8','#d6b8ff'];
var P=['#3987e5','#d95926','#199e70','#c98500','#d55181','#9085e9','#97FCE4','#9db3b0','#e8a33d','#6cc3c1'];
function nf(v,d){return v==null?'–':Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});}
function cp(v){return v==null?'':nf(Math.round(v*100)/100,2)+'%';}
function md(s){return s?(+s.slice(5,7))+'/'+(+s.slice(8,10)):'–';}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function short(s){if(!s) return '–';var t=String(s).split(/[ (/]/)[0];return t||'–';}
function chg(ser,n){if(!ser||ser.length<2) return null;var e=ser[ser.length-1][1],b=ser[Math.max(0,ser.length-1-n)][1];return e-b;}
function sg(v,d){if(v==null) return '–';return '<b class="'+(v>0?'mx-up':v<0?'mx-dn':'')+'">'+(v>0?'+':v<0?'−':'±')+nf(Math.abs(v),d)+'</b>';}
function ls(k,v){try{if(v===undefined) return localStorage.getItem('krflow.rk.'+k);localStorage.setItem('krflow.rk.'+k,v);}catch(e){return null;}}

// ---- 하이일드(HYG) AI/비AI · 투자등급(LQD) — 차트 ----
var HL=R.hysplit||{},HK=Object.keys(HL).filter(function(k){return k.charAt(0)!=='_';}).sort(),HX=HK.length?HL[HK[HK.length-1]]:null,HAI=HL._ai_hist||{};
(function(){if(!HX) return;
  var ai=(HX.ai_top||[]).map(function(a){return '<tr><td class="l">'+esc(a.name)+'</td><td>'+nf(a.w,2)+'%</td><td>'+(a.px<100?'<span class="rk-below">▼</span>':'')+nf(a.px,2)+'</td><td>'+nf(a.ytw,2)+'%</td><td class="l">'+esc(a.mat)+'</td></tr>';}).join('');
  document.getElementById('rk-hy-ai').innerHTML='<summary>AI 관련으로 분류한 HYG 보유 채권 '+HX.hy_ai.n+'개 (비중 '+nf(HX.ai_weight_pct,1)+'%) — CoreWeave · AI 데이터센터·컴퓨트 SPV · SoftBank</summary><div style="overflow-x:auto"><table class="mx-tbl rk-fit"><thead><tr><th class="l">채권</th><th>HYG 비중</th><th>가격</th><th>YTW</th><th class="l">만기</th></tr></thead><tbody>'+ai+'</tbody></table></div>';
  document.getElementById('rk-hy-sub').innerHTML='최신 '+md(HX.asof)+': 하이일드 <b>'+nf(HX.hy.g_bp,0)+'</b> (AI <b>'+nf(HX.hy_ai.g_bp,0)+'</b> · 비AI <b>'+nf(HX.hy_nonai.g_bp,0)+'</b>) · 투자등급 <b>'+nf(HX.ig.g_bp,0)+'</b> · 하이일드−투자등급 <b>'+nf(HX.hy.g_bp-HX.ig.g_bp,0)+'</b>bp (모두 국채 대비 가산금리, iShares HYG·LQD 보유채권으로 직접 계산) · 보유종목 원장 '+HK.length+'일째';
})();
var HV=ls('hv2')==null?2:+ls('hv2'),FR=(R.fred||{}).series||{};
function frs(k){return FR[k]||[];}
function drawHY(){
  segs('rk-hv',[[2,'AI vs 비AI + 국채'],[0,'공식 지수 (ICE BofA)'],[1,'하이일드 − 투자등급']],HV,function(i){HV=i;ls('hv2',i);drawHY();});
  var w=HX?HX.ai_weight_pct/100:0.039,aiK=Object.keys(HAI).sort().filter(function(k){return HAI[k][1]>=40;}),aiH=aiK.map(function(k){return [k,HAI[k][0]];}),
      aiY=aiK.filter(function(k){return HAI[k][2]!=null;}).map(function(k){return [k,HAI[k][2]];}),aiU=aiK.filter(function(k){return HAI[k][3]!=null;}).map(function(k){return [k,HAI[k][3]];});
  var hyM={};frs('hy').forEach(function(r){hyM[r[0]]=r[1];});
  // 비AI 추정 = (HY 전체 − AI 비중 × AI) ÷ (1 − AI 비중). HY 전체는 공식 OAS, AI는 FINRA 복원 — 정의가 달라 근사
  var non=aiH.filter(function(r){return hyM[r[0]]!=null;}).map(function(r){return [r[0],Math.round((hyM[r[0]]-w*r[1])/(1-w)*10)/10];});
  var nonM={};non.forEach(function(r){nonM[r[0]]=r[1];});
  var L;
  if(HV===0){var bbbM={};frs('bbb').forEach(function(r){bbbM[r[0]]=r[1];});
    L=[{n:'CCC등급',s:frs('ccc'),c:'#d55181'},{n:'B등급',s:frs('b'),c:'#d4a72c'},{n:'BB등급',s:frs('bb'),c:'#3987e5'},{n:'BBB등급',s:frs('bbb'),c:'#e8823a'},
       {n:'CCC − BBB (양극화 폭)',s:frs('ccc').filter(function(r){return bbbM[r[0]]!=null;}).map(function(r){return [r[0],Math.round((r[1]-bbbM[r[0]])*10)/10];}),c:'#F2FFFC',hide:true},
       {n:'하이일드 전체',s:frs('hy'),c:'#9db3b0',hide:true},{n:'투자등급',s:frs('ig'),c:'#2aa58a',hide:true}];
    // 올해 고점 점선(Jae 10/25: '올해 고점을 넘으면 문제') — 등급별, 기간 전체에 같은 값
    var Y0=new Date().getFullYear()+'-01-01',YH={};
    [['ccc','CCC','#d55181'],['b','B','#d4a72c'],['bb','BB','#3987e5'],['bbb','BBB','#e8823a'],['hy','하이일드 전체','#9db3b0']].forEach(function(g){var a=frs(g[0]).filter(function(r){return r[0]>=Y0&&r[1]!=null;});if(!a.length) return;
      var mx=a.reduce(function(p,r){return r[1]>p[1]?r:p;});YH[g[0]]=mx;var all=frs(g[0]);
      L.push({n:g[1]+' 올해 고점 '+nf(mx[1],0)+' ('+md(mx[0])+')',s:all.map(function(r){return [r[0],mx[1]];}),c:g[2],dash:[5,4],hide:g[0]==='hy'});});
    var lastOf=function(k){var a=frs(k);return a.length?a[a.length-1]:null;},sm=[];
    [['hy','하이일드 전체'],['ccc','CCC'],['b','B'],['bb','BB'],['bbb','BBB']].forEach(function(g){var l=lastOf(g[0]),h=YH[g[0]];if(!l||!h) return;var d=l[1]-h[1];
      sm.push(g[1]+' <b>'+nf(l[1],0)+'</b>'+(d>=0?(h[0]===l[0]?' <b class="mx-up">올해 최고</b>':' <b class="mx-up">고점 +'+nf(d,0)+'</b>'):' (고점까지 '+nf(-d,0)+')'));});
    document.getElementById('rk-hy-sub').innerHTML='ICE BofA OAS(bp) '+md((lastOf('hy')||[])[0])+' · '+sm.join(' · ')+' · 점선 = 올해 고점';}
  else if(HV===1) L=[{n:'하이일드 − 투자등급',s:frs('hy').filter(function(r){return true;}).map(function(r){var ig=(frs('ig').filter(function(x){return x[0]===r[0];})[0]||[])[1];return [r[0],ig==null?null:Math.round((r[1]-ig)*10)/10];}).filter(function(r){return r[1]!=null;}),c:'#F2FFFC'}];
  else L=[{n:'하이일드 전체 (국채 대비)',s:frs('hy'),c:'#F2FFFC',hide:true},{n:'HY 중 AI − 같은 만기 국채',s:aiH,c:'#e8823a'},{n:'HY 중 비AI (추정)',s:non,c:'#3987e5'},
          {n:'HY 중 AI 채권 수익률 (%)',s:aiY,c:'rgba(232,130,58,.55)',ax:'y3',hide:true},{n:'같은 만기 국채 금리 (%)',s:aiU,c:'rgba(200,214,212,.7)',ax:'y3',hide:true},
          {n:'AI − 비AI',s:aiH.filter(function(r){return nonM[r[0]]!=null;}).map(function(r){return [r[0],Math.round((r[1]-nonM[r[0]])*10)/10];}),c:'rgba(232,130,58,.45)',hide:true}];
  if(CH.hy) CH.hy.destroy();CH.hy=lineChart(document.getElementById('rk-hyc'),L,{fmt:function(v){return nf(v,0)+'bp';},tick:function(v){return nf(v,0);}});
  // AI 기여도: 기간 중 HY 변화 vs AI 비중 × AI 변화
  var lo=RD[RW.i0],hi=RD[RW.i1],hs=frs('hy').filter(function(r){return r[0]>=lo&&r[0]<=hi;}),as=aiH.filter(function(r){return r[0]>=lo&&r[0]<=hi;});
  var el2=document.getElementById('rk-hy-contrib');
  if(hs.length>1&&as.length>1){var dH=hs[hs.length-1][1]-hs[0][1],dA=as[as.length-1][1]-as[0][1];
    el2.innerHTML='<b>기간 기여 ('+md(hs[0][0])+'→'+md(hs[hs.length-1][0])+')</b>: 하이일드 스프레드 '+sg(dH,0)+'bp 중 AI 기여 ≈ AI 비중 '+nf(w*100,1)+'% × AI 변화 '+sg(dA,0)+'bp = <b>'+sg(w*dA,0)+'bp</b> → 나머지 '+sg(dH-w*dA,0)+'bp는 비AI 몫 (근사)';}
  else el2.textContent='';
}

// ---- 발행사 한 장 ----
var h='<div style="overflow-x:auto"><table class="mx-tbl rk-tbl"><thead><tr><th class="l">발행사</th><th class="l">등급 M / S&amp;P / F</th><th class="l">최고 YTM 채권</th><th>가격</th><th>1M Δ</th><th>YTM</th><th>G-spr</th><th>CDS 5Y</th><th>기준</th></tr></thead><tbody>';
R.issuers.forEach(function(i){var b=i.bond,r=i.rating,c=i.cds;
  var rt='<span title="'+esc('Moody\'s '+(r.m||'–')+' / S&P '+(r.sp||'–')+' / Fitch '+(r.f||'–')+(r.act?' · '+r.act:'')+(r.note?' · '+r.note:''))+'">'+short(r.m)+' / '+short(r.sp)+' / '+short(r.f)+'</span>';
  var bd=cp(b.coupon)+' '+(b.maturity?b.maturity.slice(0,4):'')+(b.conv?' 전환사채':'')+(b.is144a?' <span class="rk-tag">144A</span>':'');
  var sh=i.share;if(sh&&(sh.amt||sh.total)) bd+='<br><span class="rk-sub" title="'+esc((sh.basis||'')+(sh.note?' · '+sh.note:''))+'">'+(sh.pct!=null?'회사 전체 부채의 '+nf(sh.pct,1)+'% · ':'')+'$'+(sh.amt?nf(sh.amt/1e9,2)+'B':'–')+' / $'+(sh.total?nf(sh.total/1e9,1)+'B':'미확인')+'</span>';
  var px=b.price!=null?(b.price<100?'<span class="rk-below" title="액면가(100) 아래">▼</span>':'')+nf(b.price,2):'–';
  h+='<tr><td class="l"><b>'+i.tk+'</b>'+(r.src&&/^http/.test(r.src)?' <a class="rk-src" href="'+esc(String(r.src).split(' ')[0])+'" target="_blank" rel="noopener">등급↗</a>':'')+(c&&c.news&&/http/.test(c.news)?' <a class="rk-src" href="'+esc((String(c.news).match(/https?:\/\/\S+/)||[''])[0])+'" target="_blank" rel="noopener">CDS↗</a>':'')+'</td><td class="l">'+rt+'</td><td class="l" title="'+esc((b.cusip||'')+' · '+(b.basis||''))+'">'+bd+'</td><td>'+px+'</td><td>'+sg(chg(i.series,21),2)+'</td><td>'+nf(b.ytm,2)+'%</td><td>'+(b.g!=null?nf(b.g,0):'–')+'</td>'+
    '<td title="'+esc(c&&c.news?c.news:'')+'">'+(c?esc(c.txt)+(c.ccy?' '+c.ccy:''):'미확인')+'</td><td>'+md(b.asof)+'</td></tr>';});
document.getElementById('rk-tbl').innerHTML=h+'</tbody></table></div>';

// ---- DC 본드 표 ----
function dcName(d){return String(d.issuer||'').replace(/,? ?(Investor )?LLC.*$/,'').replace(/ DC$/,'');}
var GO=R.dc_groups||[];
function dcTable(gr){var g='<div style="overflow-x:auto"><table class="mx-tbl rk-fit"><thead><tr><th class="l">채권</th><th class="l">임차·백업</th><th class="l">등급</th><th>쿠폰·만기</th><th>규모</th><th title="채권 규모 ÷ 백커(임차·보증 주체) 전체 회사채·장기차입 잔액">백커 대비</th><th>가격</th><th>1M Δ</th><th>YTM</th></tr></thead><tbody>';
var DCS=R.dc.filter(function(d){return gr==='전체'||d.group===gr;}).sort(function(a,b){return GO.indexOf(a.group)-GO.indexOf(b.group);});var lastG=null;
DCS.forEach(function(d){
  if(d.group!==lastG){lastG=d.group;g+='<tr class="rk-grow"><td class="l" colspan="9">'+esc(d.group)+'</td></tr>';}
  var bk=d.backer?(d.backer_pct!=null?'<b>'+nf(d.backer_pct,1)+'%</b> <span style="color:var(--text-muted)">of '+d.backer+(d.backer_total?' $'+nf(d.backer_total/1e9,0)+'bn':'')+'</span>':'<span style="color:var(--text-muted)">'+d.backer+' 집계 중</span>'):'–';
  var sl=(d.src||[]).map(function(u,j){return '<a class="rk-src" href="'+esc(u)+'" target="_blank" rel="noopener" title="'+esc(u)+'">출처'+(j+1)+' ↗</a>';}).join(' ');
  g+='<tr><td class="l"><b>'+(d.src&&d.src[0]?'<a class="rk-name" href="'+esc(d.src[0])+'" target="_blank" rel="noopener">'+esc(dcName(d))+'</a>':esc(dcName(d)))+'</b>'+(sl?' '+sl:'')+(d.added?' <span class="rk-tag">추가</span>':'')+'<br><span style="color:var(--text-muted)">'+esc(d.project||'')+'</span></td><td class="l rk-wrap">'+esc(d.tenant||'')+'</td><td class="l">'+esc(d.rating||'')+'</td><td>'+cp(d.coupon)+' '+(d.maturity||'').slice(0,4)+'</td><td>'+(d.amount?'$'+nf(d.amount/1e9,2)+'bn':'–')+'</td><td title="'+esc(d.backer_src||'')+'">'+bk+'</td><td>'+(d.price!=null&&d.price<100?'<span class="rk-below">▼</span>':'')+nf(d.price,2)+'</td><td>'+sg(chg(d.series,21),2)+'</td><td>'+nf(d.ytm,2)+'%</td></tr>';});
document.getElementById('rk-dc-tbl').innerHTML=g+'</tbody></table></div>';}

// ---- 백커 익스포저 ----
(function(){var E=R.exposure||{},K=Object.keys(E);if(!K.length) return;
  var TEN=['META','ORCL','MSFT','GOOGL','AMZN','CRWV','NVDA'];
  function rows(list,t){return list.filter(function(k){return E[k];}).map(function(k){var e=E[k];
    return '<tr><td class="l"><b>'+k+'</b></td><td>'+e.n+'</td><td>$'+nf(e.sum_usd/1e9,1)+'bn</td><td>'+(e.total?'$'+nf(e.total/1e9,1)+'bn':'–')+'</td><td><b>'+nf(e.sum_pct,1)+'%</b></td><td>'+md(e.period)+'</td><td class="l rk-wrap">'+esc(e.off||'')+'</td></tr>';}).join('');}
  var head='<thead><tr><th class="l">백커</th><th>채권 수</th><th>SPV 채권 합계</th><th>백커 회사채·장기차입</th><th>비율</th><th>기준</th><th class="l">장부 밖 여부(공시)</th></tr></thead>';
  document.getElementById('rk-exp').innerHTML='<h5 style="margin:2px 0 6px;color:var(--text-muted);font-size:11.5px">임차·보증 주체</h5><div style="overflow-x:auto"><table class="mx-tbl">'+head+'<tbody>'+rows(TEN)+'</tbody></table></div>'+
    '<h5 style="margin:14px 0 6px;color:var(--text-muted);font-size:11.5px">스폰서(발행 SPV의 모회사 — 대부분 연결)</h5><div style="overflow-x:auto"><table class="mx-tbl">'+head+'<tbody>'+rows(K.filter(function(k){return TEN.indexOf(k)<0;}))+'</tbody></table></div>';})();

// ---- 기간(슬라이더·날짜 입력) — 리스크 탭 차트 공통 ----
var RDm={};R.dc.forEach(function(d){d.series.forEach(function(r){RDm[r[0]]=1;});});R.issuers.forEach(function(i){i.series.forEach(function(r){RDm[r[0]]=1;});(i.cds_series||[]).forEach(function(r){RDm[r[0]]=1;});});
Object.keys(((R.fred||{}).series)||{}).forEach(function(k){R.fred.series[k].forEach(function(r){RDm[r[0]]=1;});});
var RD=Object.keys(RDm).sort(),RN=RD.length,RW={i0:0,i1:RN-1},RMIN=5,RT=0;
var rr0=document.getElementById('rk-r0'),rr1=document.getElementById('rk-r1');rr0.max=rr1.max=RN-1;
function rIdx(m){if(!m) return 0;var t=new Date(RD[RN-1]+'T00:00:00');t.setMonth(t.getMonth()-m);var s=t.toISOString().slice(0,10);for(var i=0;i<RN;i++) if(RD[i]>=s) return i;return 0;}
var RPR=[['3M',3],['6M',6],['1Y',12],['2Y',24],['전체',0]];
function rSet(a,b,lab){RW.i0=a;RW.i1=b;rr0.value=a;rr1.value=b;ls('rp',lab||'');
  Array.prototype.forEach.call(document.getElementById('rk-presets').children,function(x){x.classList.toggle('on',x.textContent===lab);});
  document.getElementById('rk-d0').value=RD[a].replace(/-/g,'.');document.getElementById('rk-d1').value=RD[b].replace(/-/g,'.');
  document.getElementById('rk-rlab').textContent=(b-a+1)+'거래일';
  if(SHOWN&&!RT){RT=1;setTimeout(function(){RT=0;draw();},60);}}
(function(){var pb=document.getElementById('rk-presets');RPR.forEach(function(p){var b=document.createElement('button');b.type='button';b.textContent=p[0];b.onclick=function(){rSet(rIdx(p[1]),RN-1,p[0]);};pb.appendChild(b);});
  function onR(e){var a=+rr0.value,b=+rr1.value;if(b-a<RMIN){if(e.target===rr0) a=Math.max(0,b-RMIN);else b=Math.min(RN-1,a+RMIN);}rSet(a,b,null);}
  rr0.addEventListener('input',onR);rr1.addEventListener('input',onR);
  function pd(t){t=(t||'').trim().replace(/\s/g,'');var m,y,mo,d;
    if((m=t.match(/^(\d{2})(\d{2})(\d{2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
    else if((m=t.match(/^(\d{4})[-./]?(\d{1,2})[-./]?(\d{1,2})$/))){y=+m[1];mo=+m[2];d=+m[3];}
    else if((m=t.match(/^(\d{2})[-./](\d{1,2})[-./](\d{1,2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
    else if((m=t.match(/^(\d{1,2})[-./](\d{1,2})$/))){y=+RD[RN-1].slice(0,4);mo=+m[1];d=+m[2];var c=y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2);if(c>RD[RN-1]) y-=1;}
    else return null;if(mo<1||mo>12||d<1||d>31) return null;return y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2);}
  ['rk-d0','rk-d1'].forEach(function(id,k){var inp=document.getElementById(id);
    inp.addEventListener('keydown',function(e){if(e.key!=='Enter') return;var s=pd(inp.value);if(!s){inp.classList.add('bad');return;}inp.classList.remove('bad');
      var a=RW.i0,b=RW.i1,i;if(k===0){for(i=0;i<RN;i++) if(RD[i]>=s){a=i;break;}if(b-a<RMIN) b=Math.min(RN-1,a+RMIN);}else{for(i=RN-1;i>=0;i--) if(RD[i]<=s){b=i;break;}if(b-a<RMIN) a=Math.max(0,b-RMIN);}
      rSet(a,b,null);inp.blur();});inp.addEventListener('focus',function(){inp.select();});});})();

// ---- 차트 공통: [날짜, 값] 목록을 날짜 합집합 축에 ----
function lineChart(cv,list,o){
  var ds={};list.forEach(function(x){x.s.forEach(function(r){ds[r[0]]=1;});});
  var lo=RD[RW.i0],hi=RD[RW.i1],L=Object.keys(ds).filter(function(d){return d>=lo&&d<=hi;}).sort();
  var sets=list.map(function(x,j){var m={};x.s.forEach(function(r){m[r[0]]=r[1];});
    return {label:x.n,borderDash:x.dash||[],data:L.map(function(d){return m[d]==null?null:m[d];}),borderColor:x.c||P[j%P.length],backgroundColor:x.c||P[j%P.length],borderWidth:o.bw||1.8,pointRadius:o.pts?1.8:0,pointHoverRadius:3,tension:0,spanGaps:true,hidden:!!x.hide,yAxisID:x.ax||'y'};});
  (o.stocks||[]).forEach(function(tk,j){var px=((R.stocks||{})[tk])||[];var m={};px.forEach(function(r){m[r[0]]=r[1];});
    var b=null;for(var i=0;i<L.length;i++){if(m[L[i]]!=null){b=m[L[i]];break;}}if(b==null) return;
    var last=null;sets.push({label:tk+' 주가',isStock:true,data:L.map(function(d){if(m[d]!=null) last=m[d];return last==null?null:Math.round(last/b*1000)/10;}),
      borderColor:SC[j%SC.length],backgroundColor:SC[j%SC.length],borderWidth:1.4,borderDash:[2,3],pointRadius:0,tension:0,spanGaps:true,yAxisID:'y2',hidden:true});});
  if(o.par) sets.push({label:'액면가 100',data:L.map(function(){return 100;}),borderColor:'rgba(232,255,250,.35)',borderDash:[4,4],borderWidth:1,pointRadius:0,pointHoverRadius:0,yAxisID:'y'});
  // 끝 라벨(이름 + 마지막 값) — 겹치면 아래로 밀어냄
  var endLab={id:'endLab',afterDatasetsDraw:function(ch){if(!o.end) return;var c=ch.ctx,ca=ch.chartArea,it=[];
    ch.data.datasets.forEach(function(d,i){if(!ch.isDatasetVisible(i)||d.label==='액면가 100') return;var me=ch.getDatasetMeta(i);for(var k=d.data.length-1;k>=0;k--) if(d.data[k]!=null&&me.data[k]){it.push({y:me.data[k].y,t:d.label+' '+o.fmt(d.data[k]),c:d.borderColor});break;}});
    it.sort(function(a,b){return a.y-b.y;});for(var i=1;i<it.length;i++) if(it[i].y-it[i-1].y<15) it[i].y=it[i-1].y+15;
    c.save();c.font='600 12px -apple-system,"Malgun Gothic",sans-serif';c.textBaseline='middle';it.forEach(function(x){c.fillStyle=x.c;c.fillText(x.t,ca.right+8,x.y);});c.restore();}};
  var NICE=[10,25,50,75,100,150,200,300,500,750,1000,1500,2000];
  return new Chart(cv,{type:'line',plugins:[endLab],data:{labels:L,datasets:sets},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},layout:{padding:{right:o.end?130:4}},
    plugins:{legend:{labels:{color:COL.dim,boxWidth:12,boxHeight:3,font:{size:12.5}}},tooltip:{backgroundColor:'rgba(6,30,32,.95)',borderColor:'rgba(151,252,228,.25)',borderWidth:1,titleColor:COL.text,bodyColor:COL.text,
      filter:function(it){return it.raw!=null&&it.dataset.label!=='액면가 100';},callbacks:{label:function(it){return ' '+it.dataset.label+'  '+(it.dataset.isStock?nf(it.raw,1)+' (기간 시작=100)':it.dataset.yAxisID==='y3'?nf(it.raw,2)+'%':o.fmt(it.raw));}}}},
    scales:{x:{grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:8,font:{size:12},callback:function(v){var s=this.getLabelForValue(v);return s.slice(2,7).replace('-','.');}}},
      y3:{display:'auto',position:'right',grid:{display:false},border:{display:false},title:{display:true,text:'금리 %',color:COL.muted,font:{size:11}},ticks:{color:COL.muted,font:{size:11},maxTicksLimit:6,callback:function(v){return nf(v,1)+'%';}}},
      y2:{display:'auto',position:'right',grid:{display:false},border:{display:false},title:{display:true,text:'주가 (기간 시작=100)',color:COL.muted,font:{size:11}},ticks:{color:COL.muted,font:{size:11},maxTicksLimit:6}},
      y:{type:o.log?'logarithmic':'linear',afterBuildTicks:function(ax){if(o.log) ax.ticks=NICE.filter(function(v){return v>=ax.min&&v<=ax.max;}).map(function(v){return {value:v};});},grid:{color:COL.grid},border:{display:false},title:{display:!!o.ytitle,text:o.ytitle||'',color:COL.muted,font:{size:11}},ticks:{color:COL.muted,font:{size:12},maxTicksLimit:o.log?20:7,callback:function(v){return o.log?(NICE.indexOf(Math.round(v))>=0?o.tick(v):''):o.tick(v);}}}}}});
}
var M={px:{par:true,fmt:function(v){return nf(v,2);},tick:function(v){return nf(v,0);},col:1},
       ytm:{fmt:function(v){return nf(v,2)+'%';},tick:function(v){return nf(v,1)+'%';},col:2}};
function pick(ser,col){return ser.filter(function(r){return r[col]!=null;}).map(function(r){return [r[0],r[col]];});}
var DCN={DC_BEIGNET:'Beignet (Meta Hyperion)',DC_SOPAIPILLA:'Sopaipilla (Meta El Paso)',DC_BEACONPT:'Beacon Point (Hut 8 TX)',HUT:'River Bend (Hut 8 LA)',DC_QTS_FAYETTEVILLE:'QTS Fayetteville (MSFT GA)',DC_RDMICH:'RD Michigan (Oracle MI)'};
var ST={dcg:+(ls('dcg')||0),dcm:ls('dcm')||'px',ism:ls('ism')||'px',gi:+(ls('gi')||0),ci:+(ls('ci')||0)},CH={};
function segs(id,items,cur,on){var b=document.getElementById(id);b.innerHTML='';items.forEach(function(x){var e=document.createElement('button');e.type='button';e.textContent=x[1];if(x[0]===cur) e.className='on';e.onclick=function(){on(x[0]);};b.appendChild(e);});}
function drawDC(){var GA=GO.concat(['전체']);segs('rk-dcg',GA.map(function(x,i){return [i,x];}),ST.dcg,function(i){ST.dcg=i;ls('dcg',i);drawDC();});
  segs('rk-dcm',[['px','가격'],['ytm','YTM']],ST.dcm,function(k){ST.dcm=k;ls('dcm',k);drawDC();});
  if(CH.dc) CH.dc.destroy();var m=M[ST.dcm],gr=GA[ST.dcg]||GA[0];dcTable(gr);
  var GS={'Meta':['META'],'Oracle·MSFT':['ORCL','MSFT'],'Google backstop':['GOOGL','WULF','CIFR'],'Amazon':['AMZN','CIFR'],'CoreWeave 임차':['CRWV','APLD','GLXY','CORZ'],'기타·임차인 미확인':['HUT','NVDA','CLSK'],'전체':['META','ORCL','MSFT','GOOGL','AMZN','CRWV']};
  CH.dc=lineChart(document.getElementById('rk-dc'),R.dc.filter(function(d){return gr==='전체'||d.group===gr;}).map(function(d){return {n:DCN[d.key]||dcName(d),s:pick(d.series,m.col)};}),Object.assign({stocks:GS[gr]||[]},m));}
function drawIss(){segs('rk-grp',R.groups.map(function(g,i){return [i,g[0]];}),ST.gi,function(i){ST.gi=i;ls('gi',i);drawIss();});
  segs('rk-ism',[['px','가격'],['ytm','YTM']],ST.ism,function(k){ST.ism=k;ls('ism',k);drawIss();});
  var grp=R.groups[ST.gi]||R.groups[0],m=M[ST.ism];
  var L=grp[1].map(function(tk){var i=R.issuers.filter(function(x){return x.tk===tk;})[0];
    return i?{n:tk+' '+cp(i.bond.coupon)+' '+(i.bond.maturity||'').slice(0,4),s:pick(i.series,m.col)}:null;}).filter(Boolean);
  if(CH.iss) CH.iss.destroy();CH.iss=lineChart(document.getElementById('rk-iss'),L,Object.assign({stocks:grp[1]},m));}
var CG=[['비교 · 로그 · 5거래일 중앙값',['ORCL','CRWV','META','GOOGL','MSFT','AMZN','SBG','SPCX']],['고위험',['CRWV','SBG','ORCL','SPCX']],['하이퍼스케일러',['META','AMZN','GOOGL','MSFT']]];
var CNAME={ORCL:'Oracle',CRWV:'CoreWeave',META:'Meta',GOOGL:'Alphabet',MSFT:'Microsoft',AMZN:'Amazon',SBG:'SoftBank',SPCX:'SpaceX'};
var CCOL={ORCL:'#3987e5',CRWV:'#e8823a',META:'#2aa58a',GOOGL:'#a463d6',MSFT:'#d4a72c',AMZN:'#d55181',SBG:'#9db3b0',SPCX:'#6cc3c1'};
// 체결 있는 날만 있는 시계열 → 날짜축 전체로 앞값 채우기 → 직전 5개 관측의 중앙값
function med5(ser){var out=[],w=[];RD.forEach(function(d){var m=null;for(var k=0;k<ser.length;k++){if(ser[k][0]<=d) m=ser[k][1];else break;}if(m==null) return;w.push(m);if(w.length>5) w.shift();var s=w.slice().sort(function(a,b){return a-b;});out.push([d,s[Math.floor(s.length/2)]]);});return out;}
function drawCDS(){segs('rk-cg',CG.map(function(g,i){return [i,g[0]];}),ST.ci,function(i){ST.ci=i;ls('ci',i);drawCDS();});
  var cmp=ST.ci===0;
  var L=CG[ST.ci][1].map(function(tk){var i=R.issuers.filter(function(x){return x.tk===tk;})[0];if(!(i&&i.cds_series&&i.cds_series.length)) return null;
    return cmp?{n:CNAME[tk]||tk,s:med5(i.cds_series),c:CCOL[tk],hide:tk==='SBG'||tk==='SPCX'}:{n:tk,s:i.cds_series};}).filter(Boolean);
  if((cmp||ST.ci===2)&&CDX.length) L.push({n:'북미 IG CDX',s:cmp?med5(CDX):CDX,c:'#ffffff'});
  if(CH.cds) CH.cds.destroy();
  if(!L.length){document.getElementById('rk-cds-sub2').textContent='CDS 시계열 없음 — scripts/risk_history.py cds 실행 필요';return;}
  var stk={stocks:CG[ST.ci][1]};  // 회사 주가(기간 시작=100, 오른쪽 축) — 기본 꺼짐, 범례 클릭으로 켬
  CH.cds=lineChart(document.getElementById('rk-cds'),L,Object.assign(stk,cmp?{log:true,end:true,bw:2.2,ytitle:'bp (로그)',fmt:function(v){return nf(v,0);},tick:function(v){return nf(v,0);}}:{pts:true,fmt:function(v){return nf(v,0)+'bp';},tick:function(v){return nf(v,0);}}));}
// 북미 IG CDX 5Y(on-the-run) 일별 체결 중앙값 bp — DTCC CFTC 지수 CDS 공개 체결
var CDX=((R.cdsvol||{}).days||[]).filter(function(r){return r[2]!=null;}).map(function(r){return [r[0],r[2]];});
var VV=+(ls('vv')||0);
function wk(d){var t=new Date(d+'T00:00:00Z'),w=(t.getUTCDay()+6)%7;t.setUTCDate(t.getUTCDate()-w);return t.toISOString().slice(0,10);}
function drawVol(){var V=R.cdsvol;if(!V||!V.days) return;
  segs('rk-vv',[[0,'건수'],[1,'최소 거래액 ($M)']],VV,function(i){VV=i;ls('vv',i);drawVol();});
  var lo=RD[RW.i0],hi=RD[RW.i1],W={},ks=[];
  V.days.forEach(function(r){if(r[0]<lo||r[0]>hi) return;var k=wk(r[0]);if(!W[k]){W[k]={};ks.push(k);}
    Object.keys(r[1]).forEach(function(tk){W[k][tk]=(W[k][tk]||0)+r[1][tk][VV];});});
  var sets=V.names.map(function(tk){return {type:'bar',label:CNAME[tk]||tk,data:ks.map(function(k){var v=W[k][tk];return v==null?0:Math.round(v*10)/10;}),backgroundColor:CCOL[tk],stack:'v'};});
  var tot=ks.map(function(k){return Object.keys(W[k]).reduce(function(a,t){return a+W[k][t];},0);});
  var li=ks.length-1;document.getElementById('rk-vol-sub').textContent='신규 체결(NEWT) · 모든 만기 · 주간(월요일 시작) 합계 · 위 기간 바'+(li>=0?' · 최근 주('+ks[li]+') '+(VV?'$'+nf(tot[li],0)+'M 이상':nf(tot[li],0)+'건')+(li>=4?' · 4주 전 '+(VV?'$'+nf(tot[li-4],0)+'M':nf(tot[li-4],0)+'건'):''):'');
  if(CH.vol) CH.vol.destroy();
  CH.vol=new Chart(document.getElementById('rk-vol'),{type:'bar',data:{labels:ks,datasets:sets},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{color:COL.dim,boxWidth:12,boxHeight:8}},tooltip:{callbacks:{title:function(it){return it[0].label+' 주';},footer:function(it){return '합계 '+(VV?'$'+nf(tot[it[0].dataIndex],0)+'M 이상':nf(tot[it[0].dataIndex],0)+'건');}}}},
    scales:{x:{stacked:true,grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:8,callback:function(v){var s=this.getLabelForValue(v);return s.slice(2,7).replace('-','.');}}},
      y:{stacked:true,grid:{color:COL.grid},ticks:{color:COL.muted},title:{display:true,text:VV?'$M (하한)':'건',color:COL.muted}}}}});}
var BV=+(ls('bv')||0);
function bser(set,cat,f){var a=((R.breadth||{}).sets||{})[set];a=a&&a[cat];if(!a) return [];var out=[],w=[];a.forEach(function(r){w.push(f(r));if(w.length>5) w.shift();out.push([r[0],Math.round(w.reduce(function(s,v){return s+v;},0)/w.length*10)/10]);});return out;}
// r = [날짜, 상승, 하락, 보합, 52주 신고가, 52주 신저가, 거래]
var BVS=[['하락 비율 %',function(r){return r[2]/Math.max(1,r[1]+r[2])*100;},function(v){return nf(v,1)+'%';}],
         ['52주 신저가 − 신고가 (종목 수)',function(r){return r[5]-r[4];},function(v){return nf(v,0);}]];
function drawBreadth(){if(!R.breadth) return;segs('rk-bv',BVS.map(function(v,i){return [i,v[0]];}),BV,function(i){BV=i;ls('bv',i);drawBreadth();});
  var v=BVS[BV],L=[{n:'하이일드 (144A)',s:bser('a144','high yield',v[1])},{n:'하이일드 (공모)',s:bser('pub','high yield',v[1])},{n:'투자등급 (공모)',s:bser('pub','investment grade',v[1])},{n:'투자등급 (144A)',s:bser('a144','investment grade',v[1]),hide:true}];
  if(CH.br) CH.br.destroy();CH.br=lineChart(document.getElementById('rk-br'),L,{fmt:v[2],tick:v[2]});}
function draw(){drawHY();drawDC();drawIss();drawCDS();drawVol();drawBreadth();}

// ---- 부채 구조(참고) ----
var dh='';Object.keys(R.debt).forEach(function(k){var t=R.debt[k];
  dh+='<h5>'+k+'</h5><div style="overflow-x:auto"><table class="mx-tbl"><thead><tr><th class="l">일자</th><th class="l">상품</th><th>규모</th><th class="l">금리</th><th class="l">만기</th><th class="l">GPU 담보</th><th class="l">공시</th></tr></thead><tbody>'+
  t.rows.map(function(r){var o={};t.fields.forEach(function(f,i){o[f]=r[i];});
    return '<tr><td class="l">'+esc(o.date_filed)+'</td><td class="l">'+esc(o.instrument)+'</td><td>'+(o.amount?'$'+nf(o.amount/1e9,2)+'bn':'–')+'</td><td class="l">'+esc(o.rate)+'</td><td class="l">'+esc(o.maturity)+'</td><td class="l">'+(o.gpu_backed===true?'<b style="color:var(--warn)">예</b>':o.gpu_backed===false?'아니오':'–')+'</td><td class="l">'+(o.url?'<a href="'+esc(o.url)+'" target="_blank" rel="noopener" style="color:var(--hl-teal)">'+esc(o.filing||'원문')+'</a>':esc(o.filing||''))+'</td></tr>';}).join('')+'</tbody></table></div>';});
document.getElementById('rk-debt').innerHTML=dh;
document.getElementById('rk-asof').textContent=(R.finra_blocked?'⚠ FINRA 수집 멈춤('+R.finra_blocked+') — 채권 가격은 마지막 값 · ':'')+'표 = FINRA TRACE 10/16 1MM+ 체결 중앙값 · 선 = FINRA 일별 종가(T-1, 최근 2년) · CDS = DTCC 공개 체결 · 수동 갱신(개인 리서치용)';
var SHOWN=false;var rp0=ls('rp');var RP=RPR.filter(function(p){return p[0]===rp0;})[0]||RPR[1];rSet(rIdx(RP[1]),RN-1,RP[0]);
window.RISK={show:function(){if(!SHOWN){SHOWN=true;draw();}}};
if(!root.hidden) window.RISK.show();
})();

"""


def risk_data_json() -> str:
    rp = ROOT / "data" / "risk.json"
    return rp.read_text(encoding="utf-8") if rp.exists() else "null"

SEIBRO_JS = r"""
(function(){
'use strict';
var SB=window.__SEIBRO__;if(!SB) return;
var grid=document.getElementById('grid');if(!grid) return;
var css=getComputedStyle(document.documentElement);function cv(n){return css.getPropertyValue(n).trim();}
var COL={text:cv('--text'),dim:cv('--text-dim'),muted:cv('--text-muted'),up:cv('--up'),down:cv('--down'),grid:'rgba(151,252,228,.13)'};
var TC={SOXL:'#e8823a',MU:'#3987e5',SPCX:'#6cc3c1',KORU:'#d55181',QQQ:'#d4a72c'};
function nf(v,d){return v==null?'–':Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});}
function ls(k,v){try{if(v===undefined) return localStorage.getItem('krflow.sb.'+k);localStorage.setItem('krflow.sb.'+k,v);}catch(e){return null;}}
function el(t,c,h){var e=document.createElement(t);if(c) e.className=c;if(h!=null) e.innerHTML=h;return e;}
var sec=el('section','card');sec.id='card-seibro';
sec.innerHTML='<div class="card-head"><div><div class="card-title">한국인 미국주식 결제 (SEIBro)</div><div class="card-sub" id="sb-sub"></div></div>'+
  '<div class="card-tools"><div class="seg" id="sb-v"></div><div class="seg" id="sb-t"></div><div class="seg" id="sb-p"></div></div></div><div class="chart-box"><canvas id="sb-c"></canvas></div>'+
  '<div class="legend" style="margin-top:6px"><span class="note">출처: 한국예탁결제원 증권정보포털(SEIBro) · 단위 백만달러 · 날짜 = 한국시간 결제일(미국 매매 다음 날 무렵) · 종목은 그날 매수결제 상위 50위 안일 때만 값(빈칸 = 50위 밖)</span></div>';
var after=document.getElementById('card-vkospi');if(after&&after.nextSibling) grid.insertBefore(sec,after.nextSibling);else grid.appendChild(sec);
// 투자자예탁금(금투협, 억원) + 원/달러(매크로 탭 데이터)
var FL=window.__FLOWS__||{},FD=FL.dates||[],DEP=(FL.series||{}).deposit||[],MX=window.__MACRO__||{},KD=MX.dates||[],KR=(MX.series||{}).usdkrw||[];
function fxAt(d){for(var i=KD.length-1;i>=0;i--) if(KD[i]<=d&&KR[i]!=null) return KR[i];for(i=0;i<KR.length;i++) if(KR[i]!=null) return KR[i];return 1350;}
var US=SB.us||[],TK=SB.tick||{},V=ls('v0')==null?3:+ls('v0'),PR=[['1M',1],['3M',3],['6M',6],['1Y',12],['2Y',24]],P=ls('p')||'6M',CH=null;
function since(m){var t=new Date();t.setMonth(t.getMonth()-m);return t.toISOString().slice(0,10);}
function segs(id,items,cur,on){var b=document.getElementById(id);b.innerHTML='';items.forEach(function(x){var e=el('button',x[0]===cur?'on':null,x[1]);e.type='button';e.onclick=function(){on(x[0]);};b.appendChild(e);});}
function draw(){
  segs('sb-v',[[3,'예탁금 + 미국주식 (합산)'],[0,'미국주식 순매수'],[1,'종목 순매수'],[4,'종목별 + 지수'],[2,'종목 매수액']],V,function(i){V=i;ls('v0',i);draw();});
  segs('sb-p',PR.map(function(p){return [p[0],p[0]];}),P,function(p){P=p;ls('p',p);draw();});
  var PXS=SB.prices||{},TS=ls('t')||'SOXL';
  if(V===4) segs('sb-t',Object.keys(TK).map(function(k){return [k,k];}),TS,function(k){ls('t',k);draw();});else document.getElementById('sb-t').innerHTML='';
  var lo=since(PR.filter(function(p){return p[0]===P;})[0][1]),ds,L,y1fmt=function(v){return '$'+nf(v/1000,1)+'bn';},yfmt=function(v){return '$'+nf(v,0)+'M';},tip=function(v){return '$'+nf(v,1)+'M';};
  if(V===3){
    // 날짜별: 예탁금 증감(전 영업일 대비, 조원) + 미국주식 순매수(USD × 그날 원/달러, 조원)
    var dm={},prev=null;
    FD.forEach(function(d,i){var v=DEP[i];if(v==null) return;if(prev!=null&&d>=lo) (dm[d]=dm[d]||[0,0])[0]=(v-prev)/1e4;prev=v;});
    US.forEach(function(r){if(r[0]>=lo) (dm[r[0]]=dm[r[0]]||[0,0])[1]=(r[1]-r[2])*1e6*fxAt(r[0])/1e12;});
    L=Object.keys(dm).sort();var a1=0,a2=0;
    var cumT=[],cum1=[],cum2=[];L.forEach(function(d){a1+=dm[d][0];a2+=dm[d][1];cum1.push(Math.round(a1*100)/100);cum2.push(Math.round(a2*100)/100);cumT.push(Math.round((a1+a2)*100)/100);});
    ds=[
        {type:'line',label:'합산 누적',data:cumT,borderColor:'#F2FFFC',backgroundColor:'#F2FFFC',borderWidth:2.6,pointRadius:0,tension:0,yAxisID:'y',order:1},
        {type:'line',label:'예탁금 누적',data:cum1,borderColor:'#3987e5',backgroundColor:'#3987e5',borderWidth:2,pointRadius:0,tension:0,yAxisID:'y',order:2},
        {type:'line',label:'미국주식 누적',data:cum2,borderColor:'#e8823a',backgroundColor:'#e8823a',borderWidth:2,pointRadius:0,tension:0,yAxisID:'y',order:2}];
    yfmt=function(v){return nf(v,0)+'조';};tip=function(v){return (v>0?'+':'')+nf(v,2)+'조';};
    var tA=a1+a2;
    // 잔액(수준): 예탁금(금투협, 억원) + 미국주식 보관금액(SEIBro, 종가 기준 $M × 그날 원/달러)
    var CU=SB.custody||[];
    function depAt(d,first){var j=-1;for(var i=0;i<FD.length;i++){if(DEP[i]==null) continue;if(first?FD[i]>=d:FD[i]<=d){j=i;if(first) break;}}return j<0?null:[FD[j],DEP[j]/1e4];}
    function cuAt(d,first){var j=-1;for(var i=0;i<CU.length;i++){if(first?CU[i][0]>=d:CU[i][0]<=d){j=i;if(first) break;}}return j<0?null:[CU[j][0],CU[j][1]*fxAt(CU[j][0])/1e6];}
    var d0=depAt(lo,true),c0=cuAt(lo,true),d1=depAt('9999',false),c1=cuAt('9999',false);
    var lvl=(d0&&c0&&d1&&c1)?'<br><b>잔액</b> 기준일 '+d0[0].slice(5)+': 예탁금 '+nf(d0[1],1)+'조 + 미국주식 보관 '+nf(c0[1],1)+'조 = <b>'+nf(d0[1]+c0[1],1)+'조</b> → 최신 '+d1[0].slice(5)+': 예탁금 '+nf(d1[1],1)+'조 + 미국주식 '+nf(c1[1],1)+'조 = <b>'+nf(d1[1]+c1[1],1)+'조</b> (미국주식 보관 = 종가 평가액, 주가 효과 포함)':'';
    document.getElementById('sb-sub').innerHTML='기간 합산 <b>'+(tA>0?'+':'')+nf(tA,1)+'조원</b> = 예탁금 증감 '+(a1>0?'+':'')+nf(a1,1)+'조'+(a1*a2>0?' ('+nf(a1/tA*100,0)+'%)':'')+' + 미국주식 순매수 '+(a2>0?'+':'')+nf(a2,1)+'조'+(a1*a2>0?' ('+nf(a2/tA*100,0)+'%)':'')+(a1*a2<0?' — 방향이 엇갈림(국내 예탁금 '+(a1<0?'유출':'유입')+', 미국주식 '+(a2>0?'유입':'유출')+')':'')+' · 미국주식은 그날 원/달러로 환산 · 예탁금은 금투협(T+1)'+lvl;
  }
  else if(V===4){
    var tk=TS,px=(PXS[tk]||{}).px||[],fm={},pm={};(TK[tk]||[]).forEach(function(r){if(r[0]>=lo) fm[r[0]]=Math.round((r[1]-r[2])*10)/10;});px.forEach(function(r){if(r[0]>=lo) pm[r[0]]=r[1];});
    var dm2={};Object.keys(fm).forEach(function(d){dm2[d]=1;});Object.keys(pm).forEach(function(d){dm2[d]=1;});L=Object.keys(dm2).sort();
    var nm=(PXS[tk]||{}).name||tk,acc2=0;
    ds=[{type:'bar',label:tk+' 순매수 (일별)',data:L.map(function(d){return fm[d]==null?null:fm[d];}),backgroundColor:L.map(function(d){return (fm[d]||0)>=0?COL.up:COL.down;}),yAxisID:'y',order:2},
        {type:'line',label:nm,data:L.map(function(d){return pm[d]==null?null:pm[d];}),borderColor:'#F2FFFC',backgroundColor:'#F2FFFC',borderWidth:2,pointRadius:0,tension:0,spanGaps:true,yAxisID:'y1',order:1}];
    y1fmt=function(v){return nf(v,v>=1000?0:1);};
    tip=function(v){return v;};
    var s1=0,b1=0,n1=0;(TK[tk]||[]).forEach(function(r){if(r[0]>=lo){s1+=r[1]-r[2];b1+=r[1];n1++;}});var pa=px.filter(function(r){return r[0]>=lo;});
    document.getElementById('sb-sub').innerHTML=tk+' 기간 순매수 <b>$'+nf(s1,0)+'M</b> (매수 $'+nf(b1,0)+'M, 상위 50위 안에 든 '+n1+'일) · '+nm+(pa.length>1?' '+nf(pa[0][1],1)+' → '+nf(pa[pa.length-1][1],1)+' ('+((pa[pa.length-1][1]/pa[0][1]-1)>0?'+':'')+nf((pa[pa.length-1][1]/pa[0][1]-1)*100,1)+'%)':'')+' · 막대 날짜 = 한국 결제일(미국 매매 다음 날 무렵), 선 = 미국 거래일';
  }
  else if(V===0){var rows=US.filter(function(r){return r[0]>=lo;}),acc=0;L=rows.map(function(r){return r[0];});
    ds=[{type:'bar',label:'일별 순매수',data:rows.map(function(r){return Math.round((r[1]-r[2])*10)/10;}),backgroundColor:rows.map(function(r){return r[1]-r[2]>=0?COL.up:COL.down;}),yAxisID:'y',order:2},
        {type:'line',label:'누적 순매수(기간 시작부터)',data:rows.map(function(r){acc+=r[1]-r[2];return Math.round(acc);}),borderColor:'#F2FFFC',backgroundColor:'#F2FFFC',borderWidth:2,pointRadius:0,tension:0,yAxisID:'y1',order:1}];
    var tb=rows.reduce(function(s,r){return s+r[1];},0),tsl=rows.reduce(function(s,r){return s+r[2];},0),la=rows[rows.length-1];
    document.getElementById('sb-sub').innerHTML='기간 매수 $'+nf(tb/1000,1)+'bn · 매도 $'+nf(tsl/1000,1)+'bn · <b>순매수 $'+nf((tb-tsl)/1000,2)+'bn</b>'+(la?' · 최신 '+la[0].slice(5)+' 순 '+nf(la[1]-la[2],0)+'$M':'');}
  else{var dm={};Object.keys(TK).forEach(function(k){TK[k].forEach(function(r){if(r[0]>=lo) dm[r[0]]=1;});});US.forEach(function(r){if(r[0]>=lo) dm[r[0]]=1;});L=Object.keys(dm).sort();
    ds=Object.keys(TK).map(function(k){var m={};TK[k].forEach(function(r){m[r[0]]=V===1?Math.round((r[1]-r[2])*10)/10:r[1];});
      return {type:V===1?'bar':'line',label:k,data:L.map(function(d){return m[d]==null?null:m[d];}),backgroundColor:TC[k]||'#9db3b0',borderColor:TC[k]||'#9db3b0',borderWidth:1.8,pointRadius:0,spanGaps:false,tension:0,yAxisID:'y'};});
    var sums=Object.keys(TK).map(function(k){var s=0,b=0;TK[k].forEach(function(r){if(r[0]>=lo){s+=r[1]-r[2];b+=r[1];}});return k+' 순 '+nf(s,0)+' / 매수 '+nf(b,0);});
    document.getElementById('sb-sub').innerHTML='기간 합계($M): '+sums.join(' · ');}
  if(CH) CH.destroy();
  CH=new Chart(document.getElementById('sb-c'),{type:'bar',data:{labels:L,datasets:ds},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{display:true,labels:{color:COL.dim,boxWidth:12,boxHeight:3,font:{size:12.5}}},tooltip:{backgroundColor:'rgba(6,30,32,.95)',borderColor:'rgba(151,252,228,.25)',borderWidth:1,titleColor:COL.text,bodyColor:COL.text,
      filter:function(it){return it.raw!=null;},callbacks:{label:function(it){return ' '+it.dataset.label+'  '+(V===4?(it.dataset.yAxisID==='y1'?nf(it.raw,2):'$'+nf(it.raw,1)+'M'):tip(it.raw));}}}},
    scales:{x:{stacked:false,grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:8,font:{size:12},callback:function(v){var s=this.getLabelForValue(v);return s.slice(2,7).replace('-','.')+(L.length<70?'.'+s.slice(8):'');}}},
      y:{stacked:false,grid:{color:function(g){return g.tick&&g.tick.value===0?'rgba(151,252,228,.3)':COL.grid;}},border:{display:false},ticks:{color:COL.muted,font:{size:12},maxTicksLimit:7,callback:function(v){return yfmt(v);}}},
      y1:{display:V===0||V===4,position:'right',grid:{display:false},border:{display:false},ticks:{color:'#F2FFFC',font:{size:12},maxTicksLimit:6,callback:function(v){return y1fmt(v);}}}}}});
}
var shown=false;function show(){if(!shown){shown=true;draw();}else if(CH) CH.resize();}
window.SEIBRO={show:show};
if(!document.getElementById('tab-market').hidden) show();
document.addEventListener('click',function(e){var t=e.target.closest&&e.target.closest('[data-tab=market],[data-top=flow]');if(t) setTimeout(function(){if(!document.getElementById('tab-market').hidden) show();},50);});
})();

"""


def seibro_data_json() -> str:
    p = ROOT / "data" / "seibro.json"
    return p.read_text(encoding="utf-8") if p.exists() else "null"


def _emp_json() -> str:
    p = ROOT / "data" / "emp.json"
    return p.read_text(encoding="utf-8").replace("</", "<\\/") if p.exists() else "null"


def _retail_json() -> str:
    p = ROOT / "data" / "retail.json"
    return p.read_text(encoding="utf-8").replace("</", "<\\/") if p.exists() else "null"


def _ppi_json() -> str:
    p = ROOT / "data" / "ppi.json"
    return p.read_text(encoding="utf-8").replace("</", "<\\/") if p.exists() else "null"


def macro_html() -> str:
    return MACRO_HTML.replace("__LINKS__", _links_html()).replace("__PPIDATA__", _ppi_json()).replace("__RETAILDATA__", _retail_json()).replace("__EMPDATA__", _emp_json())


def macro_data_json() -> str:
    return MACRO_PATH.read_text(encoding="utf-8") if MACRO_PATH.exists() else "null"
