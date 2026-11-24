# -*- coding: utf-8 -*-
"""analysis.json (+ kr.json 한국어 요약) → fedspeak.html (단독 페이지, 데이터 내장)

  python -X utf8 build_dashboard.py

화면 규칙(Jae 11/23): 흰 배경 · 10 = 매파(진한 빨강), 5 = 중도, 0 = 비둘기파(진한 파랑) · 소수 첫째 자리
 · 그룹별 글자색 · 범례를 눌러 선을 끄면 축이 남은 선에 맞춰짐 · 변곡 로그·하우스 콜·원장은 기본 접힘.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[2] / "data" / "fedspeak"  # 원장·덮어쓰기·요약(리포에 커밋)
REPO = Path(__file__).resolve().parents[2]

TEMPLATE = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>금리 발언 tracker</title>
<meta name="claude:viewport-fit-sides" content="cover">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--text:#0b0b0b;--text-dim:#3f3e3b;--text-muted:#6f6e69;--line:rgba(0,0,0,.13);--hl:#0b0b0b;
 --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;
 --g-board:#5b3fb5;--g-v26:#0b7a3e;--g-v27:#b35c00;--g-nv:#6f6e69;--g-political:#b0307a;--g-investor:#00707d;--g-sellside:#8a6d00}
*{box-sizing:border-box}body{margin:0;background:#fff;color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;font-size:13px;line-height:1.55}
.wrap{max-width:1240px;margin:0 auto;padding-block:18px 60px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
body::before{content:"";position:fixed;inset:0 0 auto;height:env(safe-area-inset-top,0px);z-index:30;background:#fff}
h1{font-size:19px;margin:0 0 2px;letter-spacing:-.02em}h2{font-size:15px;margin:0 0 4px}.sub{color:var(--text-dim);font-size:12px}.intro{font-size:13px;margin:2px 0 3px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-top:14px}
.note{color:var(--text-muted);font-size:11.5px;margin:2px 0 8px}
.guide{background:#faf9f6}.guide ul{margin:6px 0 0 18px;padding:0}.guide li{margin:3px 0;color:var(--text-dim)}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;margin-top:12px}
.tile{background:#fff;border:1px solid var(--line);border-radius:12px;padding:11px 13px}
.tile .k{font-size:11.5px;color:var(--text-muted)}.tile .v{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.02em}.tile .v.sm{font-size:17px;line-height:36px}.tile .d{font-size:11.5px;color:var(--text-dim);font-variant-numeric:tabular-nums}
.row{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:6px 0}
.btn{padding:3px 11px;border-radius:999px;font-size:11.5px;color:var(--text-dim);background:rgba(0,0,0,.03);border:1px solid var(--line);cursor:pointer;font-family:inherit}
.btn.on{color:#fff;background:var(--hl);border-color:var(--hl);font-weight:700}
.lg{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;color:var(--text);margin-right:4px;padding:2px 8px;border:1px solid var(--line);border-radius:999px;cursor:pointer;user-select:none}
.lg i{width:14px;height:3px;border-radius:2px;display:inline-block}.lg.sq i{width:9px;height:9px}
.lg.off{opacity:.38;text-decoration:line-through}
.lgsep{font-size:11px;color:var(--text-muted);margin:0 4px 0 8px}
.ch{position:relative;height:320px}.ch.s{height:180px}
select{background:#fff;color:var(--text);border:1px solid rgba(0,0,0,.25);border-radius:8px;padding:4px 8px;font:inherit;font-size:12px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}
th{font-size:11.5px;color:var(--text-dim);font-weight:700;text-align:right;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
th small{display:block;font-weight:500;color:var(--text-muted);font-size:10.5px}
td{padding:5px 8px;border-bottom:1px solid rgba(0,0,0,.07);text-align:right;font-size:12px}
td:first-child,th:first-child{text-align:left;white-space:nowrap}.dim{color:var(--text-muted)}.lo{opacity:.5}
.hm{overflow-x:auto}.hm table{width:auto;min-width:100%}.hm td{padding:0;border:none}
.hm td.nm{padding:2px 8px 2px 0;font-size:12px;font-weight:700;line-height:1.2;max-width:132px;min-width:104px;white-space:normal;word-break:keep-all}.hm td.nm small{display:block;color:var(--text-muted);font-weight:400;font-size:10.5px}
.hm td.c{width:22px;min-width:22px;height:21px;border:1px solid #fff;border-radius:4px;cursor:pointer;text-align:center;font-size:8.5px;font-weight:700;letter-spacing:-.03em}
.hm td.c.e{background:#f6f5f2;cursor:default}.hm td.c.n{background:#fff;border:1px dashed #b9b8b3;color:#6f6e69}
.hm th{padding:2px 0;text-align:left;font-size:10px;font-weight:500;color:var(--text-muted);border:none}
.hm td.lv{padding-left:10px;font-weight:700}.hm tr.g td{padding-top:10px;font-size:11.5px;font-weight:700}
.chip{display:inline-block;min-width:34px;text-align:center;padding:1px 7px;border-radius:999px;font-size:11.5px;font-weight:700}
.item{padding:9px 0;border-bottom:1px solid rgba(0,0,0,.07)}.item .h{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.item .who{font-weight:700}.item .q{color:var(--text-dim);font-size:12px;margin-top:3px;border-left:2px solid var(--line);padding-left:8px}
.item .s{margin-top:3px}.tag{font-size:10.5px;color:var(--text-muted);border:1px solid var(--line);border-radius:6px;padding:0 5px}
.gtag{font-size:10.5px;border:1px solid currentColor;border-radius:6px;padding:0 5px;font-weight:700}
a{color:#1c5cab;text-decoration:none}a:hover{text-decoration:underline}
details>summary{cursor:pointer;font-weight:700;font-size:15px}details>summary small{font-weight:400;color:var(--text-muted);font-size:11.5px;margin-left:6px}
details.in>summary{font-size:12.5px;color:var(--text-dim)}
.scale{display:inline-flex;align-items:center;gap:4px;font-size:11px;color:var(--text-muted)}.scale i{width:18px;height:10px;border-radius:3px;display:inline-block}
.lgx{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:8px 16px;margin-top:10px}.lgx div{font-size:12px;color:var(--text-dim);line-height:1.5}.lgx b{color:var(--text)}.lgx i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px;vertical-align:-1px}
.range-bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;margin:14px -8px 0;padding:8px 8px 6px;background:linear-gradient(180deg,rgba(255,255,255,.97) 75%,rgba(255,255,255,0));backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px)}
.range-inner{background:#fff;border:1px solid var(--line);border-radius:16px;padding:10px 14px 8px;box-shadow:0 2px 10px rgba(0,0,0,.05)}
.range-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap}
.seg{display:inline-flex;gap:3px;background:rgba(0,0,0,.03);border:1px solid var(--line);border-radius:999px;padding:3px}
.seg button{padding:4px 11px;border-radius:999px;font-size:12px;font-weight:500;color:var(--text-dim);background:none;border:none;font-family:inherit;cursor:pointer;white-space:nowrap}
.seg button.on{color:#fff;background:var(--hl);font-weight:700}
.range-dates{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.range-dates>span{color:var(--text-muted);font-size:12px}
.dinp{width:96px;background:#fff;color:var(--text);border:1px solid rgba(0,0,0,.25);border-radius:8px;padding:4px 7px;font:inherit;font-size:12px;font-variant-numeric:tabular-nums;text-align:center}
.dinp:focus{outline:none;border-color:#0b0b0b}.dinp.bad{border-color:#d03b3b}
.range-label{font-size:12px;color:var(--text-muted);font-variant-numeric:tabular-nums}
.rng{position:relative;height:42px;margin-top:6px}
.rng canvas{position:absolute;left:0;right:0;top:0;width:100%;height:30px;display:block}
.rng input{position:absolute;left:0;right:0;top:0;width:100%;height:30px;margin:0;background:none;-webkit-appearance:none;appearance:none;pointer-events:none}
.rng input::-webkit-slider-runnable-track{height:30px;background:none}.rng input::-moz-range-track{height:30px;background:none}
.rng input::-webkit-slider-thumb{-webkit-appearance:none;pointer-events:auto;width:12px;height:30px;border-radius:5px;background:#0b0b0b;border:2px solid #fff;box-shadow:0 0 6px rgba(0,0,0,.35);cursor:ew-resize}
.rng input::-moz-range-thumb{pointer-events:auto;width:10px;height:28px;border-radius:5px;background:#0b0b0b;border:2px solid #fff;cursor:ew-resize}
.rng-axis{position:absolute;left:0;right:0;top:31px;display:flex;justify-content:space-between;font-size:9.5px;color:var(--text-muted);font-variant-numeric:tabular-nums;pointer-events:none}
@media(max-width:640px){.ch{height:260px}.tile .v{font-size:20px}}
</style></head><body><div class="wrap">
<h1>금리 발언 tracker</h1>
<div class="intro">2026년 1월 이후 Fed 의장 · 대통령 · 재무장관 · Fed 위원 · 셀사이드 · 투자자의 발언을 종합. 전문은 아래 발언 원장 참고.</div>
<div class="sub" id="hdr"></div>

<div class="card guide"><h2>읽는 법</h2>
<ul>
<li><b>점수는 0~10.</b> 10에 가까울수록 매파(금리를 올리자), 0에 가까울수록 비둘기파(금리를 내리자), 5가 중도. 발언 하나는 0 / 2.5 / 5 / 7.5 / 10 다섯 단계로만 매기고, 인물 수준과 지수는 그 평균이라 소수가 나옴.</li>
<li><b>색.</b> 빨강이 진할수록 매파, 파랑이 진할수록 비둘기파, 회색이 중도.
 <span class="scale" style="margin-left:6px">0 <i style="background:#0d366b"></i><i style="background:#7f93ac"></i><i style="background:#f0efec;border:1px solid #d5d4cf"></i><i style="background:#c38280"></i><i style="background:#961414"></i> 10</span></li>
<li><b>인물 수준</b> = 그 사람의 발언 점수를 최근 것일수록 크게 쳐서 낸 평균(30일 지나면 절반 무게). 새 발언이 없으면 마지막 값을 유지함.</li>
<li><b>글자색 = 그룹.</b> <span id="glegend"></span></li>
<li><b>범례를 누르면 그 선이 꺼짐.</b> 선이 줄면 세로축이 남은 선에 맞춰 자동으로 좁아짐. 금리·주가 같은 비교 지표는 켤 때마다 오른쪽에 자기 축이 따로 생김.</li>
<li><b>넣은 기준.</b> 인용 문장이 출처 페이지에 글자 그대로 있는 발언만 넣음. 드러켄밀러는 Jae 노션 아카이브가 원장임. 변곡 로그·하우스 콜·발언 원장은 맨 아래에 접혀 있음.</li>
<li><b>기간 막대.</b> 아래 막대의 양쪽 손잡이를 끌거나 날짜를 직접 넣으면 숫자 타일·차트·히트맵·목록이 그 기간으로 바뀜. 타일은 기간의 끝 날짜 기준이고, 백테스트 표도 그 기간 발언만으로 다시 계산함(주간 동행·선후행만 전체 기간 고정).</li>
</ul></div>

<div class="range-bar"><div class="range-inner">
  <div class="range-top">
    <div class="seg" id="presets" aria-label="기간 프리셋"></div>
    <div class="range-dates"><input id="d0" class="dinp" inputmode="numeric" aria-label="시작일 입력" title="날짜 입력 후 Enter (예: 2026-06-01, 260601, 6/1)">
      <span>~</span><input id="d1" class="dinp" inputmode="numeric" aria-label="종료일 입력" title="날짜 입력 후 Enter">
      <div class="range-label" id="range-label"></div></div>
  </div>
  <div class="rng">
    <canvas id="overview" aria-hidden="true"></canvas>
    <input type="range" id="r0" min="0" step="1" aria-label="시작일">
    <input type="range" id="r1" min="0" step="1" aria-label="종료일">
    <div class="rng-axis" id="rng-axis"></div>
  </div>
</div></div>

<div class="tiles" id="tiles"></div>

<div class="card"><h2>톤 지수와 시장 가격</h2>
<div class="note">왼쪽 축 = 톤(0~10). 세로 점선 = FOMC 결정일. 「FOMC 블랙아웃 구간」을 켜면 위원들이 공개 발언을 못 하는 기간(회의 전 두 번째 토요일 ~ 회의 다음 날)이 보라색 실선·음영으로 표시됨. 비교 지표는 꺼진 것을 누르면 켜지고, 각자 오른쪽에 자기 축을 씀.</div>
<details class="in" style="margin:0 0 6px"><summary>톤 지수는 이렇게 계산함</summary><div style="color:var(--text-dim);font-size:12px;line-height:1.6;margin-top:4px">① 발언 하나의 점수: 0(곧 인하 필요) / 2.5 / 5(동결·양쪽 위험) / 7.5 / 10(곧 인상 필요·인상 소수의견) 다섯 단계. 금리 의견이 없는 발언은 점수 없음.<br>② 인물 수준: 그날까지 그 사람이 한 발언 점수의 가중 평균. 가중치는 발언이 오래될수록 줄어서 30일 전 발언은 오늘 발언의 절반, 60일 전은 4분의 1 무게(반감기 30일). 같은 날 여러 발언은 먼저 평균. 새 발언이 없으면 값이 그대로 유지됨(그래서 계단 모양).<br>③ 묶음 지수: 그날 재임 중이고 발언이 한 번이라도 확인된 사람들의 인물 수준을 단순 평균(사람마다 1표). 2026 투표권자 = 이사 7명 + 뉴욕·클리블랜드·필라델피아·댈러스·미니애폴리스(마이런은 5/15까지, 워시는 5/22부터). 2027 투표권자 = 이사 + 뉴욕·시카고·리치먼드·애틀랜타·샌프란시스코.<br>④ 의장 선: 5/15까지 파월, 5/22부터 워시의 인물 수준. 트럼프·베센트 선: 두 사람 인물 수준의 평균(연준이 어떻게 해야 한다고 말했는지 기준).<br>⑤ 전일 평균이 아님: 매일 다시 계산하지만, 그날 새 발언이 없으면 수준은 바뀌지 않음.</div></details>
<div class="row"><span class="dim" style="font-size:11.5px">계산 방식:</span><div class="seg" id="tmode"><button type="button" data-t="decay" class="on">반감기 30일 가중(기본)</button><button type="button" data-t="last">최근 발언만</button></div></div>
<div class="row" id="lg1"></div>
<div class="row"><span class="dim" style="font-size:11.5px">인물 선 추가:</span><select id="psel"></select></div>
<div class="ch"><canvas id="c1"></canvas></div>
</div>

<div class="card"><details id="d-hm"><summary>누가 언제 어떤 톤이었나<small>그룹 이름을 누르면 펼쳐짐</small></summary>
<div class="note">칸 = 그 주 발언의 평균 점수(칸 안 숫자 = 평균 점수 0~10, 색이 진할수록 강함. 발언 건수는 칸에 마우스를 올리면 보임). 점선 칸 = 금리 언급 없는 발언(신용·AI만). 빈 칸 = 확인된 발언 없음. 칸을 누르면 맨 아래 원장이 그 인물·그 주로 걸러져 열림. 맨 오른쪽 = 현재 수준.</div>
<div class="hm" id="hm"></div></details></div>

<div class="card"><details id="d-bt"><summary>백테스트: 누구 발언에 시장이 같이 움직였나</summary>
<div class="note" id="btnote"></div>
<div class="row"><span class="btn on" data-bt="clean">지표 발표일·FOMC일 제외</span><span class="btn" data-bt="all">전체</span></div>
<div class="note" style="margin:0 0 6px">열 제목을 누르면 그 열 기준으로 높은 순 정렬(한 번 더 누르면 낮은 순). 기본은 방향 적중 높은 순.</div>
<div style="overflow-x:auto"><table id="bt"></table></div>
<details class="in" style="margin-top:8px"><summary>열 설명 보기</summary><ul style="margin:6px 0 0 18px;padding:0;color:var(--text-dim);font-size:12px;line-height:1.6"><li><b>발언 수</b>: 이 기간 점수가 붙은 발언 수. 「지표 발표일·FOMC일 제외」면 CPI·고용 등 발표일과 FOMC 결정일 발언을 뺀 수(의장 기자회견은 남김). 10건 미만은 흐리게.</li><li><b>평균 점수</b>: 그 사람 발언 점수의 단순 평균(0 비둘기파 ~ 10 매파).</li><li><b>서프라이즈</b>: 그날 발언 점수 − 그 사람의 직전 수준. +면 "평소보다 매파적으로 말한 날".</li><li><b>서프라이즈 ↔ 금리 기대(당일·2일)</b>: 서프라이즈와 같은 날(또는 전날~다음 날 2일) 연방기금 선물 27년 1월물 금리 변화의 순위상관 ρ. +1에 가까울수록 "평소보다 매파적으로 말하면 금리 기대가 올랐다". 굵게 = p&lt;0.1.</li><li><b>서프라이즈 ↔ 2년물</b>: 같은 계산을 미 2년물 금리 변화로.</li><li><b>점수 ↔ 금리 기대</b>: 서프라이즈가 아니라 점수 자체와 금리 기대 변화의 순위상관. 늘 매파인 사람은 여기서는 안 걸림.</li><li><b>방향 적중</b>: 서프라이즈가 0이 아니고 2년물이 움직인 날만 놓고, 서프라이즈 부호와 2년물 변화 부호가 같았던 비율. 50%면 동전 던지기 수준이고, 높을수록 그 사람 말에 시장이 같은 방향으로 반응한 날이 많았다는 뜻. 괄호는 표본 수(5건 미만은 계산 안 함).</li><li><b>발언일 |2년물 변화|</b>: 그 사람이 말한 날 2년물이 평균 몇 bp 움직였나. 제목 아래 "평소"보다 크면 그 사람 발언일에 시장이 더 출렁였다는 뜻(원인이 발언이라는 보장은 없음).</li><li><b>주간 동행</b>: 주 단위로 그 사람 수준(최근 발언 가중 평균)의 변화와 금리 기대 변화의 순위상관. 기간 막대와 상관없이 전체 기간으로 계산. +면 그 사람 톤이 매파 쪽으로 움직인 주에 금리 기대도 올랐다는 뜻.</li><li>모두 상관이지 인과가 아님. 같은 날 여러 명이 말하면 누구 때문인지 가를 수 없음.</li></ul></details>
<details class="in" style="margin-top:10px"><summary>주간 선후행(톤 지수 변화 vs 금리 기대 변화)</summary><div style="overflow-x:auto"><table id="ll"></table></div>
<div class="note">+주 = 톤이 그만큼 먼저 움직였을 때의 상관, −주 = 시장이 먼저. 순위상관(Spearman), 괄호는 주 수.</div></details>
</details></div>

<div class="card"><h2>발언이 내세운 근거 (지난 30일)</h2>
<div class="note"><b>대상</b>: 기본은 전체(Blended) = 연준 인사 + 트럼프·베센트 + 투자자 + 셀사이드의 근거 태그가 있는 모든 발언(금리 의견 없는 신용·AI 발언 포함). 「연준 인사만」은 금리 점수가 붙은 연준 발언만. 연준 밖 사람의 근거는 「연준이 무엇을 해야 하나」의 이유라서 연준 결정의 이유와 성격이 다름.<br>기본 보기는 <b>대표 근거 구성비</b>: 발언마다 근거 1·2·3순위에 1/2·1/3·1/6 가중(근거가 2개면 2/3·1/3, 1개면 전부)을 줘서 30일 창 안에서 더함 → 매 시점 합 100%. 「무엇이 금리 결정의 주된 이유였나」를 봄. 「언급률」은 한 번이라도 언급한 발언 비율(여러 개 각각 셈, 합 100% 넘음)이고, AI 조달 언급은 단서로 한마디 해도 금융안정에 넣음. 둘의 차이 = 「말은 하지만 결정의 이유는 아닌」 부분.</div>
<details class="in" style="margin:0 0 6px"><summary>%는 이렇게 계산함</summary><div style="color:var(--text-dim);font-size:12px;line-height:1.6;margin-top:4px">① 매일, 그날 포함 지난 30일 동안 나온 <b>연준 인사(이사회·투표권·비투표 총재) 발언 중 금리 점수가 붙은 것</b>만 모음(트럼프·베센트·투자자·셀사이드는 제외, 점수 없는 규제·결제 연설도 제외). 5건 미만이면 그날은 비움.<br>② 수집할 때 발언마다 "이 사람이 정책 판단의 이유로 든 것"을 근거 태그로 붙여 둠(인플레 / 고용 / 성장 / 금융안정·신용 / AI 자금조달 / 재정 / 관세 / 에너지 등, 여러 개 가능).<br>③ 선 하나 = 30일 창 안 발언 중 그 태그가 붙은 발언의 비율. 인플레 = 인플레 태그, 고용·성장 = 고용 또는 성장 태그, 금융안정·신용 = 금융안정·신용 태그이거나 AI 발언 분류가 조달 위험 주시·자본 경쟁·위험 일축인 것, 그중 AI = AI 분류가 조달 위험 주시·자본 경쟁인 것.<br>④ 한 발언이 여러 태그를 가지면 각각 세므로 선들의 합은 100%를 넘음. 태그는 사람이 아니라 수집 모델이 인용·요약을 읽고 붙였음.</div></details>
<div class="row"><span class="dim" style="font-size:11.5px">대상:</span><div class="seg" id="cscope"><button type="button" data-s="all" class="on">전체 (Blended)</button><button type="button" data-s="fed">연준 인사만</button></div><span class="dim" style="font-size:11.5px;margin-left:8px">보기:</span><div class="seg" id="cmode"><button type="button" data-c="comp" class="on">대표 근거 구성비 (3순위 가중, 합 100%)</button><button type="button" data-c="mention">언급률 (각각 셈)</button></div></div>
<div class="row" id="lg3"></div><div class="ch s"><canvas id="c3"></canvas></div><div class="lgx" id="x3"></div><div id="drvlist" style="margin-top:8px"></div>
<div style="margin-top:16px;border-top:1px solid var(--line);padding-top:12px"><h2 style="font-size:14px">주간 변화(WoW): 근거 비중 vs 나스닥</h2>
<div class="note">막대 = 그 주 금요일 비중 − 직전 금요일 비중(%p, 왼쪽 축). 점선 = 나스닥 주간 등락률(%, 오른쪽 축). 창 = 비중을 계산하는 기간. 11/24 분석: 나스닥 주간 등락과 가장 일관되게 같이 움직인 건 30일 창 인플레 비중(ρ +0.48, 46주, 상·하반기 모두 +). 금융안정·신용 비중은 나스닥이 2주 먼저 움직이는 쪽(20일 창 ρ −0.37: 나스닥이 빠지면 2주 뒤 금융안정 언급이 늘어남). 연준 근거가 나스닥을 앞선 증거는 없음.</div>
<div class="row"><span class="dim" style="font-size:11.5px">창:</span><div class="seg" id="wow-w"><button type="button" data-w="30">30일</button><button type="button" data-w="20" class="on">20일</button><button type="button" data-w="14">14일</button></div></div>
<div class="row" id="lg5"></div><div class="ch s"><canvas id="c5"></canvas></div></div></div>

<div class="card"><h2>AI 투자·자금조달을 어떤 맥락으로 말했나 (월별 건수)</h2>
<div class="note">AI 투자·자금조달을 언급한 발언을 다섯 가지 맥락으로 나눔. 분류는 인용을 읽고 직접 붙였고, 뜻은 차트 아래에 있음.<br><b>위 근거 차트와의 관계</b>: 위의 「금융안정·신용」은 금리 결정의 이유(근거 1~3순위)로 든 발언만, AI와 무관한 신용·시장 기능까지 포함해서 셈. 이 차트는 AI 투자·조달을 언급하기만 하면 순위와 상관없이 세고, 금리 의견이 없는 발언(금융안정 연설 등)도 넣음. 그래서 두 차트의 발언은 일부만 겹침.</div>
<div class="row"><span class="btn on" data-ai="all">셋 다</span><span class="btn" data-ai="fed">연준 인사</span><span class="btn" data-ai="political">트럼프·베센트</span><span class="btn" data-ai="street">투자자·셀사이드</span></div>
<div class="row" id="lg4"></div><div class="row" id="lg4g"></div><div class="row" id="lg4i"></div>
<div class="ch s"><canvas id="c4"></canvas></div><div class="lgx" id="x4"></div><div id="ailist" style="margin-top:8px"></div></div>

<div class="card"><details id="d-infl"><summary>변곡 로그<small>직전까지의 본인 수준보다 2.5점(한 단계) 이상 달라진 발언</small></summary><div id="infl" style="margin-top:8px"></div></details></div>
<div class="card" id="calls-card"><details id="d-calls"><summary>하우스 콜·투자자</summary><div id="calls" style="margin-top:8px"></div></details></div>
<div class="card"><details id="d-led"><summary>발언 원장<small id="led-n"></small></summary>
<div class="row" style="margin-top:8px"><select id="f-g"></select><select id="f-k"></select><select id="f-d"></select><select id="f-m"></select><span class="btn on" id="f-nn" title="금리 경로에 대한 의견(점수)이 없는 발언을 숨김">의견 없는 발언 제외</span><span class="btn" id="f-x">필터 지우기</span><span class="dim" id="f-n"></span></div>
<div id="list"></div></details></div>

<div class="card"><details class="in"><summary>방법과 한계</summary><div id="method" style="margin-top:8px;color:var(--text-dim)"></div></details></div>
</div>
<script>
const D=__DATA__, KR=__KR__;
const R=D.roster, dates=D.dates, N=dates.length, P=D.params;
const G7={board:'이사회',v26:'투표권 총재(2026)',v27:'투표권 총재(2027)',nv:'비투표 총재',political:'정치',investor:'투자자·은행 CEO',sellside:'셀사이드'};
const GO=Object.keys(G7);
const gc=g=>'var(--g-'+({v26:'v26',v27:'v27',nv:'nv'}[g]||g)+')';
const DRV={inflation:'인플레',labor:'고용',growth:'성장',financial_stability_credit:'금융안정·신용',ai_financing:'AI 자금조달',fiscal_term_premium:'재정·텀프리미엄',tariffs_supply:'관세·공급',energy:'에너지',political:'정치 압력',other:'기타'};
const ROLE={stanley_druckenmiller:'듀케인 오피스',mohamed_elerian:'전 PIMCO CEO',jamie_dimon:'JPMorgan CEO',ray_dalio:'브리지워터 창업자',jeffrey_gundlach:'더블라인 CEO',larry_fink:'블랙록 CEO',david_solomon:'골드만삭스 CEO',ted_pick:'모건스탠리 CEO',howard_marks:'오크트리 공동창업',bill_ackman:'퍼싱스퀘어 대표',ken_griffin:'시타델 CEO',paul_tudor_jones:'튜더 창업자',michael_burry:'빅쇼트 투자자',marc_rowan:'아폴로 CEO',david_einhorn:'그린라이트 대표',david_tepper:'아팔루사 창업자'};
const ssRole=n=>/Asset Management|Wealth|Investment Institute|PIMCO|BlackRock/.test(n)?'운용사':/rates sales/.test(n)?'채권 세일즈':'IB 리서치';
const roleOf=k=>R[k]?R[k].role:(ROLE[k]||(k.startsWith('ss_')?ssRole(nm(k)):''));
const NMK={marc_rowan:'로완',david_einhorn:'아인혼',jamie_dimon:'다이먼',ray_dalio:'달리오',jeffrey_gundlach:'건들락',bill_ackman:'애크먼',mohamed_elerian:'엘에리언',stanley_druckenmiller:'드러켄밀러',larry_fink:'핑크',howard_marks:'하워드 막스',david_solomon:'솔로몬',ted_pick:'테드 픽',paul_tudor_jones:'튜더 존스',ken_griffin:'그리핀',michael_burry:'버리',david_tepper:'테퍼'};
const byKey={};D.items.forEach(it=>{(byKey[it.key]=byKey[it.key]||[]).push(it)});
const byId={};D.items.forEach(i=>byId[i.id]=i);
const nm=k=>{if(R[k])return R[k].kr;if(NMK[k])return NMK[k];const i=(byKey[k]||[])[0];return i?(i.disp||i.speaker):k;};
const gOf=k=>byKey[k]?byKey[k][0].g7:'nv';
const who=k=>'<span style="color:'+gc(gOf(k))+';font-weight:700">'+esc(nm(k))+'</span>';
const f1=v=>v==null?'–':v.toFixed(1);
const fs=v=>v==null?'–':(v>0?'+':'')+v.toFixed(1);
function col(s){if(s==null)return '#f6f5f2';const t=Math.max(-1,Math.min(1,(s-5)/5)),m=[240,239,236],p=t>=0?[150,20,20]:[13,54,107],a=Math.abs(t);return 'rgb('+m.map((x,i)=>Math.round(x+(p[i]-x)*a)).join(',')+')';}
const ink=s=>Math.abs(s-5)>=2.2?'#fff':'#0b0b0b';
const chip=s=>s==null?'<span class="chip" style="background:#f0efec;color:#6f6e69">–</span>':'<span class="chip" style="background:'+col(s)+';color:'+ink(s)+'">'+s.toFixed(1)+'</span>';
const lastv=a=>{if(!a)return [null,-1];for(let i=a.length-1;i>=0;i--)if(a[i]!=null)return [a[i],i];return [null,-1]};
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}

// ---- 머리말·읽는 법·타일 ----
document.getElementById('hdr').textContent=P.start+' ~ '+P.end+' · 원문에서 인용을 확인한 발언 '+P.n_usable+'건(점수 '+P.n_scored+'건) · 확인 못 해 뺀 것 '+P.n_unverified+'건';
document.getElementById('glegend').innerHTML=GO.map(g=>'<span class="gtag" style="color:'+gc(g)+';margin-right:5px">'+G7[g]+'</span>').join('');
let W={i0:0,i1:N-1};  // 기간 막대가 고른 구간(날짜 인덱스)
const inW=d=>d>=dates[W.i0]&&d<=dates[W.i1];
function lastAt(a,e){if(!a)return [null,-1];for(let j=Math.min(e,a.length-1);j>=0;j--)if(a[j]!=null)return [a[j],j];return [null,-1];}
function drawTiles(){const I=D.index,M=D.market,e=W.i1,[v,i]=lastAt(I.voter27,e);const ago=i>=30?I.voter27[i-30]:null;
 const [ch]=lastAt(I.chair,e),[v26]=lastAt(I.voter26,e),[zq]=lastAt(M.zq,e),[ef]=lastAt(M.effr,e),[fin]=lastAt(D.drivers.fin,e),[ai]=lastAt(D.drivers.ai,e);
 const nh=i<0?null:I.n_hawk27[i],nd=i<0?null:I.n_dove27[i],nmid=i<0?null:I.n_mid27[i],nv=i<0?null:I.n_voter27[i],nh0=i>=30?I.n_hawk27[i-30]:null;
 const kk=Object.keys(M).filter(k=>k.startsWith('k_hike_')).sort(),gap=(zq!=null&&ef!=null)?(zq-ef)*100:null;
 const T=[['2027 투표권자 톤 (0~10)',f1(v),ago==null?'':'30일 전 '+f1(ago)+' → 변화 '+fs(v-ago),''],
 ['2027 투표권자 성향 분포',nv==null?'–':'매파 '+nh+' · 중도 '+nmid+' · 비둘기 '+nd,nv==null?'':'발언이 확인된 2027 투표권자 '+nv+'명 기준(이사 + 뉴욕·시카고·리치먼드·애틀랜타·샌프란시스코). 수준 '+P.hawk_t+' 초과 = 매파 쪽, '+P.dove_t+' 미만 = 비둘기파 쪽'+(nh0==null?'':' · 30일 전 매파 '+nh0+'명'),'sm'],
 ['의장('+(dates[e]<P.chair_switch[1]?'파월':'워시')+') 수준',f1(ch),'2026 투표권자 톤 '+f1(v26),''],
 ['시장: 금리 기대(12/9 회의 뒤)',zq==null?'–':zq.toFixed(2)+'%',(gap==null?'':'지금 금리 '+ef.toFixed(2)+'% 대비 '+(gap>0?'+':'')+gap.toFixed(0)+'bp')+kk.map(k=>{const x=lastAt(M[k],e)[0];return x==null?'':' · '+k.slice(12,17).replace('-','/')+' 인상 '+x+'%'}).join(''),''],
 ['금융안정·신용 근거 비중',fin==null?'–':fin.toFixed(0)+'%','지난 30일 연준 인사 발언 중 · AI 조달 위험·자본 경쟁 '+(ai==null?'–':ai.toFixed(0)+'%'),'']];
 document.getElementById('tiles').innerHTML=T.map(t=>'<div class="tile"><div class="k">'+t[0]+'</div><div class="v '+t[3]+'">'+t[1]+'</div><div class="d">'+t[2]+'</div></div>').join('');
 document.getElementById('hdr').textContent='수집 '+P.start+' ~ '+P.end+' · 원문에서 인용을 확인한 발언 '+P.n_usable+'건(점수 '+P.n_scored+'건) · 확인 못 해 뺀 것 '+P.n_unverified+'건 · 타일 기준일 '+dates[e];}

// ---- 차트 공통 ----
Chart.defaults.color='#52514e';Chart.defaults.devicePixelRatio=Math.max(window.devicePixelRatio||1,3);Chart.defaults.font.size=11;Chart.defaults.borderColor='rgba(0,0,0,.07)';
const fomc=Object.keys(D.releases).filter(d=>D.releases[d].includes('FOMC')&&d>=P.start&&d<=P.end);
// FOMC 블랙아웃: 회의 시작일 전 두 번째 토요일 0시 ~ 회의 끝난 다음 날 자정(연준 규정). 결정일 = 회의 둘째 날
let BOon=false;const BO=fomc.map(d=>{const f=new Date(d+'T00:00:00Z');f.setUTCDate(f.getUTCDate()-1);const s=new Date(f);do{s.setUTCDate(s.getUTCDate()-1);}while(s.getUTCDay()!==6);s.setUTCDate(s.getUTCDate()-7);const e=new Date(d+'T00:00:00Z');e.setUTCDate(e.getUTCDate()+1);const iso=x=>x.toISOString().slice(0,10);return [iso(s),iso(e)];});
let BO3on=false;const boBand={id:'bo',beforeDatasetsDraw(c){if(!(c.canvas.id==='c3'?BO3on:BOon))return;const x=c.scales.x,a=c.chartArea,g=c.ctx;g.save();BO.forEach(([s,e])=>{let i0=dates.indexOf(s),i1=dates.indexOf(e);if(i1<0&&e>dates[N-1])i1=N-1;if(i0<0&&s<dates[0])i0=0;if(i0<0||i1<0)return;const p0=x.getPixelForValue(i0),p1=x.getPixelForValue(i1);if(p1<a.left||p0>a.right)return;const l=Math.max(p0,a.left),r=Math.min(p1,a.right);g.fillStyle='rgba(98,80,214,.07)';g.fillRect(l,a.top,r-l,a.bottom-a.top);g.setLineDash([]);g.strokeStyle='rgba(98,80,214,.7)';g.lineWidth=1.3;[p0,p1].forEach(p=>{if(p>=a.left&&p<=a.right){g.beginPath();g.moveTo(p,a.top);g.lineTo(p,a.bottom);g.stroke();}});if(c.canvas.id==='c1'){g.fillStyle='rgba(98,80,214,.85)';g.font='10px sans-serif';g.fillText('블랙아웃',l+3,a.bottom-4);}});g.restore();}};
const vline={id:'vl',afterDraw(c){const x=c.scales.x,a=c.chartArea,g=c.ctx;g.save();g.setLineDash([3,3]);g.strokeStyle='rgba(0,0,0,.35)';g.fillStyle='#6f6e69';g.font='10px sans-serif';
 fomc.forEach(d=>{const i=dates.indexOf(d);if(i<0)return;const px=x.getPixelForValue(i);g.beginPath();g.moveTo(px,a.top);g.lineTo(px,a.bottom);g.stroke();if(c.canvas.id==='c1')g.fillText('FOMC',px+3,a.top+9);});g.restore();}};
const xax={ticks:{maxTicksLimit:11,callback:function(v){return dates[v].slice(2,7).replace('-','.')}},grid:{display:false}};
const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const X=dates.map((_,i)=>i);
// 범례: 누르면 그 계열을 끄고 켬. after()로 축 다시 맞춤
function legend(el,chart,after,sq){const box=document.getElementById(el);
 function draw(){box.innerHTML=chart.data.datasets.map((d,i)=>(d._person&&d.label==='(인물 선택)')?'':(d._sep?'<span class="lgsep">'+d._sep+'</span>':'')+'<span class="lg'+(sq?' sq':'')+(chart.isDatasetVisible(i)?'':' off')+'" data-i="'+i+'"><i style="background:'+d.borderColor+(d._dash?';background:repeating-linear-gradient(90deg,'+d.borderColor+' 0 4px,transparent 4px 6px)':'')+'"></i>'+d.label+'</span>').join('');
  box.querySelectorAll('.lg').forEach(s=>s.onclick=()=>{const i=+s.dataset.i;chart.setDatasetVisibility(i,!chart.isDatasetVisible(i));if(after)after(chart);chart.update();draw();});}
 draw();return draw;}
// 한 축짜리 차트: 보이는 계열에 맞춰 세로축을 다시 잡음
function fitY(chart,axis,lo,hi,pad,filter){let mn=Infinity,mx=-Infinity,nvis=0,nall=0;
 chart.data.datasets.forEach((d,i)=>{if(filter&&!filter(d))return;nall++;if(!chart.isDatasetVisible(i))return;nvis++;d.data.forEach((v,ix)=>{if(v!=null&&ix>=W.i0&&ix<=W.i1){if(v<mn)mn=v;if(v>mx)mx=v;}});});
 const s=chart.options.scales[axis];if(!nvis||nvis===nall||mn===Infinity){s.min=lo;s.max=hi;return;}
 const p=Math.max(pad,(mx-mn)*0.15);s.min=Math.max(lo,Math.floor((mn-p)*2)/2);s.max=Math.min(hi,Math.ceil((mx+p)*2)/2);}

// ---- 톤 지수 + 비교 지표 ----
const TONE=[['voter26','2026 투표권자','--s1'],['chair','의장(5월까지 파월, 이후 워시)','--s2'],['voter27','2027 투표권자','--s3'],['political','트럼프·베센트','--s4'],['investor','투자자·구루 평균','--g-investor'],['sellside','셀사이드 평균','--g-sellside']];
let TMODE='decay';const tSrc=k=>(TMODE==='last'?(D.index_last||{}):D.index)[k]||D.index[k];
function lastLevel(k){const by={};(byKey[k]||[]).forEach(i=>{if(i.score!=null)(by[i.date]=by[i.date]||[]).push(i.score)});let cur=null;return dates.map(d=>{if(by[d])cur=by[d].reduce((a,b)=>a+b,0)/by[d].length;return cur;});}
const pLevel=k=>TMODE==='last'?lastLevel(k):D.levels[k];
const OV=[['zq','금리 기대: 연방기금 선물 27년 1월물(%)','#0b0b0b',true,2],['dec_rate','12/9 회의 후 예상 금리(대시보드 FedWatch, %)','#6f6e69',false,2],['y2','미 2년물(%)','#7a4b1e',false,2],['spx','S&P 500','#6250d6',false,0],['ndq','나스닥 종합','#c2185b',true,0],['kospi','코스피','#0b7a3e',false,0],['brent','Brent 유가 ($)','#3f3e3b',false,1]]
 .concat(Object.keys(D.market).filter(k=>k.startsWith('k_hike_')).sort().map(k=>[k,'Kalshi '+k.slice(12,17).replace('-','/')+' 인상 확률(%)','#00707d',false,0]));
const ds1=TONE.map(s=>({label:s[1],data:tSrc(s[0]),borderColor:css(s[2]),backgroundColor:css(s[2]),yAxisID:'y',_tone:true,_k:s[0],borderDash:(s[0]==='investor'||s[0]==='sellside')?[2,2]:undefined,hidden:(s[0]==='investor'||s[0]==='sellside')}));
ds1.push({label:'(인물 선택)',data:X.map(()=>null),borderColor:'#d55181',backgroundColor:'#d55181',yAxisID:'y',_tone:true,hidden:true,_person:true});
const sc1={x:xax,y:{min:0,max:10,position:'left',ticks:{maxTicksLimit:9,callback:v=>v},grid:{color:c=>c.tick.value===5?'rgba(0,0,0,.6)':'rgba(0,0,0,.07)'},title:{display:true,text:'← 비둘기파(0)      중도(5)      매파(10) →'}}};
ds1.push({label:'FOMC 블랙아웃 구간',data:X.map(()=>null),borderColor:'rgba(98,80,214,.7)',backgroundColor:'rgba(98,80,214,.07)',yAxisID:'y',hidden:true,_bo:true,_sep:'구간'});
OV.forEach((o,j)=>{const id='o'+j;ds1.push({label:o[1],data:D.market[o[0]]||X.map(()=>null),borderColor:o[2],backgroundColor:o[2],borderDash:[5,3],borderWidth:1.5,yAxisID:id,hidden:!o[3],_dash:true,_sep:j===0?'비교 지표':''});
 sc1[id]={position:'right',display:!!o[3],grid:{display:false},ticks:{color:o[2],maxTicksLimit:6,callback:v=>o[4]?v.toFixed(o[4]):Math.round(v).toLocaleString()},border:{color:o[2]}};});
const C1=new Chart(document.getElementById('c1'),{type:'line',plugins:[boBand,vline],data:{labels:X,datasets:ds1},
 options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{filter:t=>t.raw!=null,callbacks:{title:t=>t.length?dates[t[0].dataIndex]:'',label:t=>t.dataset.label+': '+(t.dataset._tone?t.raw.toFixed(1):(t.raw>=1000?Math.round(t.raw).toLocaleString():t.raw.toFixed(2)))}}},scales:sc1,elements:{point:{radius:0,hoverRadius:4},line:{borderWidth:2,tension:0,spanGaps:true}}}});
function after1(c){fitY(c,'y',0,10,0.4,d=>d._tone&&!(d._person&&!c.isDatasetVisible(c.data.datasets.indexOf(d))));c.data.datasets.forEach((d,i)=>{if(d._bo){BOon=c.isDatasetVisible(i);return;}if(!d._tone)c.options.scales[d.yAxisID].display=c.isDatasetVisible(i);});if(typeof C3!=='undefined')C3.update();}
const redraw1=legend('lg1',C1,after1);
document.querySelectorAll('#tmode button').forEach(b=>b.onclick=()=>{TMODE=b.dataset.t;document.querySelectorAll('#tmode button').forEach(x=>x.classList.toggle('on',x===b));C1.data.datasets.forEach(d=>{if(d._k)d.data=tSrc(d._k);});const ps=document.getElementById('psel');if(ps.value){const d=C1.data.datasets.find(x=>x._person);d.data=pLevel(ps.value);}after1(C1);C1.update();});
(function(){const ks=Object.keys(D.levels).filter(k=>byKey[k]).sort((a,b)=>GO.indexOf(gOf(a))-GO.indexOf(gOf(b))||byKey[b].length-byKey[a].length);
 const sel=document.getElementById('psel');sel.innerHTML='<option value="">선택 안 함</option>'+ks.map(k=>'<option value="'+k+'">'+esc(nm(k))+' · '+G7[gOf(k)]+'</option>').join('');
 sel.onchange=()=>{const i=C1.data.datasets.findIndex(d=>d._person),d=C1.data.datasets[i];if(!sel.value){C1.setDatasetVisibility(i,false);d.label='(인물 선택)';d.data=X.map(()=>null);}else{d.label=nm(sel.value);d.data=pLevel(sel.value);C1.setDatasetVisibility(i,true);}after1(C1);C1.update();redraw1();};})();

// ---- 근거 비중 ----
const S3=[['infl','인플레','--s1'],['labor','고용·성장','--s2'],['fin','금융안정·신용','--s3'],['ai','그중 AI 조달 위험·자본 경쟁','--s4']];
let CMODE='comp',CSCOPE='all';
const compSrc=w=>((CSCOPE==='all'?D.comp_w_all:D.comp_w)||{})[w]||{};
const drvSrc=w=>CSCOPE==='all'?(((D.drivers_w_all||{})[w])||{}):(w==='30'?D.drivers:((D.drivers_w||{})[w]||{}));
const CMP=[['infl','인플레','--s1'],['energy','에너지','#e3a008'],['tariff','관세·공급','#8c564b'],['labor','고용·성장','--s2'],['fin','금융안정·신용 (AI 조달 포함)','--s3'],['other','재정·정치·기타','#c9c8c2']];
const colv=c=>c.startsWith('--')?css(c):c;
const mainSeries=()=>CMODE==='comp'?CMP:S3;
function ds3main(){const cm=CMODE==='comp',src=cm?compSrc('30'):drvSrc('30');return mainSeries().map((s,i)=>({label:s[1],data:src[s[0]]||X.map(()=>null),borderColor:colv(s[2]),backgroundColor:cm?colv(s[2])+'B3':colv(s[2]),fill:cm?(i?'-1':'origin'):false,borderWidth:cm?1:2,yAxisID:'y',_main:true}));}
const ds3=ds3main();
ds3.push({label:'FOMC 블랙아웃 구간',data:X.map(()=>null),borderColor:'rgba(98,80,214,.7)',backgroundColor:'rgba(98,80,214,.07)',yAxisID:'y',hidden:true,_bo:true,_sep:'구간'});
[['spx','S&P 500','#6250d6'],['ndq','나스닥 종합','#c2185b'],['kospi','코스피','#0b7a3e'],['brent','Brent 유가 ($)','#3f3e3b']].forEach((o,j)=>ds3.push({label:o[1],data:D.market[o[0]]||X.map(()=>null),borderColor:o[2],backgroundColor:o[2],borderDash:[6,3],borderWidth:2.4,order:-1,yAxisID:'y3_'+o[0],hidden:true,_dash:true,_sep:j===0?'비교 지표':''}));
const C3=new Chart(document.getElementById('c3'),{type:'line',plugins:[boBand,vline],data:{labels:X,datasets:ds3},
 options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{filter:t=>t.raw!=null,callbacks:{title:t=>dates[t[0].dataIndex],label:t=>t.dataset.label+': '+(t.dataset._dash?Math.round(t.raw).toLocaleString():t.raw.toFixed(0)+'%')}}},scales:{x:xax,y:{min:0,max:100,ticks:{maxTicksLimit:6,callback:v=>v+'%'}},y3_spx:{position:'right',display:false,grid:{display:false},ticks:{color:'#6250d6',maxTicksLimit:5,callback:v=>Math.round(v).toLocaleString()}},y3_ndq:{position:'right',display:false,grid:{display:false},ticks:{color:'#c2185b',maxTicksLimit:5,callback:v=>Math.round(v).toLocaleString()}},y3_kospi:{position:'right',display:false,grid:{display:false},ticks:{color:'#0b7a3e',maxTicksLimit:5,callback:v=>Math.round(v).toLocaleString()}},y3_brent:{position:'right',display:false,grid:{display:false},ticks:{color:'#3f3e3b',maxTicksLimit:5,callback:v=>'$'+Math.round(v)}}},elements:{point:{radius:0,hoverRadius:4},line:{borderWidth:2,tension:0,spanGaps:true}}}});
let C5,WOWW='20',wowHidden={kospi:true};
function drawWoW(){if(C5)C5.destroy();const src=CMODE==='comp'?compSrc(WOWW):drvSrc(WOWW);const fr=[];for(let i=W.i0;i<=W.i1;i++){if(new Date(dates[i]+'T00:00:00Z').getUTCDay()===5)fr.push(i);}
 const at=(a,i)=>{for(let j=i;j>=0;j--)if(a&&a[j]!=null)return a[j];return null;};
 const lab=fr.slice(1).map(i=>dates[i].slice(5).replace('-','/'));
 const ds=mainSeries().map(s=>({type:'bar',label:s[1]+' (%p)',_k:s[0],data:fr.slice(1).map((i,j)=>{const a=at(src[s[0]],i),b=at(src[s[0]],fr[j]);return a==null||b==null?null:Math.round((a-b)*10)/10;}),backgroundColor:colv(s[2]),borderColor:colv(s[2]),borderRadius:2,maxBarThickness:10,yAxisID:'y',hidden:!!wowHidden[s[0]]}));
 ds.push({type:'line',label:'나스닥 주간 등락률 (%)',_k:'ndq',data:fr.slice(1).map((i,j)=>{const a=at(D.market.ndq,i),b=at(D.market.ndq,fr[j]);return a==null||b==null?null:Math.round((a/b-1)*1000)/10;}),borderColor:'#c2185b',backgroundColor:'#c2185b',borderDash:[5,3],borderWidth:1.6,pointRadius:2,yAxisID:'y5',_dash:true,hidden:!!wowHidden.ndq});
 ds.push({type:'line',label:'코스피 주간 등락률 (%)',_k:'kospi',data:fr.slice(1).map((i,j)=>{const a=at(D.market.kospi,i),b=at(D.market.kospi,fr[j]);return a==null||b==null?null:Math.round((a/b-1)*1000)/10;}),borderColor:'#0b7a3e',backgroundColor:'#0b7a3e',borderDash:[5,3],borderWidth:1.6,pointRadius:2,yAxisID:'y5',_dash:true,hidden:!!wowHidden.kospi}); C5=new Chart(document.getElementById('c5'),{data:{labels:lab,datasets:ds},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{filter:t=>t.raw!=null}},scales:{x:{grid:{display:false},ticks:{maxTicksLimit:12}},y:{title:{display:true,text:'비중 변화 %p'},grid:{color:c=>c.tick.value===0?'rgba(0,0,0,.5)':'rgba(0,0,0,.07)'}},y5:{position:'right',grid:{display:false},title:{display:true,text:'나스닥 %'},ticks:{color:'#c2185b'}}}}});
 legend('lg5',C5,c=>{c.data.datasets.forEach((d,i)=>{wowHidden[d._k]=!c.isDatasetVisible(i);});c.options.scales.y5.display=c.data.datasets.some((d,i)=>d._dash&&c.isDatasetVisible(i));},true);}
document.querySelectorAll('#wow-w button').forEach(b=>b.onclick=()=>{WOWW=b.dataset.w;document.querySelectorAll('#wow-w button').forEach(x=>x.classList.toggle('on',x===b));drawWoW();});
const DCAT={inflation:'infl',energy:'energy',tariffs_supply:'tariff',labor:'labor',growth:'labor',financial_stability_credit:'fin',ai_financing:'fin'};
const AILAB={demand:'수요 압력',loose:'조달 쉬움',crowding:'자본 경쟁',watch:'조달 위험 주시',calm:'위험 일축'};
function drawDrvList(c){if(typeof itemHTML!=='function')return;const od=document.getElementById('drvlist-d');if(od)window.__drvOpen=od.open;
 const S=mainSeries(),on=S.filter((s,i)=>c.isDatasetVisible(i)).map(s=>s[0]),names=S.filter((s,i)=>c.isDatasetVisible(i)).map(s=>s[1]);
 const fedG=['board','voter','nonvoter'];let pool=D.items.filter(i=>inW(i.date)&&(i.drivers||[]).length&&(CSCOPE==='all'||(fedG.includes(i.group)&&i.score!=null)));
 const hit=i=>{const ds=i.drivers||[];if(CMODE==='comp'){for(let r=0;r<Math.min(3,ds.length);r++){const k=DCAT[ds[r]]||'other';if(on.includes(k))return (r+1)+'순위: '+(DRV[ds[r]]||ds[r]);}return null;}
  if(on.includes('infl')&&ds.includes('inflation'))return '인플레 언급';if(on.includes('labor')&&(ds.includes('labor')||ds.includes('growth')))return '고용·성장 언급';
  if(on.includes('ai')&&['watch','crowding'].includes(i.ai_side))return 'AI 조달 언급';if(on.includes('fin')&&(ds.includes('financial_stability_credit')||['watch','crowding','calm'].includes(i.ai_side)))return '금융안정 언급';return null;};
 const rows=pool.map(i=>[i,hit(i)]).filter(x=>x[1]).sort((a,b)=>b[0].date.localeCompare(a[0].date));
 document.getElementById('drvlist').innerHTML='<details class="in" id="drvlist-d"'+(window.__drvOpen?' open':'')+'><summary>켜 둔 근거('+(on.length===S.length?'전체':names.join(' · '))+')를 '+(CMODE==='comp'?'1~3순위로 든':'언급한')+' 발언 '+rows.length+'건 보기 · '+(CSCOPE==='all'?'전체':'연준 인사')+(rows.length>150?' (최근 150건)':'')+'</summary>'+rows.slice(0,150).map(([i,h])=>itemHTML(i,'<span class="tag" style="color:#0b0b0b">근거 '+h+'</span>'+(i.ai_side?'<span class="tag" style="color:#0b0b0b">AI 맥락: '+AILAB[i.ai_side]+'</span>':''))).join('')+'</details>';}
function after3(c){setTimeout(()=>drawDrvList(c),0);if(CMODE==='comp'){const vis=c.data.datasets.map((d,i)=>[d,i]).filter(([d,i])=>d._main&&c.isDatasetVisible(i));let mx=0;if(vis.length&&vis.length<c.data.datasets.filter(d=>d._main).length){for(let t=W.i0;t<=W.i1;t++){let s=0;vis.forEach(([d])=>{s+=d.data[t]||0;});if(s>mx)mx=s;}const st=mx>40?10:mx>15?5:mx>6?2:1;c.options.scales.y.max=Math.min(100,Math.max(st,Math.ceil(mx*1.1/st)*st));}else c.options.scales.y.max=100;c.options.scales.y.min=0;}else fitY(c,'y',0,100,3,d=>!d._dash&&!d._bo);c.data.datasets.forEach((d,i)=>{if(d._bo){BO3on=c.isDatasetVisible(i);return;}if(d._dash)c.options.scales[d.yAxisID].display=c.isDatasetVisible(i);});}
const redraw3=legend('lg3',C3,after3);C3.options.scales.y.stacked=true;C3.update();
function setCMode(m){CMODE=m;const others=C3.data.datasets.filter(d=>!d._main);C3.data.datasets=ds3main().concat(others);C3.options.scales.y.stacked=(m==='comp');after3(C3);C3.update();redraw3();drawX3();drawWoW();document.querySelectorAll('#cmode button').forEach(b=>b.classList.toggle('on',b.dataset.c===m));}
document.querySelectorAll('#cmode button').forEach(b=>b.onclick=()=>setCMode(b.dataset.c));
document.querySelectorAll('#cscope button').forEach(b=>b.onclick=()=>{CSCOPE=b.dataset.s;document.querySelectorAll('#cscope button').forEach(x=>x.classList.toggle('on',x===b));setCMode(CMODE);});
const X3=['물가가 목표(2%)보다 높거나 더 오를 위험을 이유로 든 발언. 이 선이 높을수록 매파 논리가 주도한다는 뜻.',
 '고용 둔화나 경기 약화를 이유로 든 발언. 이 선이 오르면 "더 올리면 안 된다"는 쪽 논리가 힘을 얻는 중.',
 '신용 스프레드, 사모신용, 시장 기능, 자산가격을 정책 판단의 근거로 든 발언. 연준이 금리 결정에 금융시장 상태를 끌어들이기 시작했는지 보는 선.',
 '금융안정·신용 가운데 AI 투자 자금조달(부채 의존, 스프레드 확대, 국채와의 자본 경쟁)을 직접 짚은 발언. AI 조달 문제가 반응함수에 들어오는지 보는 가장 직접적인 선.'];
const X3C=['물가가 목표보다 높거나 더 오를 위험이 결정의 주된 이유인 몫. 이 몫이 줄어야 다른 논리가 들어올 자리가 생김.',
 '유가·연료비를 이유로 든 몫. 유가가 내리면 이 몫이 줄고, 「공급 충격은 지나간다」 논리의 근거도 함께 사라짐.',
 '관세·공급망을 이유로 든 몫. 상품 물가 전이를 볼 때.',
 '고용 둔화·경기 약화를 이유로 든 몫. 커지면 「더 올리면 안 된다」 쪽 논리가 힘을 얻는 중.',
 '신용 스프레드·사모신용·AI 투자 조달 등 금융 여건이 결정의 이유로 쓰인 몫. 언급률(30% 안팎)과 달리 아직 한 자릿수면 「말은 하지만 결정 이유는 아님」. 한 자릿수를 넘어 커지면 반응함수에 들어오는 신호.',
 '재정·텀프리미엄, 정치, 그 밖의 이유.'];
function drawX3(){const S=mainSeries(),T=CMODE==='comp'?X3C:X3;document.getElementById('x3').innerHTML=S.map((s,i)=>'<div><i style="background:'+colv(s[2])+'"></i><b>'+s[1]+'</b><br>'+T[i]+'</div>').join('');}
drawX3();

// ---- AI 발언 성격 ----
const AIS=[['demand','수요 압력','#2a78d6'],['loose','조달 쉬움','#eb6834'],['crowding','자본 경쟁','#1baf7a'],['watch','조달 위험 주시','#eda100'],['calm','위험 일축','#e87ba4']];
const X4=['AI capex가 수요와 물가를 밀어 올린다는 말. 금리를 올릴 이유로 쓰는 매파 논리.',
 '금리를 올려도 AI 투자와 차입이 안 꺾인다는 말. 정책이 아직 덜 긴축적이라는 매파 논리.',
 'AI 차입이 국채 등과 돈을 두고 경쟁해 장기금리를 올린다는 말. 금리 상승을 연준이 아니라 수급 탓으로 보는 시각.',
 '스프레드 확대, 구조화 금융, 부채 의존을 위험으로 언급한 말. 인상 속도 조절이나 중단 논리로 이어질 수 있는 싹.',
 '문제 될 규모가 아니라고 선을 긋는 말. 위험을 알고도 정책을 바꿀 뜻이 없다는 신호.'];
document.getElementById('x4').innerHTML=AIS.map((s,i)=>'<div><i style="background:'+s[2]+'"></i><b>'+s[1]+'</b><br>'+X4[i]+'</div>').join('');
let C4,aicur='all',aiHidden={},aiGHidden={},aiIdx={};
const AIX=[['spx','S&P 500 (월말)','#6250d6'],['ndq','나스닥 종합 (월말)','#c2185b'],['kospi','코스피 (월말)','#0b7a3e']];
function monthEnd(arr,months){return months.map(mo=>{let v=null;for(let i=0;i<N;i++){if(dates[i].slice(0,7)===mo&&i<=W.i1&&arr[i]!=null)v=arr[i];}return v;});}const months0=[...new Set(dates.map(d=>d.slice(0,7)))];
// 그룹은 채우는 방식으로 가름: 연준 = 꽉 채움, 트럼프·베센트 = 빗금, 투자자·셀사이드 = 반투명 + 테두리
const AIG=[['fed','연준 인사'],['political','트럼프·베센트'],['street','투자자·셀사이드']];
function hatch(c){const cv=document.createElement('canvas');cv.width=cv.height=8;const g=cv.getContext('2d');g.fillStyle=c+'33';g.fillRect(0,0,8,8);g.strokeStyle=c;g.lineWidth=2;g.beginPath();g.moveTo(-2,10);g.lineTo(10,-2);g.moveTo(-2,2);g.lineTo(2,-2);g.moveTo(6,10);g.lineTo(10,6);g.stroke();return g.createPattern(cv,'repeat');}
function aiStyle(g,c){return g==='fed'?{backgroundColor:c,borderColor:c,borderWidth:0}:g==='political'?{backgroundColor:hatch(c),borderColor:c,borderWidth:1}:{backgroundColor:c+'40',borderColor:c,borderWidth:1.5};}
function aiSwatch(g){return g==='fed'?'background:#6f6e69':g==='political'?'background:repeating-linear-gradient(45deg,#6f6e69 0 2px,#6f6e6933 2px 5px);border:1px solid #6f6e69':'background:#6f6e6940;border:1.5px solid #6f6e69';}
function drawAI(){if(C4)C4.destroy();const months=months0.filter(x=>x>=dates[W.i0].slice(0,7)&&x<=dates[W.i1].slice(0,7));
 const gs=aicur==='all'?AIG.map(a=>a[0]):[aicur],ds=[];
 AIS.forEach(s=>gs.forEach(g=>{const m=(D.ai_month||{})[g]||{};ds.push(Object.assign({label:s[1],_g:g,_k:s[0],data:months.map(x=>(m[x]||{})[s[0]]||0),borderRadius:3,maxBarThickness:46,stack:'s',yAxisID:'y',hidden:!!aiHidden[s[0]]||!!aiGHidden[g]},aiStyle(g,s[2])));}))
 AIX.forEach(x=>ds.push({type:'line',label:x[1],_ix:x[0],data:monthEnd(D.market[x[0]]||[],months),borderColor:x[2],backgroundColor:x[2],borderDash:[5,3],borderWidth:1.6,pointRadius:2,yAxisID:'y_'+x[0],hidden:!aiIdx[x[0]],order:-1}));;
 C4=new Chart(document.getElementById('c4'),{type:'bar',data:{labels:months.map(x=>x.slice(2).replace('-','.')),datasets:ds},
  options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false},tooltip:{filter:t=>t.raw!=null&&(t.dataset._ix||t.raw>0),callbacks:{label:t=>t.dataset._ix?t.dataset.label+': '+Math.round(t.raw).toLocaleString():(gs.length>1?AIG.find(a=>a[0]===t.dataset._g)[1]+' · ':'')+t.dataset.label+': '+t.raw+'건'}}},scales:{x:{stacked:true,grid:{display:false}},y:{stacked:true,ticks:{precision:0,maxTicksLimit:6},title:{display:true,text:'건'}},y_spx:{beginAtZero:false,position:'right',display:!!aiIdx.spx,grid:{display:false},ticks:{color:'#6250d6',maxTicksLimit:5,callback:v=>Math.round(v).toLocaleString()}},y_kospi:{beginAtZero:false,position:'right',display:!!aiIdx.kospi,grid:{display:false},ticks:{color:'#0b7a3e',maxTicksLimit:5,callback:v=>Math.round(v).toLocaleString()}},y_ndq:{beginAtZero:false,position:'right',display:!!aiIdx.ndq,grid:{display:false},ticks:{color:'#c2185b',maxTicksLimit:5,callback:v=>Math.round(v).toLocaleString()}}}}});
 const vis=()=>{C4.data.datasets.forEach((d,i)=>C4.setDatasetVisibility(i,d._ix?!!aiIdx[d._ix]:(!aiHidden[d._k]&&!aiGHidden[d._g])));C4.options.scales.y_spx.display=!!aiIdx.spx;C4.options.scales.y_ndq.display=!!aiIdx.ndq;C4.options.scales.y_kospi.display=!!aiIdx.kospi;};
 const b1=document.getElementById('lg4'),b2=document.getElementById('lg4g');
 const draw=()=>{b1.innerHTML=AIS.map(s=>'<span class="lg sq'+(aiHidden[s[0]]?' off':'')+'" data-k="'+s[0]+'"><i style="background:'+s[2]+'"></i>'+s[1]+'</span>').join('');
  b2.innerHTML=gs.length>1?'<span class="lgsep">그룹</span>'+AIG.map(a=>'<span class="lg sq'+(aiGHidden[a[0]]?' off':'')+'" data-g="'+a[0]+'"><i style="'+aiSwatch(a[0])+';width:14px;height:11px;border-radius:2px"></i>'+a[1]+'</span>').join(''):'';
  const b3=document.getElementById('lg4i');b3.innerHTML='<span class="lgsep">비교 지표</span>'+AIX.map(x=>'<span class="lg'+(aiIdx[x[0]]?'':' off')+'" data-x="'+x[0]+'"><i style="background:repeating-linear-gradient(90deg,'+x[2]+' 0 4px,transparent 4px 6px)"></i>'+x[1]+'</span>').join('');
  b3.querySelectorAll('.lg').forEach(e=>e.onclick=()=>{aiIdx[e.dataset.x]=!aiIdx[e.dataset.x];vis();C4.update();draw();});
  b1.querySelectorAll('.lg').forEach(e=>e.onclick=()=>{aiHidden[e.dataset.k]=!aiHidden[e.dataset.k];vis();C4.update();draw();aiList();});
  b2.querySelectorAll('.lg').forEach(e=>e.onclick=()=>{aiGHidden[e.dataset.g]=!aiGHidden[e.dataset.g];vis();C4.update();draw();aiList();});};
 draw();
 aiList();}
function aiList(){const gs=aicur==='all'?AIG.map(a=>a[0]):[aicur];const od=document.getElementById('ailist-d');if(od)window.__aiOpen=od.open;
 const GG={fed:['board','voter','nonvoter'],political:['political'],street:['investor','sellside']};
 const G=gs.filter(g=>!aiGHidden[g]).flatMap(g=>GG[g]);
 const its=D.items.filter(i=>i.ai_side&&inW(i.date)&&G.includes(i.group)&&!aiHidden[i.ai_side]).sort((a,b)=>b.date.localeCompare(a.date));
 const onK=AIS.filter(s=>!aiHidden[s[0]]).map(s=>s[1]),onG=gs.filter(g=>!aiGHidden[g]).map(g=>AIG.find(a=>a[0]===g)[1]);
 const lab={};AIS.forEach(s=>lab[s[0]]=s[1]);
 document.getElementById('ailist').innerHTML='<details class="in" id="ailist-d"'+(window.__aiOpen?' open':'')+'><summary>'+(onK.length===AIS.length?'전체 맥락':onK.join('·'))+' · '+onG.join('·')+' 발언 '+its.length+'건 보기</summary>'+its.map(i=>itemHTML(i,'<span class="tag" style="color:#0b0b0b">'+lab[i.ai_side]+'</span>')).join('')+'</details>';}
document.querySelectorAll('[data-ai]').forEach(b=>b.onclick=()=>{aicur=b.dataset.ai;document.querySelectorAll('[data-ai]').forEach(x=>x.classList.toggle('on',x===b));drawAI();});

// ---- 히트맵 ----
const wk=[];for(let i=0;i<N;i+=7)wk.push(i);
let F={g:'',k:'',d:'',m:'',w:null};
const HMOPEN={};
function drawHM(){const wks=wk.map((i,wi)=>[i,wi]).filter(x=>x[0]+6>=W.i0&&x[0]<=W.i1);let h='<table><tr><th></th>'+wks.map((x,j)=>{const m=dates[x[0]].slice(5,7),pm=j?dates[wks[j-1][0]].slice(5,7):'';return '<th>'+(m!==pm?(+m)+'월':'')+'</th>'}).join('')+'<th></th></tr>';
 GO.forEach(g=>{let ks=Object.keys(byKey).filter(k=>gOf(k)===g&&(g==='investor'||byKey[k].some(i=>i.score!=null)));if(!ks.length)return;
  if(R[ks[0]])ks.sort((a,b)=>Object.keys(R).indexOf(a)-Object.keys(R).indexOf(b));else ks.sort((a,b)=>(b==='stanley_druckenmiller')-(a==='stanley_druckenmiller')||byKey[b].length-byKey[a].length);
  if(g==='sellside')ks=ks.filter(k=>byKey[k].filter(i=>i.score!=null).length>=2);
  const op=!!HMOPEN[g];h+='<tr class="g" data-g="'+g+'" style="cursor:pointer"><td colspan="'+(wks.length+2)+'" style="color:'+gc(g)+'">'+(op?'▼ ':'▶ ')+G7[g]+' <span class="dim" style="font-weight:400">('+ks.length+'명)</span></td></tr>';
  ks.forEach(k=>{h+='<tr data-gr="'+g+'"'+(op?'':' hidden')+'><td class="nm" style="color:'+gc(g)+'">'+esc(nm(k))+(roleOf(k)?'<small>'+esc(roleOf(k))+'</small>':'')+'</td>';
   wks.forEach(([i0,wi])=>{const a=dates[i0],b=dates[Math.min(N-1,i0+6)];const all=byKey[k].filter(i=>i.date>=a&&i.date<=b),its=all.filter(i=>i.score!=null);
    if(!all.length){h+='<td class="c e"></td>';return;}
    if(!its.length){h+='<td class="c n" data-k="'+k+'" data-w="'+wi+'" title="'+esc(nm(k))+' '+a.slice(5)+'~'+b.slice(5)+' · 금리 언급 없는 발언 '+all.length+'건">·</td>';return;}
    const m=its.reduce((s,i)=>s+i.score,0)/its.length;
    h+='<td class="c" style="background:'+col(m)+';color:'+ink(m)+'" data-k="'+k+'" data-w="'+wi+'" title="'+esc(nm(k))+' '+a.slice(5)+'~'+b.slice(5)+' · 평균 '+f1(m)+' · '+its.length+'건">'+(Math.round(m*10)/10).toString().replace(/\.0$/,'')+'</td>';});
   const [lv]=lastAt(D.levels[k],W.i1);h+='<td class="lv">'+(lv==null?'–':'<span class="chip" style="background:'+col(lv)+';color:'+ink(lv)+'">'+lv.toFixed(1)+'</span>')+'</td></tr>';});});
 document.getElementById('hm').innerHTML=h+'</table>';
 document.querySelectorAll('#hm tr.g[data-g]').forEach(r=>r.onclick=()=>{const g=r.dataset.g;HMOPEN[g]=!HMOPEN[g];drawHM();});
 document.querySelectorAll('.hm td.c[data-k]').forEach(c=>c.onclick=()=>{F={g:'',k:c.dataset.k,d:'',m:'',w:+c.dataset.w};sync();render();const d=document.getElementById('d-led');d.open=true;d.scrollIntoView({behavior:'smooth',block:'start'});});}

// ---- 백테스트 표 ----
let btMode='clean';
function cell(x){if(!x||x[0]==null)return '<td class="dim">–<small> ('+(x?x[2]:0)+')</small></td>';const strong=x[1]<0.1;return '<td'+(strong?' style="font-weight:700"':'')+'>'+(x[0]>0?'+':'')+x[0].toFixed(2)+'<small class="dim"> ('+x[2]+(x[1]<0.05?', p&lt;.05':x[1]<0.1?', p&lt;.1':'')+')</small></td>';}
function rank(a){const s=a.map((v,i)=>[v,i]).sort((x,y)=>x[0]-y[0]),r=Array(a.length);let i=0;while(i<s.length){let j=i;while(j+1<s.length&&s[j+1][0]===s[i][0])j++;const rk=(i+j)/2+1;for(let k=i;k<=j;k++)r[s[k][1]]=rk;i=j+1;}return r;}
function tP(t,df){const f=x=>Math.pow(1+x*x/df,-(df+1)/2),simp=(a,b,n)=>{const h=(b-a)/n;let s=f(a)+f(b);for(let i=1;i<n;i++)s+=f(a+i*h)*(i%2?4:2);return s*h/3;};const a=Math.abs(t);if(a>200)return 0;return Math.min(1,simp(a,a+300,3000)/simp(0,300,3000));}
function sp(x,y){const xs=[],ys=[];x.forEach((v,i)=>{if(v!=null&&y[i]!=null){xs.push(v);ys.push(y[i]);}});const n=xs.length;if(n<P.min_n||new Set(xs).size<2||new Set(ys).size<2)return [null,null,n];
 const rx=rank(xs),ry=rank(ys),mx=rx.reduce((a,b)=>a+b)/n,my=ry.reduce((a,b)=>a+b)/n;let sxy=0,sxx=0,syy=0;for(let i=0;i<n;i++){sxy+=(rx[i]-mx)*(ry[i]-my);sxx+=(rx[i]-mx)**2;syy+=(ry[i]-my)**2;}
 const r=sxy/Math.sqrt(sxx*syy),t=Math.abs(r)>=0.9999?1e9:r*Math.sqrt((n-2)/(1-r*r));return [Math.round(r*100)/100,n>2?tP(t,n-2):1,n];}
let btSort='hit',btDir=-1;
const BTC=[['name','인물',''],['nn','발언 수',''],['mean','평균 점수','0~10'],['a','서프라이즈 ↔ 금리 기대','당일, ρ (N)'],['b','서프라이즈 ↔ 금리 기대','2일'],['c','서프라이즈 ↔ 2년물','당일'],['d','점수 ↔ 금리 기대','수준 그대로'],['hit','방향 적중','2년물, % (N)'],['abs','발언일 |2년물 변화|',''],['wk','주간 동행','전체 기간 고정']];
function drawBT(){const m=btMode,by={};D.events.filter(e=>inW(e.date)).forEach(e=>{(by[e.key]=by[e.key]||[]).push(e)});const wkm={};D.speaker_weekly.forEach(w=>wkm[w.key]=w);
 let bs=0,bn=0,prev=null;D.market_tdays.forEach(d=>{if(!inW(d))return;const v=D.market.y2[dates.indexOf(d)];if(v!=null&&prev!=null){bs+=Math.abs(v-prev)*100;bn++;}if(v!=null)prev=v;});const base=bn?bs/bn:null;
 const rows=Object.keys(by).map(k=>{const all=by[k],cl=all.filter(e=>!e.data_day&&!(e.fomc_day&&!['warsh','powell'].includes(e.key))),g=m==='clean'?cl:all,c=x=>g.map(e=>e[x]);
  const hx=g.filter(e=>e.surprise!=null&&e.d_y2!=null&&e.surprise!==0&&e.d_y2!==0);
  return {key:k,g7:all[0].g7,n:all.length,nn:g.length,mean:all.reduce((s,e)=>s+e.score,0)/all.length,a:sp(c('surprise'),c('d_dec')),b:sp(c('surprise'),c('d_dec2')),c:sp(c('surprise'),c('d_y2')),d:sp(c('score'),c('d_dec')),
   hit:hx.length>=P.min_n?[hx.filter(e=>Math.sign(e.surprise)===Math.sign(e.d_y2)).length/hx.length*100,hx.length]:null,abs:g.length?g.reduce((s,e)=>s+Math.abs(e.d_y2||0),0)/g.length:null,wk:wkm[k]?wkm[k].same:null};}).filter(r=>r.n>=P.min_n);
 const val=r=>btSort==='name'?nm(r.key):btSort==='nn'||btSort==='mean'||btSort==='abs'?r[btSort]:(r[btSort]&&r[btSort][0]!=null?r[btSort][0]:null);
 rows.sort((x,y)=>{const a=val(x),b=val(y);if(a==null&&b==null)return y.nn-x.nn;if(a==null)return 1;if(b==null)return -1;return (typeof a==='string'?a.localeCompare(b):a-b)*btDir||y.nn-x.nn;});
 let h='<tr>'+BTC.map(c=>'<th class="sort" data-s="'+c[0]+'">'+c[1]+(btSort===c[0]?(btDir<0?' ▼':' ▲'):'')+'<small>'+(c[0]==='nn'?(m==='clean'?'제외 후':'전체'):c[0]==='abs'?'이 기간 평소 '+(base==null?'–':base.toFixed(1)+'bp'):c[2])+'</small></th>').join('')+'</tr>';
 rows.forEach(r=>{h+='<tr'+(r.nn<10?' class="lo"':'')+'><td>'+who(r.key)+' <span class="dim">'+esc(roleOf(r.key)||G7[r.g7])+'</span></td><td>'+r.nn+'</td><td>'+f1(r.mean)+'</td>'+cell(r.a)+cell(r.b)+cell(r.c)+cell(r.d)+'<td>'+(r.hit?r.hit[0].toFixed(0)+'%<small class="dim"> ('+r.hit[1]+')</small>':'<span class="dim">–</span>')+'</td><td>'+(r.abs==null?'–':r.abs.toFixed(1)+'bp')+'</td>'+(r.wk?cell(r.wk):'<td class="dim">–</td>')+'</tr>';});
 const t=document.getElementById('bt');t.innerHTML=h;if(!rows.length)t.innerHTML+='<tr><td colspan="10" class="dim">이 기간에 발언 '+P.min_n+'건 이상인 인물이 없음</td></tr>';
 t.querySelectorAll('th[data-s]').forEach(th=>th.onclick=()=>{const s=th.dataset.s;if(btSort===s)btDir=-btDir;else{btSort=s;btDir=s==='name'?1:-1;}drawBT();});}
document.querySelectorAll('[data-bt]').forEach(b=>b.onclick=()=>{btMode=b.dataset.bt;document.querySelectorAll('[data-bt]').forEach(x=>x.classList.toggle('on',x===b));drawBT();});drawBT();
document.getElementById('btnote').innerHTML='서프라이즈 = 그날 발언 점수 − 그 인물의 직전 수준. 금리 기대 = 연방기금 선물 2027년 1월물 내재 금리(12/9 회의 뒤 정책금리 기대). 시장 변화 = 발언일(ET '+P.cutoff_et+' 이후 발언은 다음 거래일)의 금리 기대·2년물 변화(bp). ρ가 +면 "평소보다 매파적으로 말한 날 금리 기대가 올랐다"는 뜻. 발언 '+P.min_n+'건 미만은 계산 안 함, 10건 미만은 흐리게. <b>같은 날 여러 명이 말하면 누구 때문인지 가를 수 없고, 표본이 작아 상관은 참고용임.</b>';
(function(){const L=D.leadlag,names={voter26:'2026 투표권자',voter26_cw:'2026 투표권자(의장 3배)',chair:'의장',fed_all:'연준 전체',nonvoter:'비투표 총재',political:'트럼프·베센트'};
 let h='<tr><th>묶음</th>'+[-3,-2,-1,0,1,2,3].map(l=>'<th>'+(l>0?'+':'')+l+'주</th>').join('')+'</tr>';
 Object.keys(names).forEach(k=>{if(!L[k])return;h+='<tr><td>'+names[k]+'</td>'+[-3,-2,-1,0,1,2,3].map(l=>cell(L[k][String(l)])).join('')+'</tr>';});document.getElementById('ll').innerHTML=h;})();

// ---- 발언 한 건 ----
const TIER={official_text:'공식 원문',official_transcript:'공식 녹취',full_interview_transcript:'인터뷰 전문',news_direct_quote:'보도 속 직접 인용',jae_notion:'Jae 노션 아카이브'};
function itemHTML(it,extra){const kr=KR[it.id]||it.summary_kr||it.summary||'',g=it.g7;
 const src=it.source_tier==='jae_notion'?'<a href="'+esc(it.notion_url)+'" target="_blank" rel="noopener">Jae 노션 아카이브</a> · <a href="'+esc(it.source_url)+'" target="_blank" rel="noopener">원본</a>':'<a href="'+esc(it.source_url)+'" target="_blank" rel="noopener">원문</a> · '+(TIER[it.source_tier]||it.source_tier||'');
 return '<div class="item"><div class="h"><span class="dim">'+it.date+'</span><span class="who" style="color:'+gc(g)+'">'+esc(nm(it.key))+'</span><span class="gtag" style="color:'+gc(g)+'">'+G7[g]+'</span><span class="dim">'+esc(it.firm&&it.disp?(it.speaker||ssRole(it.disp)):roleOf(it.key))+'</span>'+chip(it.score)+(extra||'')+(it.drivers||[]).map(d=>'<span class="tag">'+(DRV[d]||d)+'</span>').join('')+(it.call?'<span class="tag">'+esc(it.call)+'</span>':'')+(it.credit_view?'<span class="tag">신용: '+esc(it.credit_view)+'</span>':'')+'</div><div class="s">'+esc(kr)+'</div><div class="q">“'+esc(it.quote)+'”'+(it.ai_quote&&it.ai_quote!==it.quote?'<br>“'+esc(it.ai_quote)+'”':'')+'</div><div class="dim" style="font-size:11px;margin-top:2px">'+esc(it.occasion||'')+' · '+src+(it.verify==='near'?' · 인용 근사 일치':'')+'</div></div>';}

// ---- 변곡 로그 ----
function drawInfl(){const ev=D.events.filter(e=>inW(e.date)&&e.surprise!=null&&Math.abs(e.surprise)>=2.5&&['board','voter','nonvoter','political'].includes(e.group)).sort((a,b)=>b.date.localeCompare(a.date));
 document.querySelector('#d-infl summary small').textContent='직전까지의 본인 수준보다 2.5점(한 단계) 이상 달라진 발언 · '+ev.length+'건';
 document.getElementById('infl').innerHTML=ev.length?ev.map(e=>itemHTML(byId[e.id],'<span class="tag">직전 수준 대비 '+fs(e.surprise)+'</span><span class="tag">금리 기대 '+(e.d_dec==null?'–':(e.d_dec>0?'+':'')+e.d_dec.toFixed(1)+'bp')+' · 2년물 '+(e.d_y2==null?'–':(e.d_y2>0?'+':'')+e.d_y2.toFixed(0)+'bp')+'</span>')).join(''):'<div class="dim">해당 없음</div>';}

// ---- 하우스 콜·투자자 ----
(function(){let h='';const lc=[];Object.values((D.extra||{}).latest_calls||{}).forEach(a=>(a||[]).forEach(x=>lc.push(x)));
 if(lc.length){h+='<div style="overflow-x:auto"><table><tr><th>하우스</th><th>기준일</th><th>다음 결정</th><th>2027 경로</th><th>출처</th></tr>'+lc.sort((a,b)=>String(b.as_of).localeCompare(String(a.as_of))).map(x=>'<tr><td style="color:'+gc('sellside')+';font-weight:700">'+esc(x.firm)+'</td><td>'+esc(x.as_of||'–')+'</td><td style="text-align:left">'+esc(x.next_move||'–')+'</td><td style="text-align:left">'+esc(x.path_2027||'–')+'</td><td>'+(x.source_url?'<a href="'+esc(x.source_url)+'" target="_blank" rel="noopener">링크</a>':'–')+'</td></tr>').join('')+'</table></div>';}
 const cv=D.items.filter(i=>i.credit_view).sort((a,b)=>b.date.localeCompare(a.date));
 if(cv.length){const CV={stress_rising:'스트레스 커짐',contained:'관리 가능',no_stress:'스트레스 없음',bubble_warning:'버블 경고',constructive:'긍정적'};const c={};cv.forEach(i=>c[i.credit_view]=(c[i.credit_view]||0)+1);
  h+='<div class="note" style="margin-top:10px">투자자·은행 CEO의 신용·AI 자금조달 발언 '+cv.length+'건: '+Object.keys(c).map(k=>(CV[k]||k)+' '+c[k]).join(' · ')+'</div>'+cv.map(i=>itemHTML(i)).join('');}
 if(!h)document.getElementById('calls-card').style.display='none';else document.getElementById('calls').innerHTML=h;})();

// ---- 원장 ----
function opts(id,arr,first){document.getElementById(id).innerHTML='<option value="">'+first+'</option>'+arr.map(a=>'<option value="'+a[0]+'">'+esc(a[1])+'</option>').join('');}
opts('f-g',GO.filter(g=>D.items.some(i=>i.g7===g)).map(g=>[g,G7[g]]),'그룹 전체');
opts('f-k',Object.keys(byKey).sort((a,b)=>GO.indexOf(gOf(a))-GO.indexOf(gOf(b))||byKey[b].length-byKey[a].length).map(k=>[k,nm(k)+' ('+byKey[k].length+')']),'인물 전체');
opts('f-d',Object.keys(DRV).filter(d=>D.items.some(i=>(i.drivers||[]).includes(d))).map(d=>[d,DRV[d]]),'근거 전체');
opts('f-m',[...new Set(D.items.map(i=>i.date.slice(0,7)))].sort().reverse().map(m=>[m,m]),'월 전체');

function sync(){['g','k','d','m'].forEach(x=>document.getElementById('f-'+x).value=F[x]);}
['g','k','d','m'].forEach(x=>document.getElementById('f-'+x).onchange=e=>{F[x]=e.target.value;F.w=null;render();});
document.getElementById('f-x').onclick=()=>{F={g:'',k:'',d:'',m:'',w:null};sync();render();};
let NOOP=true;document.getElementById('f-nn').onclick=e=>{NOOP=!NOOP;e.target.classList.toggle('on',NOOP);render();};
function render(){let a=D.items.filter(i=>inW(i.date)&&(!NOOP||i.score!=null)&&(!F.g||i.g7===F.g)&&(!F.k||i.key===F.k)&&(!F.d||(i.drivers||[]).includes(F.d))&&(!F.m||i.date.startsWith(F.m)));
 if(F.w!=null){const s=dates[wk[F.w]],e=dates[Math.min(N-1,wk[F.w]+6)];a=a.filter(i=>i.date>=s&&i.date<=e);}
 a.sort((x,y)=>y.date.localeCompare(x.date));document.getElementById('f-n').textContent=a.length+'건'+(a.length>200?' (최근 200건만 표시)':'');
 document.getElementById('list').innerHTML=a.slice(0,200).map(i=>itemHTML(i)).join('')||'<div class="dim">해당 없음</div>';}

// ---- 기간 막대 ----
const r0=document.getElementById('r0'),r1=document.getElementById('r1');r0.max=r1.max=N-1;
const PRESETS=[['1M',30],['3M',91],['6M',182],['전체',0]],pbox=document.getElementById('presets');
PRESETS.forEach(p=>{const b=document.createElement('button');b.type='button';b.textContent=p[0];b.onclick=()=>setWindow(p[1]?Math.max(0,N-1-p[1]):0,N-1,p[0]);pbox.appendChild(b);});
function drawOverview(){const cv=document.getElementById('overview'),w=cv.clientWidth,h=30,r=window.devicePixelRatio||1;cv.width=w*r;cv.height=h*r;const g=cv.getContext('2d');g.scale(r,r);g.clearRect(0,0,w,h);
 const x=i=>6+(w-12)*i/(N-1);g.fillStyle='#f4f3f0';g.fillRect(0,4,w,22);g.fillStyle='rgba(42,120,214,.16)';g.fillRect(x(W.i0),4,x(W.i1)-x(W.i0),22);
 const line=(a,lo,hi,c)=>{g.beginPath();let on=false;a.forEach((v,i)=>{if(v==null)return;const y=25-(v-lo)/(hi-lo)*20;if(on)g.lineTo(x(i),y);else{g.moveTo(x(i),y);on=true;}});g.strokeStyle=c;g.lineWidth=1.2;g.stroke();};
 const z=D.market.zq.filter(v=>v!=null);if(z.length)line(D.market.zq,Math.min(...z),Math.max(...z),'#9a9993');line(D.index.voter26,0,10,'#2a78d6');}
function setWindow(a,b,preset){a=Math.max(0,Math.min(a,N-2));b=Math.max(a+7,Math.min(b,N-1));W.i0=a;W.i1=b;r0.value=a;r1.value=b;
 [...pbox.children].forEach((btn,i)=>btn.classList.toggle('on',PRESETS[i][0]===preset));
 document.getElementById('d0').value=dates[a].replace(/-/g,'.');document.getElementById('d1').value=dates[b].replace(/-/g,'.');
 document.getElementById('range-label').textContent=(b-a+1)+'일';
 drawOverview();drawTiles();
 [C1,C3].forEach(c=>{c.options.scales.x.min=a;c.options.scales.x.max=b;});after1(C1);after3(C3);C1.update();C3.update();drawWoW();
 drawHM();drawAI();drawInfl();drawBT();render();
 const n=D.items.filter(i=>inW(i.date)).length;document.getElementById('led-n').textContent='이 기간 '+n+'건 · 그룹·인물·근거·월로 거르기';}
function onSlide(e){let a=+r0.value,b=+r1.value;if(b-a<7){if(e.target===r0)a=Math.max(0,b-7);else b=Math.min(N-1,a+7);}setWindow(a,b,null);}
r0.addEventListener('input',onSlide);r1.addEventListener('input',onSlide);
function parseD(s,ref){s=s.trim();let m;if((m=s.match(/^(\d{4})[.\-\/](\d{1,2})[.\-\/](\d{1,2})$/)))return m[1]+'-'+m[2].padStart(2,'0')+'-'+m[3].padStart(2,'0');
 if((m=s.match(/^(\d{2})(\d{2})(\d{2})$/)))return '20'+m[1]+'-'+m[2]+'-'+m[3];if((m=s.match(/^(\d{1,2})[\/.\-](\d{1,2})$/)))return ref.slice(0,4)+'-'+m[1].padStart(2,'0')+'-'+m[2].padStart(2,'0');return null;}
['d0','d1'].forEach((id,j)=>{const el=document.getElementById(id);el.addEventListener('keydown',e=>{if(e.key!=='Enter')return;const d=parseD(el.value,dates[j?W.i1:W.i0]);let i=d?dates.findIndex(x=>x>=d):-1;
  if(d&&i<0&&d>dates[N-1])i=N-1;if(i<0){el.classList.add('bad');return;}el.classList.remove('bad');if(j)setWindow(Math.min(W.i0,i-7),i,null);else setWindow(i,Math.max(W.i1,i+7),null);el.blur();});});
(function(){const ax=document.getElementById('rng-axis'),ms=[...new Set(dates.map(d=>d.slice(0,7)))];ax.innerHTML=ms.filter((_,i)=>i%Math.ceil(ms.length/8)===0).map(m=>'<span>'+m.slice(2).replace('-','.')+'</span>').join('');})();
window.addEventListener('resize',drawOverview);
setWindow(0,N-1,'전체');
document.getElementById('method').innerHTML='<p><b>수집</b>: '+P.start+' 이후 공개 발언을 인물별로 모으고, 각 건마다 출처 페이지를 스크립트로 직접 받아 인용 문장이 글자 그대로 있는지 대조함. 대조에 실패한 건과 원문을 열 수 없던 건('+P.n_unverified+'건)은 지수·백테스트에서 뺌. 드러켄밀러는 Jae 노션 아카이브의 인터뷰 전문을 원장으로 삼아 그 사본과 대조함.</p><p><b>점수</b>: 그날 금리 경로에 대해 한 말만 채점. 10 곧 인상 필요·인상 소수의견 / 7.5 인플레 위험 우세·인상에 열림 / 5 동결 적절·양쪽 위험 / 2.5 성장·고용·금융안정 위험 우세·추가 인상 반대 / 0 곧 인하 필요. 연준 밖 인물은 "연준이 무엇을 해야 한다 / 할 것이다"를 같은 눈금으로 채점함. 통화정책 내용이 없는 발언은 점수 없이 원장에만 둠. 채점은 모델이 했고, 두 단계 사이에서 애매하면 5에 가까운 쪽으로 둠.</p><p><b>수준·지수</b>: 인물별로 발언 점수를 반감기 '+P.half_life_days+'일로 지수 가중 평균. 2026 투표권자 지수는 그 시점 재임 중인 투표권자의 단순 평균(마이런은 5월까지, 워시는 5/22부터). 의장 선은 5/15까지 파월, 5/22부터 워시.</p><p><b>백테스트 한계</b>: 인물별 발언 수가 적음. 발언 시각을 모르는 건은 당일 종가 변화에 붙였고, 지표 발표일에는 지표가 금리를 움직였을 가능성이 커서 따로 뺀 판을 기본으로 함. 상관은 인과가 아님.</p>';
</script></body></html>"""


