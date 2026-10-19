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
    public = public_dashboard_snapshot({'agent_board':board})
    from katarina.monitoring.learning_evidence import read_learning
    public['agent_board']['learning'] = (
        read_learning(root, observation_utc=evidence.get('operational', {}).get('observation_utc'))
        if board['snapshot_process_matches'] and board.get('result') == 'SNAPSHOT_PASS'
        else {'status': 'NOT_ATTESTED', 'source': 'CANONICAL_RESEARCH_SNAPSHOT'})
    from katarina.monitoring.public_research import read_public_research
    allowed = board['snapshot_process_matches'] and board.get('result') == 'SNAPSHOT_PASS'
    graph, entries = read_public_research(root,evidence.get('operational',{}).get('observation_utc')) if allowed else (
        {'schema_version':1,'nodes':[],'edges':[],'status':'NOT_ATTESTED'},
        {'status':'NOT_ATTESTED','positions':[]})
    public_board=public['agent_board']
    public_board['research_graph']=graph
    public_board['entries']=entries
    public_board['market_symbols']=None
    public_board['operational']={}
    public_board['learning'].pop('no_signal_observations',None)
    trace=public_board['activity']
    trace['events']=[{k:e[k] for k in ('seq','at_utc','phase','state')} for e in trace['events']]
    trace['current']=trace['events'][-1] if trace['events'] else None
    public_board['public_scope']='RESEARCH_GRAPH_AND_ENTRY_ONLY'
    return public
