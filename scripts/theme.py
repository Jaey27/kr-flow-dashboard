# -*- coding: utf-8 -*-
"""다크/라이트 테마 (11/23 Jae: 기본 라이트 + 초록·빨강·파랑, 다크는 토글로 유지).

화면 코드(render.py · render_macro.py · render_sector.py …)에는 다크용 색이 글자 그대로 박혀 있다.
여기서 굽는 시점에 그 색들을 CSS 변수로 바꿔 한 페이지가 두 테마를 모두 그리게 한다.

- themeify(src): 데이터·Chart.js 를 넣기 '전'의 화면 코드(CSS+HTML+JS)에 적용한다.
  1) 첫 :root{…} 블록은 그대로 두고(변수 정의 자체가 바뀌면 안 됨)
  2) 다크 고정색 → var(--…) / rgba(var(--…-rgb),a)
  3) JS 안에서 색 하나만 담은 문자열('rgba(var(--ac-rgb),.13)')은 T('…') 로 감싼다.
     캔버스(Chart.js)는 var() 를 못 읽으므로 T() 가 실행 시점에 실제 색으로 풀어 준다.
  4) :root 뒤에 새 변수(다크 값)와 라이트 덮어쓰기 블록을 붙인다.
- HEAD: <head> 맨 앞에 넣는 스크립트 — 저장된 테마 적용 + T() 정의.
- TOGGLE: 헤더에 넣는 전환 버튼(누르면 저장하고 새로고침 → 차트도 새 색으로 다시 그림).
"""

from __future__ import annotations

import re

# (다크 고정색, 바꿔 넣을 CSS 식) — 긴 것·구체적인 것부터
_RGBA = [
    ("151,252,228", "--ac-rgb"),     # 강조(민트) — 테두리·격자·옅은 바탕
    ("6,30,32", "--tip-rgb"),        # 툴팁 바탕
    ("157,179,176", "--gray-rgb"),   # 회색 보조선(코스피 겹치기)
    ("200,215,212", "--ov-rgb"),     # 매크로 탭 코스피 겹치기
    ("232,255,250", "--text-rgb"),   # 액면가 100 점선 등
    ("255,255,255", "--hi-rgb"),     # 흰색 옅은 강조(자금조달 표 칸 바탕)
]
_HEX = [
    ("#97FCE4", "var(--hl-teal)"), ("#50D2C1", "var(--hl-teal-dim)"),
    ("#F2FFFC", "var(--text)"), ("#B4D6D1", "var(--text-dim)"), ("#8FB3AE", "var(--text-muted)"),
    ("#061E20", "var(--on-ac)"), ("#0b2b2d", "var(--surface-2)"), ("#0b1212", "var(--surface)"),
    ("#9db3b0", "var(--c-gray)"),
    ("#c9d1d9", "var(--c-soft)"), ("#c8d6d4", "var(--c-soft)"), ("#c9d6d4", "var(--c-soft)"),
    ("#fca5a5", "var(--up)"), ("#93c5fd", "var(--down)"),
    ("#ffffff", "var(--c-white)"), ("#c9c2ff", "var(--c-vio2)"), ("#ff9cc4", "var(--c-pink2)"),
]

DARK_EXTRA = ("--ac-rgb:151,252,228;--on-ac:#061E20;--surface-2:#0b2b2d;--tip-rgb:6,30,32;--gray-rgb:157,179,176;"
              "--c-gray:#9db3b0;--c-soft:#c9d1d9;--text-rgb:232,255,250;--ov-rgb:200,215,212;--hi-rgb:255,255,255;--c-white:#ffffff;--c-vio2:#c9c2ff;--c-pink2:#ff9cc4;--page:#000000;color-scheme:dark")

