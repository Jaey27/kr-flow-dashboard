"""수급 탭 「자사주 매입」 — buyback-dashboard 의 buyback.json(현재 시즌 + 지난 시즌)을 회사별 카드로 그린다.

render.py 가 BB_HTML·BB_CSS·BB_JS·bb_data_json() 을 끼워 넣는다. 데이터는 scripts/buyback_fetch.py 가 받아 둔 data/buyback.json.
시즌: 프로그램(DART 자기주식 취득결정)마다 시즌 1, 2, … — 새 취득결정이 잡히면 buyback-dashboard 가 새 시즌을 만들고 지난 시즌은 archive 로 남긴다.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BB_HTML = """<div id="tab-buyback" hidden><div class="grid" id="bb-grid"></div></div>"""

BB_CSS = """
.bb-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin:4px 0 10px}
.bb-k{border:1px solid rgba(151,252,228,.16);border-radius:10px;padding:8px 10px;min-width:0}
.bb-k .l{font-size:11.5px;color:var(--text-muted)}.bb-k .v{font-size:19px;font-weight:700;margin-top:2px;white-space:nowrap}
.bb-k .s{font-size:11.5px;color:var(--text-dim);margin-top:2px}
.bb-bar{height:8px;border-radius:5px;background:rgba(151,252,228,.12);overflow:hidden;margin-top:6px}.bb-bar i{display:block;height:100%;background:#97FCE4}
.bb-badge{display:inline-block;font-size:11.5px;font-weight:700;padding:2px 8px;border-radius:10px;border:1px solid rgba(151,252,228,.3);margin-left:6px;vertical-align:middle}
.bb-badge.ok{color:#97FCE4}.bb-badge.bad{color:var(--down)}.bb-badge.end{color:var(--text-dim)}
"""

BB_JS = r"""
(function(){
'use strict';
var B=window.__BUYBACK__;var grid=document.getElementById('bb-grid');if(!grid) return;
if(!B||!B.companies){grid.innerHTML='<section class="card"><div class="card-title">자사주 매입</div><div class="card-sub">데이터 없음 — scripts/buyback_fetch.py 실행 필요</div></section>';return;}
var css=getComputedStyle(document.documentElement);function cv(n){return css.getPropertyValue(n).trim();}
var COL={text:cv('--text'),dim:cv('--text-dim'),muted:cv('--text-muted'),grid:'rgba(151,252,228,.13)'};
function nf(v,d){return v==null?'–':Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d||0,maximumFractionDigits:d||0});}
function man(v){return v==null?'–':nf(v/1e4,0)+'만주';}
function jo(v){return v==null?'–':nf(v/1e12,2)+'조';}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function ls(k,v){try{if(v===undefined) return localStorage.getItem('krflow.bb.'+k);localStorage.setItem('krflow.bb.'+k,v);}catch(e){return null;}}
var CH={};
function seasons(code){var cur=B.companies[code],past=((B.archive||{})[code]||[]).slice().reverse();return [cur].concat(past);}
function card(code){
  var list=seasons(code),pick=+(ls('s'+code)||list[0].meta.season||1);
  var co=list.filter(function(x){return (x.meta.season||1)===pick;})[0]||list[0];
  var p=co.program,d=co.derived,v=d.completion_verdict||{},rows=co.daily||[];
  var ended=co!==list[0]||co.meta.status==='ended'||v.code==='ended';
  var badge='<span class="bb-badge '+(ended?'end':(v.code==='unlikely'||v.code==='impossible')?'bad':'ok')+'">'+esc(v.label||'')+'</span>';
  var basis=d.progress_basis==='amount'?' (금액 기준)':'';
  var pr=(d.progress_ratio||0)*100;
  var id='bb-'+code;
  var sec=document.getElementById(id);if(!sec){sec=document.createElement('section');sec.className='card';sec.id=id;grid.appendChild(sec);}
  sec.innerHTML='<div class="card-head"><div><div class="card-title">'+esc(co.meta.name)+' 자사주 매입 · 시즌'+(co.meta.season||1)+badge+'</div>'+
    '<div class="card-sub">취득기간 '+esc(p.period_from)+' ~ '+esc(p.period_to)+' · <a href="https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+esc(p.rcept_no)+'" target="_blank" rel="noopener">DART 취득결정 '+esc(p.rcept_no)+' ↗</a> · '+esc(p.purpose||'')+(p.is_cancellation===true?' · 소각':'')+'</div></div>'+
    '<div class="card-tools"><div class="seg" id="'+id+'-s"></div></div></div>'+
    '<div class="bb-kpis">'+
      '<div class="bb-k"><div class="l">진행률'+basis+'</div><div class="v">'+nf(pr,1)+'%</div><div class="bb-bar"><i style="width:'+Math.min(100,pr)+'%"></i></div></div>'+
      '<div class="bb-k"><div class="l">누적 취득 / 예정</div><div class="v">'+man(d.cum_filled)+'</div><div class="s">예정 '+man(p.plan_shares)+(d.remaining_shares?' · 남음 '+man(d.remaining_shares):'')+'</div></div>'+
      '<div class="bb-k"><div class="l">누적 금액 / 예정</div><div class="v">'+jo(d.spent_krw)+'</div><div class="s">예정 '+jo(p.plan_amount_krw)+'</div></div>'+
      '<div class="bb-k"><div class="l">평균 단가</div><div class="v">'+nf(d.avg_cost,0)+'원</div><div class="s">최근 5일 평균 '+man(d.recent5_avg)+'/일</div></div>'+
      '<div class="bb-k"><div class="l">'+(ended?'최종 체결일':'완료 예상(현 페이스)')+'</div><div class="v">'+esc(ended?(d.last_settled_date||'–'):(d.pace_eta_date||'–'))+'</div><div class="s">'+(ended?'체결 '+nf(d.exec_days)+'거래일':'마감까지 '+nf(d.business_days_left)+'거래일 · 여유 '+nf(d.pace_margin_business_days)+'일')+'</div></div>'+
    '</div>'+
    '<div class="chart-box"><canvas id="'+id+'-c"></canvas></div>'+
    '<div class="legend" style="margin-top:6px"><span class="note">'+esc(v.reason||'')+' · 출처: KIND 자기주식 신청·체결(신고 체결금액누계), DART 취득결정 · 갱신 '+esc((co.meta.generated_at||'').slice(0,16).replace('T',' '))+
    ' · <a href="https://jaey27.github.io/buyback-dashboard/" target="_blank" rel="noopener">자사주 대시보드 전체 ↗</a></span></div>';
  var sb=document.getElementById(id+'-s');
  list.forEach(function(x){var b=document.createElement('button');b.type='button';var n=x.meta.season||1;b.className=n===(co.meta.season||1)?'on':'';
    b.textContent='시즌'+n+(x!==list[0]?' (종료)':'');b.onclick=function(){ls('s'+code,n);card(code);};sb.appendChild(b);});
  if(CH[code]) CH[code].destroy();
  var labels=rows.map(function(r){return r.date.slice(5).replace('-','/');});
  var den=d.progress_basis==='amount'?p.plan_amount_krw:p.plan_shares,acc=0;
  var prog=rows.map(function(r){acc+=(d.progress_basis==='amount'?(r.amount_krw||0):(r.filled||0));return den?Math.round(acc/den*1000)/10:null;});
  CH[code]=new Chart(document.getElementById(id+'-c'),{data:{labels:labels,datasets:[
    {type:'bar',label:'일별 체결(만주)',data:rows.map(function(r){return r.filled==null?null:Math.round(r.filled/1e3)/10;}),backgroundColor:'rgba(151,252,228,.45)',yAxisID:'y'},
    {type:'line',label:'누적 진행률(%)'+basis,data:prog,borderColor:'#e8823a',backgroundColor:'#e8823a',pointRadius:0,borderWidth:2,yAxisID:'y2'}]},
    options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{labels:{color:COL.dim,boxWidth:12,boxHeight:3}}},
      scales:{x:{grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:8}},
        y:{grid:{color:COL.grid},ticks:{color:COL.muted},title:{display:true,text:'만주',color:COL.muted}},
        y2:{position:'right',min:0,max:100,grid:{display:false},ticks:{color:COL.muted,callback:function(x){return x+'%';}}}}}});
}
function all(){Object.keys(B.companies).forEach(card);}
all();
window.BUYBACK={show:function(){Object.keys(CH).forEach(function(k){if(CH[k]) CH[k].resize();});}};
})();
"""


def bb_data_json() -> str:
    p = ROOT / "data" / "buyback.json"
    return p.read_text(encoding="utf-8") if p.exists() else "null"
