# -*- coding: utf-8 -*-
"""data/flows.json -> 자기완결 dashboard.html (Chart.js 인라인, 외부 요청 0건).

usage: python scripts/render.py [--out PATH] [--docs]
  --docs  docs/index.html 도 함께 굽는다(GitHub Pages 배포 단계에서 사용)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import render_macro
import render_buyback
import render_shlong

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "flows.json"
HOL_PATH = ROOT / "data" / "holidays_kr.json"
VENDOR_PATH = ROOT / "vendor" / "chart.umd.min.js"
OUT_PATH = ROOT / "dashboard.html"
DOCS_PATH = ROOT / "docs" / "index.html"


def js_safe_json(obj) -> str:
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    for raw, e in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"),
                   (" ", "\\u2028"), (" ", "\\u2029")):
        s = s.replace(raw, e)
    return s


def script_safe(src: str) -> str:
    return src.replace("</script", "<\\/script")


# --------------------------------------------------------------------------
# CSS — 자사주 대시보드(buyback-dashboard)와 같은 틸 다크 토큰을 쓴다
# --------------------------------------------------------------------------
CSS = r"""
:root{
  --hl-teal:#97FCE4; --hl-teal-dim:#50D2C1; --hl-teal-soft:rgba(151,252,228,.12);
  --hl-teal-border:rgba(151,252,228,.25);
  --bg-0:#061E20; --surface:rgba(9,34,36,.94);
  --text:#F2FFFC; --text-dim:#B4D6D1; --text-muted:#8FB3AE;
  --up:#F87171; --down:#60A5FA; --warn:#FBBF24;
  --s-foreign:#3987e5; --s-inst:#d95926; --s-indiv:#199e70;
  --shadow:0 4px 30px rgba(0,0,0,.4);
}
*{box-sizing:border-box;margin:0;padding:0}
body,.notice,footer,.tile .s,.card-sub{word-break:keep-all;overflow-wrap:anywhere}
html,body{
  background:radial-gradient(ellipse at top,#0F3537 0%,#061E20 60%,#03100F 100%);
  background-color:#061E20;background-attachment:fixed;color:var(--text);
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;
  min-height:100vh;-webkit-font-smoothing:antialiased;letter-spacing:-.01em;scrollbar-gutter:stable;
}
body::before{content:'';position:fixed;inset:0;
  background:radial-gradient(circle at 20% 10%,rgba(151,252,228,.08),transparent 40%),
             radial-gradient(circle at 80% 90%,rgba(80,210,193,.06),transparent 50%);
  pointer-events:none;z-index:0}
.container{position:relative;z-index:1;max-width:1240px;margin:0 auto;padding:30px 24px 48px}
@media (max-width:520px){.container{padding:18px 14px 36px}}

header{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:14px}
.brand{display:flex;align-items:center;gap:12px}
.logo-dot{width:12px;height:12px;border-radius:50%;background:var(--hl-teal);box-shadow:0 0 16px var(--hl-teal);animation:pulse 2s ease-in-out infinite;flex-shrink:0}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.6;transform:scale(.85)}}
.brand h1{font-size:18px;font-weight:600}
.brand .sub{font-size:12px;color:var(--text-dim)}
.stamp{font-size:11px;color:var(--text-muted);font-variant-numeric:tabular-nums;text-align:right;line-height:1.7}
.chips{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;margin-top:4px}
.chip{display:inline-flex;align-items:center;gap:5px;padding:2px 9px;border-radius:999px;font-size:10.5px;font-weight:600;
  color:var(--text-dim);background:rgba(151,252,228,.05);border:1px solid rgba(151,252,228,.12);white-space:nowrap}
.chip i{width:6px;height:6px;border-radius:50%;background:var(--hl-teal-dim);display:inline-block}
.chip.prov i{background:var(--warn)}
.chip.wait i{background:var(--text-muted)}
@media (max-width:640px){.stamp{text-align:left}.chips{justify-content:flex-start}}

.stale{display:flex;gap:10px;font-size:13px;line-height:1.6;border-radius:12px;padding:12px 15px;margin-bottom:14px;font-weight:600;
  color:var(--warn);background:rgba(251,191,36,.10);border:1px solid rgba(251,191,36,.34)}
.stale[hidden]{display:none}
[hidden]{display:none!important}
.top-nav-row{display:flex;justify-content:flex-start;margin:0 0 10px}
.top-nav{display:inline-flex;align-items:center;gap:4px;background:rgba(151,252,228,.04);
  border:1px solid rgba(151,252,228,.10);border-radius:999px;padding:4px;max-width:100%;overflow-x:auto;scrollbar-width:none}
.top-nav::-webkit-scrollbar{display:none}
.nav-link{padding:6px 14px;border-radius:999px;font-size:13px;font-weight:500;color:var(--text-dim);
  background:none;border:none;font-family:inherit;cursor:pointer;white-space:nowrap;flex-shrink:0;letter-spacing:-.01em}
.nav-link:hover{color:var(--hl-teal)}
a.nav-link{text-decoration:none}
.nav-link.active{color:var(--bg-0);background:var(--hl-teal);box-shadow:0 0 14px rgba(151,252,228,.28);font-weight:600}
.nav-link:focus-visible{outline:2px solid var(--hl-teal);outline-offset:2px}
.sub-nav .nav-link{font-size:12px;padding:4px 12px}
#tabs .nav-link{font-size:14px;font-weight:700;padding:7px 18px}
.claim{margin-bottom:16px}
.grid2top .card{margin-bottom:16px}
.claim-sub{margin-top:10px}.claim-sub summary{cursor:pointer;font-size:12.5px;font-weight:700;color:var(--text-dim);padding:6px 2px}.claim-sub summary:hover{color:var(--hl-teal)}
.sec-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 14px}
.sec-lbl{font-size:12px;color:var(--text-muted)}
.sec-note{font-size:11px;color:var(--text-muted)}
#tab-sector .card{margin-bottom:16px}
.sec3{display:grid;grid-template-columns:90px repeat(3,1fr);border:1px solid rgba(151,252,228,.10);border-radius:12px;overflow:hidden}
.sec3>div{padding:9px 11px;border-bottom:1px solid rgba(151,252,228,.07);border-left:1px solid rgba(151,252,228,.05);font-size:12px;line-height:1.55;font-variant-numeric:tabular-nums;min-width:0}
.sec3 .h{font-size:11px;font-weight:700;color:var(--text-muted);background:rgba(151,252,228,.04)}
.sec3 .who{font-weight:700;color:var(--text);border-left:none}
.sec3 .who small{display:block;font-weight:500;color:var(--text-dim);font-size:10.5px}
.sec3 .sx{margin-bottom:7px}.sec3 .sx:last-child{margin-bottom:0}
.sec3 .sn{font-weight:700;color:var(--text)}
.sec3 ol{margin:2px 0 0 15px;color:var(--text-dim);font-size:11px}
.sec3 a{color:inherit;text-decoration:none;border-bottom:1px dotted rgba(127,168,164,.5)}
@media (max-width:820px){.sec3{grid-template-columns:1fr}.sec3 .h{display:none}.sec3 .who{background:rgba(151,252,228,.05)}
  .sec3>div{border-left:none}.sec3 .c::before{content:attr(data-h);display:block;font-size:10.5px;color:var(--text-muted);font-weight:700;margin-bottom:3px}}
.heat-box{position:relative;overflow:hidden}
#sec-heat{display:block;width:100%}
.heat-tip{position:absolute;pointer-events:none;background:rgba(6,30,32,.96);border:1px solid rgba(151,252,228,.25);border-radius:9px;
  padding:7px 9px;font-size:11.5px;line-height:1.5;color:var(--text);white-space:nowrap;z-index:5;font-variant-numeric:tabular-nums}
