"""Activate independent DEMO worker using the existing Windows task principal."""
from pathlib import Path
import argparse
import json
import subprocess
import xml.etree.ElementTree as ET


def activate(root,state,python,config):
    root=Path(root);state=Path(state)
    s=json.loads((state/'continuous-status.json').read_text(encoding='utf-8'))
    d=json.loads((state/'demo-forward/status.json').read_text(encoding='utf-8'))
    if not (s.get('live_execution_authorized') is False and s.get('production_execution') is False
            and d.get('live_authorized') is False and d.get('broker_positions_open')==0
            and d.get('unresolved_submissions')==0):raise RuntimeError('FLAT_DEMO_AND_LIVE_OFF_REQUIRED')
    name='KatarinaDemoExecutionWorker'
    task=subprocess.run(['schtasks','/Query','/TN',name,'/XML'],capture_output=True,text=True)
    if task.returncode==0 and 'run_independent_demo_worker.py' not in task.stdout:
        raise RuntimeError('EXISTING_TASK_NOT_OWNED')
    xml=subprocess.run(['schtasks','/Query','/TN','KatarinaOwnerContinuousReadonly','/XML'],capture_output=True,text=True,check=True).stdout
    ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'};ET.register_namespace('',ns['t']);tree=ET.fromstring(xml)
    action=tree.find('t:Actions/t:Exec',ns)
    if action is None:raise RuntimeError('UNKNOWN_EXISTING_TASK_ACTION')
    action.find('t:Command',ns).text=str(python)
    action.find('t:Arguments',ns).text='"'+str(root/'scripts/ai/run_independent_demo_worker.py')+'" --state-dir "'+str(state)+'" --connection-config "'+str(config)+'"'
    working=action.find('t:WorkingDirectory',ns)
    if working is not None:working.text=str(root)
    for tag in ('t:RegistrationInfo/t:URI','t:RegistrationInfo/t:Description'):
        node=tree.find(tag,ns)
        if node is not None:node.text='\\'+name if tag.endswith('URI') else 'Independent protected Katarina DEMO execution worker; LIVE OFF'
    # A continuous worker must not inherit a wall-clock kill from its scanner task.
    limit=tree.find('t:Settings/t:ExecutionTimeLimit',ns)
    if limit is not None:limit.text='PT0S'
    definition=root/'handoff-backups/autonomous-workers-20261020/executor-task.xml';definition.parent.mkdir(parents=True,exist_ok=True)
    tree.write(definition,encoding='utf-16',xml_declaration=True)
    subprocess.run(['schtasks','/Create','/TN',name,'/XML',str(definition),'/F'],check=True)
    if (state/'demo-forward/demo.stop').exists() or (state/'continuous.stop').exists():
        raise RuntimeError('OWNER_STOP_MUST_BE_PRESERVED')
    subprocess.run(['schtasks','/End','/TN','KatarinaOwnerContinuousReadonly'],check=True)
    try:
        marker=state/'demo-forward/independent.enabled';marker.write_text('DEMO_ONLY_AUTONOMOUS_EXECUTOR_V1\n',encoding='utf-8')
    finally:
        # Restore scanning even if writing the independent-mode marker fails.
        subprocess.run(['schtasks','/Run','/TN','KatarinaOwnerContinuousReadonly'],check=True)
    subprocess.run(['schtasks','/Run','/TN',name],check=True)
    print(json.dumps({'activated':True,'execution_mode':'DEMO','independent':True,'live_authorized':False}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--state-dir',required=True);p.add_argument('--python',required=True);p.add_argument('--connection-config',required=True);a=p.parse_args()
    activate(a.root,a.state_dir,a.python,a.connection_config)
