"""Explicit foreground Owner browser surface, bearer-authenticated; never starts on import."""
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import ipaddress
import json
import os
import ssl

from katarina.adapters.agent_dashboard_page import AGENT_PAGE

PAGE = '''<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Katarina AI</title><style>body{font:17px system-ui;background:#101826;color:#e4eefb;max-width:820px;margin:30px auto;padding:20px}
input,textarea,button,select{box-sizing:border-box;font:inherit;padding:12px;border:1px solid #40516a;border-radius:8px;background:#19283a;color:inherit;margin:6px 0;width:100%}
button{background:#256a67;cursor:pointer}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;background:#19283a;border-radius:12px}small{color:#a9c4d8}</style>
<h1>Katarina AI</h1><p>Satu otak · LIVE OFF</p><small>Akses Owner. Jawaban model belum tentu benar; lihat bukti alat. Ctrl+C pada komputer host untuk berhenti.</small>
<p><input id="token" type="password" autocomplete="off" placeholder="Token Owner"><input id="session" value="owner" aria-label="Sesi">
<select id="mode" aria-label="Mode"><option value="auto">Otomatis</option><option>fast</option><option>deep</option></select></p>
<button id="check" type="button">Periksa status Katarina</button><pre id="runtime" aria-live="polite">Masukkan token Owner untuk memeriksa status.</pre>
<div id="history" aria-live="polite"></div><form id="form"><textarea id="prompt" rows="4" maxlength="8000" required placeholder="Perintah untuk Katarina" aria-label="Perintah"></textarea><button id="send">Kirim</button></form><p id="status" role="status">Siap</p>
<script>
const byId=id=>document.getElementById(id);
byId('check').onclick=async()=>{byId('check').disabled=true;try{
const response=await fetch('/status',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+byId('token').value},body:'{}'});
if(!response.ok)throw Error('Pemeriksaan ditolak ('+response.status+')');const report=await response.json();
byId('runtime').textContent=JSON.stringify(report,null,2);
if(report.dialog_available===false){byId('send').disabled=true;byId('status').textContent='Status tersedia. Dialog menunggu konfigurasi model.'}
}catch(error){byId('runtime').textContent=error.message}finally{byId('check').disabled=false}};
byId('form').onsubmit=async event=>{event.preventDefault();byId('send').disabled=true;byId('status').textContent='Berjalan…';
const input=byId('prompt').value;try{const response=await fetch('/turn',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+byId('token').value},body:JSON.stringify({text:input,session_id:byId('session').value,mode:byId('mode').value})});
if(!response.ok)throw Error('Permintaan ditolak ('+response.status+')');const report=await response.json();
const entry=document.createElement('pre');entry.textContent='Owner: '+input+'\\n\\nKatarina: '+report.answer+'\\n\\nBukti alat: '+JSON.stringify(report.trace,null,2);byId('history').append(entry);byId('status').textContent=report.status;byId('prompt').value='';
}catch(error){byId('status').textContent=error.message}finally{byId('send').disabled=false}};
</script></html>'''



def public_dashboard_snapshot(report):
    """Only technical display fields; never expose the full owner status payload."""
    from katarina.monitoring.agent_projection import project_agent_board
    import re
    board = report['agent_board']
    source = board.get('operational', {})
    passed = board.get('result') == 'SNAPSHOT_PASS'
    def code(value):
        return value if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:+-]{1,96}', value) else None
    rows = []
    for row in source.get('technical_evaluations', [])[:17] if passed else []:
        values = {key: code(row.get(key)) for key in ('symbol', 'market_state', 'method', 'action')}
        if all(values.values()):
            rows.append(values)
    operational = {'technical_evaluations': rows}
    tick = source.get('market_tick_utc')
    if isinstance(tick, str) and re.fullmatch(r'[0-9T:.+Z-]{1,40}', tick):
        operational['market_tick_utc'] = tick
    public = project_agent_board({
        'result': 'PASS_READONLY_SNAPSHOT_ONLY' if passed else 'BLOCKED',
        'received_market_data_symbols': board.get('market_symbols'),
        'cycles': board.get('cycles'), 'successful_cycles': board.get('successful_cycles'),
        'assessed_at_utc': board.get('observed_at_utc') if isinstance(board.get('observed_at_utc'), str)
            and re.fullmatch(r'[0-9T:.+Z-]{1,40}', board['observed_at_utc']) else None,
        'blockers': [] if passed else ['SNAPSHOT_NOT_VERIFIED'],
        'operational': operational,
    }, delivery=board.get('delivery'))
    pid = board.get('current_process_pid')
    public['current_process_pid'] = pid if type(pid) is int and pid > 0 else None
    public['snapshot_process_matches'] = board.get('snapshot_process_matches') is True
    model = board.get('model', {})
    telemetry = model.get('telemetry') or {}
    public['model'] = {
        'configured': model.get('configured') is True, 'quality_verified': False,
        'telemetry': {key: value for key in ('successful_calls', 'failed_calls')
                      if type(value := telemetry.get(key)) is int and value >= 0},
    }
    from katarina.monitoring.activity_trace import clean_activity
    public['activity'] = clean_activity(board.get('activity', {}))
    return {'agent_board': public, 'view_mode': 'PUBLIC_READONLY',
            'dialog_available': False, 'delivery': public['delivery']}


