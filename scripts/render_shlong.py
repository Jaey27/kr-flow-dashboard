"""외국인 보유 탭 '삼성전자·SK하이닉스 외국인 보유' 카드 — 5년 시계열(자체 기간 버튼) + 삼성·하이닉스 주가·코스피 겹치기.

기존 카드(card-shhold, 전체 기간 바 2년에 묶임)를 숨기고 그 자리에 이 카드를 넣는다. 데이터: scripts/stock_long.py → data/stock_long.json
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SL_JS = r"""
(function(){
'use strict';
var L=window.__SLONG__;if(!L||!L.dates) return;
var old=document.getElementById('card-shhold');var grid=document.getElementById('grid2');if(!grid) return;
var css=getComputedStyle(document.documentElement);function cv(n){return css.getPropertyValue(n).trim();}
var COL={text:cv('--text'),dim:cv('--text-dim'),muted:cv('--text-muted'),grid:'rgba(151,252,228,.13)'};
var C={s:'#9085e9',h:'#d55181',k:'#97FCE4',sp:'#c9c2ff',hp:'#ff9cc4'};
function nf(v,d){return v==null?'–':Number(v).toLocaleString('ko-KR',{minimumFractionDigits:d||0,maximumFractionDigits:d||0});}
function ls(k,v){try{if(v===undefined) return localStorage.getItem('krflow.sl.'+k);localStorage.setItem('krflow.sl.'+k,v);}catch(e){return null;}}
function el(t,c,h){var e=document.createElement(t);if(c) e.className=c;if(h!=null) e.innerHTML=h;return e;}
var sec=el('section','card');sec.id='card-shlong';
sec.innerHTML='<div class="card-head"><div><div class="card-title">삼성전자·SK하이닉스 외국인 보유</div><div class="card-sub" id="sl-sub"></div></div>'+
  '<div class="card-tools"><div class="seg" id="sl-v"></div><div class="seg" id="sl-p"></div><div class="seg" id="sl-o"></div></div></div>'+
  '<div class="chart-box"><canvas id="sl-c"></canvas></div>'+
  '<div class="legend" style="margin-top:6px"><span class="note">출처: '+L.src+' · 보유액 = 외국인 보유주식 수 × 종가(삼성전자 보통주) · 2년 이전 보유주식 수는 보유율 × 상장주식 수(다음 값으로 역산, 소각 반영)로 추정 · 주가·코스피는 기간 시작=100</span></div>';
if(old){old.hidden=true;grid.insertBefore(sec,old);}else grid.appendChild(sec);
['card-share','card-shlong'].forEach(function(id){var e=document.getElementById(id);if(e) e.style.alignSelf='start';});  /* 접힌 옆 카드가 이 카드 높이로 늘어나 비어 보이지 않게 */
var D=L.dates,S=L['005930'],H=L['000660'],K=L.kospi;
var V=ls('v')||'val',P=ls('p')||'5Y',O={};try{O=JSON.parse(ls('o')||'{}');}catch(e){O={};}
var PR=[['1Y',1],['2Y',2],['3Y',3],['5Y',5]],CH=null;
function segs(id,items,cur,on){var b=document.getElementById(id);b.innerHTML='';items.forEach(function(x){var e=el('button',(typeof cur==='function'?cur(x[0]):x[0]===cur)?'on':null,x[1]);e.type='button';e.onclick=function(){on(x[0]);};b.appendChild(e);});}
function idx(a,i0,i1){var b=null;for(var i=i0;i<=i1;i++) if(a[i]!=null){b=a[i];break;}return a.slice(i0,i1+1).map(function(v){return v==null||!b?null:Math.round(v/b*1000)/10;});}
function draw(){
  segs('sl-v',[['val','보유액'],['rate','지분율(주식 수)']],V,function(x){V=x;ls('v',x);draw();});
  segs('sl-p',PR.map(function(p){return [p[0],p[0]];}),P,function(x){P=x;ls('p',x);draw();});
  segs('sl-o',[['sp','삼성 주가'],['hp','하이닉스 주가'],['k','코스피']],function(k){return !!O[k];},function(k){O[k]=!O[k];ls('o',JSON.stringify(O));draw();});
  var yrs=+P.replace('Y',''),t=new Date();t.setFullYear(t.getFullYear()-yrs);var from=t.toISOString().slice(0,10);
  var i0=0;while(i0<D.length-1&&D[i0]<from) i0++;var i1=D.length-1;
  var lab=D.slice(i0,i1+1),ds=[];
  if(V==='val'){
    ds.push({label:'삼성전자',data:S.val.slice(i0,i1+1),borderColor:C.s,backgroundColor:'rgba(144,133,233,.35)',fill:'origin',stack:'v',pointRadius:0,borderWidth:1.5,yAxisID:'y'});
    ds.push({label:'SK하이닉스',data:H.val.slice(i0,i1+1),borderColor:C.h,backgroundColor:'rgba(213,81,129,.35)',fill:'-1',stack:'v',pointRadius:0,borderWidth:1.5,yAxisID:'y'});
  }else{
    ds.push({label:'삼성전자',data:S.rate.slice(i0,i1+1),borderColor:C.s,backgroundColor:C.s,pointRadius:0,borderWidth:2,yAxisID:'y'});
    ds.push({label:'SK하이닉스',data:H.rate.slice(i0,i1+1),borderColor:C.h,backgroundColor:C.h,pointRadius:0,borderWidth:2,yAxisID:'y'});
  }
  if(O.sp) ds.push({label:'삼성 주가(=100)',data:idx(S.close,i0,i1),borderColor:C.sp,backgroundColor:C.sp,borderDash:[4,3],pointRadius:0,borderWidth:1.4,yAxisID:'y2',isIdx:1});
  if(O.hp) ds.push({label:'하이닉스 주가(=100)',data:idx(H.close,i0,i1),borderColor:C.hp,backgroundColor:C.hp,borderDash:[4,3],pointRadius:0,borderWidth:1.4,yAxisID:'y2',isIdx:1});
  if(O.k) ds.push({label:'코스피(=100)',data:idx(K,i0,i1),borderColor:C.k,backgroundColor:C.k,borderDash:[2,3],pointRadius:0,borderWidth:1.4,yAxisID:'y2',isIdx:1});
  var any2=!!(O.sp||O.hp||O.k),u=V==='val'?'조':'%';
  var last=i1;document.getElementById('sl-sub').textContent='최신 '+D[last]+' · 삼성 '+(V==='val'?nf(S.val[last],1)+'조':nf(S.rate[last],2)+'%')+' · 하이닉스 '+(V==='val'?nf(H.val[last],1)+'조':nf(H.rate[last],2)+'%')+
    ' · '+P+' 전('+D[i0]+') 대비 삼성 '+(V==='val'?nf(S.val[last]-S.val[i0],1)+'조':nf(S.rate[last]-S.rate[i0],2)+'%p')+', 하이닉스 '+(V==='val'?nf(H.val[last]-H.val[i0],1)+'조':nf(H.rate[last]-H.rate[i0],2)+'%p');
  if(CH) CH.destroy();
  CH=new Chart(document.getElementById('sl-c'),{type:'line',data:{labels:lab,datasets:ds},options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
    plugins:{legend:{labels:{color:COL.dim,boxWidth:12,boxHeight:3}},tooltip:{callbacks:{label:function(it){var v=it.raw;return ' '+it.dataset.label+'  '+(it.dataset.isIdx?nf(v,1):(V==='val'?nf(v,1)+'조':nf(v,2)+'%'));}}}},
    scales:{x:{grid:{display:false},ticks:{color:COL.muted,maxRotation:0,autoSkip:true,maxTicksLimit:8,callback:function(v){var s=this.getLabelForValue(v);return s.slice(2,7).replace('-','.');}}},
      y:{stacked:V==='val',grid:{color:COL.grid},ticks:{color:COL.muted,callback:function(v){return nf(v,V==='val'?0:0)+u;}},title:{display:true,text:V==='val'?'보유액 (조원, 누적)':'외국인 지분율 (%)',color:COL.muted}},
      y2:{display:any2,position:'right',grid:{display:false},ticks:{color:COL.muted},title:{display:true,text:'기간 시작=100',color:COL.muted}}}}});
}
draw();
var b=document.querySelector('#subtabs [data-tab="foreign"]');if(b) b.addEventListener('click',function(){setTimeout(function(){if(CH) CH.resize();},30);});
})();
"""


def sl_data_json() -> str:
    p = ROOT / "data" / "stock_long.json"
    return p.read_text(encoding="utf-8") if p.exists() else "null"
