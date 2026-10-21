"""One PC acceptance run. Synthetic results never imply broker/live readiness."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import html
import json
import os
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from katarina.host import inspect_host, state_directory
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.adapters.automatic_connection import ConnectionConfig, run_connected
from katarina.adapters.pc_simulation import PCSimulationBroker


def _safe(result):
    return result.get('orders_submitted')==0 and result.get('live_execution_authorized') is False


def write_report(root,report):
    root.mkdir(parents=True,exist_ok=True)
    rows=''.join('<tr><td>'+html.escape(k)+'</td><td>'+html.escape(str(v))+'</td></tr>'
                 for k,v in report.items())
    page=('<!doctype html><html lang="id"><meta charset="utf-8"><title>Katarina PC Test</title>'
          '<style>body{font:16px system-ui;max-width:960px;margin:40px auto;padding:20px;'
          'background:#101826;color:#e4eefb}h1{color:#7ce5c0}table{border-collapse:collapse;width:100%}'
          'td{padding:12px;border:1px solid #40516a;overflow-wrap:anywhere}</style>'
          '<h1>Katarina — hasil uji PC</h1><p>LIVE OFF. Uji sintetis bukan bukti broker atau profit.</p>'
          '<table>'+rows+'</table></html>')
    for name,content in [('latest-pc-test.json',json.dumps(report,indent=2,sort_keys=True)),
                         ('latest-pc-test.html',page)]:
        target=root/name
        temporary=root/(name+'.'+uuid.uuid4().hex+'.tmp')
        temporary.write_text(content,encoding='utf-8'); temporary.replace(target)


def run(root,*,mode='demo',connection_config=None):
    root=Path(root)
    host=inspect_host(root)
    run_id=uuid.uuid4().hex
    work=root/'pc-tests'/run_id
    report={'schema_version':1,'mode':mode,'observed_at_utc':datetime.now(timezone.utc).isoformat(),
        'status':'BLOCKED','input':'SYNTHETIC_INVENTED' if mode=='demo' else 'CONFIGURED_BROKER_READONLY',
        'live_authorized':False,'broker_verified':False,'profitability_proven':False,'orders_sent':0,
        'run_directory':str(work),'checks':[]}
    try:
        if host['blockers']:
            raise RuntimeError('HOST_PREFLIGHT_BLOCKED')
        if mode=='demo':
            sensor=PCSimulationBroker()
            result=UnifiedKatarinaBrain.observe_once(work,broker=sensor,max_symbols=3,fetch_news=False)
            observed=json.loads((work/'latest.json').read_text())
            if (not _safe(observed) or result.get('orders')!=0 or result.get('observed_symbols')!=3 or not sensor.closed
                    or any('sensor_error:' in '|'.join(x['blocking_reasons']) for x in observed['symbols'].values())):
                raise RuntimeError('SYNTHETIC_OBSERVER_CHECK_FAILED')
            report['checks'].append('PASS: three invented sensors and actual brain pipeline, no orders')
            for _ in range(2):
                if not _safe(UnifiedKatarinaBrain.research_once(work)):
                    raise RuntimeError('OFFLINE_RESTART_CHECK_FAILED')
            report['checks'].append('PASS: checkpoint reopened twice with shared local memory')
            report['status']='PASS_SYNTHETIC_PC_ONLY'
        elif mode=='observe':
            if not connection_config:
                raise RuntimeError('CONNECTION_CONFIG_REQUIRED')
            config=ConnectionConfig.load(connection_config)
            # Broker evidence uses its normal state, never the invented demo database.
            work=root/'readonly-observer'
            report['run_directory']=str(work)
            result=run_connected(UnifiedKatarinaBrain,work,config=config,
                                 max_symbols=host['budget']['max_symbols'],fetch_news=False)
            route=result['connection']['route']
            report['route']=route
            # run_connected returns only static redacted diagnostic codes, never
            # exception messages/account values. Preserve them in the PC report.
            report['connection']=result['connection']
            if route not in ('local','cloud'):
                raise RuntimeError('BROKER_UNAVAILABLE_OFFLINE_ONLY')
            observed=json.loads((work/'latest.json').read_text())
            # A route being connected is not evidence that usable market data was read.
            if (not _safe(observed) or result.get('orders')!=0
                    or result.get('observed_symbols',0)<1 or not observed.get('symbols')
                    or any('sensor_error:' in '|'.join(x['blocking_reasons']) for x in observed['symbols'].values())):
                raise RuntimeError('BROKER_SENSOR_DATA_DEGRADED')
            report['status']='PASS_READONLY_OBSERVATION_ONLY'
            report['broker_verified']=True
            report['checks'].append('PASS: bound account and one read-only data pass; no risk/live clearance')
        else:
            raise ValueError('invalid_pc_test_mode')
    except Exception as exc:
        # No exception text, account identifiers, token, URL or credentials in the summary.
        report['error_type']=type(exc).__name__
        allowed={'HOST_PREFLIGHT_BLOCKED','SYNTHETIC_OBSERVER_CHECK_FAILED',
                 'OFFLINE_RESTART_CHECK_FAILED','CONNECTION_CONFIG_REQUIRED',
                 'BROKER_UNAVAILABLE_OFFLINE_ONLY','BROKER_SENSOR_DATA_DEGRADED'}
        report['reason']=str(exc) if str(exc) in allowed else 'PC_TEST_FAILED_SEE_CONFIGURATION'
        report['checks'].append('BLOCKED: inspect environment/configuration; no trading enabled')
    write_report(root,report)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['demo','observe'],default='demo')
    parser.add_argument('--state-dir')
    parser.add_argument('--connection-config')
    args=parser.parse_args()
    root=state_directory(args.state_dir)
    config=args.connection_config or os.environ.get('KATARINA_CONNECTION_CONFIG')
    report=run(root,mode=args.mode,connection_config=config)
    print('KATARINA_PC_TEST',report['status'],flush=True)
    print('Laporan:',root/'latest-pc-test.html',flush=True)
    print('JSON:',root/'latest-pc-test.json',flush=True)
    return 0 if report['status'].startswith('PASS_') else 2


if __name__=='__main__':
    raise SystemExit(main())
