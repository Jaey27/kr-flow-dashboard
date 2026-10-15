# -*- coding: utf-8 -*-
"""섹터 수급 전용 페이지 → sector.html (+ docs/sector.html).

당일 · 1주(5영업일) · 2주(10영업일) 창으로 네이버 업종 78개의 개인·기관·외국인 순매수를 본다.
기준일은 텍스트로 입력(Enter)하거나 ◀ ▶ 로 하루씩 옮긴다. 상위 종목은 최신 기준일에서만 나온다(원자료 60일 범위).
render.py 의 CSS·Chart.js·직렬화 함수를 그대로 쓴다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render  # noqa: E402

OUT = render.ROOT / "sector.html"
DOCS = render.ROOT / "docs" / "sector.html"

CSS = r"""
.sp-bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 14px;position:sticky;top:0;z-index:20;
  padding:10px 0;background:linear-gradient(180deg,rgba(6,30,32,.97) 75%,rgba(6,30,32,0))}
.sp-bar .lbl{font-size:12px;color:var(--text-muted)}
.sp-date{display:flex;align-items:center;gap:4px}
.sp-date button{background:rgba(151,252,228,.06);border:1px solid rgba(151,252,228,.15);color:var(--text-dim);border-radius:8px;
  padding:4px 9px;cursor:pointer;font:inherit;font-size:12px}
.sp-date button:hover{color:var(--hl-teal)}
.sp-sum{font-size:12px;color:var(--text-dim);font-variant-numeric:tabular-nums}
.inv3{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:16px}
@media (max-width:1100px){.inv3{grid-template-columns:1fr}}
.inv3 .card{margin:0}
.bars{position:relative;height:620px}
@media (max-width:768px){.bars{height:560px}}
table.st{width:100%;border-collapse:collapse;font-size:12.5px;font-variant-numeric:tabular-nums}
table.st th{position:sticky;top:0;background:#0b2b2d;text-align:right;font-size:11px;color:var(--text-muted);padding:7px 8px;
  border-bottom:1px solid rgba(151,252,228,.14);cursor:pointer;white-space:nowrap;user-select:none}
table.st th:first-child,table.st td:first-child{text-align:left}
table.st th.on{color:var(--hl-teal)}
table.st td{padding:6px 8px;border-bottom:1px solid rgba(151,252,228,.05);text-align:right;white-space:nowrap}
table.st tr.sec{cursor:pointer}
table.st tr.sec:hover td{background:rgba(151,252,228,.04)}
table.st tr.exp td{background:rgba(151,252,228,.03);white-space:normal;text-align:left;font-size:11.5px;color:var(--text-dim)}
table.st .heat{border-radius:4px;padding:2px 6px;display:inline-block;min-width:64px;text-align:right}
.st-wrap{max-height:none;overflow-x:auto}
.exp-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
@media (max-width:760px){.exp-grid{grid-template-columns:1fr}}
.exp-grid b{color:var(--text);font-size:11px}
.exp-grid a{color:inherit;text-decoration:none;border-bottom:1px dotted rgba(127,168,164,.5)}
.back{font-size:12px;color:var(--hl-teal-dim);text-decoration:none;border:1px solid rgba(151,252,228,.2);border-radius:999px;padding:5px 12px}
"""

JS = r"""
(function(){
'use strict';
var F=window.__SF__,D=F.dates,SF=F.sector,N=D.length;
var css=getComputedStyle(document.documentElement);function cv(n){return css.getPropertyValue(n).trim();}
var COL={up:cv('--up'),down:cv('--down'),text:cv('--text'),dim:cv('--text-dim'),muted:cv('--text-muted'),
  foreign:cv('--s-foreign'),inst:cv('--s-inst'),indiv:cv('--s-indiv'),grid:'rgba(151,252,228,.07)',zero:'rgba(151,252,228,.30)'};
var INV=['indiv','inst','foreign'],NAME={indiv:'개인',inst:'기관',foreign:'외국인'};
function nf(v,d){d=d||0;return Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});}
function eok(v){var a=Math.abs(v);return a>=10000?nf(v/10000,a>=100000?1:2)+'조':nf(Math.round(v))+'억';}
function sg(v){return (v>0?'+':'')+eok(v);}
var WD=['일','월','화','수','목','금','토'];
function dlong(s){var d=new Date(s+'T00:00:00');return s.replace(/-/g,'.')+' ('+WD[d.getDay()]+')';}
// 막대 끝 값 라벨: 순매수는 막대 오른쪽, 순매도는 왼쪽
var barLabels={id:'barLabels',afterDatasetsDraw:function(ch){
  var c=ch.ctx,meta=ch.getDatasetMeta(0),data=ch.data.datasets[0].data;
  c.save();c.font='600 10.5px -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo",sans-serif';c.textBaseline='middle';
  meta.data.forEach(function(el,i){var v=data[i];if(v==null) return;
    c.fillStyle=v>=0?'#fca5a5':'#93c5fd';c.textAlign=v>=0?'left':'right';
    c.fillText(sg(v),el.x+(v>=0?5:-5),el.y);});
  c.restore();}};