# 라이트: 바탕 밝은 회색·카드 흰색, 강조 = 초록, 상승 빨강 · 하락 파랑(흰 바탕 명암비 4.8~5.5:1)
LIGHT = (":root[data-theme=\"light\"]{"
         "--hl-teal:#15803D;--hl-teal-dim:#166534;--hl-teal-soft:rgba(21,128,61,.10);--hl-teal-border:rgba(21,128,61,.32);"
         "--bg-0:#F3F5F7;--surface:#FFFFFF;--text:#17202B;--text-dim:#3E4A59;--text-muted:#657181;"
         "--up:#DC2626;--down:#2563EB;--warn:#B45309;--shadow:0 2px 12px rgba(15,23,42,.08);"
         "--ac-rgb:21,128,61;--on-ac:#FFFFFF;--surface-2:#EEF2F5;--tip-rgb:255,255,255;--gray-rgb:91,102,117;"
         "--c-gray:#6B7684;--c-soft:#4B5563;--text-rgb:23,32,43;--ov-rgb:91,102,117;--hi-rgb:23,32,43;--c-white:#17202B;--c-vio2:#6D28D9;--c-pink2:#BE185D;--page:#F3F5F7;color-scheme:light}\n"
         "html,body{background:var(--page) !important;background-color:var(--page) !important}\n"
         ".theme-btn{font:inherit;font-size:12px;font-weight:600;color:var(--text-dim);background:var(--surface);"
         "border:1px solid var(--hl-teal-border);border-radius:999px;padding:4px 12px;cursor:pointer;margin-left:8px}\n"
         ".theme-btn:hover{color:var(--text);border-color:var(--hl-teal)}\n"
         ":root[data-theme=\"light\"] .card,:root[data-theme=\"light\"] .tile{box-shadow:0 1px 3px rgba(15,23,42,.06)}\n"
         # 경제지표 탭에 끼워 넣는 CPI 페이지(cpi.html)는 자체 다크 화면 — 라이트에서는 임시로 색 반전(전용 라이트 화면은 다음 작업)
         ":root[data-theme=\"light\"] #ec-cpi{filter:invert(.92) hue-rotate(180deg)}\n"
         # 리스크 탭 자금조달 표: 다크용 파스텔 글씨는 흰 바탕에서 안 읽힌다 → 같은 색상을 어둡게
         ":root[data-theme=\"light\"] .fund-cal .b{color:#C2410C}:root[data-theme=\"light\"] .fund-cal .e{color:#6D28D9}\n"
         ":root[data-theme=\"light\"] .fund-cal .x[style*=\"color\"],:root[data-theme=\"light\"] .fund-cal [style*=\"#f0756a\"]{color:#DC2626 !important}\n"
         ":root[data-theme=\"light\"] .fund-cal td.l>b[style*=\"color\"],:root[data-theme=\"light\"] .rk-st{filter:brightness(.62) saturate(1.5)}\n")

HEAD = """<script>
(function(){var t='light';try{t=localStorage.getItem('krflow.theme')||'light';}catch(e){}
  if(t!=='dark'&&t!=='light') t='light';document.documentElement.setAttribute('data-theme',t);window.__THEME__=t;
  var cs=null,memo={};
  // 색 문자열 안의 var(--x) 를 실제 값으로 푼다 — 캔버스(Chart.js)는 CSS 변수를 못 읽는다
  window.T=function(c){if(typeof c!=='string'||c.indexOf('var(')<0) return c;if(memo[c]) return memo[c];
    cs=cs||getComputedStyle(document.documentElement);
    return memo[c]=c.replace(/var\\((--[\\w-]+)\\)/g,function(_,n){return cs.getPropertyValue(n).trim();});};
  window.__setTheme=function(n){try{localStorage.setItem('krflow.theme',n);}catch(e){}location.reload();};
})();
</script>"""

TOGGLE = ("<button type=\"button\" class=\"theme-btn\" id=\"theme-btn\" "
          "onclick=\"__setTheme(window.__THEME__==='dark'?'light':'dark')\">테마</button>"
          "<script>document.getElementById('theme-btn').textContent=window.__THEME__==='dark'?'라이트 모드로':'다크 모드로';</script>")

_ROOT = re.compile(r":root\{[^}]*\}")
_SOLO = re.compile(r"'((?:rgba\(var\(--[\w-]+\),[0-9.]+\))|(?:var\(--[\w-]+\)))'")


def themeify(src: str) -> str:
    m = _ROOT.search(src)
    root = m.group(0) if m else ""
    if m:
        src = src[:m.start()] + "\x00ROOT\x00" + src[m.end():]
    for rgb, var in _RGBA:
        src = re.sub(r"rgba\(\s*" + rgb.replace(",", r"\s*,\s*") + r"\s*,", f"rgba(var({var}),", src)
    for hx, expr in _HEX:
        src = re.sub(re.escape(hx) + r"(?![0-9a-fA-F])", expr, src, flags=re.I)
    src = _SOLO.sub(lambda g: "T('" + g.group(1) + "')", src)
    if m:
        root2 = root[:-1].rstrip().rstrip(";") + ";" + DARK_EXTRA + "}"
        src = src.replace("\x00ROOT\x00", root2 + "\n" + LIGHT, 1)
    return src
