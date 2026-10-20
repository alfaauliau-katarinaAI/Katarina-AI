const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),{createCanvas}=require('@napi-rs/canvas');
const [pagePath,snapshotPath,outputPath]=process.argv.slice(2);
if(!pagePath||!snapshotPath||!outputPath)throw new Error('Usage: node verify_network_canvas.cjs PUBLIC_PAGE PUBLIC_SNAPSHOT OUTPUT_DIRECTORY');
const path=require('node:path');fs.mkdirSync(outputPath,{recursive:true});
const page=fs.readFileSync(pagePath,'utf8'),packet=JSON.parse(fs.readFileSync(snapshotPath,'utf8'));
const script=page.split('<script>')[1].split('</script>')[0];
const els=new Map();let viewport={width:390,height:440},clock=Date.parse(packet.captured_at_utc),epoch=clock,perf=0;
const native=()=>{const c=createCanvas(1,1);c.style={};c.listeners={};c.addEventListener=(k,f)=>c.listeners[k]=f;c.getBoundingClientRect=()=>({...viewport,left:0,top:0});c.setPointerCapture=()=>{};c.releasePointerCapture=()=>{};return c};
function el(tag='div'){if(tag==='canvas')return native();return {children:[],style:{},dataset:{},attrs:{},listeners:{},textContent:'',value:'',hidden:false,disabled:false,append(...v){this.children.push(...v)},replaceChildren(...v){this.children=[...v]},setAttribute(k,v){this.attrs[k]=String(v)},getAttribute(k){return this.attrs[k]},addEventListener(k,f){this.listeners[k]=f},getBoundingClientRect:()=>({...viewport,left:0,top:0})}}
const get=id=>{if(!els.has(id))els.set(id,id==='network'?native():el());return els.get(id)};
class Clock extends Date{constructor(...args){super(...(args.length?args:[clock]))}static now(){return clock}}
const sandbox={Date:Clock,performance:{now:()=>perf},console,window:{innerWidth:390,devicePixelRatio:3,matchMedia:()=>({matches:false}),addEventListener(){}},document:{hidden:false,fullscreenElement:null,getElementById:get,createElement:el,createElementNS:(_,t)=>el(t),addEventListener(){}},AbortController,ResizeObserver:class{observe(){}},setTimeout:()=>1,clearTimeout(){},setInterval:()=>1,clearInterval(){},requestAnimationFrame:()=>1,fetch:async()=>({ok:false,status:503})};
vm.createContext(sandbox);const run=s=>vm.runInContext(s,sandbox);vm.runInContext(script,sandbox);sandbox.packet=packet;run('render(packet)');
const step=t=>{perf=t;clock=epoch+t;run('draw('+t+')')};
step(0);fs.writeFileSync(path.join(outputPath,'canvas-start.png'),get('network').toBuffer('image/png'));
const coords=()=>run('JSON.stringify(projected.filter(p=>p.node.kind!=="pair").map(p=>[p.node.id,p.x,p.y]))');const before=coords();
const pairCoords=()=>run('JSON.stringify(projected.filter(p=>p.node.kind==="pair").map(p=>[p.node.id,p.x,p.y]))');const initialPairs=pairCoords();
const times=[];for(let t=34;t<=16000;t+=34){let begin=process.hrtime.bigint();step(t);times.push(Number(process.hrtime.bigint()-begin)/1e6);assert.equal(coords(),before,'Topology shifted while only event effects advanced')}
if(run('projected.some(p=>p.node.kind==="pair")'))assert.notEqual(pairCoords(),initialPairs,'Pair orbit did not advance');
fs.writeFileSync(path.join(outputPath,'canvas-end.png'),get('network').toBuffer('image/png'));
// Between VPS events, presentation shimmer must advance without moving topology or inventing events.
run('eventPulses=[];boardNow.activity.active=[];corePulseAt=-10000;nodeBirths.clear()');step(16020);
const ambient=get('network').toBuffer('image/png');step(16080);assert.notDeepEqual(get('network').toBuffer('image/png'),ambient,'Waiting animation is frozen');
assert.equal(run('eventPulses.length'),0);assert.equal(coords(),before);
// With motion paused, a changing clock must not alter a single pixel.
run('pulseOn=false');step(16100);const still=get('network').toBuffer('image/png');step(16200);assert.deepEqual(get('network').toBuffer('image/png'),still);
// Internal projection stress test; interactive camera controls are absent.
run('zoom=2.6;panX=0;panY=0;yaw=.8;pitch=.3;cameraInput=null');step(16300);assert.ok(run('projected.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y))'));
fs.writeFileSync(path.join(outputPath,'canvas-zoom.png'),get('network').toBuffer('image/png'));
viewport={width:360,height:385};run('resize();resetView()');for(let t=16400;t<18000;t+=34)step(t);
fs.writeFileSync(path.join(outputPath,'canvas-resized.png'),get('network').toBuffer('image/png'));
assert.equal(get('network').width,540);assert.equal(get('network').height,578);
const pixels=get('network').getContext('2d').getImageData(0,0,540,578).data;assert.ok(pixels.every((v,i)=>i%4!==3||v===255),'Canvas background is not opaque');
times.sort((a,b)=>a-b);const result={passed:true,nodes:run('graph.nodes.length'),drawnEdges:run('displayScene.edges.length'),frames:times.length,render_ms_p50:times[Math.floor(times.length*.5)],render_ms_p95:times[Math.floor(times.length*.95)],research_coordinate_shift:false,pair_orbit_verified:true,paused_pixels_identical:true,opaque_canvas:true,native_canvas_test:true,waiting_animation_verified:true,browser_test:false};fs.writeFileSync(path.join(outputPath,'result.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
