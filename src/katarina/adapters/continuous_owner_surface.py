"""Foreground HTTP requests run serially inside the existing observation brain."""
from contextlib import contextmanager
import time
import os

from katarina.adapters.owner_dialog_server import create_server


def owner_surface(model=None, *, workspace=None, sources_config=None, state_dir=None, **server_options):
    sources = None
    if sources_config:
        from katarina.adapters.research_sources import load_sources
        sources = load_sources(sources_config)
    @contextmanager
    def attach(brain):
        brain.dashboard_model = model
        public_only = getattr(getattr(model, 'config', None), 'data_scope', None) == 'PUBLIC_RESEARCH_ONLY'
        brain.public_research_model = model if public_only else None
        def turn(text, *, session_id, mode='auto', principal=None):
            if public_only:
                return dict(status='BLOCKED_EXTERNAL_MODEL_PUBLIC_ONLY',
                            answer='Gemini hanya untuk riset artikel publik; dialog dan memori privat tidak dikirim.',
                            trace=[], orders_submitted=0, live_execution_authorized=False)
            if model is None:
                return dict(status='BLOCKED_MODEL_NOT_CONFIGURED',
                            answer='Model dialog belum dikonfigurasi. Gunakan pemeriksaan status.',
                            trace=[], orders_submitted=0, live_execution_authorized=False)
            # HTTP clients never supply tool grants or Owner research approval.
            role = principal['role'] if principal else 'owner'
            allowed = ['status', 'research'] if role == 'owner' else ['status']
            if role == 'owner' and workspace:
                allowed.append('read_file')
            if role == 'owner' and sources:
                allowed.append('read_source')
            result = brain.converse(text, model=model, session_id=session_id,
                                    mode=mode, allowed_tools=allowed, workspace=workspace, sources=sources)
            brain.control.checkpoint()
            return result
        def status():
            from katarina.intelligence.runtime_evidence import read_runtime
            evidence = read_runtime(state_dir) if state_dir is not None else dict(
                result='BLOCKED', blockers=['OBSERVER_STATE_NOT_CONFIGURED'], live_clearance=False)
            from katarina.monitoring.agent_projection import project_agent_board
            delivery = brain.control.snapshot()['delivery']
            board = project_agent_board(evidence, delivery=delivery)
            board['current_process_pid'] = os.getpid()
            operational = evidence.get('operational', {})
            board['snapshot_process_matches'] = operational.get('snapshot_pid') == os.getpid()
            board['model'] = {'configured': model is not None, 'quality_verified': False,
                              'telemetry': model.telemetry() if callable(getattr(model, 'telemetry', None)) else None}
            from katarina.monitoring.activity_trace import read_activity
            board['activity'] = read_activity(state_dir) if state_dir is not None else {}
            return {**evidence, 'dialog_available': model is not None and not public_only,
                    'surface_mode': 'PUBLIC_RESEARCH_AND_STATUS' if public_only else 'DIALOG_AND_STATUS' if model is not None else 'STATUS_ONLY',
                    'delivery': delivery,
                    'agent_board': board}
        server = create_server(turn, status_callback=status, **server_options)
        try:
            def idle(_):
                started = time.monotonic()
                server.handle_request()
                time.sleep(max(0, 1 - (time.monotonic() - started)))
            yield idle
        finally:
            server.server_close()
    return attach