def handler_type(turn, token, *, access_config=None, status_callback=None, public_status=False):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)

        def log_message(self, *args):
            pass

        def reply(self, code, content, mime='application/json'):
            raw = content.encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', mime + '; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Connection', 'close')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if self.path == '/public-status':
                if not public_status or status_callback is None:
                    self.reply(404, '{}')
                    return
                try:
                    content = json.dumps(public_dashboard_snapshot(status_callback()),
                                         ensure_ascii=False, allow_nan=False)
                except Exception:
                    self.reply(503, '{"status":"SNAPSHOT_UNAVAILABLE"}')
                    return
                self.reply(200, content)
                return
            if self.path not in ('/', '/agents', '/owner'):
                self.reply(404, '{}')
                return
            from katarina.adapters.agent_dashboard_page import dashboard_page
            dashboard = self.path == '/agents' or (self.path == '/' and public_status)
            self.reply(200, dashboard_page(public_status=public_status) if dashboard else PAGE, 'text/html')

        def do_POST(self):
            principal = None
            allowed = False
            try:
                if access_config:
                    from katarina.adapters.owner_access import authenticate
                    principal = authenticate(access_config, self.headers.get('Authorization', ''))
                    allowed = principal is not None
                else:
                    allowed = hmac.compare_digest(self.headers.get('Authorization', '').encode('utf-8'),
                                                  ('Bearer ' + token).encode('utf-8'))
            except (ValueError, OSError):
                pass
            if self.path not in ('/turn', '/status') or not allowed:
                # A close with unread POST data can reset TCP on Windows and
                # discard the denial response. Drain only a bounded fixed body.
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not self.headers.get('Transfer-Encoding') and 0 < length <= 40000:
                        self.rfile.read(length)
                except (ValueError, OSError):
                    pass
                self.close_connection = True
                self.reply(403, '{}')
                return
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if self.headers.get('Transfer-Encoding') or not 0 < length <= 40000:
                    raise ValueError()
                value = json.loads(self.rfile.read(length))
                if self.path == '/status':
                    if value != {} or not isinstance(value, dict) or status_callback is None:
                        raise ValueError('status_unavailable_or_invalid_request')
                    self.reply(200, json.dumps(status_callback(), ensure_ascii=False, allow_nan=False))
                    return
                if not isinstance(value, dict) or set(value) != {'text', 'session_id', 'mode'}:
                    raise ValueError()
                if principal:
                    from katarina.adapters.owner_access import scoped_session
                    report = turn(value['text'], session_id=scoped_session(principal, value['session_id']),
                                  mode=value['mode'], principal=principal)
                else:
                    report = turn(value['text'], session_id=value['session_id'], mode=value['mode'])
                self.reply(200, json.dumps(report, ensure_ascii=False, allow_nan=False))
            except Exception:
                self.reply(400, '{"status":"REQUEST_BLOCKED"}')
    return Handler


def create_server(turn, *, bind='127.0.0.1', port=8765, cert=None, key=None, access_config=None,
                  status_callback=None, public_status=False):
    if type(public_status) is not bool:
        raise ValueError('invalid_public_status_option')
    token = os.environ.get('KATARINA_OWNER_TOKEN', '')
    if access_config:
        from katarina.adapters.owner_access import load_access
        load_access(access_config)
    elif len(token) < 32 or not token.isascii() or any(x.isspace() for x in token):
        raise ValueError('owner_token_required')
    loopback = bind == 'localhost'
    try:
        loopback = loopback or ipaddress.ip_address(bind).is_loopback
    except ValueError:
        pass
    if not loopback and not (cert and key):
        raise ValueError('remote_owner_surface_requires_tls')
    context = None
    if cert or key:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(cert, key)
    class BoundedServer(HTTPServer):
        def get_request(self):
            client, address = super().get_request()
            try:
                client.settimeout(10)
                if context is not None:
                    client = context.wrap_socket(client, server_side=True, do_handshake_on_connect=False)
                    client.do_handshake()
                return client, address
            except BaseException:
                client.close()
                raise
    server = BoundedServer((bind, port), handler_type(turn, token, access_config=access_config,
                                                  status_callback=status_callback, public_status=public_status))
    try:
        print('KATARINA_OWNER_UI_READY · LIVE OFF · port ' + str(server.server_port), flush=True)
        server.timeout = 1
        return server
    except BaseException:
        server.server_close()
        raise


def serve(turn, **options):
    server = create_server(turn, **options)
    try:
        server.serve_forever()
    finally:
        server.server_close()
