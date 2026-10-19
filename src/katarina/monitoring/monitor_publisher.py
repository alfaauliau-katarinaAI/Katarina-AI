"""Outbound test telemetry only. Reads snapshots; never opens MT5 or mutates AI memory."""
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
        raise ValueError('monitor_snapshot_too_large')
    context=ssl.create_default_context(cafile=config.get('ca_file'))
    request=Request(endpoint,data=raw,method='POST',
                    headers=headers)
    with build_opener(ProxyHandler({}),HTTPSHandler(context=context),NoRedirect()).open(request,timeout=30) as response:
        if response.status!=202:
            raise ValueError('monitor_ingest_not_accepted')
    return {'status':'PUBLISHED','captured_at_utc':report['captured_at_utc']}

def run(root,config_path,*,interval_seconds=15,once=False):
    if type(interval_seconds) is not int or not 10<=interval_seconds<=60:
        raise ValueError('invalid_monitor_interval')
    config=json.loads(Path(config_path).read_text(encoding='utf-8-sig'))
    failures=0
    while True:
        try:
            health=publish_once(root,config)
            failures=0
        except Exception:
            failures+=1
            health={'status':'PUBLISH_FAILED','consecutive_failures':failures,
                    'checked_at_utc':datetime.now(timezone.utc).isoformat()}
        temp=Path(root)/'monitor-publisher.tmp'
        temp.write_text(json.dumps(health)+'\n',encoding='utf-8')
        temp.replace(Path(root)/'monitor-publisher-health.json')
        if once:
            return health
        time.sleep(min(60,interval_seconds*2**min(failures,2)))