Chart.defaults.font.family='-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",sans-serif';
function ls(k,v){try{if(v===undefined) return localStorage.getItem('krsec.'+k);localStorage.setItem('krsec.'+k,v);}catch(e){return null;}}

// 섹터 데이터가 있는 날짜만 기준일 후보
var has=[];for(var i=0;i<N;i++) if(SF.trade[SF.names[0]][i]!=null) has.push(i);
var S={w:+(ls('w')||1),end:has[has.length-1],sort:'foreign',dir:-1,open:{}},charts={};
var PROV={};(SF.prov||[]).forEach(function(d){PROV[d]=1;});

function parseDate(t){
  t=(t||'').trim().replace(/\s/g,'');var m,y,mo,d;
  if((m=t.match(/^(\d{2})(\d{2})(\d{2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{4})[-./]?(\d{1,2})[-./]?(\d{1,2})$/))){y=+m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{2})[-./](\d{1,2})[-./](\d{1,2})$/))||(m=t.match(/^(\d{2})(\d{2})(\d{2})$/))){y=2000+ +m[1];mo=+m[2];d=+m[3];}
  else if((m=t.match(/^(\d{1,2})[-./](\d{1,2})$/))){y=+D[N-1].slice(0,4);mo=+m[1];d=+m[2];
    if(y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2)>D[N-1]) y-=1;}
  else return null;
  if(mo<1||mo>12||d<1||d>31) return null;
  return y+'-'+('0'+mo).slice(-2)+'-'+('0'+d).slice(-2);
}
function pad(pick){var mx=0,mn=0;pick.forEach(function(o){mx=Math.max(mx,o.v);mn=Math.min(mn,o.v);});
  var span=Math.max(mx-mn,1),g=span*0.42;return {min:mn<0?mn-g:-span*0.04,max:mx>0?mx+g:span*0.04};}
function win(){var k=has.indexOf(S.end);return has.slice(Math.max(0,k-S.w+1),k+1);}
function sums(){
  var idx=win(),out={};
  SF.names.forEach(function(n){var r={trade:0};INV.forEach(function(k){r[k]=0;});
    idx.forEach(function(i){INV.forEach(function(k){r[k]+=SF.net[k][n][i]||0;});r.trade+=SF.trade[n][i]||0;});out[n]=r;});
  return {idx:idx,by:out};
}
function topKey(){return S.end===has[has.length-1]&&SF.top[String(S.w)]?String(S.w):null;}

