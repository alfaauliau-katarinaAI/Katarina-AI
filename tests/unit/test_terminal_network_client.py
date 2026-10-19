"""Execute the actual hosted terminal client without a browser or network."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node required for terminal client verification")
class TerminalNetworkClientTests(unittest.TestCase):
    def test_real_events_touch_zoom_inspection_pulses_and_expiry(self):
        source = (Path(__file__).resolve().parents[2] / "sites/runtime-monitor/worker/index.js").read_text(encoding="utf-8")
        harness = r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
const source=WORKER_SOURCE;
const page=JSON.parse(source.slice(source.indexOf('const PAGE=')+11,source.indexOf(';\nconst phases=')));
const script=page.split('<script>')[1].split('</script>')[0];
assert.match(page,/touch-action:none/);
assert.match(page,/max-width:420px/);
assert.match(page,/id="network"/);
assert.ok(!page.includes('type="password"'));
const nodes=new Map(),intervals=[],requests=[],frames=[],draws=[];
const context=new Proxy({}, {get:(target,key)=>target[key]||((...args)=>draws.push([key,...args])),set:(t,k,v)=>(t[k]=v,true)});
function el(tag='div'){
 return {tag,children:[],style:{},dataset:{},attrs:{},listeners:{},textContent:'',value:'',hidden:false,disabled:false,
 append(...values){this.children.push(...values)},replaceChildren(...values){this.children=[...values];this.textContent=''},
 setAttribute(k,v){this.attrs[k]=String(v)},getAttribute(k){return this.attrs[k]},
 addEventListener(k,fn){this.listeners[k]=fn},getBoundingClientRect(){return {width:390,height:385,left:0,top:0}},
 getContext(){return context},setPointerCapture(){},scrollIntoView(){}};
}
function get(id){if(!nodes.has(id))nodes.set(id,el());return nodes.get(id)}
const fixed=Date.now();let clock=fixed;
class Clock extends Date{constructor(...args){super(...(args.length?args:[clock]))}static now(){return clock}}
const listeners={};
const sandbox={console,Date:Clock,performance:{now:()=>clock-fixed},window:{innerWidth:390,devicePixelRatio:3,matchMedia:()=>({matches:false}),addEventListener(){}},
 document:{hidden:false,fullscreenElement:null,getElementById:get,createElement:el,createElementNS:(_,tag)=>el(tag),addEventListener:(key,fn)=>listeners[key]=fn},
 ResizeObserver:class{observe(){}},AbortController,
 requestAnimationFrame:fn=>(frames.push(fn),frames.length),setInterval:(fn,ms)=>(intervals.push({fn,ms}),intervals.length),clearInterval(){},setTimeout:()=>1,clearTimeout(){},
 fetch:async(url,options)=>{requests.push({url,options});return {ok:false,status:503}}};
vm.createContext(sandbox);vm.runInContext(script,sandbox);
const run=code=>vm.runInContext(code,sandbox);
assert.equal(requests[0].url,'/public-status');assert.equal(requests[0].options.method,'GET');
assert.equal(requests[0].options.headers,undefined);
assert.equal(get('network').width,780); // DPR bounded at 2, suitable for phone
const stamp=new Date(fixed).toISOString();
const event=(seq,phase,state,fields={})=>({seq,at_utc:stamp,phase,state,...fields});
const packet={captured_at_utc:stamp,agent_board:{schema_version:1,result:'SNAPSHOT_PASS',market_symbols:1,cycles:4,successful_cycles:4,
 delivery:'DISABLED',current_process_pid:42,snapshot_process_matches:true,live_execution_authorized:false,blockers:[],model:{configured:false},
 operational:{market_tick_utc:stamp,technical_evaluations:[{symbol:'XAUUSD',method:'TREND_PULLBACK',market_state:'TREND_UP',action:'WAIT'}]},
 activity:{pid:42,cycle:4,fresh:true,events:[event(1,'CONNECT','STARTED'),event(2,'TECHNICAL','DONE',{symbol:'XAUUSD',method:'TREND_PULLBACK',market_state:'TREND_UP',action:'WAIT'})],current:event(2,'TECHNICAL','DONE')},
 lanes:['SCAN','ANALYST','STRATEGY','BALANCE','EXEC','AUDIT'].map(id=>({id,status:id==='EXEC'?'LIVE_OFF':'OBSERVED',description:id}))}};
sandbox.packet=packet;
run('render(packet)');
assert.equal(get('symbols').textContent,'1');assert.equal(get('cycles').textContent,'4');
assert.equal(get('execution').textContent,'LIVE / OFF');assert.equal(get('model-proof').textContent,'BELUM TERHUBUNG');
assert.equal(get('events').children.length,2);assert.equal(get('lanes').children.length,6);
assert.equal(run('pulseKeys.size'),0); // first load is historical, not new work
assert.ok(run('graph.nodes.length')>2);
assert.ok(run('graph.edges.every(e=>nodeMap.has(e.a)&&nodeMap.has(e.b))'));
run('draw(0)');assert.ok(draws.some(d=>d[0]==='quadraticCurveTo'));
const graphBefore=run('graph'),tableRowBefore=get('events').children[0],watchBefore=get('watch').children[0];
run('render(packet)');assert.equal(run('pulseKeys.size'),0);
assert.equal(run('graph'),graphBefore);assert.equal(get('events').children[0],tableRowBefore);
assert.equal(get('watch').children[0],watchBefore);
const orbitYaw=run('yaw');run('draw(500)');assert.ok(run('yaw')>orbitYaw);
get('orbit').listeners.click();assert.equal(run('orbitOn'),false);
const stoppedYaw=run('yaw');run('draw(600)');assert.equal(run('yaw'),stoppedYaw);
get('orbit').listeners.click();assert.equal(run('orbitOn'),true);
packet.agent_board.activity.events.push(event(3,'MEMORY','STARTED'));
packet.agent_board.activity.current=event(3,'MEMORY','STARTED');
run('render(packet)');assert.equal(run('pulseKeys.size'),1);
const pulseStart=run('pulseAt'),eventGraph=run('graph');clock=fixed+700;
run('render(packet)');assert.equal(run('pulseKeys.size'),1);assert.equal(run('pulseAt'),pulseStart);
assert.equal(run('graph'),eventGraph);clock=fixed;
assert.ok(intervals.some(x=>x.ms===2000));
assert.equal(get('lanes').children.filter(x=>x.className==='lane active').length,1);
run('selectNode("s:XAUUSD")');assert.ok(get('selection').children[1].textContent.includes('TREND_PULLBACK'));
assert.equal(get('node-select').value,'s:XAUUSD');
const yaw0=run('yaw');
get('network').listeners.pointerdown({pointerId:1,clientX:20,clientY:20});
get('network').listeners.pointermove({pointerId:1,clientX:60,clientY:25});
assert.notEqual(run('yaw'),yaw0);
get('network').listeners.pointerdown({pointerId:2,clientX:100,clientY:25});
get('network').listeners.pointermove({pointerId:2,clientX:120,clientY:25});
get('network').listeners.pointermove({pointerId:2,clientX:180,clientY:25});
assert.ok(run('zoom')>1);
get('network').listeners.pointercancel({pointerId:1});get('network').listeners.pointercancel({pointerId:2});
let prevented=false;get('network').listeners.keydown({key:'ArrowRight',preventDefault(){prevented=true}});assert.ok(prevented);
get('reset').listeners.click();assert.equal(run('zoom'),1);
const touchedYaw=run('yaw');run('draw(2000)');assert.equal(run('yaw'),touchedYaw);
get('motion').listeners.click();assert.equal(run('pulseOn'),false);
clock=fixed+121000;run('checkFreshness()');
assert.equal(run('graph.nodes.length'),0);assert.equal(get('events').children.length,0);
assert.equal(get('watch').children.length,0);assert.equal(get('symbols').textContent,'—');
assert.equal(run('graphFresh'),false);assert.equal(get('execution').textContent,'BELUM TERVERIFIKASI');
clock=fixed;
packet.agent_board.result='BLOCKED';packet.agent_board.snapshot_process_matches=false;
run('render(packet)');assert.equal(get('symbols').textContent,'—');assert.equal(get('watch').children.length,1);
assert.equal(run('graph.nodes.filter(n=>n.kind==="symbol").length'),0);
const stale=JSON.parse(JSON.stringify(packet));stale.captured_at_utc=new Date(fixed-121000).toISOString();
sandbox.stale=stale;assert.throws(()=>run('render(stale)'),/kedaluwarsa/);
;(async()=>{
 // Let the initial failed automatic request finish before testing the real refresh path.
 await new Promise(resolve=>setImmediate(resolve));
 clock=fixed;packet.agent_board.result='SNAPSHOT_PASS';packet.agent_board.snapshot_process_matches=true;
 sandbox.fetch=async()=>({ok:true,json:async()=>packet});
 await run('refresh()');const retained=run('graph');assert.ok(retained.nodes.length>0);
 sandbox.fetch=async()=>{throw new TypeError('temporary network loss')};clock=fixed+1000;
 await run('refresh()');assert.equal(run('graph'),retained);assert.ok(get('notice').textContent.includes('snapshot terakhir'));
 clock=fixed+121000;await run('refresh()');assert.equal(run('graph.nodes.length'),0);
 assert.equal(get('symbols').textContent,'—');
 console.log('PASS_TERMINAL_EVENTS_TOUCH_ZOOM_INSPECTION_PULSE_EXPIRY_REFRESH');
})().catch(error=>{console.error(error);process.exitCode=1});
"""
        result = subprocess.run([shutil.which("node")], input=harness.replace("WORKER_SOURCE", json.dumps(source), 1),
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