.rank-box{position:relative}
.sec-pick{background:#0b2b2d;color:var(--text);border:1px solid rgba(151,252,228,.2);border-radius:8px;padding:5px 8px;font:inherit;font-size:12px;max-width:220px}
.mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media (max-width:640px){.mini-grid{grid-template-columns:repeat(2,1fr)}}
.mini{border:1px solid rgba(151,252,228,.08);border-radius:12px;padding:8px 8px 4px;cursor:pointer;min-width:0}
.mini:hover{border-color:var(--hl-teal-border)}
.mini .t{font-size:11.5px;font-weight:700;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mini .v{font-size:10.5px;color:var(--text-dim);font-variant-numeric:tabular-nums;margin-bottom:2px}
.mini .cb{position:relative;height:90px}
.top-tbl{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:10px}
@media (max-width:640px){.top-tbl{grid-template-columns:1fr}}
.top-tbl h4{font-size:11.5px;color:var(--text-dim);margin-bottom:4px;font-weight:700}
.top-tbl table{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}
.top-tbl td{padding:4px 6px;border-bottom:1px solid rgba(151,252,228,.05)}
.top-tbl td:last-child{text-align:right}
.table-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.ct{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums;min-width:640px}
table.ct th{text-align:right;font-size:12px;font-weight:700;color:var(--text);padding:6px 10px;border-bottom:1px solid rgba(151,252,228,.14);white-space:nowrap}
table.ct th span{display:block;font-size:10.5px;font-weight:500;color:var(--text-muted)}
table.ct td{padding:6px 10px;text-align:right;border-bottom:1px solid rgba(151,252,228,.05);white-space:nowrap}
table.ct td:first-child{text-align:left;color:var(--text-dim);white-space:normal;min-width:150px}
table.ct td:first-child,table.ct th:first-child{position:sticky;left:0;z-index:1;background:#0b2b2d}
table.ct tr.hl td:first-child{background:#0f3436}
table.ct tr.hl td{background:rgba(151,252,228,.05);font-weight:700;color:var(--text)}
table.ct .dim{color:var(--text-muted);font-weight:400;font-size:11px}
.verdict{display:grid;grid-template-columns:minmax(170px,.75fr) 2.5fr;border:1px solid rgba(151,252,228,.12);border-radius:12px;overflow:hidden;margin-top:14px}
.verdict>div{padding:10px 12px;border-bottom:1px solid rgba(151,252,228,.08);font-size:12.5px;line-height:1.7;font-variant-numeric:tabular-nums}
.verdict>div:nth-last-child(-n+2){border-bottom:none}
.verdict .q{color:var(--text);font-weight:700;background:rgba(151,252,228,.04)}
.verdict b{color:var(--hl-teal)}
@media (max-width:640px){.verdict{grid-template-columns:1fr}.verdict .q{border-bottom:none}}

/* ── 기간 바 (상단 고정) ─────────────────────────────────────── */
.range-bar{position:sticky;top:0;z-index:20;margin:0 -8px 16px;padding:10px 8px 8px;
  background:linear-gradient(180deg,rgba(6,30,32,.97) 70%,rgba(6,30,32,.0));
  backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.range-inner{background:var(--surface);border:1px solid rgba(151,252,228,.10);border-radius:16px;padding:10px 14px 8px}
.range-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.seg{display:inline-flex;gap:3px;background:rgba(151,252,228,.04);border:1px solid rgba(151,252,228,.10);border-radius:999px;padding:3px;
  max-width:100%;overflow-x:auto;scrollbar-width:none}
.seg::-webkit-scrollbar{display:none}
.seg button{padding:4px 11px;border-radius:999px;font-size:12px;font-weight:500;color:var(--text-dim);background:none;border:none;
  font-family:inherit;cursor:pointer;white-space:nowrap;letter-spacing:-.01em}
.seg button:hover{color:var(--hl-teal)}
.seg button.on{color:var(--bg-0);background:var(--hl-teal);font-weight:700;box-shadow:0 0 12px rgba(151,252,228,.25)}
.seg button:focus-visible{outline:2px solid var(--hl-teal);outline-offset:1px}
.range-dates{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.range-dates>span{color:var(--text-muted);font-size:12px}
.dinp{width:96px;background:#0b2b2d;color:var(--text);border:1px solid rgba(151,252,228,.2);border-radius:8px;padding:4px 7px;
  font:inherit;font-size:12px;font-variant-numeric:tabular-nums;text-align:center}
.dinp:focus{outline:none;border-color:var(--hl-teal)}
.dinp.bad{border-color:var(--up)}
.range-label{font-size:12px;color:var(--text);font-variant-numeric:tabular-nums;font-weight:600}
.range-label span{color:var(--text-muted);font-weight:500;margin-left:6px}
.rng{position:relative;height:40px;margin-top:6px}
.rng canvas{position:absolute;left:0;right:0;top:0;width:100%;height:30px;display:block}
.rng input{position:absolute;left:0;right:0;top:0;width:100%;height:30px;margin:0;background:none;
  -webkit-appearance:none;appearance:none;pointer-events:none}
.rng input::-webkit-slider-runnable-track{height:30px;background:none}
.rng input::-moz-range-track{height:30px;background:none}
.rng input::-webkit-slider-thumb{-webkit-appearance:none;pointer-events:auto;width:12px;height:30px;border-radius:5px;
  background:var(--hl-teal);border:2px solid #061E20;box-shadow:0 0 10px rgba(151,252,228,.45);cursor:ew-resize}
.rng input::-moz-range-thumb{pointer-events:auto;width:10px;height:28px;border-radius:5px;background:var(--hl-teal);
  border:2px solid #061E20;cursor:ew-resize}
.rng input:focus-visible::-webkit-slider-thumb{outline:2px solid #fff}
.rng-axis{position:absolute;left:0;right:0;top:31px;display:flex;justify-content:space-between;font-size:9.5px;
  color:var(--text-muted);font-variant-numeric:tabular-nums;pointer-events:none}

/* ── 요약 타일 ───────────────────────────────────────────────── */
.tiles{display:grid;grid-template-columns:repeat(6,1fr);gap:10px;margin-bottom:16px}
@media (max-width:1100px){.tiles{grid-template-columns:repeat(3,1fr)}}
@media (max-width:560px){.tiles{grid-template-columns:1fr 1fr}}
.tile{background:var(--surface);border:1px solid rgba(151,252,228,.08);border-left:3px solid var(--hl-teal-border);
  border-radius:14px;padding:12px 14px;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);min-width:0}
.tile .k{font-size:11px;color:var(--text-muted);margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tile .v{font-size:20px;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em;white-space:nowrap}
.tile .s{font-size:11px;color:var(--text-dim);margin-top:4px;font-variant-numeric:tabular-nums;line-height:1.5}
.tile .s b{font-weight:600}
@media (max-width:560px){.tile .v{font-size:17px}}
.pos{color:var(--up)} .neg{color:var(--down)}

/* ── 카드 그리드 ─────────────────────────────────────────────── */
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media (max-width:1000px){.grid{grid-template-columns:1fr}}
.card{background:var(--surface);border:1px solid rgba(151,252,228,.08);border-radius:20px;padding:18px 18px 14px;
  backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);box-shadow:var(--shadow);min-width:0}
@media (max-width:520px){.card{padding:15px 12px 12px;border-radius:16px}}
.card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:10px}
.card-title{font-size:14px;font-weight:700}
.card-sub{font-size:11px;color:var(--text-muted);margin-top:3px;font-variant-numeric:tabular-nums}
.card-sub .prov-tag{font-size:9.5px;font-weight:700;color:var(--warn);background:rgba(251,191,36,.12);
  border:1px solid rgba(251,191,36,.30);border-radius:4px;padding:0 4px;margin-left:4px}
.card-tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.card .seg button{font-size:11.5px;padding:3px 9px}
.tbl-btn{font-size:11px;font-weight:600;color:var(--text-dim);background:rgba(151,252,228,.04);border:1px solid rgba(151,252,228,.12);
  border-radius:999px;padding:4px 10px;cursor:pointer;font-family:inherit}
.tbl-btn:hover,.tbl-btn.on{color:var(--hl-teal);border-color:var(--hl-teal-border)}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11px;color:var(--text-dim);margin:0 0 6px;min-height:16px}
.legend button{display:inline-flex;align-items:center;gap:6px;background:none;border:none;color:inherit;font:inherit;cursor:pointer;padding:1px 0}
.legend button.off{opacity:.38}
.legend i{width:10px;height:10px;border-radius:3px;display:inline-block}
.legend .note{color:var(--text-muted)}
.chart-box{position:relative;height:300px}
@media (max-width:768px){.chart-box{height:250px}}
.tbl-wrap{max-height:300px;overflow:auto;margin-top:8px;border-top:1px solid rgba(151,252,228,.08)}
.tbl-wrap[hidden]{display:none}
table.dt{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}
table.dt th{position:sticky;top:0;background:#0b2b2d;text-align:right;font-size:10.5px;font-weight:600;color:var(--text-muted);
  padding:6px 8px;border-bottom:1px solid rgba(151,252,228,.12);white-space:nowrap}
table.dt td{padding:5px 8px;text-align:right;border-bottom:1px solid rgba(151,252,228,.05);white-space:nowrap}
table.dt th:first-child,table.dt td:first-child{text-align:left;color:var(--text-dim)}

footer{margin-top:28px;padding-top:18px;border-top:1px solid rgba(151,252,228,.10);font-size:12px;color:var(--text-dim);line-height:1.75}
footer b{color:var(--text)}
footer ul{margin:6px 0 0 16px}
footer li{margin-bottom:3px}
.foot-h{font-size:11px;font-weight:700;color:var(--text-dim);letter-spacing:.04em;margin-top:14px;margin-bottom:2px}
footer a{color:var(--hl-teal-dim);text-decoration:none;border-bottom:1px dotted rgba(80,210,193,.45)}
@media (prefers-reduced-motion:reduce){.logo-dot{animation:none}}
"""

# --------------------------------------------------------------------------
# JS
# --------------------------------------------------------------------------
JS = r"""
(function(){
'use strict';
var F=window.__FLOWS__, HOL=window.__HOL__;
var D=F.dates, S=F.series, N=D.length;
var css=getComputedStyle(document.documentElement);
function cv(n){return css.getPropertyValue(n).trim();}
var COL={up:cv('--up'),down:cv('--down'),text:cv('--text'),dim:cv('--text-dim'),muted:cv('--text-muted'),
  teal:cv('--hl-teal'),foreign:cv('--s-foreign'),inst:cv('--s-inst'),indiv:cv('--s-indiv'),
  grid:'rgba(151,252,228,.13)',zero:'rgba(151,252,228,.30)'};
// 기관 세부 6색: 검증 통과(인접 CVD ΔE≥8.4) 순서 고정
var C6=['#3987e5','#d95926','#199e70','#c98500','#d55181','#9085e9'];
// 종목 색: 삼성전자=파랑(우선주는 같은 색상 밝은 단계), SK하이닉스=주황, 기타=무채(‘Other’), 금감원 실측점=틸
// 외국인 탭 색: 투자자 색(외국인 파랑·기관 주황·개인 청록)과 겹치지 않게 종목은 보라·자홍, 기타는 무채.
// 검증(dark, all-pairs): 보라↔자홍 CVD 16.0·정상 19.7, 기타 #9db3b0 은 '기타'용 무채(채도 하한만 의도적 미달).
var CS={samsung:'#9085e9',hynix:'#d55181',other:'#9db3b0',kospi:'#97FCE4',kosdaq:'#9db3b0',fss:'#ffffff',
  total:'#97FCE4',trade:'#3987e5',price:'#c98500'};

// ---- 파생 시리즈 ----------------------------------------------------------
S.ratio_credit_deposit=D.map(function(_,i){var a=S.credit_total[i],b=S.deposit[i];
  return (a==null||b==null||!b)?null:Math.round(a/b*10000)/100;});
// 외국인 보유 삼성·하이닉스 ÷ 코스피 시총 (%)
['005930','000660'].forEach(function(c){S['s'+c+'_fo_in_mcap']=D.map(function(_,i){var a=S['s'+c+'_fo_val'][i],b=S.mcap_kospi[i];return (a==null||!b)?null:Math.round(a/b*10000)/100;});});
S.sh_fo_in_mcap=D.map(function(_,i){var a=S.sh_fo_val[i],b=S.mcap_kospi[i];return (a==null||!b)?null:Math.round(a/b*10000)/100;});

// ---- 잠정 날짜 -----------------------------------------------------------
var PROV={};
['investor','futures','index'].forEach(function(k){(F.asof[k].prov||[]).forEach(function(d){PROV[d]=1;});});

// ---- 숫자 형식 -----------------------------------------------------------
function nf(v,d){d=d||0;return Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});}
var FMT={
  jo:function(v){return nf(v/10000,Math.abs(v)>=1e7?1:2)+'조';},
  eok:function(v){var a=Math.abs(v);return a>=10000?nf(v/10000,a>=100000?1:2)+'조':nf(Math.round(v))+'억';},
  eok2:function(v){return nf(v,Math.abs(v)<100?1:0)+'억';},
  ct:function(v){return nf(Math.round(v))+'계약';},
  pct:function(v){return nf(v,2)+'%';},
  idx:function(v){return nf(v,2);},
  shr:function(v){return nf(v/1e8,2)+'억주';},
  cnt:function(v){return nf(Math.round(v))+'개';}
};
var TICK={
  jo:function(v){return nf(v/10000,Math.abs(v)<200000?1:0)+'조';},
  eok:function(v){var a=Math.abs(v);return a>=10000?nf(v/10000,a>=100000?0:1)+'조':nf(v)+'억';},
  eok2:function(v){return nf(v)+'억';},
  ct:function(v){var a=Math.abs(v);return a>=10000?nf(v/10000,1)+'만':nf(v);},
  pct:function(v){return nf(v,1)+'%';},
  idx:function(v){return nf(v);},
  shr:function(v){return nf(v/1e8,1)+'억';},
  cnt:function(v){return nf(v);}
};
function sg(f,v){return (v>0?'+':'')+f(v);}
function cls(v){return v>0?'pos':(v<0?'neg':'');}
function arrow(v){return v>0?'▲':(v<0?'▼':'');}
var WD=['일','월','화','수','목','금','토'];
function dlong(s){var d=new Date(s+'T00:00:00');return s.replace(/-/g,'.')+' ('+WD[d.getDay()]+')';}
function dshort(s){return s.slice(5).replace('-','/');}
function dyy(s){return s.slice(2).replace(/-/g,'.');}

// ---- 기간 상태 -----------------------------------------------------------
var W={i0:0,i1:N-1};
function idxMonthsBack(m){
  if(!m) return 0;
  var t=new Date(D[N-1]+'T00:00:00');t.setMonth(t.getMonth()-m);
  var s=t.getFullYear()+'-'+('0'+(t.getMonth()+1)).slice(-2)+'-'+('0'+t.getDate()).slice(-2);
  for(var i=0;i<N;i++) if(D[i]>=s) return i;
  return 0;
}
function lastNN(a,from,to){for(var i=to;i>=from;i--) if(a[i]!=null) return i;return -1;}
function firstNN(a,from,to){for(var i=from;i<=to;i++) if(a[i]!=null) return i;return -1;}
// cum: 기간 시작일부터 누적. base: 시작일 '종가'를 0 으로 두고 그 다음 날부터 누적(잔고 변화 분해용 — 잔고 Δ 와 같은 기준)
function slice(k,cum,base){
  var a=S[k],out=[],i;
  if(!cum){for(i=W.i0;i<=W.i1;i++) out.push(a[i]);return out;}
  var li=lastNN(a,W.i0,W.i1),acc=0;
  for(i=W.i0;i<=W.i1;i++){if(i>li){out.push(null);continue;}
    if(!(base&&i===W.i0)&&a[i]!=null) acc+=a[i];out.push(Math.round(acc*10)/10);}
  return out;
}

// ---- 패널 정의 (항목 추가 = 여기 한 줄 + build_data.py assemble) ------------
function inv(mk,f,name,color){return {k:mk+'_'+f,name:name,color:color};}
function invViews(mk){
  return [
    {label:'누적',type:'line',cum:true,unit:'eok',series:[inv(mk,'foreign','외국인',COL.foreign),inv(mk,'inst','기관',COL.inst),inv(mk,'indiv','개인',COL.indiv)]},
    {label:'외국인 일별',type:'bar',unit:'eok',series:[{k:mk+'_foreign',name:'외국인 순매수',sign:true}]},
    {label:'기관 일별',type:'bar',unit:'eok',series:[{k:mk+'_inst',name:'기관 순매수',sign:true}]},
    {label:'개인 일별',type:'bar',unit:'eok',series:[{k:mk+'_indiv',name:'개인 순매수',sign:true}]}
  ];
}
function stockViews(pre){
  return [
    {label:'누적',type:'line',cum:true,unit:'eok',series:[{k:pre+'_net_foreign',name:'외국인',color:COL.foreign},{k:pre+'_net_inst',name:'기관',color:COL.inst},{k:pre+'_net_indiv',name:'개인',color:COL.indiv}]},
    {label:'외국인 일별',type:'bar',unit:'eok',series:[{k:pre+'_net_foreign',name:'외국인 순매수',sign:true}]},
    {label:'기관 일별',type:'bar',unit:'eok',series:[{k:pre+'_net_inst',name:'기관 순매수',sign:true}]},
    {label:'개인 일별',type:'bar',unit:'eok',series:[{k:pre+'_net_indiv',name:'개인 순매수',sign:true}]}
  ];
}
var INST=[['fin_invest','금융투자'],['pension','연기금'],['trust','투신'],['private_fund','사모'],['insurance','보험'],['bank','은행']];
function instView(mk,label){
  return {label:label,type:'line',cum:true,unit:'eok',series:INST.map(function(x,i){return {k:mk+'_'+x[0],name:x[1],color:C6[i]};})};
}
var PANELS=[
  {id:'credit',title:'신용거래융자 잔고',src:'금융투자협회',asof:'credit',views:[
    {label:'합계',type:'line',unit:'jo',series:[{k:'credit_total',name:'신용융자 합계',color:COL.teal}]},
    {label:'코스피',type:'line',unit:'jo',series:[{k:'credit_kospi',name:'코스피',color:COL.foreign}]},
    {label:'코스닥',type:'line',unit:'jo',series:[{k:'credit_kosdaq',name:'코스닥',color:COL.inst}]},
    {label:'시장별 누적',type:'stack',unit:'jo',series:[{k:'credit_kospi',name:'코스피',color:COL.foreign},{k:'credit_kosdaq',name:'코스닥',color:COL.inst}]}
  ]},
  {id:'deposit',title:'투자자예탁금',src:'금융투자협회',asof:'funds',views:[
    {label:'예탁금',type:'line',unit:'jo',series:[{k:'deposit',name:'투자자예탁금',color:COL.teal}]},
    {label:'신용÷예탁금',type:'line',unit:'pct',series:[{k:'ratio_credit_deposit',name:'신용융자 ÷ 예탁금',color:COL.teal}]},
    {label:'파생 예수금',type:'line',unit:'jo',series:[{k:'deriv_deposit',name:'장내파생 거래예수금',color:COL.teal}]}
  ]},
  {id:'forced',title:'미수금 · 반대매매',src:'금융투자협회',asof:'funds',views:[
    {label:'반대매매 비중',type:'line',unit:'pct',series:[{k:'forced_ratio',name:'미수금 대비 반대매매 비중',color:COL.teal}]},
    {label:'반대매매',type:'bar',unit:'eok2',series:[{k:'forced_sale',name:'반대매매 금액',color:COL.teal}]},
    {label:'미수금',type:'line',unit:'eok',series:[{k:'unpaid',name:'위탁매매 미수금',color:COL.teal}]}
  ]},
  {id:'vkospi',title:'VKOSPI · 삼성전자/하이닉스 주가 YoY',src:'KRX 파생상품지수 · 왼쪽 VKOSPI / 오른쪽 YoY%',asof:'index',views:[
    {label:'VKOSPI + YoY',type:'line',unit:'idx',unit2:'pct',note:(S.vkospi.some(function(v){return v!=null;})?'오른쪽 축 = 전년 같은 날 대비 주가 상승률':'VKOSPI 는 KRX 파생상품지수 승인 후 표시'),series:[
      {k:'vkospi',name:'VKOSPI',color:COL.teal},
      {k:'yoy_005930',name:'삼성전자 YoY',color:'#9085e9',axis:'y1',unit:'pct',signed:true},
      {k:'yoy_000660',name:'SK하이닉스 YoY',color:'#d55181',axis:'y1',unit:'pct',signed:true}]},
    {label:'YoY만',type:'line',unit:'pct',zero:true,series:[
      {k:'yoy_005930',name:'삼성전자',short:'삼성',color:'#9085e9',signed:true},{k:'yoy_000660',name:'SK하이닉스',short:'하이닉스',color:'#d55181',signed:true}]}
  ]},
  {id:'futures',title:'외국인 코스피200 선물',src:'다음 금융(KRX) · 전 월물 합계',asof:'futures',views:[
    {label:'누적 순매수',type:'line',cum:true,unit:'ct',series:[{k:'fut_foreign',name:'외국인 누적',color:COL.foreign}]},
    {label:'일별',type:'bar',unit:'ct',series:[{k:'fut_foreign',name:'외국인 순매수',sign:true}]},
    {label:'투자자별 누적',type:'line',cum:true,unit:'ct',series:[{k:'fut_foreign',name:'외국인',color:COL.foreign},{k:'fut_inst',name:'기관',color:COL.inst},{k:'fut_indiv',name:'개인',color:COL.indiv}]},
    {label:'미결제약정',type:'line',unit:'ct',series:[{k:'fut_oi',name:'미결제약정(전 월물)',color:COL.teal}]}
  ]},
  {id:'kospi',title:'코스피 투자자별 순매수',src:'다음 금융(KRX)',asof:'investor',views:invViews('kospi')},
  {id:'kosdaq',title:'코스닥 투자자별 순매수',src:'다음 금융(KRX)',asof:'investor',views:invViews('kosdaq')},
  {id:'inst',title:'기관 세부 누적 순매수',src:'다음 금융(KRX)',asof:'investor',views:[instView('kospi','코스피'),instView('kosdaq','코스닥')]},
  {id:'index',title:'지수',src:'다음 금융',asof:'index',views:[
    {label:'코스피',type:'line',unit:'idx',series:[{k:'idx_kospi',name:'코스피',color:COL.teal}]},
    {label:'코스닥',type:'line',unit:'idx',series:[{k:'idx_kosdaq',name:'코스닥',color:COL.teal}]},
    {label:'K200 선물',type:'line',unit:'idx',series:[{k:'fut_price',name:'코스피200 선물(최다 거래 월물)',color:COL.teal}]}
  ]},
  {id:'adr',title:'ADR (등락비율 · 20일)',src:'KRX 종목별 시세 · 20영업일 상승 종목 수 합 ÷ 하락 종목 수 합 · 120 이상 과매수 / 80 이하 과매도',asof:'mcap',views:[
    {label:'코스피·코스닥',type:'line',unit:'idx',bands:[{v:120,label:'과매수',color:'rgba(240,117,106,.9)',fill:'rgba(240,117,106,.08)',above:true},{v:80,label:'과매도',color:'rgba(120,170,255,.9)',fill:'rgba(120,170,255,.08)'}],series:[{k:'adr_kospi',name:'코스피 ADR',short:'코스피',color:COL.foreign},{k:'adr_kosdaq',name:'코스닥 ADR',short:'코스닥',color:COL.inst}]},
    {label:'코스피',type:'line',unit:'idx',bands:[{v:120,label:'과매수',color:'rgba(240,117,106,.9)',fill:'rgba(240,117,106,.08)',above:true},{v:80,label:'과매도',color:'rgba(120,170,255,.9)',fill:'rgba(120,170,255,.08)'}],series:[{k:'adr_kospi',name:'코스피 ADR',color:COL.teal}]},
    {label:'코스닥',type:'line',unit:'idx',bands:[{v:120,label:'과매수',color:'rgba(240,117,106,.9)',fill:'rgba(240,117,106,.08)',above:true},{v:80,label:'과매도',color:'rgba(120,170,255,.9)',fill:'rgba(120,170,255,.08)'}],series:[{k:'adr_kosdaq',name:'코스닥 ADR',color:COL.teal}]},
    {label:'일별 상승·하락',type:'line',unit:'cnt',series:[{k:'adv_kospi',name:'코스피 상승',short:'코스피↑',color:'#f0756a'},{k:'dec_kospi',name:'코스피 하락',short:'코스피↓',color:'#78aaff'},{k:'adv_kosdaq',name:'코스닥 상승',short:'코스닥↑',color:'#f5b3ab'},{k:'dec_kosdaq',name:'코스닥 하락',short:'코스닥↓',color:'#b9d0ff'}]}
  ]},
  // ---- 외국인 보유 · 삼성/하이닉스 탭 ----
  {id:'shtop',tab:'foreign',top:true,title:'외국인의 삼성전자·SK하이닉스 — 보유액 · 코스피 시총 대비 · 보유 주식 수',src:'보유주식 수(다음, KRX)×종가 · 범례를 눌러 삼성/하이닉스를 켜고 끔 · 코스피는 오른쪽 위 버튼',asof:'stock',views:[
    {label:'보유액',type:'line',unit:'jo',series:[{k:'sh_fo_val',name:'삼성+하이닉스',short:'합계',color:CS.total},{k:'s005930_fo_val',name:'삼성전자',short:'삼성',color:CS.samsung},{k:'s000660_fo_val',name:'SK하이닉스',short:'하이닉스',color:CS.hynix}]},
    {label:'코스피 시총 대비',type:'line',unit:'pct',note:'외국인 보유액 ÷ 코스피 시총',series:[{k:'sh_fo_in_mcap',name:'삼성+하이닉스',short:'합계',color:CS.total},{k:'s005930_fo_in_mcap',name:'삼성전자',short:'삼성',color:CS.samsung},{k:'s000660_fo_in_mcap',name:'SK하이닉스',short:'하이닉스',color:CS.hynix}]},
    {label:'보유 주식 수',type:'line',unit:'shr',unit2:'shr',note:'주가 효과 제외 — 장외 이동·DR 예탁 포함',series:[{k:'s005930_fo_shares',name:'삼성전자',short:'삼성',color:CS.samsung},{k:'s000660_fo_shares',name:'SK하이닉스',short:'하이닉스',color:CS.hynix,axis:'y1',unit:'shr'}]}
  ]},
  {id:'mkthold',tab:'foreign',title:'시장 전체 외국인 보유액 (코스피+코스닥)',src:'금투협(KRX) 일별 실측 · 금감원 월말',asof:'fo_market',views:[
    {label:'보유액',type:'stack',unit:'jo',series:[
      {k:'fo_kospi',name:'코스피',color:CS.kospi},{k:'fo_kosdaq',name:'코스닥',color:CS.kosdaq},
      {k:'fo_total_fss',name:'금감원 월말(결제 기준)',color:CS.fss,points:true}]},
    {label:'외국인 비중',type:'line',unit:'pct',note:'시가총액 대비',series:[
      {k:'fo_pct_kospi',name:'코스피',color:CS.kospi},{k:'fo_pct_kosdaq',name:'코스닥',color:CS.kosdaq}]},
    {label:'삼성+하이닉스 비중',type:'line',unit:'pct',series:[
      {k:'sh_in_fo_kospi',name:'코스피 외국인 보유액 중 삼성+하이닉스',color:CS.total}]}
  ]},
  {id:'decomp',tab:'foreign',title:'외국인 보유액 변화 분해 — 매매 vs 주가',src:'기간 시작일부터 누적 · 매매+주가 = 보유액 변화',asof:'fo_market',views:[
    {label:'시장 전체',type:'line',cum:true,base:true,unit:'jo',note:'주가 효과 = 보유액 변화 − 순매수(잔차)',series:[
      {k:'fo_dH_total',name:'보유액 변화',short:'보유액 변화',color:CS.total},
      {k:'fo_net_total',name:'매매(외국인 순매수)',short:'매매',color:CS.trade},
      {k:'fo_eff_price_total',name:'주가 효과',short:'주가',color:CS.price}]},
    {label:'삼성+하이닉스',type:'line',cum:true,base:true,unit:'jo',note:'매매 = 보유주식 수 변화 × 주가(장외·DR 예탁 포함)',series:[
      {k:'sh_dH',name:'보유액 변화',short:'보유액 변화',color:CS.total},
      {k:'sh_eff_trade',name:'매매(보유주식 수 변화)',short:'매매',color:CS.trade},
      {k:'sh_eff_price',name:'주가 효과',short:'주가',color:CS.price}]},
    {label:'삼성전자',type:'line',cum:true,base:true,unit:'jo',series:[
      {k:'s005930_dH',name:'보유액 변화',short:'보유액 변화',color:CS.total},
      {k:'s005930_eff_trade',name:'매매(보유주식 수 변화)',short:'매매',color:CS.trade},
      {k:'s005930_eff_price',name:'주가 효과',short:'주가',color:CS.price}]},
    {label:'SK하이닉스',type:'line',cum:true,base:true,unit:'jo',series:[
      {k:'s000660_dH',name:'보유액 변화',short:'보유액 변화',color:CS.total},
      {k:'s000660_eff_trade',name:'매매(보유주식 수 변화)',short:'매매',color:CS.trade},
      {k:'s000660_eff_price',name:'주가 효과',short:'주가',color:CS.price}]}
  ]},
  {id:'shhold',tab:'foreign',title:'삼성전자·SK하이닉스 외국인 보유',src:'보유주식 수(다음, KRX 기준)×종가(KRX) · 삼성전자는 보통주',asof:'stock',views:[
    {label:'보유액',type:'stack',unit:'jo',series:[
      {k:'s005930_fo_val',name:'삼성전자',short:'삼성',color:CS.samsung},{k:'s000660_fo_val',name:'SK하이닉스',short:'하이닉스',color:CS.hynix}]},
    {label:'지분율(주식 수)',type:'line',unit:'pct',series:[
      {k:'s005930_fo_rate',name:'삼성전자',short:'삼성',color:CS.samsung},{k:'s000660_fo_rate',name:'SK하이닉스',short:'하이닉스',color:CS.hynix}]}
  ]},
  {id:'share',tab:'foreign',title:'코스피 시총 비중',src:'KRX 종목 시총 ÷ 금투협 코스피 시총',asof:'stock',views:[
    {label:'비중',type:'line',unit:'pct',series:[{k:'share_sh',name:'삼성+하이닉스',short:'합계',color:CS.total},
      {k:'share_samsung',name:'삼성전자',short:'삼성',color:CS.samsung},{k:'share_hynix',name:'SK하이닉스',short:'하이닉스',color:CS.hynix}]},
    {label:'시총',type:'stack',unit:'jo',series:[{k:'s005930_mcap',name:'삼성전자',short:'삼성',color:CS.samsung},
      {k:'s000660_mcap',name:'SK하이닉스',short:'하이닉스',color:CS.hynix},{k:'mcap_kospi_rest',name:'코스피 기타',short:'기타',color:CS.other}]}
  ]},
  {id:'samsung',tab:'foreign',title:'삼성전자 투자자별 순매수',src:'수량(네이버)×평균가(다음) 추정',asof:'stock_flow',views:stockViews('s005930')},
  {id:'hynix',tab:'foreign',title:'SK하이닉스 투자자별 순매수',src:'수량(네이버)×평균가(다음) 추정',asof:'stock_flow',views:stockViews('s000660')}
];

// ---- 저장된 선택(뷰어 편의용, 실패해도 무시) ------------------------------
function ls(k,v){try{if(v===undefined) return localStorage.getItem('krflow.'+k);localStorage.setItem('krflow.'+k,v);}catch(e){return null;}}

// ---- Chart.js 플러그인 ----------------------------------------------------
var crosshair={id:'crosshair',afterDatasetsDraw:function(ch){
  var a=ch.tooltip&&ch.tooltip.getActiveElements();if(!a||!a.length) return;
  var x=a[0].element.x,ca=ch.chartArea,c=ch.ctx;
  c.save();c.strokeStyle='rgba(151,252,228,.35)';c.lineWidth=1;c.setLineDash([3,3]);
  c.beginPath();c.moveTo(x,ca.top);c.lineTo(x,ca.bottom);c.stroke();c.restore();}};
var endLabels={id:'endLabels',afterDatasetsDraw:function(ch,args,o){
  if(!o||!o.on) return;
  var c=ch.ctx,ca=ch.chartArea,items=[];
  ch.data.datasets.forEach(function(ds,i){
    if(!ch.isDatasetVisible(i)||ds.showLine===false) return;
    var meta=ch.getDatasetMeta(i),d=ds.data;
    for(var k=d.length-1;k>=0;k--){if(d[k]!=null&&meta.data[k]){items.push({y:meta.data[k].y,name:ds.short||ds.label,color:ds.borderColor});break;}}
  });
  items.sort(function(a,b){return a.y-b.y;});
  for(var i=1;i<items.length;i++) if(items[i].y-items[i-1].y<13) items[i].y=items[i-1].y+13;
  c.save();c.font=LABEL_FONT;c.textBaseline='middle';
  items.forEach(function(it){var x=ca.right+8;c.fillStyle=it.color;c.beginPath();c.arc(x+3,it.y,3.5,0,Math.PI*2);c.fill();
    c.fillStyle=COL.dim;c.fillText(it.name,x+11,it.y);});
  c.restore();}};
// 기준선·구간 음영 (view.bands: [{v,label,color,above|below}]) — ADR 과매수/과매도 등
var bands={id:'bands',beforeDatasetsDraw:function(ch,args,o){
  if(!o||!o.list||!ch.scales.y) return;
  var c=ch.ctx,ca=ch.chartArea,y=ch.scales.y;c.save();
  o.list.forEach(function(b){var py=y.getPixelForValue(b.v);if(py<ca.top-1||py>ca.bottom+1) return;
    c.fillStyle=b.fill;if(b.above) c.fillRect(ca.left,ca.top,ca.right-ca.left,py-ca.top);else c.fillRect(ca.left,py,ca.right-ca.left,ca.bottom-py);
    c.strokeStyle=b.color;c.lineWidth=1;c.setLineDash([4,4]);c.beginPath();c.moveTo(ca.left,py);c.lineTo(ca.right,py);c.stroke();c.setLineDash([]);
    c.font='600 11px '+getComputedStyle(document.body).fontFamily;c.fillStyle=b.color;c.textBaseline=b.above?'bottom':'top';
    c.fillText(b.label+' '+b.v,ca.left+6,b.above?py-3:py+3);});
  c.restore();}};
Chart.register(crosshair,endLabels,bands);
Chart.defaults.font.family='-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif';
Chart.defaults.color=COL.dim;Chart.defaults.font.size=12;

// ---- 카드 ---------------------------------------------------------------
var CARDS=[];
function hexA(h,a){var n=parseInt(h.slice(1),16);return 'rgba('+(n>>16&255)+','+(n>>8&255)+','+(n&255)+','+a+')';}

function isCum(view,sp){return sp.cum!=null?sp.cum:!!view.cum;}
function shTxt(sp,i){var m=/^(s(\d{6})|sh)_eff_trade$/.exec(sp.k);if(!m) return '';
  function d(c){var a=S['s'+c+'_fo_shares'];if(!a) return null;var b=null;for(var j=W.i0;j<=i;j++) if(a[j]!=null){b=a[j];break;}var e=null;for(j=i;j>=W.i0;j--) if(a[j]!=null){e=a[j];break;}return b==null||e==null?null:e-b;}
  function t(v){return v==null?'–':(v>0?'+':v<0?'−':'')+Math.abs(Math.round(v/1e4)).toLocaleString('ko-KR')+'만주';}
  if(m[2]) return ' (누적 '+t(d(m[2]))+')';
  return ' (누적 삼성 '+t(d('005930'))+' · 하이닉스 '+t(d('000660'))+')';}
function cumText(view){return view.base?'· 기준 '+dyy(D[W.i0])+' 종가 = 0':'· 누적 기준일 '+dyy(D[W.i0]);}
var LABEL_FONT='600 10.5px -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif';
var measureCtx=document.createElement('canvas').getContext('2d');
function labelOf(sp){return sp.short||sp.name;}
function labelPad(view){measureCtx.font=LABEL_FONT;var w=0;
  view.series.forEach(function(sp){if(!sp.points) w=Math.max(w,measureCtx.measureText(labelOf(sp)).width);});
  return Math.ceil(w)+22;}
// 겹치기 지수: 보기 이름이 '코스닥'(코스피 언급 없음)이면 코스닥, 아니면 코스피 (Jae 10/21)
function ovKD(view){return /코스닥/.test(view.label||'')&&!/코스피/.test(view.label||'');}
function ovOn(card,view){return !!card&&card.ov&&card.p.id!=='index'&&!view.series.some(function(sp){return sp.axis==='y1';});}
function datasets(view,card){
  var out=view.series.map(function(sp,j){
    var data=slice(sp.k,isCum(view,sp),view.base);
    if(view.type==='bar'){
      return {type:'bar',label:sp.name,data:data,borderWidth:0,borderRadius:2,borderSkipped:'start',
        categoryPercentage:1,barPercentage:.82,
        backgroundColor:sp.sign?data.map(function(v){return v>=0?COL.up:COL.down;}):(sp.color||COL.teal)};
    }
    var o={type:'line',label:sp.name,short:sp.short,data:data,borderColor:sp.color,backgroundColor:sp.color,borderWidth:2,
      pointRadius:0,pointHoverRadius:4,pointHoverBorderWidth:2,pointHoverBorderColor:'#061E20',tension:0,spanGaps:true};
    if(sp.points){o.showLine=false;o.pointRadius=4.5;o.pointHoverRadius=6;o.pointStyle='rectRot';
      o.pointBackgroundColor=sp.color;o.pointBorderColor='#061E20';o.pointBorderWidth=1.5;o.spanGaps=false;o.stack='pts';}
    else if(view.type==='stack'){o.stack='s';o.fill=j===0?'origin':'-1';o.backgroundColor=hexA(sp.color,.30);}
    if(sp.dash) o.borderDash=[5,4];
    if(sp.axis==='y1') o.yAxisID='y1';
    return o;
  });
  if(ovOn(card,view)) out.push({type:'line',label:ovKD(view)?'코스닥':'코스피',isOv:true,data:slice(ovKD(view)?'idx_kosdaq':'idx_kospi',false),borderColor:'rgba(157,179,176,.6)',backgroundColor:'rgba(157,179,176,.6)',
    borderWidth:1.2,pointRadius:0,pointHoverRadius:3,tension:0,spanGaps:true,yAxisID:'y1',order:9});
  return out;
}

function config(card){
  var view=card.p.views[card.v],unit=view.unit;
  var lines=view.series.filter(function(sp){return !sp.points;}).length;
  var OVN=ovOn(card,view),hasY1=OVN||view.series.some(function(sp){return sp.axis==='y1';});
  var direct=view.series.length>1&&lines<=4&&view.type!=='bar'&&!hasY1;
  var anyCum=view.series.some(function(sp){return isCum(view,sp);});
  function signedOf(sp){return isCum(view,sp)||view.type==='bar'||!!sp.signed;}
  return {
    data:{labels:D.slice(W.i0,W.i1+1),datasets:datasets(view,card)},
    options:{
      responsive:true,maintainAspectRatio:false,animation:false,normalized:true,
      interaction:{mode:'index',intersect:false},
      layout:{padding:{right:direct?labelPad(view):4,top:4}},
      plugins:{
        legend:{display:false},
        endLabels:{on:direct},
        bands:{list:view.bands||null},
        tooltip:{backgroundColor:'rgba(6,30,32,.95)',borderColor:'rgba(151,252,228,.25)',borderWidth:1,
          titleColor:COL.text,bodyColor:COL.text,footerColor:COL.dim,padding:10,cornerRadius:10,
          titleFont:{weight:'600',size:12},bodyFont:{size:12},footerFont:{size:11,weight:'400'},
          usePointStyle:true,boxPadding:4,
          filter:function(it){return it.raw!=null;},
          callbacks:{
            title:function(items){if(!items.length) return '';var d=items[0].label;return dlong(d)+(PROV[d]?' · 잠정':'');},
            label:function(it){if(it.dataset.isOv) return ' '+it.dataset.label+'  '+FMT.idx(it.raw);var sp=view.series[it.datasetIndex],f=FMT[sp.unit||unit];return ' '+it.dataset.label+'  '+(signedOf(sp)?sg(f,it.raw):f(it.raw))+shTxt(sp,W.i0+it.dataIndex);},
            labelColor:function(it){if(it.dataset.isOv) return {borderColor:'#9db3b0',backgroundColor:'#9db3b0',borderRadius:2};var c=it.dataset.type==='bar'?(it.raw>=0?COL.up:COL.down):it.dataset.borderColor;
              if(it.dataset.type==='bar'&&!view.series[it.datasetIndex].sign) c=COL.teal;
              return {borderColor:c,backgroundColor:c,borderRadius:2};},
            footer:function(items){
              if(!anyCum||!items.length) return '';
              var i=W.i0+items[0].dataIndex,f=FMT[unit];
              return '당일 '+view.series.filter(function(sp,j){return isCum(view,sp)&&(card.chart?card.chart.isDatasetVisible(j):true);})
                .map(function(sp){var v=S[sp.k][i];return sp.name+' '+(v==null?'–':sg(f,v));}).join(' · ');
            }
          }}
      },
      scales:{
        x:{grid:{display:false},border:{color:'rgba(151,252,228,.14)'},
          ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:7,font:{size:12},
            callback:function(v){var s=this.getLabelForValue(v);return (W.i1-W.i0>140)?s.slice(2,7).replace('-','.'):dshort(s);}}},
        y:{stacked:view.type==='stack',beginAtZero:!!(anyCum||view.type==='bar'||view.type==='stack'||view.zero),
          border:{display:false},
          grid:{color:function(c){return c.tick&&c.tick.value===0?COL.zero:COL.grid;},drawTicks:false},
          ticks:{color:COL.muted,font:{size:12},padding:6,maxTicksLimit:6,callback:function(v){return TICK[unit](v);}}},
        y1:hasY1?{position:'right',border:{display:false},grid:{display:false},
          ticks:{color:COL.muted,font:{size:12},padding:4,maxTicksLimit:6,callback:function(v){return TICK[OVN?'idx':(view.unit2||'pct')](v);}}}:{display:false}
      }
    }
  };
}

function el(tag,cls,html){var e=document.createElement(tag);if(cls) e.className=cls;if(html!=null) e.innerHTML=html;return e;}

function buildCard(p){
  var card={p:p,v:0,table:false};
  var saved=parseInt(ls('view.'+p.id),10);if(saved>=0&&saved<p.views.length) card.v=saved;
  var root=el('section','card');root.id='card-'+p.id;
  var head=el('div','card-head');
  var tt=el('div');tt.appendChild(el('div','card-title',p.title));card.sub=el('div','card-sub');tt.appendChild(card.sub);
  head.appendChild(tt);
  var tools=el('div','card-tools');
  if(p.views.length>1){
    var seg=el('div','seg');seg.setAttribute('role','tablist');
    p.views.forEach(function(v,i){var b=el('button',null,v.label);b.type='button';b.setAttribute('role','tab');
      b.onclick=function(){card.v=i;ls('view.'+p.id,i);rebuild(card);};seg.appendChild(b);});
    tools.appendChild(seg);card.seg=seg;
  }
  card.ov=ls('ov.'+p.id)!=='0';
  if(p.id!=='index'){var ob=el('button','tbl-btn'+(card.ov?' on':''),'코스피');ob.type='button';ob.title='코스피를 회색 선(오른쪽 축)으로 겹치기';
    ob.onclick=function(){card.ov=!card.ov;ls('ov.'+p.id,card.ov?'1':'0');ob.classList.toggle('on',card.ov);rebuild(card);};tools.appendChild(ob);card.ob=ob;}
  var tb=el('button','tbl-btn','표');tb.type='button';tb.title='현재 기간의 값을 표로 보기';
  tb.onclick=function(){card.table=!card.table;tb.classList.toggle('on',card.table);renderTable(card);};
  tools.appendChild(tb);
  head.appendChild(tools);root.appendChild(head);
  card.legend=el('div','legend');root.appendChild(card.legend);
  var box=el('div','chart-box');var cvs=document.createElement('canvas');cvs.setAttribute('role','img');box.appendChild(cvs);
  root.appendChild(box);card.canvas=cvs;
  card.tbl=el('div','tbl-wrap');card.tbl.hidden=true;root.appendChild(card.tbl);
  document.getElementById(p.top?'grid2top':(p.tab==='foreign'?'grid2':'grid')).appendChild(root);
  CARDS.push(card);rebuild(card);
}

function rebuild(card){
  var view=card.p.views[card.v];
  if(card.ob){card.ob.textContent=ovKD(view)?'코스닥':'코스피';card.ob.title=card.ob.textContent+'를 회색 선(오른쪽 축)으로 겹치기';}
  if(card.seg) Array.prototype.forEach.call(card.seg.children,function(b,i){b.classList.toggle('on',i===card.v);b.setAttribute('aria-selected',i===card.v);});
  if(card.chart) card.chart.destroy();
  var cfg=config(card);cfg.type=view.type==='bar'?'bar':'line';
  card.chart=new Chart(card.canvas,cfg);
  card.canvas.setAttribute('aria-label',card.p.title+' — '+view.label);
  // 범례: 2개 이상일 때 항상(클릭으로 숨기기). 단일 시리즈는 제목이 이름 역할
  card.legend.innerHTML='';
  if(view.series.length>1){
    view.series.forEach(function(sp,i){var b=el('button',null,'<i style="background:'+sp.color+(sp.points?';transform:rotate(45deg) scale(.8)':'')+(sp.dash?';opacity:.7':'')+'"></i>'+sp.name);b.type='button';
      b.onclick=function(){var vis=card.chart.isDatasetVisible(i);card.chart.setDatasetVisibility(i,!vis);b.classList.toggle('off',vis);card.chart.update('none');};
      card.legend.appendChild(b);});
  } else if(view.type==='bar'&&view.series[0].sign){
    card.legend.innerHTML='<span><i style="background:'+COL.up+'"></i> 순매수</span> <span><i style="background:'+COL.down+'"></i> 순매도</span>';
    card.legend.querySelectorAll('span').forEach(function(s){s.style.display='inline-flex';s.style.alignItems='center';s.style.gap='6px';});
  }
  if(view.series.some(function(sp){return isCum(view,sp);})){var n=el('span','note',cumText(view));card.legend.appendChild(n);card.cumNote=n;card.cumView=view;} else card.cumNote=null;
  if(view.note){card.legend.appendChild(el('span','note','· '+view.note));}
  updateSub(card);renderTable(card);
}

function updateSub(card){
  var view=card.p.views[card.v],a=F.asof[card.p.asof]||{},d=a.date;
  var prov=d&&(a.prov||[]).indexOf(d)>=0;
  var unitName={jo:'조원',eok:'억원',eok2:'억원',ct:'계약',pct:'%',idx:'pt',cnt:'종목 수',shr:'주(왼쪽 삼성·오른쪽 하이닉스)'}[view.unit];
  card.sub.innerHTML=card.p.src+' · '+unitName+(d?' · '+dshort(d)+' 기준':'')+(prov?'<span class="prov-tag">잠정</span>':'');
}

function updateCard(card){
  var view=card.p.views[card.v],ch=card.chart;
  ch.data.labels=D.slice(W.i0,W.i1+1);
  var fresh=datasets(view,card);
  ch.data.datasets.forEach(function(ds,i){ds.data=fresh[i].data;if(view.type==='bar') ds.backgroundColor=fresh[i].backgroundColor;});
  ch.update('none');
  if(card.cumNote) card.cumNote.textContent=cumText(view);
  if(card.table) renderTable(card);
}

function renderTable(card){
  card.tbl.hidden=!card.table;if(!card.table) return;
  var view=card.p.views[card.v],f=FMT[view.unit];
  var cols=view.series.map(function(sp){var c=isCum(view,sp);return {name:sp.name+(c?' (누적)':''),data:slice(sp.k,c,view.base),signed:c||view.type==='bar'||!!sp.signed};});
  var h='<table class="dt"><thead><tr><th>날짜</th>'+cols.map(function(c){return '<th>'+c.name+'</th>';}).join('')+'</tr></thead><tbody>';
  for(var j=W.i1-W.i0;j>=0;j--){
    var d=D[W.i0+j];
    if(cols.every(function(c){return c.data[j]==null;})) continue;
    h+='<tr><td>'+d+(PROV[d]?' 잠정':'')+'</td>'+cols.map(function(c){var v=c.data[j];
      return '<td class="'+(c.signed&&v!=null?cls(v):'')+'">'+(v==null?'–':(c.signed?sg(f,v):f(v)))+'</td>';}).join('')+'</tr>';
  }
  card.tbl.innerHTML=h+'</tbody></table>';
}

// ---- 요약 타일 -----------------------------------------------------------
function balTile(k,label,unit,extra){
  var a=S[k],li=lastNN(a,W.i0,W.i1);if(li<0) return {k:label,v:'–',s:''};
  var pi=lastNN(a,W.i0,li-1),fi=firstNN(a,W.i0,W.i1),f=FMT[unit],v=a[li];
  var s='';
  if(pi>=0){var dd=v-a[pi];s+='전일 <b class="'+cls(dd)+'">'+arrow(dd)+f(Math.abs(dd))+'</b>';}
  if(fi>=0&&fi<li){var dw=v-a[fi];s+=' · 구간 <b class="'+cls(dw)+'">'+arrow(dw)+f(Math.abs(dw))+'</b>';}
  return {k:label+' · '+dshort(D[li]),v:f(v),s:s+(extra?'<br>'+extra(li):'')};
}
function flowTile(k,label,unit){
  var a=S[k],li=lastNN(a,W.i0,W.i1);if(li<0) return {k:label,v:'–',s:''};
  var sum=0;for(var i=W.i0;i<=li;i++) if(a[i]!=null) sum+=a[i];
  var f=FMT[unit];
  return {k:label+' · 구간 누적',v:'<span class="'+cls(sum)+'">'+sg(f,sum)+'</span>',
    s:'최근 '+dshort(D[li])+(PROV[D[li]]?'(잠정)':'')+' <b class="'+cls(a[li])+'">'+sg(f,a[li])+'</b>'};
}
function renderTiles(){
  var T=[
    balTile('credit_total','신용융자 잔고','jo',function(i){return '코스피 '+FMT.jo(S.credit_kospi[i])+' · 코스닥 '+FMT.jo(S.credit_kosdaq[i]);}),
    balTile('deposit','투자자예탁금','jo',function(i){var r=S.ratio_credit_deposit[i];return r!=null?'신용÷예탁금 '+FMT.pct(r):'';}),
    (function(){var a=S.forced_sale,li=lastNN(a,W.i0,W.i1);if(li<0) return {k:'반대매매',v:'–',s:''};
      var n=0,s=0;for(var i=W.i0;i<=li;i++) if(a[i]!=null){n++;s+=a[i];}
      return {k:'반대매매 · '+dshort(D[li]),v:FMT.eok2(a[li]),s:'비중 '+FMT.pct(S.forced_ratio[li])+' · 구간 평균 '+FMT.eok2(s/n)};})(),
    flowTile('fut_foreign','외국인 선물','ct'),
    flowTile('kospi_foreign','외국인 코스피','eok'),
    flowTile('kosdaq_foreign','외국인 코스닥','eok')
  ];
  document.getElementById('tiles').innerHTML=T.map(function(t){
    return '<div class="tile"><div class="k">'+t.k+'</div><div class="v">'+t.v+'</div><div class="s">'+t.s+'</div></div>';}).join('');
}

function rateTile(code,label){
  var a=S['s'+code+'_fo_rate'],sh=S['s'+code+'_fo_shares'],li=lastNN(a,W.i0,W.i1),fi=firstNN(a,W.i0,W.i1);
  if(li<0||fi<0) return {k:label,v:'–',s:''};
  var dp=a[li]-a[fi],dsh=(sh[li]/sh[fi]-1)*100,pf=function(x){return nf(x,1)+'%';};
  return {k:label+' · '+dshort(D[li]),v:FMT.pct(a[li]),
    s:'구간 <b class="'+cls(dp)+'">'+arrow(dp)+nf(Math.abs(dp),2)+'%p</b> · 보유주식 <b class="'+cls(dsh)+'">'+sg(pf,dsh)+'</b>'};
}
function sumW(k,a,b){var s=0,x=S[k];for(var i=a;i<=b;i++) if(x[i]!=null) s+=x[i];return s;}
function renderTiles2(){
  var T=[
    balTile('fo_total','외국인 보유 전체','jo',function(i){return '코스피 '+FMT.jo(S.fo_kospi[i])+' · 코스닥 '+FMT.jo(S.fo_kosdaq[i]);}),
    (function(){var a=S.fo_pct_kospi,li=lastNN(a,W.i0,W.i1),fi=firstNN(a,W.i0,W.i1);if(li<0) return {k:'외국인 비중',v:'–',s:''};
      var dp=a[li]-a[fi];return {k:'코스피 외국인 비중 · '+dshort(D[li]),v:FMT.pct(a[li]),
        s:'구간 <b class="'+cls(dp)+'">'+arrow(dp)+nf(Math.abs(dp),2)+'%p</b> · 코스닥 '+FMT.pct(S.fo_pct_kosdaq[li])};})(),
    balTile('sh_fo_val','외국인 보유 삼성+하이닉스','jo',function(i){var r=S.sh_in_fo_kospi[i];return '삼성 '+FMT.jo(S.s005930_fo_val[i])+' · 하이닉스 '+FMT.jo(S.s000660_fo_val[i])+(r!=null?'<br>코스피 외국인 보유의 '+FMT.pct(r):'');}),
    rateTile('005930','삼성전자 외국인 지분율'),
    rateTile('000660','하이닉스 외국인 지분율'),
    (function(){var li=lastNN(S.fo_dH_total,W.i0,W.i1);if(li<0) return {k:'보유액 변화',v:'–',s:''};
      var h0=firstNN(S.fo_total,W.i0,W.i1),base=h0>=0?S.fo_total[h0]:null;
      var dh=sumW('fo_dH_total',h0+1,li),nb=sumW('fo_net_total',h0+1,li),pr=sumW('fo_eff_price_total',h0+1,li);
      return {k:'구간 외국인 보유액 변화',v:'<span class="'+cls(dh)+'">'+sg(FMT.jo,dh)+'</span>',
        s:'매매 <b class="'+cls(nb)+'">'+sg(FMT.jo,nb)+'</b> · 주가 <b class="'+cls(pr)+'">'+sg(FMT.jo,pr)+'</b>'+(base?'<br>순매수 ÷ 시작 보유액 <b>'+nf(nb/base*100,1)+'%</b>':'')};})()
  ];
  document.getElementById('tiles2').innerHTML=T.map(function(t){
    return '<div class="tile"><div class="k">'+t.k+'</div><div class="v">'+t.v+'</div><div class="s">'+t.s+'</div></div>';}).join('');
}

// ---- 주장 검증 카드 (고정 기준일 — 기간 바와 무관, 매일 자동 재계산) ------------------
function renderClaim(){
  var box=document.getElementById('claim');if(!box) return;
  function ok(i){return S.fo_total[i]!=null&&S.sh_fo_val[i]!=null&&S.idx_kospi[i]!=null;}
  function ix(s){for(var i=N-1;i>=0;i--) if(D[i]<=s&&ok(i)) return i;return -1;}
  var iB=-1;for(var t=N-1;t>=0;t--) if(ok(t)){iB=t;break;}
  if(iB<0){box.hidden=true;return;}
  var A0=ix('2024-10-31'),A1=ix('2024-12-31'),A2=ix('2025-12-31');
  var iP=-1,hP=-Infinity;for(t=A2+1;t<=iB;t++) if(S.fo_total[t]!=null&&S.fo_total[t]>hP){hP=S.fo_total[t];iP=t;}
  var AH=ix('2025-06-30');
  // 표시 열(Jae 10/18): 24.10.31 빼고 25.06.30 추가. A0 는 아래 주장별 대조 ①② 계산에만 쓴다
  var cols=[A1,AH,A2,iP,iB],heads=['연말 2,400 무렵','25년 상반기 말','2026년 시작','2026 보유액 고점','최신'];
  var J=FMT.jo,P=function(x){return x==null?'–':nf(x,2)+'%';};
  function v(k,i,f){var x=S[k][i];return x==null?'–':(f||J)(x);}
  function fssAt(i){for(var j=i;j>=0;j--) if(S.fo_total_fss[j]!=null) return {v:S.fo_total_fss[j],d:D[j]};return null;}
  var SHR=function(x){return x==null?'–':nf(x/1e8,2)+'억주';};
  function tbl(rows){var t='<div class="table-scroll"><table class="ct"><thead><tr><th></th>'+cols.map(function(i,c){
      return '<th>'+(i<0?'–':dyy(D[i]))+'<span>'+heads[c]+'</span></th>';}).join('')+'</tr></thead><tbody>';
    rows.forEach(function(r){t+='<tr'+(r[2]?' class="hl"':'')+'><td>'+r[0]+'</td>'+cols.map(function(i){return '<td>'+(i<0?'–':r[1](i))+'</td>';}).join('')+'</tr>';});
    return t+'</tbody></table></div>';}
  // 맨 위(접지 않음) — Jae 10/18 지정
  var main=[
    ['코스피 지수 · 시총',function(i){return v('idx_kospi',i,FMT.idx)+' <span class="dim">·</span> '+v('mcap_kospi',i);}],
    ['외국인 보유 · 코스피',function(i){return v('fo_kospi',i);},1],
    ['외국인 보유 · 삼성전자 / SK하이닉스',function(i){return v('s005930_fo_val',i)+' <span class="dim">/</span> '+v('s000660_fo_val',i);}],
    ['외국인 코스피 보유 중 삼성+하이닉스 비중',function(i){return P(S.sh_in_fo_kospi[i])+' <span class="dim">('+v('sh_fo_val',i)+')</span>';},1]
  ];
  var kq=[
    ['코스닥 지수 · 시총',function(i){return v('idx_kosdaq',i,FMT.idx)+' <span class="dim">·</span> '+v('mcap_kosdaq',i);}],
    ['외국인 보유 · 코스닥',function(i){return v('fo_kosdaq',i);}]
  ];
  var tot=[
    ['코스피+코스닥 합산 시총',function(i){return v('mcap_total',i);}],
    ['코스피+코스닥 합산 외국인 보유',function(i){return v('fo_total',i);},1],
    ['외국인 보유 비중 · 코스피+코스닥 합산',function(i){return P(S.fo_pct_total[i]);}]
  ];
  var etc=[
    ['외국인 비중 · 코스피',function(i){return P(S.fo_pct_kospi[i]);}],
    ['(참고) 금감원 월말 · 결제 기준',function(i){var r=fssAt(i);if(!r) return '–';
      return J(r.v)+' <span class="dim">('+r.d.slice(2,7).replace('-','.')+'말)</span>';}],
    ['삼성전자 시총 · 코스피 비중',function(i){return v('s005930_mcap',i)+' · '+P(S.share_samsung[i]);}],
    ['SK하이닉스 시총 · 코스피 비중',function(i){return v('s000660_mcap',i)+' · '+P(S.share_hynix[i]);}],
    ['외국인 지분율(주식 수) 삼성 · 하이닉스',function(i){return P(S.s005930_fo_rate[i])+' · '+P(S.s000660_fo_rate[i]);}]
  ];
  function dt(id,title,body,def){var o=!!def;try{var x=localStorage.getItem('krflow.claim.'+id);if(x!==null) o=x==='1';}catch(e){}
    return '<details class="claim-sub" data-k="'+id+'"'+(o?' open':'')+'><summary>'+title+'</summary>'+body+'</details>';}
  var h=tbl(main)+dt('tot','합계 (코스피+코스닥)',tbl(tot),true)+dt('kq','코스닥',tbl(kq))+dt('etc','기타 — 외국인 비중·금감원·종목 시총·지분율',tbl(etc));

  // ---- 주장별 대조 ----
  function sumR(k,a,b){var s=0;for(var i=a+1;i<=b;i++) if(S[k][i]!=null) s+=S[k][i];return s;}   // (a,b]
  function pc(x){return (x>0?'+':'')+nf(x,1)+'%';}
  function mult(a,b){return '×'+nf(b/a,2);}
  var kP=-Infinity,ikP=-1;for(t=A0;t<=iB;t++) if(S.idx_kospi[t]!=null&&S.idx_kospi[t]>kP){kP=S.idx_kospi[t];ikP=t;}
  var nbK=sumR('kospi_foreign',A2,iB),nbQ=sumR('kosdaq_foreign',A2,iB),nb=nbK+nbQ;
  var hA=S.fo_total[A2],hB=S.fo_total[iB];
  var f0=fssAt(A0);
  var near=Math.abs(S.fo_total[A0]-7e6)<Math.abs(S.sh_fo_val[A0]-7e6)?'시장 전체 보유액':'삼성+하이닉스 보유액';
  function shareChg(c){var a=S['s'+c+'_fo_shares'];return (a[iB]/a[A2]-1)*100;}
  function qtyChg(c){var a=S['s'+c+'_fo_shares'];return sumR('s'+c+'_net_foreign_qty',A2,iB)/a[A2]*100;}
  var w=0,wb=0;['005930','000660'].forEach(function(c){var vv=S['s'+c+'_fo_val'][A2];w+=shareChg(c)*vv;wb+=vv;});
  // 고점 이후 분해
  var dTot=sumR('fo_dH_total',iP,iB),nbP=sumR('fo_net_total',iP,iB),prP=sumR('fo_eff_price_total',iP,iB);
  var dSH=sumR('sh_dH',iP,iB),trSH=sumR('sh_eff_trade',iP,iB),prSH=sumR('sh_eff_price',iP,iB);
  var q=[
    ['① 지수 2,500일 때 외국인 700조',
     dyy(D[A0])+' 코스피 '+FMT.idx(S.idx_kospi[A0])+': 외국인 보유 코스피+코스닥 <b>'+J(S.fo_total[A0])+'</b>'+(f0?' (금감원 '+f0.d.slice(2,7).replace('-','.')+'말 '+J(f0.v)+')':'')+
     ' · 삼성+하이닉스 '+J(S.sh_fo_val[A0])+'<br>'+dyy(D[A1])+' 코스피 '+FMT.idx(S.idx_kospi[A1])+': 코스피+코스닥 <b>'+J(S.fo_total[A1])+'</b> · 삼성+하이닉스 '+J(S.sh_fo_val[A1])+
     '<br>→ 700조에 가까운 것은 <b>'+near+'</b>'],
    ['② 지수 3배 → 외국인 보유 2,000조',
     '코스피 '+FMT.idx(S.idx_kospi[A0])+' → '+FMT.idx(S.idx_kospi[iB])+' ('+mult(S.idx_kospi[A0],S.idx_kospi[iB])+') · 고점 '+FMT.idx(kP)+' ('+dyy(D[ikP])+', '+mult(S.idx_kospi[A0],kP)+')<br>'+
     '외국인 보유 코스피+코스닥 '+J(S.fo_total[A0])+' → <b>'+J(hB)+'</b> ('+mult(S.fo_total[A0],hB)+') · 고점 '+J(hP)+' ('+dyy(D[iP])+', '+mult(S.fo_total[A0],hP)+')'],
    ['③ 2026년 200조 매도 = 보유의 10%',
     dyy(D[A2])+' 이후 외국인 순매수 코스피 <b>'+sg(J,nbK)+'</b> · 코스닥 '+sg(J,nbQ)+' (합 '+sg(J,nb)+')<br>'+
     '÷ 연초 보유 '+J(hA)+' = <b>'+pc(nb/hA*100)+'</b> · ÷ 2026 고점 '+J(hP)+' = <b>'+pc(nb/hP*100)+'</b> · ÷ 현재 '+J(hB)+' = <b>'+pc(nb/hB*100)+'</b>'],
    ['④ 주가 효과를 뺀 실제 감축 (주식 수)',
     '외국인 보유주식 수 '+dyy(D[A2])+' → '+dyy(D[iB])+': 삼성전자 <b>'+pc(shareChg('005930'))+'</b> (장내 순매수 누적 '+pc(qtyChg('005930'))+') · SK하이닉스 <b>'+pc(shareChg('000660'))+'</b> (장내 '+pc(qtyChg('000660'))+')'+
     '<br>삼성+하이닉스 합산(연초 보유액 가중) <b>'+pc(w/wb)+'</b> · 코스피 외국인 비중 '+P(S.fo_pct_kospi[A2])+' → '+P(S.fo_pct_kospi[iB])],
    ['⑤ 고점 이후 보유액 감소의 정체',
     dyy(D[iP])+' → '+dyy(D[iB])+': 시장 전체 <b>'+sg(J,dTot)+'</b> = 순매수 '+sg(J,nbP)+' + 주가 <b>'+sg(J,prP)+'</b><br>'+
     '삼성+하이닉스 <b>'+sg(J,dSH)+'</b> = 매매(보유주식 수) '+sg(J,trSH)+' + 주가 <b>'+sg(J,prSH)+'</b>']
  ];
  h+=dt('vd','주장별 대조 ①~⑤','<div class="verdict">'+q.map(function(r){return '<div class="q">'+r[0]+'</div><div>'+r[1]+'</div>';}).join('')+'</div>');
  var cb=document.getElementById('claim-body');cb.innerHTML=h;
  Array.prototype.forEach.call(cb.querySelectorAll('details.claim-sub'),function(d){d.addEventListener('toggle',function(){try{localStorage.setItem('krflow.claim.'+d.dataset.k,d.open?'1':'0');}catch(e){}});});
}

// ---- 섹터 수급 탭 (네이버 업종 78개 × KRX 주체별) -----------------------------------
var SF=F.sector, SEC={inv:'foreign',sort:'trade',rows:20,pick:'',win:'5',minis:[],rank:null,det:null};
var INV_NAME={foreign:'외국인',inst:'기관',indiv:'개인'}, INV_COL={foreign:COL.foreign,inst:COL.inst,indiv:COL.indiv};
function eokF(v){return FMT.eok(v);}
function secSum(arr,a,b){var s=0;for(var i=a;i<=b;i++) if(arr[i]!=null) s+=arr[i];return s;}
function nlink(n,c){return '<a href="https://m.stock.naver.com/domestic/stock/'+c+'/total" target="_blank" rel="noopener">'+n+'</a>';}
function initSector(){
  if(!SF){document.getElementById('tab-sector').innerHTML='<section class="card"><div class="card-title">섹터 수급</div><div class="card-sub" style="margin-top:6px">KRX 종목별 투자자 데이터가 아직 없습니다(.env 의 KRX_ID/KRX_PW 필요).</div></section>';return;}
  var segs=[['sec-inv',[['foreign','외국인'],['inst','기관'],['indiv','개인']],'inv'],['sec-sort',[['trade','거래대금순'],['net','순매수순']],'sort'],['sec-rows',[[20,'상위 20'],[999,'전체 '+SF.n_sectors]],'rows']];
  segs.forEach(function(g){var box=document.getElementById(g[0]);g[1].forEach(function(o){var b=el('button',null,o[1]);b.type='button';
    b.onclick=function(){SEC[g[2]]=o[0];paintSegs();renderSector();};b.dataset.v=o[0];b.dataset.k=g[2];box.appendChild(b);});});
  var sel=document.getElementById('sec-pick');sel.innerHTML='<option value="">전체 (상위 12개)</option>'+SF.names.map(function(n){return '<option>'+n+'</option>';}).join('');
  sel.onchange=function(){SEC.pick=sel.value;renderDetail();};
  document.getElementById('sec-note').textContent='네이버 업종 '+SF.n_sectors+'개(기타 제외) · KRX 확정 · '+dyy(SF.first)+'~'+dyy(SF.last);
  paintSegs();renderLatest();
}
function paintSegs(){Array.prototype.forEach.call(document.querySelectorAll('#tab-sector .seg button'),function(b){b.classList.toggle('on',String(SEC[b.dataset.k])===b.dataset.v);});}
function renderLatest(){
  var L=SF.latest,h='<div class="sec3"><div class="h">주체</div><div class="h">거래액 섹션</div><div class="h">순매수 섹션</div><div class="h">순매도 섹션</div>';
  function cell(list,hd,signed){return '<div class="c" data-h="'+hd+'">'+(list.length?list.map(function(x){
    return '<div class="sx"><span class="sn">'+x[0]+'</span> '+(signed?sg(eokF,x[1]):eokF(x[1]))+'<ol>'+x[2].map(function(s){return '<li>'+nlink(s[0],s[1])+' '+(signed?sg(eokF,s[2]):eokF(s[2]))+(s[3]!=null?' ('+nf(s[3],1)+'%)':'')+'</li>';}).join('')+'</ol></div>';}).join(''):'–')+'</div>';}
  ['indiv','inst','foreign'].forEach(function(k){var r=L.inv[k];
    h+='<div class="who">'+INV_NAME[k]+'<small>'+sg(eokF,r.net)+' ('+eokF(r.trade)+')</small></div>'+cell(r.trade_secs,'거래액 섹션',false)+cell(r.buy_secs,'순매수 섹션',true)+cell(r.sell_secs,'순매도 섹션',true);});
  document.getElementById('sec-latest').innerHTML=h+'</div>';
  document.getElementById('sec-latest-sub').textContent=dlong(L.date)+' 확정 · KRX · 괄호는 업종 안 비중 · 종목명은 네이버 증권 링크';
}
function secOrder(){
  var a=W.i0,b=W.i1,inv=SEC.inv;
  var arr=SF.names.map(function(n){return {n:n,net:secSum(SF.net[inv][n],a,b),tr:secSum(SF.trade[n],a,b)};});
  arr.sort(SEC.sort==='net'?function(x,y){return y.net-x.net;}:function(x,y){return y.tr-x.tr;});
  return arr;
}
function heatCols(){
  var cols=[],span=W.i1-W.i0+1,any=SF.trade[SF.names[0]];
  if(span<=130){for(var i=W.i0;i<=W.i1;i++) if(any[i]!=null) cols.push({a:i,b:i,l:D[i]});return {cols:cols,weekly:false};}
  var cur=null;
  for(i=W.i0;i<=W.i1;i++){if(any[i]==null) continue;var d=new Date(D[i]+'T00:00:00Z'),wk=Math.floor((d.getTime()/864e5+3)/7);
    if(!cur||cur.wk!==wk){cur={a:i,b:i,wk:wk,l:D[i]};cols.push(cur);} else cur.b=i;}
  return {cols:cols,weekly:true};
}
function drawHeat(){
  var cv=document.getElementById('sec-heat'),box=cv.parentNode,inv=SEC.inv;if(!box.clientWidth) return;
  var ord=secOrder();if(SEC.sort==='net'&&SEC.rows<ord.length){ord=ord.slice(0,10).concat(ord.slice(-10));} else ord=ord.slice(0,SEC.rows);
  var hc=heatCols(),cols=hc.cols,narrow=box.clientWidth<560,LW=narrow?92:138,CH=narrow?14:16,TOP=4,BOT=20;
  var W2=box.clientWidth,H=TOP+ord.length*CH+BOT,dpr=window.devicePixelRatio||1;
  cv.width=W2*dpr;cv.height=H*dpr;cv.style.height=H+'px';var c=cv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,W2,H);
  var cw=(W2-LW)/Math.max(1,cols.length),vals=[],abs=[];
  ord.forEach(function(o,r){vals[r]=cols.map(function(cl){var v=0,has=false;for(var i=cl.a;i<=cl.b;i++){var x=SF.net[inv][o.n][i];if(x!=null){v+=x;has=true;}}if(has) abs.push(Math.abs(v));return has?v:null;});});
  abs.sort(function(a,b){return a-b;});var sc=abs.length?abs[Math.floor(abs.length*0.95)]||1:1;
  c.font='600 '+(narrow?10:11)+'px -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif';c.textBaseline='middle';
  ord.forEach(function(o,r){var y=TOP+r*CH;c.fillStyle=COL.dim;c.textAlign='right';
    var name=o.n;while(c.measureText(name).width>LW-8&&name.length>2) name=name.slice(0,-1);if(name!==o.n) name+='…';c.fillText(name,LW-6,y+CH/2);
    vals[r].forEach(function(v,j){if(v==null) return;var t=Math.min(1,Math.abs(v)/sc),a=0.08+0.92*Math.pow(t,0.7);
      c.fillStyle=v>=0?'rgba(248,113,113,'+a+')':'rgba(96,165,250,'+a+')';c.fillRect(LW+j*cw+0.5,y+0.5,Math.max(1,cw-1),CH-1);});});
  c.fillStyle=COL.muted;c.textAlign='center';c.font='10px -apple-system,sans-serif';
  var step=Math.max(1,Math.ceil(cols.length/(narrow?4:8)));
  for(var j=0;j<cols.length;j+=step){c.fillText(cols[j].l.slice(2).replace(/-/g,'.'),LW+j*cw+cw/2,H-BOT/2);}
  SEC.heat={ord:ord,cols:cols,vals:vals,LW:LW,CH:CH,TOP:TOP,cw:cw,weekly:hc.weekly};
  document.getElementById('sec-heat-sub').textContent=INV_NAME[inv]+' · '+(hc.weekly?'주 단위 합계':'일별')+' · 색 진하기 = 95% 분위 기준 · 억원';
  document.getElementById('sec-heat-note').textContent=SEC.sort==='net'&&SEC.rows<99?'· 기간 순매수 상위 10 / 하위 10':'· 기간 거래대금 순';
}
(function(){var cv=document.getElementById('sec-heat'),tip=document.getElementById('sec-tip');if(!cv) return;
  cv.addEventListener('mousemove',function(e){var H=SEC.heat;if(!H) return;var r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    var ri=Math.floor((y-H.TOP)/H.CH),ci=Math.floor((x-H.LW)/H.cw);
    if(ri<0||ri>=H.ord.length||ci<0||ci>=H.cols.length||x<H.LW){tip.hidden=true;return;}
    var v=H.vals[ri][ci],cl=H.cols[ci];tip.hidden=false;
    tip.innerHTML='<b>'+H.ord[ri].n+'</b><br>'+(H.weekly?dyy(D[cl.a])+'~'+dyy(D[cl.b]):dlong(D[cl.a]))+'<br>'+INV_NAME[SEC.inv]+' '+(v==null?'–':sg(eokF,v));
    var tx=Math.min(x+12,r.width-tip.offsetWidth-4);tip.style.left=tx+'px';tip.style.top=(y+14)+'px';});
  cv.addEventListener('mouseleave',function(){tip.hidden=true;});
  cv.addEventListener('click',function(){var H=SEC.heat,tipOn=!tip.hidden;if(!H||!tipOn) return;});
})();
function drawRank(){
  var ord=secOrder().slice();ord.sort(function(x,y){return y.net-x.net;});
  var pick=ord.slice(0,10).concat(ord.slice(-10).filter(function(o){return ord.indexOf(o)>=10;}));
  var labels=pick.map(function(o){return o.n;}),a=W.i0,b=W.i1;
  var ds=['foreign','inst','indiv'].map(function(k){return {label:INV_NAME[k],data:pick.map(function(o){return Math.round(secSum(SF.net[k][o.n],a,b));}),
    backgroundColor:INV_COL[k],borderRadius:2,barPercentage:.9,categoryPercentage:.8};});
  var cv=document.getElementById('sec-rank');cv.parentNode.style.height=(pick.length*34+40)+'px';
  if(SEC.rank) SEC.rank.destroy();
  SEC.rank=new Chart(cv,{type:'bar',data:{labels:labels,datasets:ds},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:false,
    plugins:{legend:{display:false},tooltip:{callbacks:{label:function(it){return ' '+it.dataset.label+' '+sg(eokF,it.raw);}}}},
    scales:{x:{grid:{color:function(c){return c.tick&&c.tick.value===0?COL.zero:COL.grid;}},ticks:{color:COL.muted,font:{size:10},callback:function(v){return TICK.eok(v);}}},
      y:{grid:{display:false},ticks:{color:COL.dim,font:{size:11}}}}}});
  document.getElementById('sec-rank-sub').textContent=INV_NAME[SEC.inv]+' 기간 순매수 상위 10·하위 10 섹터 · '+dyy(D[a])+'~'+dyy(D[b])+' · 막대는 세 주체 모두';
}
function cumArr(arr,a,b){var out=[],s=0;for(var i=a;i<=b;i++){if(arr[i]!=null) s+=arr[i];out.push(arr[i]==null&&i>lastNN(arr,a,b)?null:Math.round(s));}return out;}
function renderDetail(){
  var box=document.getElementById('sec-detail'),a=W.i0,b=W.i1;
  SEC.minis.forEach(function(ch){ch.destroy();});SEC.minis=[];if(SEC.det){SEC.det.destroy();SEC.det=null;}
  var lineDs=function(n){return ['foreign','inst','indiv'].map(function(k){return {label:INV_NAME[k],data:cumArr(SF.net[k][n],a,b),borderColor:INV_COL[k],backgroundColor:INV_COL[k],borderWidth:1.6,pointRadius:0,tension:0,spanGaps:true};});};
  var labels=D.slice(a,b+1);
  if(!SEC.pick){
    var ord=secOrder().sort(function(x,y){return y.tr-x.tr;}).slice(0,12);
    box.innerHTML='<div class="legend"><span><i style="background:var(--s-foreign)"></i>외국인</span><span><i style="background:var(--s-inst)"></i>기관</span><span><i style="background:var(--s-indiv)"></i>개인</span><span class="note">· 기간 누적 순매수 · 거래대금 상위 12 · 누르면 상세</span></div><div class="mini-grid">'+
      ord.map(function(o,i){return '<div class="mini" data-n="'+o.n+'"><div class="t">'+o.n+'</div><div class="v">외 '+sg(eokF,secSum(SF.net.foreign[o.n],a,b))+' · 기 '+sg(eokF,secSum(SF.net.inst[o.n],a,b))+' · 개 '+sg(eokF,secSum(SF.net.indiv[o.n],a,b))+'</div><div class="cb"><canvas id="mini'+i+'"></canvas></div></div>';}).join('')+'</div>';
    ord.forEach(function(o,i){SEC.minis.push(new Chart(document.getElementById('mini'+i),{type:'line',data:{labels:labels,datasets:lineDs(o.n)},
      options:{responsive:true,maintainAspectRatio:false,animation:false,events:[],plugins:{legend:{display:false},tooltip:{enabled:false}},
        scales:{x:{display:false},y:{display:false,grid:{display:false}}}}}));});
    Array.prototype.forEach.call(box.querySelectorAll('.mini'),function(m){m.onclick=function(){SEC.pick=m.dataset.n;document.getElementById('sec-pick').value=SEC.pick;renderDetail();};});
    return;
  }
  var n=SEC.pick,w=SEC.win,t=(SF.top[w]||{});
  var tb=function(k){var r=(t[k]||{})[n]||{buy:[],sell:[]};
    var row=function(x){return '<tr><td>'+nlink(x[0],x[1])+'</td><td class="'+cls(x[2])+'">'+sg(eokF,x[2])+'</td></tr>';};
    return '<div><h4>'+INV_NAME[k]+' 순매수</h4><table>'+(r.buy.map(row).join('')||'<tr><td>–</td></tr>')+'</table></div><div><h4>'+INV_NAME[k]+' 순매도</h4><table>'+(r.sell.map(row).join('')||'<tr><td>–</td></tr>')+'</table></div>';};
  box.innerHTML='<div class="legend"><span><i style="background:var(--s-foreign)"></i>외국인</span><span><i style="background:var(--s-inst)"></i>기관</span><span><i style="background:var(--s-indiv)"></i>개인</span><span class="note">· 누적 기준일 '+dyy(D[a])+'</span></div>'+
    '<div class="chart-box"><canvas id="sec-det"></canvas></div>'+
    '<div class="card-tools" style="margin-top:12px"><span class="sec-lbl">상위 종목</span><div class="seg" id="sec-win"></div></div><div class="top-tbl">'+tb(SEC.inv)+'</div>';
  var wb=document.getElementById('sec-win');[['1','최근일'],['5','5일'],['20','20일'],['60','60일']].forEach(function(o){var x=el('button',null,o[1]);x.type='button';if(o[0]===w) x.classList.add('on');x.onclick=function(){SEC.win=o[0];renderDetail();};wb.appendChild(x);});
  SEC.det=new Chart(document.getElementById('sec-det'),{type:'line',data:{labels:labels,datasets:lineDs(n)},options:{responsive:true,maintainAspectRatio:false,animation:false,
    interaction:{mode:'index',intersect:false},layout:{padding:{right:labelPad({series:[{name:'외국인'}]})}},
    plugins:{legend:{display:false},endLabels:{on:true},tooltip:{callbacks:{title:function(it){return it.length?dlong(it[0].label):'';},label:function(it){return ' '+it.dataset.label+' '+sg(eokF,it.raw);}}}},
    scales:{x:{grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:6,font:{size:12},callback:function(v){var s=this.getLabelForValue(v);return (b-a>140)?s.slice(2,7).replace('-','.'):dshort(s);}}},
      y:{beginAtZero:true,grid:{color:function(c){return c.tick&&c.tick.value===0?COL.zero:COL.grid;}},ticks:{color:COL.muted,font:{size:12},callback:function(v){return TICK.eok(v);}}}}}});
  document.getElementById('sec-detail-sub').textContent=n+' · 기간 누적 순매수(억원) · 상위 종목은 '+INV_NAME[SEC.inv]+' 기준';
}
function renderSector(){if(!SF||TAB!=='sector') return;drawHeat();drawRank();renderDetail();}
window.addEventListener('resize',function(){if(TAB==='sector') drawHeat();});

// ---- 탭 -------------------------------------------------------------------
var TAB=ls('tab')||'risk';
function setTab(t){
  TAB=t;ls('tab',t);
  document.getElementById('tab-market').hidden=t!=='market';
  document.getElementById('tab-foreign').hidden=t!=='foreign';
  var bbt=document.getElementById('tab-buyback');if(bbt) bbt.hidden=t!=='buyback';
  document.getElementById('tab-sector').hidden=t!=='sector';
  document.getElementById('tab-macro').hidden=t!=='macro';
  document.getElementById('tab-risk').hidden=t!=='risk';
  document.getElementById('tab-econ').hidden=t!=='econ';
  var FL=['market','foreign','sector','buyback'].indexOf(t)>=0;if(FL) ls('flowsub',t);
  document.querySelector('.range-bar').hidden=!FL||t==='buyback';document.getElementById('subnav-row').hidden=!FL;
  Array.prototype.forEach.call(document.querySelectorAll('#tabs .nav-link[data-top]'),function(b){var on=b.getAttribute('data-top')===(FL?'flow':t);b.classList.toggle('active',on);b.setAttribute('aria-selected',on);});
  if(t==='econ'&&window.ECON) window.ECON.show();
  if(t==='risk'&&window.RISK) window.RISK.show();
  if(t==='macro'&&window.MACRO) window.MACRO.show();
  if(t==='buyback'&&window.BUYBACK) window.BUYBACK.show();
  Array.prototype.forEach.call(document.querySelectorAll('#subtabs .nav-link[data-tab]'),function(b){var on=b.getAttribute('data-tab')===t;b.classList.toggle('active',on);b.setAttribute('aria-selected',on);});
  CARDS.forEach(function(c){if((c.p.tab||'market')===t&&c.chart) c.chart.resize();});
  if(t==='sector'){renderSector();setTimeout(renderSector,60);}
}
Array.prototype.forEach.call(document.querySelectorAll('#subtabs .nav-link[data-tab]'),function(b){b.onclick=function(){setTab(b.getAttribute('data-tab'));};});
Array.prototype.forEach.call(document.querySelectorAll('#tabs .nav-link[data-top]'),function(b){b.onclick=function(){var t=b.getAttribute('data-top');setTab(t==='flow'?(ls('flowsub')||'market'):t);};});

// ---- 기간 슬라이더 + 개요 스파크라인 --------------------------------------
var r0=document.getElementById('r0'),r1=document.getElementById('r1'),ov=document.getElementById('overview');
// 텍스트 날짜 → ISO. 2025-06-01 · 20250601 · 2025.6.1 · 25.06.01 · 250601 · 6/1(최근 연도)
function parseDate(t){
  t=(t||'').trim().replace(/\s/g,'');var m,y,mo,d;
  if((m=t.match(/^(\d{2})(\d{2})(\d{2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{4})[-./]?(\d{1,2})[-./]?(\d{1,2})$/))){y=+m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{2})[-./](\d{1,2})[-./](\d{1,2})$/))||(m=t.match(/^(\d{2})(\d{2})(\d{2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{1,2})[-./](\d{1,2})$/))){y=+D[N-1].slice(0,4);mo=+m[1];d=+m[2];
    var c=y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2);if(c>D[N-1]) y-=1;}
  else return null;
  if(mo<1||mo>12||d<1||d>31) return null;
  return y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2);
}
function idxAtOrBefore(s){for(var i=N-1;i>=0;i--) if(D[i]<=s) return i;return 0;}
function idxAtOrAfter(s){for(var i=0;i<N;i++) if(D[i]>=s) return i;return N-1;}
['d0','d1'].forEach(function(id,k){var inp=document.getElementById(id);
  inp.addEventListener('keydown',function(e){if(e.key!=='Enter') return;var iso=parseDate(inp.value);
    if(!iso){inp.classList.add('bad');return;} inp.classList.remove('bad');
    var a=W.i0,b=W.i1;if(k===0){a=idxAtOrAfter(iso);if(b-a<MINSPAN) b=Math.min(N-1,a+MINSPAN);}
    else{b=idxAtOrBefore(iso);if(b-a<MINSPAN) a=Math.max(0,b-MINSPAN);}
    setWindow(a,b,null);inp.blur();});
  inp.addEventListener('focus',function(){inp.select();});});
