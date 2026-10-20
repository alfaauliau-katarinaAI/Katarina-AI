"""Outbound test telemetry only. Reads snapshots; never opens MT5 or mutates AI memory."""
from katarina.monitoring.snapshot_io import replace_snapshot
from datetime import datetime,timezone
import json
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPSHandler,ProxyHandler,HTTPRedirectHandler

from katarina.monitoring.public_runtime import build_public_runtime

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('monitor_redirect_rejected')

def publish_once(root,config):
    endpoint=config['endpoint']
    target=urlsplit(endpoint)
    if (target.scheme!='https' or not target.hostname or not (target.hostname.endswith('.onrender.com') or target.hostname.endswith('.chatgpt.site'))
            or target.path!='/ingest' or target.username or target.password or target.query or target.fragment
            or target.port not in (None,443)):
        raise ValueError('invalid_monitor_endpoint')
    token=config['token']
    if not isinstance(token,str) or len(token)<32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError('invalid_monitor_secret')
    headers={'Content-Type':'application/json','Authorization':'Bearer '+token,
             'User-Agent':'Katarina-Runtime-Monitor/1.0'}
    service_token=config.get('sites_service_token')
    if service_token:
        if (not target.hostname.endswith('.chatgpt.site')
                or config.get('service_origin') != 'https://'+target.netloc
                or not isinstance(service_token,str) or len(service_token)<32
                or not service_token.isascii() or any(c.isspace() for c in service_token)):
            raise ValueError('site_service_access_origin_mismatch')
        headers['OAI-Sites-Authorization']='Bearer '+service_token
    report=build_public_runtime(root)
    report['captured_at_utc']=datetime.now(timezone.utc).isoformat()
    raw=json.dumps(report,allow_nan=False).encode()
    if len(raw)>131072:
        # Keep result reports deliverable as provenance grows; the graph is a bounded view.
        graph=report.get('agent_board',{}).get('research_graph',{})
        priority={'experiment':0,'dataset':1,'instrument':2,'source':3,'topic':4}
        graph['nodes']=sorted(graph.get('nodes',[]),key=lambda n:priority.get(n.get('kind'),5))[:256]
        ids={n['id'] for n in graph['nodes']}
        graph['edges']=[e for e in graph.get('edges',[]) if e['a'] in ids and e['b'] in ids][:384]
        graph['truncated']=True
        raw=json.dumps(report,allow_nan=False).encode()
    if len(raw)>131072:
        raise ValueError('monitor_snapshot_too_large')
    context=ssl.create_default_context(cafile=config.get('ca_file'))
    request=Request(endpoint,data=raw,method='POST',
                    headers=headers)
    with build_opener(ProxyHandler({}),HTTPSHandler(context=context),NoRedirect()).open(request,timeout=30) as response:
        if response.status!=202:
            raise ValueError('monitor_ingest_not_accepted')
    return {'status':'PUBLISHED','captured_at_utc':report['captured_at_utc']}

def _source_version(root):
    try:
        root=Path(root)
        return tuple((root/name).stat().st_mtime_ns if (root/name).exists() else 0
                     for name in ('runtime-activity.json','continuous-status.json','research-reports.json','data-recovery.json'))
    except OSError:
        return None


def _wait_for_publication(root,version,started,interval_seconds,*,sleep=time.sleep,clock=time.monotonic):
    """Coalesce changed lifecycle files; no broker/DB access and at most two uploads per second."""
    deadline=started+interval_seconds
    while True:
        now=clock()
        if now>=deadline or (now-started>=0.5 and _source_version(root)!=version):
            return
        sleep(min(0.25,max(0,deadline-now)))


def run(root,config_path,*,interval_seconds=15,once=False):
    if type(interval_seconds) is not int or not 10<=interval_seconds<=60:
        raise ValueError('invalid_monitor_interval')
    config=json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    failures=0
    while True:
        version=_source_version(root)
        started=time.monotonic()
        try:
            health=publish_once(root,config)
            failures=0
        except Exception:
            failures+=1
            health={'status':'PUBLISH_FAILED','consecutive_failures':failures,
                    'checked_at_utc':datetime.now(timezone.utc).isoformat()}
        temp=Path(root)/'monitor-publisher.tmp'
        temp.write_text(json.dumps(health)+'\n',encoding='utf-8')
        replace_snapshot(temp,Path(root)/'monitor-publisher-health.json')
        if once:
            return health
        if failures:
            time.sleep(min(60,interval_seconds*2**min(failures,2)))
        else:
            _wait_for_publication(root,version,started,interval_seconds)
