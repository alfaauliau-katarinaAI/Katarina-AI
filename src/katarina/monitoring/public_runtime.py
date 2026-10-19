"""Reconstruct a technical-only, freshness-checked view without opening broker or memory."""
from pathlib import Path
import json
from katarina.intelligence.runtime_evidence import read_runtime
from katarina.monitoring.agent_projection import project_agent_board
from katarina.monitoring.activity_trace import read_activity
from katarina.adapters.owner_dialog_server import public_dashboard_snapshot

def build_public_runtime(root):
    root=Path(root)
    try:
        status=json.loads((root/'continuous-status.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):
        status={}
    evidence=read_runtime(root)
    board=project_agent_board(evidence,delivery=status.get('delivery','UNVERIFIED'))
    activity=read_activity(root)
    pid=status.get('pid')
    board['current_process_pid']=pid
    board['snapshot_process_matches']=bool(type(pid) is int and activity.get('pid')==pid
        and evidence.get('operational',{}).get('snapshot_pid')==pid and activity.get('fresh'))
    if status.get('status') in ('STOPPED','BLOCKED'):
        board['result']='BLOCKED'
    board['model']={'configured':status.get('model_configured') is True,
                    'telemetry':status.get('model_telemetry',{})}
    board['activity']=activity
    return public_dashboard_snapshot({'agent_board':board})