var PRESETS=[['1M',1],['3M',3],['6M',6],['1Y',12],['전체',0]];
var presetBox=document.getElementById('presets');
PRESETS.forEach(function(p){var b=el('button',null,p[0]);b.type='button';b.onclick=function(){setWindow(idxMonthsBack(p[1]),N-1,p[0]);};presetBox.appendChild(b);});
r0.max=r1.max=N-1;
var MINSPAN=5;
function onSlide(e){
  var a=+r0.value,b=+r1.value;
  if(b-a<MINSPAN){if(e&&e.target===r0) a=Math.max(0,b-MINSPAN);else b=Math.min(N-1,a+MINSPAN);}
  setWindow(a,b,null);
}
r0.addEventListener('input',onSlide);r1.addEventListener('input',onSlide);
var raf=0;
function setWindow(a,b,preset){
  W.i0=a;W.i1=b;r0.value=a;r1.value=b;
  Array.prototype.forEach.call(presetBox.children,function(btn,i){btn.classList.toggle('on',PRESETS[i][0]===preset);});
  if(preset) ls('preset',preset);else ls('preset','');
  document.getElementById('d0').value=D[a].replace(/-/g,'.');document.getElementById('d1').value=D[b].replace(/-/g,'.');
  document.getElementById('range-label').innerHTML='<span>'+(b-a+1)+'영업일</span>';
  // rAF 는 백그라운드 탭에서 멈추므로 타이머를 함께 건다(먼저 오는 쪽이 한 번만 그린다)
  if(raf) return;
  raf=1;
  var run=function(){if(!raf) return;raf=0;CARDS.forEach(updateCard);renderTiles();renderTiles2();drawOverview();renderSector();};
  requestAnimationFrame(run);setTimeout(run,80);
}
function drawOverview(){
  var w=ov.clientWidth,h=30,dpr=window.devicePixelRatio||1;if(!w) return;
  ov.width=w*dpr;ov.height=h*dpr;var c=ov.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.clearRect(0,0,w,h);
  var a=S.idx_kospi,mn=Infinity,mx=-Infinity,i;
  for(i=0;i<N;i++) if(a[i]!=null){mn=Math.min(mn,a[i]);mx=Math.max(mx,a[i]);}
  var pad=6,xs=function(i){return pad+(w-2*pad)*i/(N-1);},ys=function(v){return h-3-(h-8)*(v-mn)/((mx-mn)||1);};
  c.fillStyle='rgba(151,252,228,.05)';c.beginPath();c.roundRect?c.roundRect(0,0,w,h,8):c.rect(0,0,w,h);c.fill();
  c.fillStyle='rgba(151,252,228,.13)';c.fillRect(xs(W.i0),0,Math.max(2,xs(W.i1)-xs(W.i0)),h);
  c.strokeStyle='rgba(151,252,228,.55)';c.lineWidth=1.2;c.beginPath();var st=false;
  for(i=0;i<N;i++){if(a[i]==null) continue;var x=xs(i),y=ys(a[i]);if(!st){c.moveTo(x,y);st=true;}else c.lineTo(x,y);}
  c.stroke();
  var ax=document.getElementById('rng-axis');
  if(!ax.childElementCount){[0,Math.round(N/2),N-1].forEach(function(i){ax.appendChild(el('span',null,D[i].slice(0,7).replace('-','.')));});}
}
window.addEventListener('resize',function(){drawOverview();});

