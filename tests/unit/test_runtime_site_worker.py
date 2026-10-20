"""Execute the deployed Worker handler against a conditional object store."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

@unittest.skipUnless(shutil.which('node'),'Node required for Worker runtime verification')
class RuntimeSiteWorkerTests(unittest.TestCase):
    def test_real_worker_auth_redaction_expiry_replay_and_readonly_routes(self):
        source=(Path(__file__).resolve().parents[2]/'sites/runtime-monitor/worker/index.js').read_text(encoding='utf-8')
        harness=r"""
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
globalThis.crypto??=webcrypto;
const source=WORKER_SOURCE;
const {default:worker}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
let stored=null,version=0;
const BUCKET={
 async get(){return stored?{etag:stored.etag,httpEtag:JSON.stringify(stored.etag),json:async()=>JSON.parse(stored.raw)}:null},
 async put(key,raw,options){
  assert.equal(key,'current-snapshot.json');
  if(options.onlyIf.get('If-None-Match')==='*'&&stored)return null;
  if(options.onlyIf.has('If-Match')&&options.onlyIf.get('If-Match')!==JSON.stringify(stored?.etag))return null;
  stored={raw,etag:'v'+(++version)};return {etag:stored.etag};
 }
};
const token='test-only-'+ 'x'.repeat(40),env={BUCKET,KATARINA_MONITOR_INGEST_TOKEN:token};
async function request(path,body,key){
 const headers={};const options={method:body===undefined?'GET':'POST',headers};
 if(body!==undefined){options.body=JSON.stringify(body);headers['Content-Length']=String(Buffer.byteLength(options.body));headers['Content-Type']='application/json'}
 if(key)headers.Authorization='Bearer '+key;
 return worker.fetch(new Request('https://example.chatgpt.site'+path,options),env);
}
const now=new Date().toISOString();
const packet={captured_at_utc:now,private:'PRIVATE_SENTINEL',agent_board:{
 result:'SNAPSHOT_PASS',research_source_verified:true,market_symbols:1,cycles:2,delivery:'DISABLED',
 observed_at_utc:now,current_process_pid:42,snapshot_process_matches:true,model:{configured:false,endpoint:'PRIVATE_SENTINEL'},
 operational:{account_login:'PRIVATE_SENTINEL',positions_count:123,
 technical_evaluations:[{symbol:'XAUUSD',method:'PULLBACK',market_state:'TREND_UP',action:'WAIT',secret:'PRIVATE_SENTINEL'}]},
 activity:{pid:42,cycle:2,events:[{seq:1,at_utc:now,phase:'TECHNICAL',state:'DONE',symbol:'XAUUSD',secret:'PRIVATE_SENTINEL'}]}}};
packet.agent_board.pair_activity={status:'OBSERVED',pid:42,as_of_utc:now,scan_observation_utc:now,symbols:['EURUSD.vx'],events:[{symbol:'EURUSD.vx',phase:'TECHNICAL',state:'DONE',seq:1,at_utc:now,bid:999,login:'PRIVATE_SENTINEL'}],active:[],secret:'PRIVATE_SENTINEL'};
packet.agent_board.worker_runtime={status:'OBSERVED',pid:42,as_of_utc:now,mt5_algo_enabled:true,demo_permission:true,demo_status:'PROTECTED_VARIANT_NOT_QUALIFIED',private:'PRIVATE_SENTINEL',workers:[{fresh:true,autonomous:true,status:'PAUSED_STORAGE_BUDGET',completed:4,secret:'PRIVATE_SENTINEL'}],executor:{pid:99,independent:true,audit_only:false,cycles:2,status:'RUNNING',as_of_utc:now,login:'PRIVATE_SENTINEL'}};
packet.agent_board.learning={status:'NO_NEW_MATURED_EVIDENCE',observation_utc:now,cognitive_as_of_utc:now,
 ledger_status:'ALREADY_LEARNED_NO_REWRITE',matured_observations:0,memory_records_inserted:0,
 shadow_rows_read:1,external_models_invoked:0,account_login:'PRIVATE_SENTINEL',improvement_verified:true};