def main() -> None:
    a = json.loads((HERE / "analysis.json").read_text(encoding="utf-8"))
    krp = HERE / "kr.json"
    kr = json.loads(krp.read_text(encoding="utf-8")) if krp.exists() else {}
    # 내장 데이터 다이어트: 화면에서 안 쓰는 칸 제거
    for it in a["items"]:
        for k in ("verify_note", "collector", "date_basis", "score_note", "raw_score", "summary" if (it["id"] in kr or it.get("summary_kr")) else "_"):
            it.pop(k, None)
    kr = {k: v for k, v in kr.items() if any(i["id"] == k for i in a["items"])}
    dj, kj = json.dumps(a, ensure_ascii=False), json.dumps(kr, ensure_ascii=False)
    # 1) 로컬 단독 파일(데이터 내장)
    html = TEMPLATE.replace("__DATA__", dj.replace("</", "<\\/")).replace("__KR__", kj.replace("</", "<\\/"))
    import sys
    out = (REPO / "docs" / "fedspeak.html") if "--docs" in sys.argv else (HERE / "fedspeak.html")
    out.write_text(html, encoding="utf-8")
    # 2) 공유용 Artifact: 문서 뼈대 없이, 데이터는 옆 파일(data.json)에서 불러옴
    if "--docs" in sys.argv:
        print(f"{out} {len(html) / 1024:.0f}KB · 한국어 요약 {len(kr)}건")
        return
    art = HERE / "artifact"
    art.mkdir(exist_ok=True)
    t = TEMPLATE
    head_end = t.index("<title>")
    t = t[head_end:]
    t = t.replace("</style></head><body>", "</style>").replace("</script></body></html>", "</script>")
    t = t.replace("const D=__DATA__, KR=__KR__;",
                  "fetch('data.json').then(r=>{if(!r.ok)throw new Error(r.status);return r.json();}).then(function(J){const D=J.D,KR=J.K;")
    t = t.replace("</script>", "}).catch(e=>{document.getElementById('hdr').textContent='데이터를 불러오지 못함 ('+e.message+'). 새로고침해 보세요.';});\n</script>", 1) if False else t
    # 마지막 </script> 앞에서 fetch 블록을 닫는다
    k = t.rindex("</script>")
    t = t[:k] + "}).catch(e=>{document.getElementById('hdr').textContent='데이터를 불러오지 못함 ('+e.message+'). 새로고침해 보세요.';});\n" + t[k:]
    (art / "index.html").write_text(t, encoding="utf-8")
    (art / "data.json").write_text(json.dumps({"D": a, "K": kr}, ensure_ascii=False), encoding="utf-8")
    print(f"{out.name} {len(html) / 1024:.0f}KB · artifact/index.html {len(t) / 1024:.0f}KB + data.json · 한국어 요약 {len(kr)}건")


if __name__ == "__main__":
    main()