function draw(){
  var s=sums(),idx=s.idx,a=D[idx[0]],b=D[idx[idx.length-1]];
  document.getElementById('dinp').value=b.replace(/-/g,'.');
  document.getElementById('span').textContent=(S.w===1?dlong(b):dlong(a)+' ~ '+dlong(b))+' · '+idx.length+'영업일'+(PROV[b]?' · 잠정':' · 확정');
  Array.prototype.forEach.call(document.querySelectorAll('#wseg button'),function(x){x.classList.toggle('on',+x.dataset.w===S.w);});
  INV.forEach(function(k){
    var arr=SF.names.map(function(n){return {n:n,v:s.by[n][k]};}).sort(function(x,y){return y.v-x.v;});
    var pick=arr.slice(0,10).concat(arr.slice(-10)).filter(function(o,j,all){return all.indexOf(o)===j;});
    var tot=arr.reduce(function(t,o){return t+o.v;},0);
    document.getElementById('sum-'+k).textContent='업종 합계 '+sg(tot)+' · 상위 10 / 하위 10';
    var cfg={type:'bar',data:{labels:pick.map(function(o){return o.n;}),datasets:[{data:pick.map(function(o){return Math.round(o.v);}),
      backgroundColor:pick.map(function(o){return o.v>=0?COL.up:COL.down;}),borderRadius:2,barPercentage:.85,categoryPercentage:.9}]},
      plugins:[barLabels],
      options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,animation:false,
        plugins:{legend:{display:false},tooltip:{callbacks:{label:function(it){return ' '+NAME[k]+' '+sg(it.raw);}}}},
        scales:{x:{min:pad(pick).min,max:pad(pick).max,grid:{color:function(c){return c.tick&&c.tick.value===0?COL.zero:COL.grid;}},ticks:{color:COL.muted,font:{size:10},
          callback:function(v){var a=Math.abs(v);return a>=10000?nf(v/10000,1)+'조':nf(v)+'억';}}},
          y:{grid:{display:false},ticks:{color:COL.dim,font:{size:11},autoSkip:false}}}}};
    if(charts[k]) charts[k].destroy();charts[k]=new Chart(document.getElementById('c-'+k),cfg);
  });
  table(s);
}
function table(s){
  var tk=topKey(),rows=SF.names.map(function(n){return Object.assign({n:n},s.by[n]);});
  rows.sort(function(x,y){var r=S.sort==='n'?x.n.localeCompare(y.n,'ko'):(x[S.sort]-y[S.sort]);return S.dir<0?-r:r;});
  var mx=Math.max.apply(null,rows.map(function(r){return Math.max(Math.abs(r.indiv),Math.abs(r.inst),Math.abs(r.foreign));}))||1;
  function cell(v){var t=Math.min(1,Math.abs(v)/mx),al=0.06+0.6*Math.sqrt(t);
    return '<span class="heat" style="background:'+(v>=0?'rgba(248,113,113,'+al+')':'rgba(96,165,250,'+al+')')+'">'+sg(v)+'</span>';}
  var cols=[['n','섹터'],['foreign','외국인'],['inst','기관'],['indiv','개인'],['trade','거래대금']];
  var h='<table class="st"><thead><tr>'+cols.map(function(c){return '<th data-k="'+c[0]+'" class="'+(S.sort===c[0]?'on':'')+'">'+c[1]+(S.sort===c[0]&&c[0]!=='n'?(S.dir<0?' ▼':' ▲'):'')+'</th>';}).join('')+'</tr></thead><tbody>';
  rows.forEach(function(r){
    h+='<tr class="sec" data-n="'+r.n+'"><td>'+(S.open[r.n]?'▾ ':'▸ ')+r.n+'</td><td>'+cell(r.foreign)+'</td><td>'+cell(r.inst)+'</td><td>'+cell(r.indiv)+'</td><td>'+eok(r.trade)+'</td></tr>';
    if(S.open[r.n]){
      var body=tk?['foreign','inst','indiv'].map(function(k){var t=((SF.top[tk]||{})[k]||{})[r.n]||{buy:[],sell:[]};
        var li=function(x){return '<a href="https://m.stock.naver.com/domestic/stock/'+x[1]+'/total" target="_blank" rel="noopener">'+x[0]+'</a> '+sg(x[2]);};
        return '<div><b>'+NAME[k]+'</b><br>매수 '+(t.buy.map(li).join(' · ')||'–')+'<br>매도 '+(t.sell.map(li).join(' · ')||'–')+'</div>';}).join('')
        :'<div>상위 종목은 최신 기준일('+D[has[has.length-1]].replace(/-/g,'.')+')에서만 제공합니다.</div>';
      h+='<tr class="exp"><td colspan="5"><div class="exp-grid">'+body+'</div></td></tr>';
    }
  });
  var box=document.getElementById('tbl');box.innerHTML=h+'</tbody></table>';
  Array.prototype.forEach.call(box.querySelectorAll('th'),function(th){th.onclick=function(){var k=th.dataset.k;
    if(S.sort===k) S.dir*=-1; else {S.sort=k;S.dir=-1;} table(sums());};});
  Array.prototype.forEach.call(box.querySelectorAll('tr.sec'),function(tr){tr.onclick=function(){var n=tr.dataset.n;S.open[n]=!S.open[n];table(sums());};});
}
// 컨트롤
[[1,'당일'],[5,'1주 (5일)'],[10,'2주 (10일)']].forEach(function(o){var b=document.createElement('button');b.type='button';b.textContent=o[1];b.dataset.w=o[0];
  b.onclick=function(){S.w=o[0];ls('w',o[0]);draw();};document.getElementById('wseg').appendChild(b);});
var inp=document.getElementById('dinp');
inp.addEventListener('keydown',function(e){if(e.key!=='Enter') return;var iso=parseDate(inp.value);if(!iso){inp.classList.add('bad');return;}
  inp.classList.remove('bad');var best=has[0];has.forEach(function(i){if(D[i]<=iso) best=i;});S.end=best;draw();inp.blur();});
