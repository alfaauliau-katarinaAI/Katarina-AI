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
sandbox.packet=packet;
run('render(packet)');
assert.equal(get('symbols').textContent,'1');
assert.equal(get('execution').textContent,'LIVE / OFF');
assert.ok(run('graph.nodes.length')>2);
assert.ok(run('graph.edges.every(e=>nodeMap.has(e.a)&&nodeMap.has(e.b))'));
const firstGraph=run('graph');run('render(packet)');assert.equal(run('graph'),firstGraph);
assert.equal(run('nodeCode({kind:"phase",phase:"TEST_MOMENTUM_H4",id:"p:test"})'),'W01');
assert.match(run('nodeCode({kind:"document",id:"k:doc"})'),/^DOC-[0-9a-f]{8}$/);
assert.equal(run('nodeCode({kind:"document",id:"k:doc"})'),run('nodeCode({kind:"document",id:"k:doc"})'));
const count=draws.length;run('resize()');assert.equal(draws.slice(count).filter(d=>d[0]==='setTransform').length,0);
const older=JSON.parse(JSON.stringify(packet));older.captured_at_utc=new Date(fixed-1000).toISOString();older.agent_board.research_graph.nodes=[];
sandbox.older=older;run('render(older)');assert.equal(run('graph'),firstGraph);
run('orbitOn=false;draw(0)');
const coordinates=run('JSON.stringify(projected.map(p=>[p.node.id,p.x,p.y]))');run('draw(100)');
assert.equal(run('JSON.stringify(projected.map(p=>[p.node.id,p.x,p.y]))'),coordinates);
sandbox.growth={status:'PERSISTED_RESEARCH_COUNTS',as_of_utc:stamp,experiments:12,hypotheses:3,documents:4,reports:8};
run('renderLearning({status:"NOT_ATTESTED"},{research_growth:growth,model:{telemetry:{successful_calls:2}}})');
assert.ok(get('learning-proof').children.some(c=>c.textContent.includes('12 eksperimen')));
assert.ok(get('learning-proof').children.some(c=>c.textContent==='CHECKPOINT KOGNITIF BELUM SINKRON'));
assert.ok(draws.some(d=>d[0]==='quadraticCurveTo'));
run('selectNode("k:"+packet.agent_board.research_graph.nodes[0].id)');assert.ok(get('selection').children[1].textContent.includes('DOC / aaaaaaaa'));
get('network').listeners.pointerdown({pointerId:1,clientX:20,clientY:20});
get('network').listeners.pointermove({pointerId:1,clientX:60,clientY:25});
get('network').listeners.pointercancel({pointerId:1});
clock=fixed+121000;run('checkFreshness()');assert.equal(run('graph.nodes.length'),0);assert.equal(run('graphFresh'),false);
console.log('PASS_CURRENT_HOSTED_CODES_RESIZE_ORDER_PROVENANCE_EXPIRY');

"""
        result = subprocess.run([shutil.which("node")], input=harness.replace("WORKER_SOURCE", json.dumps(source), 1),
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