packet.agent_board.operational.technical_evaluations[0].symbol='PRIVATE_MARKET_SYMBOL';
packet.agent_board.activity.events[0].symbol='PRIVATE_MARKET_SYMBOL';
packet.agent_board.entries={status:'OBSERVED',positions:[{symbol:'EURUSD',side:'BUY',entry_price:1.2,opened_utc:now,lot:88,profit:'PRIVATE_SENTINEL',ticket:'PRIVATE_SENTINEL'}]};
const docId='document:'+ 'a'.repeat(24),partId='paragraph:'+ 'b'.repeat(24);
packet.agent_board.research_graph={nodes:[{id:docId,kind:'document',label:'DOC / aaaaaaaa',known_utc:now,body:'PRIVATE_SENTINEL'},{id:partId,kind:'paragraph',label:'TEXT / bbbbbbbb'}],edges:[{a:docId,b:partId,relation:'PART_OF_DOCUMENT'}],total_documents:1};
assert.equal((await request('/public-status')).status,503);
assert.match(await (await request('/')).text(),/const PUBLIC_STATUS = true;/);
assert.equal((await request('/ingest',packet)).status,403);
assert.equal((await request('/turn',{},token)).status,403);
assert.equal((await request('/status',{},token)).status,403);
assert.equal((await request('/ingest',packet,token)).status,202);
const response=await request('/public-status'),body=await response.text();
const etag=response.headers.get('ETag');assert.ok(etag);const unchanged=await worker.fetch(new Request('https://example.chatgpt.site/public-status',{headers:{'If-None-Match':etag}}),env);assert.equal(unchanged.status,304);assert.equal(await unchanged.text(),'');
assert.equal(response.status,200);assert.equal(response.headers.get('Cache-Control'),'no-store');
assert.ok(!body.includes('PRIVATE_SENTINEL'));assert.ok(!body.includes('positions_count'));
assert.equal(JSON.parse(body).agent_board.activity.current.phase,'TECHNICAL');assert.equal(JSON.parse(body).agent_board.pair_activity.events[0].symbol,'EURUSD.vx');assert.ok(!body.includes('\"bid\"'));assert.equal(JSON.parse(body).agent_board.pair_activity.events[0].login,undefined);
assert.equal(JSON.parse(body).agent_board.worker_runtime.mt5_algo_enabled,true);assert.equal(JSON.parse(body).agent_board.worker_runtime.paused_workers,1);assert.equal(JSON.parse(body).agent_board.worker_runtime.executor.pid,99);assert.equal(JSON.parse(body).agent_board.worker_runtime.live_authorized,false);
assert.equal(JSON.parse(body).agent_board.learning.status,'NO_NEW_MATURED_EVIDENCE');
assert.equal(JSON.parse(body).agent_board.learning.memory_records_inserted,0);
assert.equal(JSON.parse(body).agent_board.learning.improvement_verified,false);
assert.deepEqual(JSON.parse(body).agent_board.operational,{});
assert.ok(!body.includes('PRIVATE_MARKET_SYMBOL'));assert.ok(!body.includes('"lot"'));assert.ok(!body.includes('"ticket"'));
assert.equal(JSON.parse(body).agent_board.entries.positions[0].symbol,'EURUSD');
assert.equal(JSON.parse(body).agent_board.entries.positions[0].entry_price,1.2);
assert.equal(JSON.parse(body).agent_board.research_graph.nodes.length,2);
assert.equal(JSON.parse(body).agent_board.research_graph.edges.length,1);
assert.equal((await request('/ingest',packet,token)).status,409);
const stale=structuredClone(packet);stale.captured_at_utc=new Date(Date.now()-121000).toISOString();
assert.equal((await request('/ingest',stale,token)).status,400);
stored.raw=JSON.stringify(stale);
assert.equal((await request('/public-status')).status,503);assert.equal((await worker.fetch(new Request('https://example.chatgpt.site/public-status',{headers:{'If-None-Match':etag}}),env)).status,503);
console.log('PASS_WORKER_AUTH_PRIVACY_ACTIVITY_EXPIRY');
"""
        result=subprocess.run([shutil.which('node'),'--input-type=module'],
            input=harness.replace('WORKER_SOURCE',json.dumps(source),1),
            capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
