"""Exercise actual dashboard JavaScript after an authenticated status read."""
import json
import shutil
import subprocess
import unittest

from katarina.adapters.agent_dashboard_page import AGENT_PAGE, dashboard_page


@unittest.skipUnless(shutil.which("node"), "Node is required for the browser-script regression")
class AgentDashboardClientTests(unittest.TestCase):
    def test_failed_or_missing_auth_clears_previously_valid_evidence(self):
        script = AGENT_PAGE.split("<script>", 1)[1].split("</script>", 1)[0]
        harness = r"""
const assert = require("node:assert/strict"), vm = require("node:vm");
const nodes = new Map();
function element() {
 return {textContent:"",value:"",disabled:false,children:[],
  append(...x){this.children.push(...x)},replaceChildren(...x){this.children=x},
  addEventListener(){},setAttribute(){},getBoundingClientRect(){return {width:400,height:300}},
  getContext(){return null}};
}
const context = vm.createContext({
 document:{getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)},
 createElement:element,createElementNS:element,hidden:false},window:{devicePixelRatio:1,addEventListener(){}},
 AbortController,setTimeout,clearTimeout,setInterval,clearInterval
});
vm.runInContext(SCRIPT, context);
context.document.getElementById("token");
const board={schema_version:1,result:"SNAPSHOT_PASS",market_symbols:3,cycles:24,
 delivery:"DISABLED",blockers:[],snapshot_process_matches:true,current_process_pid:42,
 operational:{technical_evaluations:[{symbol:"XAUUSD",market_state:"TREND_UP",method:"PULLBACK",action:"WAIT"}]},observed_at_utc:"2026-10-19T00:00:00Z",
 lanes:["SCAN","ANALYST","STRATEGY","BALANCE","EXEC","AUDIT"].map(id=>({
 id,status:"OBSERVED",description:id,reason:"fixture"}))};
(async()=>{
 for(const mode of ["forbidden","network","malformed","missing-token"]){
  nodes.get("token").value="test-only";
  context.fetch=async()=>({ok:true,json:async()=>({agent_board:board})});
  await vm.runInContext("refresh()",context);
  assert.equal(nodes.get("overall").textContent,"SNAPSHOT_PASS");
  assert.equal(nodes.get("lanes").children.length,6);
  assert.match(nodes.get("trace-count").textContent,/1 SIMBOL \/ 0 EVENT TERCATAT/);
  assert.ok(nodes.get("trace").children.length>4);
  if(mode==="missing-token") nodes.get("token").value="";
  else context.fetch=async()=>{
   if(mode==="network")throw Error("disconnected");
   return mode==="forbidden"?{ok:false,status:403}:{ok:true,json:async()=>({})};
  };
  await vm.runInContext("refresh()",context);
  assert.equal(nodes.get("overall").textContent,"BELUM TERVERIFIKASI");
  assert.equal(nodes.get("symbols").textContent,"—");
  assert.equal(nodes.get("cycles").textContent,"—");
  assert.equal(nodes.get("execution").textContent,"BELUM TERVERIFIKASI");
  assert.equal(nodes.get("lanes").children.length,0);
  assert.equal(nodes.get("trace").children.length,0);
  assert.equal(nodes.get("activity-events").children.length,0);
  assert.equal(nodes.get("trace-count").textContent,"MENUNGGU BUKTI");
  assert.equal(nodes.get("refresh").disabled,false);
 }
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", harness.replace("SCRIPT", json.dumps(script), 1)],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_public_page_loads_and_refreshes_without_a_token_or_authorization_header(self):
        script = dashboard_page(public_status=True).split("<script>",1)[1].split("</script>",1)[0]
        harness = r"""
const assert=require("node:assert/strict"),vm=require("node:vm"),nodes=new Map(),requests=[];
function element(){return {value:"",textContent:"",children:[],append(...v){this.children.push(...v)},
 replaceChildren(...v){this.children=v},setAttribute(){},addEventListener(){}}}
const board={schema_version:1,result:"SNAPSHOT_PASS",market_symbols:1,cycles:7,
 activity:{pid:42,cycle:7,fresh:true,current:{seq:2,at_utc:"2026-10-19T11:00:00Z",phase:"TECHNICAL",state:"DONE",symbol:"XAUUSD"},
 events:[{seq:1,at_utc:"2026-10-19T10:59:59Z",phase:"TECHNICAL",state:"STARTED",symbol:"XAUUSD"},{seq:2,at_utc:"2026-10-19T11:00:00Z",phase:"TECHNICAL",state:"DONE",symbol:"XAUUSD"}]},
 delivery:"DISABLED",blockers:[],lanes:[],snapshot_process_matches:true,current_process_pid:42,
 operational:{technical_evaluations:[{symbol:"XAUUSD",market_state:"TREND_UP",method:"PULLBACK",action:"WAIT"}]}};
const context=vm.createContext({
 document:{getElementById(id){if(!nodes.has(id))nodes.set(id,element());return nodes.get(id)},
 createElement:element,createElementNS:element,hidden:false},
 AbortController,setTimeout(){return 1},clearTimeout(){},setInterval(){return 1},clearInterval(){},
 fetch:async(url,options)=>{requests.push({url,options});return {ok:true,json:async()=>({agent_board:board})}}
});
vm.runInContext(SCRIPT,context);
(async()=>{
 await new Promise(setImmediate);
 assert.equal(requests.length,1);
 assert.equal(requests[0].url,"/public-status");
 assert.equal(requests[0].options.method,"GET");
 assert.equal(requests[0].options.headers,undefined);
 assert.equal(nodes.get("token").value,"");
 assert.equal(nodes.get("overall").textContent,"SNAPSHOT_PASS");
 assert.equal(nodes.get("auto").textContent,"Auto: ON");
 assert.equal(nodes.get("activity-events").children.length,2);
 assert.match(nodes.get("trace-state").textContent,/TECHNICAL.*selesai/);
 assert.equal(vm.runInContext("activityChanged",context),true);
 await vm.runInContext("refresh()",context);
 assert.equal(requests.length,2);
 assert.equal(vm.runInContext("activityChanged",context),false);
 context.fetch=async()=>({ok:false,status:503});
 await vm.runInContext("refresh()",context);
 assert.equal(nodes.get("overall").textContent,"BELUM TERVERIFIKASI");
 assert.equal(nodes.get("trace").children.length,0);
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        result=subprocess.run([shutil.which("node"),"-e",harness.replace("SCRIPT",json.dumps(script),1)],
                              capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
