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
    market_process_matches=evidence.get('operational',{}).get('snapshot_pid')==pid
    board['snapshot_process_matches']=bool(type(pid) is int and activity.get('pid')==pid and activity.get('fresh'))
    if not market_process_matches:
        board['result']='BLOCKED'
    if status.get('status') in ('STOPPED','BLOCKED'):
        board['result']='BLOCKED'
    board['model']={'configured':status.get('model_configured') is True,
                    'telemetry':status.get('model_telemetry',{})}
    board['activity']=activity
    public = public_dashboard_snapshot({'agent_board':board})
    from katarina.monitoring.learning_evidence import read_learning
    from katarina.monitoring.public_research import read_public_research
    allowed = board['snapshot_process_matches'] and board.get('result') == 'SNAPSHOT_PASS'
    research_allowed = bool(board['snapshot_process_matches'] and status.get('delivery') == 'DISABLED'
        and status.get('live_execution_authorized') is False and status.get('orders_submitted') == 0
        and status.get('status') in ('WAITING','OBSERVING','DEGRADED'))
    # Sensor completeness and persisted research provenance are separate attestations.
    try:
        with (root/'latest.json').open('rb') as stream:
            raw=stream.read(2_000_001)
        observation_stamp=json.loads(raw)['observed_at_utc'] if len(raw)<=2_000_000 else None
    except (OSError,ValueError,KeyError):
        observation_stamp=None
    graph, entries = read_public_research(root,observation_stamp) if research_allowed else (
        {'schema_version':1,'nodes':[],'edges':[],'status':'NOT_ATTESTED'},
        {'status':'NOT_ATTESTED','positions':[]})
    if research_allowed and graph.get('status')=='NOT_ATTESTED':
        from katarina.monitoring.public_research import worker_research_runs,graph_from_report
        runs=worker_research_runs(root)
        if runs:graph=graph_from_report({'continuous_research_lab':{'recent':runs}})
    public_board=public['agent_board']
    # Process activity, market completeness and learning are distinct evidence scopes.
    from datetime import datetime, timezone
    try:
        heartbeat_age=(datetime.now(timezone.utc)-datetime.fromisoformat(status['heartbeat_utc'])).total_seconds()
    except (KeyError,ValueError,TypeError):
        heartbeat_age=float('inf')
    public_board['telemetry_verified']=bool(research_allowed and status.get('production_execution') is False
                                           and (-30<=heartbeat_age<=180 or activity.get('fresh') is True))
    public_board['market_snapshot_verified']=board.get('result')=='SNAPSHOT_PASS'
    public_board['sensor_blockers']=evidence.get('blockers',[])
    public_board['learning']=(read_learning(root,observation_utc=observation_stamp)
                              if public_board['telemetry_verified'] else {'status':'NOT_ATTESTED'})
    from katarina.monitoring.research_growth import read_growth
    public_board['research_growth']=read_growth(root,pid) if research_allowed else {'status':'NOT_ATTESTED'}
    public_board['research_graph']=graph
    from katarina.intelligence.research_reports import read_reports
    public_board['research_reports']=read_reports(root,pid) if research_allowed else {'status':'NOT_ATTESTED'}
    from katarina.monitoring.research_lab_status import read_lab_status
    public_board['research_lab'] = read_lab_status(root) if research_allowed else {'status':'NOT_ATTESTED'}
    from katarina.intelligence.data_recovery import read_recovery
    public_board['research_lab']['recovery']=read_recovery(root,pid) if research_allowed else {'status':'NOT_ATTESTED'}
    public_board['research_source_verified'] = research_allowed and graph.get('status') != 'NOT_ATTESTED'
    public_board['entries']=entries
    public_board['market_symbols']=None
    public_board['operational']={}
    public_board['learning'].pop('no_signal_observations',None)
    trace=public_board['activity']
    trace['events']=[{k:e[k] for k in ('seq','at_utc','phase','state')} for e in trace['events']]
    trace['current']=trace['events'][-1] if trace['events'] else None
    from katarina.monitoring.worker_runtime import read_worker_runtime
    public_board['worker_runtime']=read_worker_runtime(root,pid)
    public_board['public_scope']='RESEARCH_GRAPH_AND_ENTRY_ONLY'
    from katarina.monitoring.pair_activity import read_pair_activity
    public_board['pair_activity']=read_pair_activity(root,pid,allowed=public_board.get('telemetry_verified') is True and board['snapshot_process_matches'])
    return public
