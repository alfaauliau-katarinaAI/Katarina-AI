"""Owner-only six-lane visualization; all actual status comes from authenticated POST /status.

The radial graph maps actual snapshot records, not simulated neural activity.
This file contains no external dependencies, market-feed proxies or trade controls.
"""
AGENT_PAGE = r'''<!doctype html>
<html lang="id"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Katarina AI | Multi-Agent Monitor</title>
<style>
:root{color-scheme:dark;--bg:#090c14;--panel:#0d121e;--line:#293043;--text:#e4e6ee;--muted:#929aaf;--mint:#80d4bd;--amber:#d7cf89;--bad:#d57798}
*{box-sizing:border-box}body{font:13px/1.55 ui-monospace,SFMono-Regular,Consolas,monospace;background:var(--bg);color:var(--text);margin:0}
main{max-width:1500px;margin:auto;padding:20px 18px 40px}header{display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding-bottom:16px}
h1{font-size:clamp(22px,4vw,34px);letter-spacing:.04em;margin:8px 0 0}h2{font-size:12px;letter-spacing:.14em;margin:0 0 14px;text-transform:uppercase;color:#d4d6e2}p{margin:8px 0;color:var(--muted)}
a{color:var(--mint);text-decoration:none}a:hover{text-decoration:underline}.pill{font-size:10px;letter-spacing:.1em;border:1px solid var(--line);padding:6px 10px;color:var(--amber)}
main>section{margin-top:14px}.panel{border:1px solid var(--line);background:var(--panel);padding:16px}
.auth{display:grid;grid-template-columns:1fr auto auto;gap:8px;align-items:center;margin-top:16px}
input,button{font:inherit;border:1px solid #42495e;border-radius:3px;color:var(--text);padding:10px 12px;background:#101622;min-height:44px;min-width:0}
button{background:#253e3d;font-weight:700;cursor:pointer}button:hover{background:#345854}button:disabled{opacity:.5;cursor:wait}
.token-help{color:var(--muted);font-size:12px;margin-top:8px}.token-help summary{cursor:pointer;min-height:28px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;border:1px solid var(--line);background:var(--line)}
.stat{padding:14px;background:#101522}.stat small{color:var(--muted);display:block}.stat strong{display:block;font-size:clamp(16px,2.5vw,24px);font-variant-numeric:tabular-nums;margin-top:6px}
.trace-panel{padding:0;background:radial-gradient(ellipse at center,#171a2a 0%,#0b0f19 62%)}
.trace-head{padding:12px 16px;display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;border-bottom:1px solid var(--line)}.trace-head h2{margin:0}.trace-head span{color:var(--amber);font-size:11px}
.trace-viewport{overflow:auto;overscroll-behavior-x:contain}#trace{display:block;width:100%;min-width:600px;max-height:760px}
.trace-legend{border-top:1px solid var(--line);padding:10px 16px;color:var(--muted);font-size:11px}.trace-legend b{color:var(--amber)}
.layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(280px,1fr);gap:14px}
.lanes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.lane{padding:12px;border:1px solid var(--line);background:#101522}.lane-top{display:flex;align-items:center;gap:8px;justify-content:space-between}.lane b{letter-spacing:.09em;font-size:12px}.lane small{display:block;color:var(--muted);line-height:1.5;margin-top:7px}
.state{font-size:9px;border:1px solid #546077;padding:3px 5px;color:#b3bfd4;overflow-wrap:anywhere}.state.ok{border-color:#3f6c61;color:var(--mint)}.state.warn{border-color:#6b653e;color:var(--amber)}.state.bad{border-color:#77425a;color:var(--bad)}
table{border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #242a3b;vertical-align:top}th{color:var(--amber);font-weight:500}
#blockers{font:12px/1.6 ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);margin:0}#notice{min-height:24px;margin-top:10px}
.center-note,footer{font-size:11px;color:var(--muted)}footer{margin-top:24px;border-top:1px solid var(--line);padding-top:14px}
@media(max-width:850px){.layout{grid-template-columns:1fr}}
@media(max-width:600px){main{padding:14px 10px 30px}.auth{grid-template-columns:1fr 1fr}.auth input{grid-column:1/-1}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.lanes{grid-template-columns:1fr}.panel{padding:12px}.trace-panel{padding:0}#trace{min-width:600px}h1{font-size:23px}}
</style></head><body><main>
<header><div><div class="pill" style="display:inline-block">KATARINA · OWNER CONSOLE</div><h1>KATARINA / INTELLIGENCE</h1><p>READ-ONLY TERMINAL · satu otak · enam kapabilitas · tanpa API berbayar saat ini</p></div>
<div><span class="pill" id="overall">BELUM DIPERIKSA</span> &nbsp; <a href="/">Dialog Owner ↗</a></div></header>
<div class="auth"><input id="token" type="password" autocomplete="off" placeholder="Token Owner (tidak disimpan)" aria-label="Token autentikasi Owner"><button id="refresh">Periksa sekarang</button><button id="auto" aria-pressed="false">Auto: OFF</button></div>
<details class="token-help"><summary>Token Owner dan API key berbeda — baca petunjuk</summary><p>Token Owner diberikan oleh pemilik instalasi untuk masuk dashboard. Token ini tidak dibeli dan tidak dibuat di penyedia AI. API key hanya diperlukan bila model bahasa eksternal diaktifkan. Mesin teknis dan monitor ini bekerja tanpa API model. Token tidak disimpan di browser.</p></details>
<div id="notice" role="status" aria-live="polite">Tidak ada data sampai pemeriksaan berautentikasi berhasil.</div>
<section class="stats" aria-label="Ringkasan observasi">
<div class="stat"><small>Instrumen tervalidasi</small><strong id="symbols">—</strong></div>
<div class="stat"><small>Siklus observer</small><strong id="cycles">—</strong></div>
<div class="stat"><small>Status eksekusi</small><strong id="execution">BELUM DIPERIKSA</strong></div>
<div class="stat"><small>Profit broker terverifikasi</small><strong id="profit">—</strong></div>
</section>
<section class="panel trace-panel" aria-label="Peta hasil proses aktual">
<div class="trace-head"><h2>◈ KATARINA / PROCESS TRACE</h2><span id="trace-count">MENUNGGU BUKTI</span></div>
<div class="trace-viewport"><svg id="trace" viewBox="0 0 1000 760" role="img" aria-label="Pohon hasil analisis dari snapshot Katarina yang tervalidasi"><text x="500" y="380" text-anchor="middle" fill="#929aaf">Masukkan token dan periksa snapshot.</text></svg></div>
<div class="trace-legend"><b>PID → simbol → kondisi / metode / tindakan</b> · Setiap cabang berasal dari satu hasil mesin. Bukan visualisasi neuron atau worker tambahan. Geser diagram di HP; rincian lengkap ada di tabel.</div>
</section>
<section class="layout">
<div class="panel"><h2>Proses Katarina Nyata</h2><p id="process-proof">Proses belum diperiksa.</p><p id="model-proof">Model AI belum diperiksa.</p><p id="book-proof">Buku posisi broker belum diperiksa.</p><div style="overflow-x:auto"><table style="width:100%;font-size:12px;text-align:left"><thead><tr><th>Simbol</th><th>Kondisi</th><th>Metode</th><th>Tindakan</th></tr></thead><tbody id="evaluations"></tbody></table></div><p class="center-note">Baris hanya berasal dari keluaran mesin pada snapshot terbaru. Analisis teknis deterministik, panggilan model bahasa, dan izin trading adalah bukti yang berbeda.</p></div>
<div class="panel"><h2>Status Kapabilitas</h2><div class="lanes" id="lanes"><p>Status belum diterima.</p></div></div>
</section>
<section class="panel"><h2>Audit / Freshness</h2><div id="blockers">Snapshot broker, risk governor, kualitas model, serta profit belum dibuktikan pada sesi ini.</div>
<p id="timestamp">Pembaruan terakhir: —</p></section>
<footer>LIVE OFF • Data hanya dari endpoint /status berautentikasi • Tidak ada tombol pengiriman order • Jangan menganggap indikator UI sebagai persetujuan live.</footer>
</main><script>
"use strict";
const names=["SCAN","ANALYST","STRATEGY","BALANCE","EXEC","AUDIT"];
const $=id=>document.getElementById(id);
let timer=null,busy=false;
function classify(value){return ["OBSERVED","SNAPSHOT_PASS","TECHNICAL_EVALUATED","RESEARCH_EVALUATED","BOOK_OBSERVED"].includes(value)?"ok":value==="BLOCKED"?"bad":"warn"}
function put(id,text){$(id).textContent=String(text)}

function traceElement(tag,attrs,text){
 const el=document.createElementNS("http://www.w3.org/2000/svg",tag);
 for(const [key,value] of Object.entries(attrs))el.setAttribute(key,String(value));
 if(text!==undefined)el.textContent=String(text);
 return el;
}
function drawTrace(board,op){
 const svg=$("trace");svg.replaceChildren();
 const rows=Array.isArray(op.technical_evaluations)?op.technical_evaluations.slice(0,17):[];
 const verified=board.result==="SNAPSHOT_PASS"&&board.snapshot_process_matches===true;
 if(!verified||!rows.length){
  svg.append(traceElement("text",{x:500,y:380,"text-anchor":"middle",fill:"#929aaf"},"Belum ada hasil proses yang tervalidasi."));
  put("trace-count","MENUNGGU BUKTI");return;
 }
 const center={x:500,y:380};
 function point(radius,angle){return {x:center.x+radius*Math.cos(angle),y:center.y+radius*Math.sin(angle)}}
 function link(a,b,color,width){
  const d="M "+a.x+" "+a.y+" Q "+((a.x+b.x)/2+12)+" "+((a.y+b.y)/2-12)+" "+b.x+" "+b.y;
  svg.append(traceElement("path",{d,fill:"none",stroke:color,"stroke-width":width,opacity:.6}));
 }
 for(let i=0;i<rows.length;i++){
  const row=rows[i],angle=-Math.PI/2+i*2*Math.PI/rows.length;
  const node=point(235,angle),color=i<Math.ceil(rows.length/2)?"#d7cf89":"#b4a4de";
  const start=point(82,angle);link(start,node,color,1.1);
  const circle=traceElement("circle",{cx:node.x,cy:node.y,r:4,fill:color});
  circle.append(traceElement("title",{},row.symbol+" · "+row.market_state+" · "+row.method+" · "+row.action));svg.append(circle);
  const label=point(262,angle);
  svg.append(traceElement("text",{x:label.x,y:label.y,"text-anchor":"middle",fill:color,"font-size":12},row.symbol));
  const values=[row.market_state,row.method,row.action];
  for(let j=0;j<values.length;j++){
   const leaf=point(315+(j===1?20:0),angle+(j-1)*.048);
   link(node,leaf,color,.8);
   const dot=traceElement("circle",{cx:leaf.x,cy:leaf.y,r:j===2?3:2,fill:row.action==="WAIT"&&j===2?"#d7cf89":color});
   dot.append(traceElement("title",{},row.symbol+" / "+["kondisi","metode","tindakan"][j]+": "+values[j]));svg.append(dot);
  }
 }
 svg.append(traceElement("circle",{cx:500,cy:380,r:80,fill:"#111725",stroke:"#57617c","stroke-width":1}));
 for(const [y,size,color,text] of [[355,12,"#929aaf","SATU OTAK"],[383,22,"#e4e6ee","KATARINA"],[407,12,"#d7cf89","PID "+board.current_process_pid]]){
  svg.append(traceElement("text",{x:500,y,"text-anchor":"middle",fill:color,"font-size":size},text));
 }
 put("trace-count",rows.length+" SIMBOL / "+rows.length*3+" HASIL / LIVE OFF");
}

function render(report){
 const board=report.agent_board;if(!board||board.schema_version!==1||!Array.isArray(board.lanes))throw Error("Status agent belum tersedia di versi server ini.");
 const op=board.operational||{}, model=board.model||{};
 put("process-proof","PID server: "+(board.current_process_pid||"—")+" · snapshot cocok: "+(board.snapshot_process_matches===true?"YA":"BELUM TERVERIFIKASI")+" · siklus: "+(board.cycles??"—")+" · tick UTC: "+(op.market_tick_utc||"—"));
 const telemetry=model.telemetry;
 put("model-proof",model.configured===true?"Model dikonfigurasi · panggilan berhasil: "+(telemetry?.successful_calls??"belum ada bukti")+" · kualitas belum tervalidasi":"Model bahasa BELUM TERHUBUNG; analisis tabel berasal dari mesin teknis.");
 put("book-proof",op.account_book_observed===true?"Buku broker: "+op.positions_count+" posisi · "+op.pending_orders_count+" pending · izin risiko: BELUM DIBERIKAN":"Buku broker belum tervalidasi.");
 const table=$("evaluations");table.replaceChildren();
 for(const row of (Array.isArray(op.technical_evaluations)?op.technical_evaluations:[])){
  const tr=document.createElement("tr");
  for(const value of [row.symbol,row.market_state,row.method,row.action]){const td=document.createElement("td");td.textContent=String(value);tr.append(td)}
  table.append(tr);
 }
 put("overall",board.result);put("symbols",board.market_symbols===null?"—":board.market_symbols);
 put("cycles",Number.isInteger(board.cycles)?board.cycles:"—");
 put("execution",board.delivery==="DISABLED"?"LIVE OFF":"BELUM TERVERIFIKASI");
 put("profit","—"); // No broker PnL provenance in the authenticated snapshot.
 const list=$("lanes");list.replaceChildren();
 for(const name of names){
  const v=board.lanes.find(x=>x.id===name);if(!v)continue;
  const div=document.createElement("div");div.className="lane";
  const top=document.createElement("div");top.className="lane-top";
  const title=document.createElement("b");title.textContent=name;
  const badge=document.createElement("span");badge.className="state "+classify(v.status);badge.textContent=v.status;
  const sub=document.createElement("small");sub.textContent=v.description;
  const reason=document.createElement("small");reason.textContent=v.reason;
  top.append(title,badge);div.append(top,sub,reason);list.append(div);
 }
 drawTrace(board,op);
 const details=board.blockers.length?"Blocker: "+board.blockers.join(", "):"Snapshot lulus pemeriksaan struktur dan freshness. Ini bukan bukti trading, model, atau proses independen.";
 put("blockers",details);put("timestamp","Pemeriksaan: "+(board.observed_at_utc||"tidak tersedia"));
}
function invalidate(){
 $("trace").replaceChildren();put("trace-count","MENUNGGU BUKTI");
 put("overall","BELUM TERVERIFIKASI");put("symbols","—");put("cycles","—");
 put("execution","BELUM TERVERIFIKASI");put("profit","—");
 $("evaluations").replaceChildren();put("process-proof","Proses belum terverifikasi.");put("model-proof","Status model belum terverifikasi.");put("book-proof","Buku broker belum terverifikasi.");
 $("lanes").replaceChildren();put("blockers","Data tidak tersedia; lakukan pemeriksaan berautentikasi lagi.");
 put("timestamp","Pembaruan terakhir: —");
}
async function refresh(){
 if(busy)return;const token=$("token").value;if(!token){invalidate();put("notice","Masukkan token Owner terlebih dahulu.");return}
 busy=true;$("refresh").disabled=true;
 const controller=new AbortController(),deadline=setTimeout(()=>controller.abort(),10000);
 try{const response=await fetch("/status",{method:"POST",cache:"no-store",signal:controller.signal,headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:"{}"});
 if(!response.ok)throw Error("Permintaan status ditolak (HTTP "+response.status+")");
 const data=await response.json();render(data);
 put("notice","Data dibaca dari pemeriksaan snapshot read-only; tidak ada perintah trading.");
 }catch(e){invalidate();put("notice",e.message)}finally{clearTimeout(deadline);busy=false;$("refresh").disabled=false}
}
$("refresh").addEventListener("click",refresh);
$("auto").addEventListener("click",()=>{if(timer){clearInterval(timer);timer=null}else{timer=setInterval(()=>{if(!document.hidden)refresh()},30000);refresh()}
 const on=Boolean(timer);$("auto").textContent=on?"Auto: ON":"Auto: OFF";$("auto").setAttribute("aria-pressed",String(on));
});

</script></body></html>'''
