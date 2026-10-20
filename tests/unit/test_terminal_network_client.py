"""Execute the actual hosted terminal client without a browser or network."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which("node"), "Node required for terminal client verification")
class TerminalNetworkClientTests(unittest.TestCase):
    def test_real_events_spherical_rotation_and_expiry(self):
        source = (Path(__file__).resolve().parents[2] / "sites/runtime-monitor/worker/index.js").read_text(encoding="utf-8")
        harness = r"""
const assert=require('node:assert/strict'),vm=require('node:vm');
const source=WORKER_SOURCE;
const page=JSON.parse(source.slice(source.indexOf('const PAGE=')+11,source.indexOf(';\nconst phases=')));
const script=page.split('<script>')[1].split('</script>')[0];
assert.match(page,/canvas#network\{touch-action:none/);assert.ok(!page.includes("touch-action:pan-y"));assert.ok(!page.includes('id="pair-focus"'));assert.ok(!page.includes('id="pause-pulse"'));assert.ok(!page.includes('id="reset-view"'));assert.ok(!page.includes('class="controls"'));
assert.match(page,/max-width:420px/);
assert.match(page,/id="network"/);assert.ok(!page.includes('class="parallel-board"'));assert.ok(!page.includes('id="parallel-grid"'));assert.match(page,/Rotasi visual/);
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
const stamp=new Date(fixed).toISOString();
const event=(seq,phase,state,fields={})=>({seq,at_utc:stamp,phase,state,...fields});
const packet={captured_at_utc:stamp,agent_board:{schema_version:1,result:'SNAPSHOT_PASS',telemetry_verified:true,research_source_verified:true,market_symbols:1,cycles:4,successful_cycles:4,
 delivery:'DISABLED',current_process_pid:42,snapshot_process_matches:true,live_execution_authorized:false,blockers:[],model:{configured:false},
 operational:{market_tick_utc:stamp,technical_evaluations:[{symbol:'XAUUSD',method:'TREND_PULLBACK',market_state:'TREND_UP',action:'WAIT'}]},
 activity:{pid:42,cycle:4,fresh:true,events:[event(1,'CONNECT','STARTED'),event(2,'TECHNICAL','DONE',{symbol:'XAUUSD',method:'TREND_PULLBACK',market_state:'TREND_UP',action:'WAIT'})],current:event(2,'TECHNICAL','DONE')},
 lanes:['SCAN','ANALYST','STRATEGY','BALANCE','EXEC','AUDIT'].map(id=>({id,status:id==='EXEC'?'LIVE_OFF':'OBSERVED',description:id}))}};
const docId='document:'+ 'a'.repeat(24),partId='paragraph:'+ 'b'.repeat(24);
packet.agent_board.research_graph={nodes:[{id:docId,kind:'document',label:'DOC / aaaaaaaa',known_utc:stamp},{id:partId,kind:'paragraph',label:'TEXT / bbbbbbbb',known_utc:stamp}],edges:[{a:docId,b:partId,relation:'PART_OF_DOCUMENT'}],total_documents:1};
packet.agent_board.entries={status:'OBSERVED',positions:[]};
packet.agent_board.pair_activity={status:'OBSERVED',pid:42,as_of_utc:stamp,scan_observation_utc:stamp,symbols:['XAUUSD.vx','EURUSD.vx'],events:[event(3,'TEST_MOMENTUM_H4','STARTED',{symbol:'XAUUSD.vx'}),event(4,'TEST_BREAKOUT_H4','DONE',{symbol:'EURUSD.vx'})],active:[event(3,'TEST_MOMENTUM_H4','STARTED',{symbol:'XAUUSD.vx'})]};
sandbox.packet=packet;
run('render(packet)');
assert.equal(get('symbols').textContent,'1');
assert.equal(get('execution').textContent,'LIVE KATARINA / OFF');
assert.ok(run('graph.nodes.length')>2);assert.equal(run('graph.nodes.filter(n=>n.kind==="pair").length'),2);assert.ok(run('graph.edges.some(e=>e.relation==="PAIR_WORK"&&e.a==="pair:XAUUSD.vx")'));assert.equal(run('nodeCode({kind:"pair",symbol:"EURUSD.vx"})'),'EURUSD.vx');
assert.ok(run('graph.edges.every(e=>nodeMap.has(e.a)&&nodeMap.has(e.b))'));
const firstGraph=run('graph');run('render(packet)');assert.equal(run('graph'),firstGraph);
assert.equal(run('nodeCode({kind:"phase",phase:"TEST_MOMENTUM_H4",id:"p:test"})'),'W01');
assert.match(run('nodeCode({kind:"document",id:"k:doc"})'),/^DOC-[0-9a-f]{8}$/);
assert.equal(run('nodeCode({kind:"document",id:"k:doc"})'),run('nodeCode({kind:"document",id:"k:doc"})'));
assert.ok(run('graph.edges.filter(e=>e.relation==="PROCESS_PHASE_REPORT").every(e=>e.b==="core")'));
assert.equal(run('nodeCode({kind:"phase",phase:"DEMO_EXECUTION"})'),'E01');
run('renderWorkerRuntime({status:"OBSERVED",mt5_algo_enabled:true,demo_permission:true,demo_status:"PROTECTED_VARIANT_NOT_QUALIFIED",fresh_workers:9,paused_workers:9,executor:{pid:99,cycles:2,status:"RUNNING",as_of_utc:new Date().toISOString()}})');
assert.equal(get('mt5-algo-proof').textContent,'ON');assert.equal(get('demo-permission-proof').textContent,'ON · KHUSUS DEMO');assert.equal(get('demo-status-proof').textContent,'Menunggu strategi lolos uji');assert.match(get('worker-runtime-proof').textContent,/9 jeda kapasitas/);
const count=draws.length;run('resize()');assert.equal(draws.slice(count).filter(d=>d[0]==='setTransform').length,0);
const older=JSON.parse(JSON.stringify(packet));older.captured_at_utc=new Date(fixed-1000).toISOString();older.agent_board.research_graph.nodes=[];
sandbox.older=older;run('render(older)');assert.equal(run('graph'),firstGraph);
run('orbitOn=false;draw(0)');
const coordinates=run('JSON.stringify(projected.filter(p=>p.node.kind!=="pair").map(p=>[p.node.id,p.x,p.y]))');run('draw(100)');
assert.notEqual(run('JSON.stringify(projected.filter(p=>p.node.kind!=="pair").map(p=>[p.node.id,p.x,p.y]))'),coordinates);assert.ok(run('networkRotation>0'));assert.ok(run('Array.from({length:12},(_,slot)=>orbitPair({node:{slot}})).every(p=>Math.abs(Math.hypot(p.x,p.y,p.z)-1.16)<1e-9)'));assert.equal(run('new Set(Array.from({length:12},(_,slot)=>orbitPair({node:{slot}}).y)).size'),12);
sandbox.growth={status:'PERSISTED_RESEARCH_COUNTS',as_of_utc:stamp,experiments:12,hypotheses:3,documents:4,reports:8};
run('renderLearning({status:"NOT_ATTESTED"},{research_growth:growth,model:{telemetry:{successful_calls:2}}})');
assert.ok(get('learning-proof').children.some(c=>c.textContent.includes('12 eksperimen')));
assert.ok(get('learning-proof').children.some(c=>c.textContent==='CHECKPOINT KOGNITIF BELUM SINKRON'));
assert.ok(draws.some(d=>d[0]==='lineTo'));assert.ok(draws.some(d=>d[0]==='drawImage'));
assert.equal(run('ambientAllowed()'),true);const ambientDraws=draws.length;run('draw(150)');assert.ok(draws.slice(ambientDraws).some(d=>d[0]==='arc'));
const pairBefore=run('JSON.stringify(projected.filter(p=>p.node.kind==="pair").map(p=>[p.x,p.y]))');const cachedDraws=draws.length;run('draw(200)');assert.notEqual(run('JSON.stringify(projected.filter(p=>p.node.kind==="pair").map(p=>[p.x,p.y]))'),pairBefore);assert.ok(draws.slice(cachedDraws).some(d=>d[0]==='lineTo'));
assert.equal(run('orbitOn'),false);
run('acceptPulseEvents([packet.agent_board.activity.current,packet.agent_board.activity.current],200,false)');assert.equal(run('eventPulses.filter(e=>e.phase==="TECHNICAL").length'),1);
run('selectNode("k:"+packet.agent_board.research_graph.nodes[0].id)');assert.ok(get('selection').children[1].textContent.includes('DOC / aaaaaaaa'));
const actualProjected=run('projected');
run('projected=[{x:-20,y:100,node:{id:"p:TEST_MOMENTUM_H4",kind:"phase",phase:"TEST_MOMENTUM_H4"}},{x:100,y:100,node:{id:"p:TEST_MOMENTUM_H12",kind:"phase",phase:"TEST_MOMENTUM_H12"}}]');
assert.equal(run('labelCandidates().length'),1);assert.equal(run('labelCandidates()[0].node.phase'),'TEST_MOMENTUM_H12');
sandbox.actualProjected=actualProjected;run('projected=actualProjected');
assert.equal(run('signalSegment({x:0,y:0},{x:100,y:0}).a.x'),15);
assert.equal(run('signalSegment({x:0,y:0},{x:100,y:0}).b.x'),89);
assert.equal(run('signalSegment({x:0,y:0},{x:10,y:0})'),null);
// Rendering budgets are enforced regardless of server graph density.
sandbox.edges=Array.from({length:1000},(_,i)=>({a:'k:a'+i,b:'k:b'+i,relation:'PART_OF_DOCUMENT'}));
assert.equal(run('visibleEdges(edges).length'),640);
run('selected=null;acceptPulseEvents(Array.from({length:40},(_,i)=>({phase:"P"+i,seq:i,state:"DONE",at_utc:new Date().toISOString()})),300,false)');assert.ok(run('eventPulses.length')<=96);
// Preserve multiple actual events per phase, deduplicate exact identities, keep concurrent timestamps.
run('eventPulses=[];acceptPulseEvents([{phase:"TECHNICAL",seq:101,state:"STARTED",at_utc:new Date().toISOString()},{phase:"TECHNICAL",seq:102,state:"DONE",at_utc:new Date().toISOString()},{phase:"MEMORY",seq:103,state:"STARTED",at_utc:new Date().toISOString()}],400,false)');
assert.equal(run('eventPulses.length'),3);assert.equal(run('new Set(eventPulses.map(p=>p.start)).size'),1);
run('acceptPulseEvents([{phase:"TECHNICAL",seq:102,state:"DONE",at_utc:new Date().toISOString()}],400,false)');assert.equal(run('eventPulses.length'),3);
run('acceptPulseEvents([{phase:"TECHNICAL",seq:104,state:"DONE",at_utc:new Date(Date.now()-25000).toISOString()}],400,false)');assert.equal(run('eventPulses.length'),3);

assert.ok(run('graph.nodes.some(n=>n.kind==="event")'));assert.ok(run('graph.edges.some(e=>e.relation==="EVENT_REPORT")'));
// Lists are collapsed by default, selected detail survives data refresh, stale data clears both lists.
sandbox.entryFixture={status:'OBSERVED',history_status:'OBSERVED',plans_status:'OBSERVED',history:[{id:'a'.repeat(24),symbol:'XAUUSD.vx',side:'BUY',state:'CLOSED',decision_utc:stamp,requested_price:4000,stop_loss:3990,take_profit:4020}],plans:[{id:'b'.repeat(24),symbol:'EURUSD.vx',side:'SELL',method:'BREAKOUT',state:'NOT_QUALIFIED',lookback:24,horizon:4,threshold:.5,last_reviewed_utc:stamp,checks:[]}]};
run('renderEntries(null,entryFixture)');let row=get('methods').children[0],planRow=get('entry-plans').children[0];
assert.equal(row.tag,'details');assert.equal(row.open,false);assert.equal(planRow.open,false);assert.equal(row.children[0].tag,'summary');assert.match(row.children[0].children[0].textContent,/XAUUSD/);
row.open=true;row.listeners.toggle();sandbox.entryFixture.history[0].state='OPEN';run('renderEntries(null,entryFixture)');assert.equal(get('methods').children[0].open,true,'Selection lost on refresh');
assert.match(run('planTrigger(entryFixture.plans[0])'),/low terendah/);
run('renderEntries(null,null)');assert.ok(get('methods').children.every(r=>r.tag!=='details'));assert.ok(get('entry-plans').children.every(r=>r.tag!=='details'));
// Exercise actual registered controls: drag, simultaneous pinch/pan, cancellation and resume.
const controls=get('network').listeners;
const pointer=(id,x,y)=>({pointerId:id,clientX:x,clientY:y,button:0,preventDefault(){}});
clock=fixed+2000;run('resetView();draw(2000)');const initialYaw=run('yaw'),initialRotation=run('networkRotation');
controls.pointerdown(pointer(1,100,100));clock+=32;controls.pointermove(pointer(1,150,120));
assert.ok(run('yaw')>initialYaw);assert.ok(run('pitch')>0);run('draw(2032)');assert.equal(run('networkRotation'),initialRotation);
controls.pointerdown(pointer(2,250,120));const oldZoom=run('zoom'),oldPan=run('panX');
clock+=32;controls.pointermove(pointer(2,290,140));assert.ok(run('zoom')>oldZoom);assert.ok(run('panX')>oldPan);
controls.pointerup(pointer(2,290,140));const yawBefore=run('yaw');clock+=32;controls.pointermove(pointer(1,155,120));assert.ok(Math.abs(run('yaw')-yawBefore)<.1,'Second finger release jumped');
controls.pointercancel(pointer(1,155,120));assert.equal(run('pointers.size'),0);assert.equal(get('network').dataset.dragging,'false');assert.equal(run('cameraVelocity.yaw'),0);
clock=fixed+3000;run('draw(3000)');assert.equal(run('networkRotation'),initialRotation);
clock=fixed+4100;run('draw(4100)');assert.ok(run('networkRotation')>initialRotation,'Auto rotation did not resume');
controls.wheel({deltaY:-100,preventDefault(){}});assert.ok(run('zoom')>oldZoom);
controls.keydown({key:'Home',preventDefault(){}});assert.equal(run('zoom'),1);assert.equal(run('panX'),0);assert.equal(run('yaw'),0);
clock+=50;controls.pointerdown(pointer(1,10,10));controls.pointerup(pointer(1,10,10));run('zoom=2');clock+=150;controls.pointerdown(pointer(1,10,10));controls.pointerup(pointer(1,10,10));assert.equal(run('zoom'),1,'Double tap must restore view');
run('pulseOn=false');assert.equal(run('ambientAllowed()'),false);run('pulseOn=true');
clock=fixed+121000;run('checkFreshness()');assert.equal(run('graph.nodes.length'),0);assert.equal(run('graphFresh'),false);
console.log('PASS_CURRENT_HOSTED_CODES_RESIZE_ORDER_PROVENANCE_EXPIRY');

"""
        result = subprocess.run([shutil.which("node")], input=harness.replace("WORKER_SOURCE", json.dumps(source), 1),
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
