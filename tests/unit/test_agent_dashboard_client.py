"""Exercise actual dashboard JavaScript after an authenticated status read."""
import json
import shutil
import subprocess
import unittest

from katarina.adapters.agent_dashboard_page import AGENT_PAGE


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
  assert.match(nodes.get("trace-count").textContent,/1 SIMBOL \/ 3 HASIL/);
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
  assert.equal(nodes.get("trace-count").textContent,"MENUNGGU BUKTI");
  assert.equal(nodes.get("refresh").disabled,false);
 }
})().catch(e=>{console.error(e);process.exitCode=1});
"""
        result = subprocess.run(
            [shutil.which("node"), "-e", harness.replace("SCRIPT", json.dumps(script), 1)],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