// ---- 헤더: 출처별 기준일 칩 + 갱신 멈춤 경고 ------------------------------
var HOLS={};(HOL.holidays||[]).forEach(function(d){HOLS[d]=1;});
function iso(d){return d.toISOString().slice(0,10);}
function isB(s){var d=new Date(s+'T00:00:00Z'),w=d.getUTCDay();return w>0&&w<6&&!HOLS[s];}
function prevB(s){var d=new Date(s+'T00:00:00Z');do{d.setUTCDate(d.getUTCDate()-1);}while(!isB(iso(d)));return iso(d);}
function onOrBefore(s){return isB(s)?s:prevB(s);}
(function(){
  var kst=new Date(Date.now()+9*3600e3),today=iso(kst),hm=kst.getUTCHours()*60+kst.getUTCMinutes();
  var expFlow=(isB(today)&&hm>=16*60)?today:(isB(today)?prevB(today):onOrBefore(today));
  var expCredit=isB(today)?prevB(today):prevB(onOrBefore(today));
  var A=F.asof,chips=[];
  function chip(name,a,exp){
    var d=a.date,prov=d&&(a.prov||[]).indexOf(d)>=0,wait=d&&d<exp;
    return '<span class="chip'+(prov?' prov':'')+(wait?' wait':'')+'"><i></i>'+name+' '+(d?dshort(d):'–')+(prov?' 잠정':(wait?' · '+dshort(exp)+'분 대기':''))+'</span>';
  }
  chips.push(chip('수급·선물',A.investor,expFlow));
  chips.push(chip('신용·예탁금',A.credit,expCredit));
  if(A.mcap&&A.mcap.date) chips.push(chip('KRX 시총',A.mcap,expCredit));
  var fl=(F.holdings&&F.holdings.fss)||[];
  if(fl.length){var m=fl[fl.length-1].month;chips.push('<span class="chip"><i></i>금감원 '+m.slice(2).replace('-','.')+'월말</span>');}
  document.getElementById('chips').innerHTML=chips.join('');
  document.getElementById('gen').textContent='생성 '+F.generated_at.slice(0,16).replace('T',' ')+' KST';
  var late=[];
  if(A.investor.date&&A.investor.date<prevB(expFlow)) late.push('수급·선물('+A.investor.date+')');
  if(A.credit.date&&A.credit.date<prevB(expCredit)) late.push('신용·예탁금('+A.credit.date+')');
  if(late.length){var s=document.getElementById('stale');s.hidden=false;
    s.innerHTML='<span>⚠︎</span><span>자동 갱신이 멈췄을 수 있습니다 — '+late.join(', ')+' 이후 값이 없습니다. 맥미니 launchd 작업(com.pjy.kr-flow-dashboard)과 logs/ 를 확인하세요.</span>';}
})();