inp.addEventListener('focus',function(){inp.select();});
function step(dk){var k=has.indexOf(S.end)+dk;if(k>=0&&k<has.length){S.end=has[k];draw();}}
document.getElementById('prev').onclick=function(){step(-1);};document.getElementById('next').onclick=function(){step(1);};
document.getElementById('last').onclick=function(){S.end=has[has.length-1];draw();};
document.getElementById('gen').textContent='생성 '+F.generated_at.slice(0,16).replace('T',' ')+' KST · 네이버 업종 '+SF.n_sectors+'개 · KRX';
draw();
})();
"""

HTML = r"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="color-scheme" content="dark" />
<meta name="theme-color" content="#061E20" />
<title>섹터별 수급</title>
<meta name="description" content="네이버 업종 78개의 개인·기관·외국인 순매수 — 당일·1주·2주." />
<style>__CSS__</style>
</head>
<body>
<div class="container">
<header>
  <div class="brand"><span class="logo-dot" aria-hidden="true"></span>
    <div><h1>섹터별 수급</h1><div class="sub">네이버 업종 78개 × 개인·기관·외국인 순매수 (KRX)</div></div></div>
  <div class="stamp"><div id="gen"></div><div style="margin-top:6px"><a class="back" href="./">← 전체 수급 대시보드</a></div></div>
</header>
<div class="sp-bar">
  <div class="seg" id="wseg" aria-label="기간"></div>
  <span class="lbl">기준일</span>
  <div class="sp-date"><button id="prev" type="button" aria-label="전 영업일">◀</button>
    <input id="dinp" class="dinp" inputmode="numeric" aria-label="기준일 입력" title="날짜 입력 후 Enter (예: 2026-10-06, 261006, 10/6)">
    <button id="next" type="button" aria-label="다음 영업일">▶</button><button id="last" type="button">최신</button></div>
  <span class="sp-sum" id="span"></span>
</div>
<div class="inv3">
  <section class="card"><div class="card-head"><div><div class="card-title">개인</div><div class="card-sub" id="sum-indiv"></div></div></div><div class="bars"><canvas id="c-indiv"></canvas></div></section>
  <section class="card"><div class="card-head"><div><div class="card-title">기관</div><div class="card-sub" id="sum-inst"></div></div></div><div class="bars"><canvas id="c-inst"></canvas></div></section>
  <section class="card"><div class="card-head"><div><div class="card-title">외국인</div><div class="card-sub" id="sum-foreign"></div></div></div><div class="bars"><canvas id="c-foreign"></canvas></div></section>
</div>
<section class="card"><div class="card-head"><div><div class="card-title">전체 78개 섹터</div>
  <div class="card-sub">머리글을 누르면 정렬 · 행을 누르면 주체별 상위 매수·매도 종목(최신 기준일) · 색 = 순매수 빨강 / 순매도 파랑</div></div></div>
  <div class="st-wrap" id="tbl"></div></section>
<footer>
  <div class="foot-h">출처 · 갱신</div>
  <ul>
    <li>업종: 네이버 증권 업종 분류 79개 중 '기타' 제외 78개(현재 소속 기준으로 과거까지 묶음).</li>
    <li>수급: KRX 정보데이터시스템 종목별 투자자(개인·외국인·기관합계) 매수·매도 거래대금. 장 마감 15분 뒤 <b>잠정</b>, 18:40 이후 <b>확정</b>으로 다시 받는다.</li>
    <li>1주 = 최근 5영업일, 2주 = 최근 10영업일 합계(기준일 포함).</li>
  </ul>
</footer>
</div>
<script>window.__SF__ = __DATA__;</script>
<script>__CHARTJS__</script>
<script>__APP__</script>
</body>
</html>
"""


def main() -> int:
    flows = json.loads(render.DATA_PATH.read_text(encoding="utf-8"))
    if not flows.get("sector"):
        print("[render_sector] 섹터 데이터 없음 — 건너뜀")
        return 0
    payload = {"generated_at": flows["generated_at"], "dates": flows["dates"], "sector": flows["sector"]}
    html = (HTML.replace("__CSS__", render.CSS + CSS)
            .replace("__DATA__", render.js_safe_json(payload))
            .replace("__CHARTJS__", render.script_safe(render.VENDOR_PATH.read_text(encoding="utf-8")))
            .replace("__APP__", render.script_safe(JS)))
    targets = [OUT] + ([DOCS] if "--docs" in sys.argv else [])
    for t in targets:
        tmp = t.with_suffix(".tmp")
        tmp.write_text(html, encoding="utf-8")
        tmp.replace(t)
        print(f"[render_sector] {t} ({len(html)/1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
