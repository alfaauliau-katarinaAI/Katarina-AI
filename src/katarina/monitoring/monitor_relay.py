"""Small memory-only relay for signed technical snapshots; no broker/model/owner commands."""
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import hmac
import json
import os
from threading import Lock

from katarina.adapters.agent_dashboard_page import dashboard_page
from katarina.adapters.owner_dialog_server import public_dashboard_snapshot

class SnapshotBuffer:
    def __init__(self, *, now=None):
        self.now=now or (lambda:datetime.now(timezone.utc))
        self.lock=Lock()
        self.payload=None
        self.captured=None

    def accept(self,report):
        stamp=datetime.fromisoformat(report['captured_at_utc'].replace('Z','+00:00'))
        if stamp.tzinfo is None or not -30 <= (self.now()-stamp).total_seconds() <= 120:
            raise ValueError('invalid_snapshot_time')
        public=public_dashboard_snapshot(report)
        public['captured_at_utc']=stamp.isoformat()
        public['transport']='VPS_SIGNED_TELEMETRY'
        with self.lock:
            if self.captured is not None and stamp<=self.captured:
                raise ValueError('snapshot_replay')
            self.payload=public
            self.captured=stamp

    def read(self):
        with self.lock:
            if self.payload is None or (self.now()-self.captured).total_seconds()>120:
                return None
            return self.payload

def create_relay(*,token,bind='127.0.0.1',port=0,buffer=None):
    if not isinstance(token,str) or len(token)<32 or not token.isascii() or any(c.isspace() for c in token):
        raise ValueError('relay_secret_required')
    buffer=buffer or SnapshotBuffer()
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(5)
        def log_message(self,*args):
            pass
        def reply(self,code,value,mime='application/json'):
            raw=value.encode()
            self.send_response(code)
            for key,value in {'Content-Type':mime+'; charset=utf-8','Content-Length':str(len(raw)),
                    'Cache-Control':'no-store','Connection':'close','X-Content-Type-Options':'nosniff',
                    'X-Frame-Options':'DENY'}.items():
                self.send_header(key,value)
            self.end_headers()
            self.wfile.write(raw)
            self.close_connection=True
        def do_GET(self):
            if self.path in ('/','/agents'):
                self.reply(200,dashboard_page(public_status=True),'text/html')
            elif self.path=='/healthz':
                self.reply(200,'{"status":"READY"}')
            elif self.path=='/public-status':
                report=buffer.read()
                self.reply(200,json.dumps(report,allow_nan=False)) if report else self.reply(503,'{"status":"VPS_TELEMETRY_STALE_OR_MISSING"}')
            else:
                self.reply(404,'{}')
        def do_POST(self):
            allowed=hmac.compare_digest(self.headers.get('Authorization','').encode(),
                                        ('Bearer '+token).encode())
            if self.path!='/ingest' or not allowed:
                try:
                    n=int(self.headers.get('Content-Length','0'))
                    if not self.headers.get('Transfer-Encoding') and 0<n<=131072:
                        self.rfile.read(n)
                except (OSError,ValueError):
                    pass
                self.reply(403,'{}')
                return
            try:
                n=int(self.headers.get('Content-Length','0'))
                if self.headers.get('Transfer-Encoding') or not 0<n<=131072:
                    raise ValueError()
                report=json.loads(self.rfile.read(n))
                buffer.accept(report)
            except Exception:
                self.reply(400,'{"status":"SNAPSHOT_REJECTED"}')
                return
            self.reply(202,'{"status":"ACCEPTED"}')
    server=ThreadingHTTPServer((bind,port),Handler)
    server.daemon_threads=True
    server.buffer=buffer
    return server

def serve():
    server=create_relay(token=os.environ.get('KATARINA_MONITOR_INGEST_TOKEN',''),
                        bind='0.0.0.0',port=int(os.environ.get('PORT','10000')))
    try:
        server.serve_forever()
    finally:
        server.server_close()