// ---- 시작 ---------------------------------------------------------------
PANELS.forEach(buildCard);
renderClaim();
initSector();
setTab(['market','foreign','sector','risk','econ','macro'].indexOf(TAB)>=0?TAB:'risk');
var pre=ls('preset');var P=PRESETS.filter(function(p){return p[0]===pre;})[0]||PRESETS[2];  // 기본 6M(Jae 10/19)
setWindow(idxMonthsBack(P[1]),N-1,P[0]);
})();
"""

HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<meta name="theme-color" content="#061E20" />
<title>리스크·매크로·수급</title>
<meta name="description" content="신용거래융자·투자자예탁금·반대매매·외국인 코스피200 선물·코스피/코스닥 투자자별 순매수를 매일 자동 갱신하는 대시보드." />
<style>__CSS__</style>
</head>
<body>
<div class="container">
<header>
  <div class="brand"><span class="logo-dot" aria-hidden="true"></span>
    <div><h1>리스크 · 매크로 · 수급</h1><div class="sub">회사채·데이터센터 채권 · 경제지표 · 미 금리·텀프리미엄·BEI · 국내 수급</div></div></div>
  <div class="stamp"><div id="gen"></div><div class="chips" id="chips"></div></div>
</header>
<div class="stale" id="stale" hidden></div>
<div class="top-nav-row"><nav class="top-nav" id="tabs" aria-label="보기 전환">
  <button class="nav-link" data-top="risk" type="button">리스크</button>
  <button class="nav-link" data-top="flow" type="button">수급</button>
  <button class="nav-link" data-top="macro" type="button">매크로</button>
  <button class="nav-link" data-top="econ" type="button">경제지표</button>
</nav></div>
<div class="top-nav-row" id="subnav-row" hidden><nav class="top-nav sub-nav" id="subtabs" aria-label="수급 보기">
  <button class="nav-link active" data-tab="market" type="button">시장 수급</button>
  <button class="nav-link" data-tab="buyback" type="button">자사주 매입</button>
  <button class="nav-link" data-tab="foreign" type="button">외국인 보유 · 삼성/하이닉스</button>
  <button class="nav-link" data-tab="sector" type="button">섹터 수급</button>
  <a class="nav-link" href="sector.html">섹터 일·주간 ↗</a>
</nav></div>

<div class="range-bar"><div class="range-inner">
  <div class="range-top">
    <div class="seg" id="presets" aria-label="기간 프리셋"></div>
    <div class="range-dates"><input id="d0" class="dinp" inputmode="numeric" aria-label="시작일 입력" title="날짜 입력 후 Enter (예: 2025-06-01, 250601, 6/1)">
      <span>~</span><input id="d1" class="dinp" inputmode="numeric" aria-label="종료일 입력" title="날짜 입력 후 Enter">
      <div class="range-label" id="range-label"></div></div>
  </div>
  <div class="rng">
    <canvas id="overview" aria-hidden="true"></canvas>
    <input type="range" id="r0" min="0" step="1" aria-label="시작일" />
    <input type="range" id="r1" min="0" step="1" aria-label="종료일" />
    <div class="rng-axis" id="rng-axis"></div>
  </div>
</div></div>

__MACROHTML__
<div id="tab-market">
<div class="tiles" id="tiles"></div>
<div class="grid" id="grid"></div>
</div>
__BBHTML__
<div id="tab-foreign" hidden>
<div id="grid2top" class="grid2top"></div>
<section class="card claim" id="claim">
  <div class="card-head"><div><div class="card-title">주장 검증 — "지수 2,500 때 외국인 700조 → 3배 → 2026년 200조 매도는 10%"</div>
  <div class="card-sub">고정 기준일 비교(위 기간 바와 무관) · 매일 자동 재계산 · 시장 전체는 금투협 일별 실측, 삼성전자는 보통주</div></div></div>
  <div id="claim-body"></div>
</section>
<div class="tiles" id="tiles2"></div>
<div class="grid" id="grid2"></div>
</div>
<div id="tab-sector" hidden>
<div class="sec-bar"><span class="sec-lbl">주체</span><div class="seg" id="sec-inv"></div>
  <span class="sec-note" id="sec-note"></span></div>
<section class="card" id="sec-latest-card"><div class="card-head"><div><div class="card-title">섹션별 수급</div>
  <div class="card-sub" id="sec-latest-sub"></div></div></div><div id="sec-latest"></div></section>
<section class="card" id="sec-heat-card"><div class="card-head"><div><div class="card-title">섹터 × 날짜 순매수 히트맵</div>
  <div class="card-sub" id="sec-heat-sub"></div></div>
  <div class="card-tools"><div class="seg" id="sec-sort"></div><div class="seg" id="sec-rows"></div></div></div>
  <div class="legend"><span><i style="background:var(--up)"></i> 순매수</span><span><i style="background:var(--down)"></i> 순매도</span><span class="note" id="sec-heat-note"></span></div>
  <div class="heat-box"><canvas id="sec-heat"></canvas><div class="heat-tip" id="sec-tip" hidden></div></div></section>
<div class="grid">
<section class="card" id="sec-rank-card"><div class="card-head"><div><div class="card-title">기간 누적 순매수 — 섹터 순위</div>
  <div class="card-sub" id="sec-rank-sub"></div></div></div>
  <div class="legend"><span><i style="background:var(--s-foreign)"></i>외국인</span><span><i style="background:var(--s-inst)"></i>기관</span><span><i style="background:var(--s-indiv)"></i>개인</span></div>
  <div class="rank-box"><canvas id="sec-rank"></canvas></div></section>
<section class="card" id="sec-detail-card"><div class="card-head"><div><div class="card-title">섹터 상세</div>
  <div class="card-sub" id="sec-detail-sub">섹터를 고르면 그 섹터만, 안 고르면 거래대금 상위 12개를 한꺼번에</div></div>
  <div class="card-tools"><select id="sec-pick" class="sec-pick"></select></div></div>
  <div id="sec-detail"></div></section>
</div>
</div>

<footer>
  <div class="foot-h">출처 · 갱신</div>
  <ul>
    <li><b>신용거래융자·투자자예탁금·미수금·반대매매</b> — 금융투자협회 <a href="https://freesis.kofia.or.kr/" rel="noopener">FreeSIS</a>. 기준일 T의 값은 <b>다음 영업일(T+1)</b>에 공표돼 다른 항목보다 하루 늦다.</li>
    <li><b>투자자별 순매수·코스피200 선물·지수</b> — 다음 금융(원천 KRX). 장 마감 10분 뒤 <b>잠정치</b>를 받고, 18:30 이후 다시 받아 <b>확정치</b>로 덮어쓴다.</li>
    <li>맥미니 launchd 가 10분마다 '새 값이 나올 차례인 출처'만 확인하고, 값이 바뀌었을 때만 이 페이지를 다시 굽는다. 매일 아침 최근 15일을 다시 받아 출처의 정정분도 반영한다.</li>
    <li><b>매크로 탭</b> — 미 재무부 명목·실질 커브(BEI = 명목 − 실질), NY Fed ACM 텀프리미엄(1영업일 지연), Yahoo(Brent BZ=F·원/달러 KRW=X 일봉), Kalshi 연준 결정 시장, CNBC 시세(타일의 '실시간' 줄만, 비공식). 날짜축은 미 채권시장 영업일이고, 코스피 겹치기는 그 날짜 이전 마지막 국내 종가. 1년 백분위는 최근 252개 관측치 기준. 색 신호는 일부러 끄고 회색으로 둔다(기준은 직접 정함).</li>
  </ul>
  <div class="foot-h">지표 정의</div>
  <ul>
    <li><b>누적</b> 보기는 위 기간 바의 <b>시작일부터</b> 일별 순매수를 더한 값이다(기간을 바꾸면 기준점이 바뀐다).</li>
    <li><b>외국인 선물</b> — 코스피200 선물 전 월물 합계 순매수(계약). 롤오버 주간에도 근월물만 보는 왜곡이 없다. 미결제약정은 상장 월물 전부의 합.</li>
    <li><b>외국인</b> 현물은 KRX '외국인' 구분(기타외국인 제외). <b>기관</b> = 금융투자+보험+투신+사모+은행+기타금융+연기금.</li>
    <li><b>신용융자</b> = 신용거래융자(대주 제외). 신용÷예탁금 = 신용거래융자 합계 ÷ 투자자예탁금.</li>
  </ul>
  <div class="foot-h">외국인 보유 탭</div>
  <ul>
    <li><b>시장 전체 외국인 보유액</b> = 금투협 FreeSIS '증시동향'의 외국인 보유 시가총액(코스피·코스닥, KRX 원천, 일별 실측). 금감원 월말 값은 결제 기준이고 분모가 달라 참고점으로만 표시한다.</li>
    <li><b>종목 외국인 보유액</b> = 외국인 보유주식 수(다음 금융, KRX 외국인 보유 기준) × KRX 종가. <b>삼성전자는 보통주만</b>(우선주 제외).</li>
    <li><b>보유액 변화 분해</b> — 종목: 매매 = 보유주식 수 변화 × 주가, 주가 = 전일 보유주식 수 × 주가 변화(정확히 더해짐). 시장 전체: 매매 = 외국인 순매수(코스피+코스닥), 주가 = 보유액 변화 − 순매수(잔차, 집계 기준 차이 포함).</li>
    <li><b>보유주식 수에는 장외 이동·DR 예탁이 포함</b>된다. 예: SK하이닉스 2026-07-16 외국인 보유 +1,823만주(장내 순매수 −47만주) — 7월 미국 ADR 상장 예탁분. 그래서 하이닉스는 '보유주식 수 변화'와 '장내 순매수 누적'이 다르다.</li>
    <li><b>시총·비중</b> — 종목 시총은 KRX Open API(기준일 다음 날 오전 공개, 최신일은 종가×상장주식수), 코스피 시총은 금투협.</li>
    <li><b>종목 투자자별 순매수 금액</b> = 순매수 수량(네이버) × 그날 평균 체결가(다음, 거래대금÷거래량) — 추정치.</li>
  </ul>
</footer>
</div>
<script>window.__FLOWS__ = __DATA__; window.__HOL__ = __HOLDATA__;</script>
<script>__CHARTJS__</script>
<script>__APP__</script>
<script>window.__MACRO__ = __MACRODATA__;</script>
<script>__MACROJS__</script>
<script>__FSJS__</script>
<script>__ECONJS__</script>
<script>window.__RISK__ = __RISKDATA__;</script>
<script>__RISKJS__</script>
<script>window.__SEIBRO__ = __SEIBRODATA__;</script>
<script>__SEIBROJS__</script>
<script>window.__BUYBACK__ = __BBDATA__;</script>
<script>window.__SLONG__ = __SLDATA__;</script>
<script>__SLJS__</script>
<script>__BBJS__</script>
</body>
</html>
"""


