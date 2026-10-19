"""Owner-only six-lane visualization; all actual status comes from authenticated POST /status.

The network drawing is a topology illustration, not proof of neural activity.
This file contains no external dependencies, market-feed proxies or trade controls.
"""
AGENT_PAGE = r'''<!doctype html>
<html lang="id"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Katarina AI | Multi-Agent Monitor</title>
<style>
:root{color-scheme:dark;--bg:#07101c;--panel:#101d30;--line:#253952;--text:#e8f3ff;--muted:#91a9c0;--mint:#59e2c0;--amber:#f9cb71;--bad:#fa7e94}
*{box-sizing:border-box}body{font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;background:radial-gradient(ellipse at 60% 0%,#123047 0%,var(--bg) 55%);color:var(--text);margin:0}
main{max-width:1240px;margin:auto;padding:24px 18px 60px}header{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between}
h1{font-size:clamp(23px,4vw,34px);letter-spacing:.01em;margin:0}h2{font-size:15px;letter-spacing:.12em;margin:0 0 14px;text-transform:uppercase;color:#bed6eb}p{margin:8px 0;color:var(--muted)}
a{color:var(--mint);text-decoration:none}a:hover{text-decoration:underline}.pill{font-size:11px;letter-spacing:.1em;border:1px solid var(--line);border-radius:30px;padding:6px 12px;color:#bed6eb}
main>section{margin-top:22px}.panel{border:1px solid var(--line);border-radius:16px;background:linear-gradient(145deg,#142439,#0d1a2b);box-shadow:0 8px 36px #0002;padding:20px}
.auth{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;margin-top:18px}
input,button{font:inherit;border:1px solid #40607c;border-radius:10px;color:var(--text);padding:12px 14px;background:#0b1829;min-height:44px}
button{background:#0d5e67;font-weight:700;cursor:pointer}button:hover{background:#117d88}button:disabled{opacity:.5;cursor:wait}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px}
.stat{padding:16px;border:1px solid var(--line);border-radius:12px;background:#0a182a}
.stat small{color:var(--muted);display:block}.stat strong{display:block;font-size:clamp(17px,2.6vw,25px);font-variant-numeric:tabular-nums;margin-top:8px}
.layout{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(280px,1fr);gap:18px}
.network{position:relative;height:380px;border:1px solid var(--line);border-radius:14px;overflow:hidden;background:radial-gradient(circle at center,#193e50 0%,#0a1425 70%)}
canvas{width:100%;height:100%;display:block}.center-note{font-size:12px;margin-top:10px;color:var(--muted)}
.lanes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.lane{padding:14px;border:1px solid var(--line);border-radius:12px;background:#0b1929}
.lane-top{display:flex;align-items:center;gap:10px;justify-content:space-between}
.lane b{letter-spacing:.09em;font-size:13px}.lane small{display:block;color:var(--muted);line-height:1.4;margin-top:5px}
.state{font-size:10px;border-radius:30px;border:1px solid #54677a;padding:4px 7px;color:#b3cce1;white-space:nowrap}
.state.ok{border-color:#276e5c;color:var(--mint)}.state.warn{border-color:#6b542e;color:var(--amber)}.state.bad{border-color:#77425a;color:var(--bad)}
#blockers{font:12px/1.6 ui-monospace,Consolas,monospace;white-space:pre-wrap;overflow-wrap:anywhere;color:var(--muted);margin:0}
#notice{min-height:24px;margin-top:10px}footer{margin-top:30px;font-size:12px;color:var(--muted)}
@media(max-width:850px){.layout{grid-template-columns:1fr}.network{height:300px}}
@media(max-width:600px){.auth{grid-template-columns:1fr 1fr}.auth input{grid-column:1/-1}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.lanes{grid-template-columns:1fr}}
</style></head><body><main>
<header><div><div class="pill" style="display:inline-block">KATARINA · OWNER CONSOLE</div><h1>Multi-Agent Intelligence</h1><p>Satu otak, enam kapabilitas observasi. Bukan enam worker terpisah.</p></div>
<div><span class="pill" id="overall">BELUM DIPERIKSA</span> &nbsp; <a href="/">Dialog Owner ↗</a></div></header>
<div class="auth"><input id="token" type="password" autocomplete="off" placeholder="Token Owner (tidak disimpan)" aria-label="Token autentikasi Owner"><button id="refresh">Periksa sekarang</button><button id="auto" aria-pressed="false">Auto: OFF</button></div>
<div id="notice" role="status" aria-live="polite">Tidak ada data sampai pemeriksaan berautentikasi berhasil.</div>
<section class="stats" aria-label="Ringkasan observasi">
<div class="stat"><small>Instrumen tervalidasi</small><strong id="symbols">—</strong></div>
<div class="stat"><small>Siklus observer</small><strong id="cycles">—</strong></div>
<div class="stat"><small>Status eksekusi</small><strong id="execution">BELUM DIPERIKSA</strong></div>
<div class="stat"><small>Profit broker terverifikasi</small><strong id="profit">—</strong></div>
</section>
<section class="layout">
<div class="panel"><h2>Brain Topology</h2><div class="network"><canvas id="mesh" role="img" aria-label="Ilustrasi statis enam kemampuan di sekitar satu otak Katarina"></canvas></div><p class="center-note">Diagram jaringan hanya ilustrasi arsitektur. Garis dan titik bukan aktivitas neuron atau bukti transaksi.</p></div>
<div class="panel"><h2>Status Kapabilitas</h2><div class="lanes" id="lanes"><p>Status belum diterima.</p></div></div>
</section>
<section class="panel"><h2>Evidence &amp; Limitations</h2><div id="blockers">Snapshot broker, risk governor, kualitas model, serta profit belum dibuktikan pada sesi ini.</div>
<p id="timestamp">Pembaruan terakhir: —</p></section>
<footer>LIVE OFF • Data hanya dari endpoint /status berautentikasi • Tidak ada tombol pengiriman order • Jangan menganggap indikator UI sebagai persetujuan live.</footer>
</main><script>
"use strict";
const names=["SCAN","ANALYST","STRATEGY","BALANCE","EXEC","AUDIT"];
const $=id=>document.getElementById(id);
let timer=null,busy=false;
function visual(){
 const canvas=$("mesh"),bounds=canvas.getBoundingClientRect(),ratio=Math.min(2,window.devicePixelRatio||1);
 const w=Math.max(260,bounds.width),h=Math.max(200,bounds.height);
 canvas.width=Math.round(w*ratio);canvas.height=Math.round(h*ratio);
 const g=canvas.getContext("2d");if(!g)return;g.scale(ratio,ratio);
 const cx=w/2,cy=h/2,r=Math.min(w*.34,h*.35);
 const pts=names.map((name,i)=>{const a=(i/6)*2*Math.PI-Math.PI/2;return {name,x:cx+Math.cos(a)*r,y:cy+Math.sin(a)*r}});
 g.strokeStyle="#326079";g.lineWidth=1.3;
 for(const p of pts){g.beginPath();g.moveTo(cx,cy);g.lineTo(p.x,p.y);g.stroke()}
 for(let i=0;i<pts.length;i++)for(let j=i+1;j<pts.length;j++)if((i+j)%3===0){g.strokeStyle="#204159";g.beginPath();g.moveTo(pts[i].x,pts[i].y);g.lineTo(pts[j].x,pts[j].y);g.stroke()}
 g.shadowColor="#3ebea9";g.shadowBlur=21;g.fillStyle="#12404a";g.beginPath();g.arc(cx,cy,45,0,Math.PI*2);g.fill();g.shadowBlur=0;g.strokeStyle="#5fe5d0";g.stroke();
 g.fillStyle="#e9ffff";g.font="bold 14px system-ui";g.textAlign="center";g.textBaseline="middle";g.fillText("KATARINA",cx,cy-6);g.font="11px system-ui";g.fillText("ONE BRAIN",cx,cy+13);
 pts.forEach(p=>{g.fillStyle="#12304a";g.strokeStyle="#537b9b";g.beginPath();g.arc(p.x,p.y,Math.max(21,Math.min(28,w/17)),0,Math.PI*2);g.fill();g.stroke();g.fillStyle="#e6f2ff";g.font="bold 10px system-ui";g.fillText(p.name,p.x,p.y)});
}
function classify(value){return ["OBSERVED","SNAPSHOT_PASS"].includes(value)?"ok":value==="BLOCKED"?"bad":"warn"}
function put(id,text){$(id).textContent=String(text)}
function render(report){
 const board=report.agent_board;if(!board||board.schema_version!==1||!Array.isArray(board.lanes))throw Error("Status agent belum tersedia di versi server ini.");
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
 const details=board.blockers.length?"Blocker: "+board.blockers.join(", "):"Snapshot lulus pemeriksaan struktur dan freshness. Ini bukan bukti trading, model, atau proses independen.";
 put("blockers",details);put("timestamp","Pemeriksaan: "+(board.observed_at_utc||"tidak tersedia"));
}
async function refresh(){
 if(busy)return;const token=$("token").value;if(!token){put("notice","Masukkan token Owner terlebih dahulu.");return}
 busy=true;$("refresh").disabled=true;
 try{const response=await fetch("/status",{method:"POST",cache:"no-store",headers:{"Content-Type":"application/json","Authorization":"Bearer "+token},body:"{}"});
 if(!response.ok)throw Error("Permintaan status ditolak (HTTP "+response.status+")");
 const data=await response.json();render(data);
 put("notice","Data dibaca dari pemeriksaan snapshot read-only; tidak ada perintah trading.");
 }catch(e){put("notice",e.message);put("overall","BELUM TERVERIFIKASI")}finally{busy=false;$("refresh").disabled=false}
}
$("refresh").addEventListener("click",refresh);
$("auto").addEventListener("click",()=>{if(timer){clearInterval(timer);timer=null}else{timer=setInterval(()=>{if(!document.hidden)refresh()},30000);refresh()}
 const on=Boolean(timer);$("auto").textContent=on?"Auto: ON":"Auto: OFF";$("auto").setAttribute("aria-pressed",String(on));
});
window.addEventListener("resize",visual);visual();
</script></body></html>'''