def build(flows: dict, hol: dict) -> str:
    return (HTML.replace("__CSS__", CSS + render_macro.MACRO_CSS + render_buyback.BB_CSS)
            .replace("__BBHTML__", render_buyback.BB_HTML)
            .replace("__BBDATA__", js_safe_json(json.loads(render_buyback.bb_data_json())))
            .replace("__BBJS__", script_safe(render_buyback.BB_JS))
            .replace("__SLDATA__", js_safe_json(json.loads(render_shlong.sl_data_json())))
            .replace("__SLJS__", script_safe(render_shlong.SL_JS))
            .replace("__MACROHTML__", render_macro.macro_html())
            .replace("__DATA__", js_safe_json(flows))
            .replace("__HOLDATA__", js_safe_json({"holidays": hol["holidays"]}))
            .replace("__CHARTJS__", script_safe(VENDOR_PATH.read_text(encoding="utf-8")))
            .replace("__APP__", script_safe(JS))
            .replace("__MACRODATA__", js_safe_json(json.loads(render_macro.macro_data_json())))
            .replace("__MACROJS__", script_safe(render_macro.MACRO_JS))
            .replace("__FSJS__", script_safe(render_macro.FS_JS))
            .replace("__ECONJS__", script_safe(render_macro.ECON_JS))
            .replace("__RISKDATA__", js_safe_json(json.loads(render_macro.risk_data_json())))
            .replace("__RISKJS__", script_safe(render_macro.RISK_JS))
            .replace("__SEIBRODATA__", js_safe_json(json.loads(render_macro.seibro_data_json())))
            .replace("__SEIBROJS__", script_safe(render_macro.SEIBRO_JS)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT_PATH))
    ap.add_argument("--docs", action="store_true")
    a = ap.parse_args()
    if not DATA_PATH.exists():
        print("[render] data/flows.json 이 없다 — build_data.py 를 먼저 실행하라.", file=sys.stderr)
        return 1
    flows = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    hol = json.loads(HOL_PATH.read_text(encoding="utf-8"))
    html = build(flows, hol)
    targets = [Path(a.out)] + ([DOCS_PATH] if a.docs else [])
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        tmp = t.with_suffix(".tmp")
        tmp.write_text(html, encoding="utf-8")
        tmp.replace(t)
        print(f"[render] {t} ({len(html)/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
