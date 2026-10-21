"""Foreground Owner console; same lifecycle also serves the optional browser UI."""
from contextlib import contextmanager
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from katarina.adapters.dialog_model import JSONDialogModel, ModelConfig
from katarina.host import state_directory
from katarina.intelligence.cognition.observer import lock_worker
from katarina.intelligence.news.public_context import ContextStore
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.memory.store import MemoryStore


@contextmanager
def assistant_runtime(root, model, *, workspace=None, connection_config=None, sources_config=None):
    lock = lock_worker(root)
    context = memory = None
    try:
        context = ContextStore(root / 'context.sqlite3')
        memory = MemoryStore(root / 'cognitive-memory.sqlite3')
        brain = UnifiedKatarinaBrain(context.db, memory)
        brain.context_store = context
        tools = ['status', 'research']
        if workspace:
            tools.append('read_file')
        sources = None
        if sources_config:
            from katarina.adapters.research_sources import load_sources
            sources = load_sources(sources_config)
            tools.append('read_source')
        observe = None
        if connection_config:
            from katarina.adapters.automatic_connection import ConnectionConfig, run_connected
            config = ConnectionConfig.load(connection_config)
            class SameBrainRoutes:
                @staticmethod
                def observe_once(root, *, broker, max_symbols, fetch_news):
                    return brain.observe_connected_market(root, broker,
                        max_symbols=max_symbols, fetch_news=fetch_news)

                @staticmethod
                def research_once(root):
                    from datetime import datetime, timezone
                    brain.prepare_research()
                    result = brain.run_unified_cognitive_cycle(as_of_utc=datetime.now(timezone.utc))
                    result['research_policy'] = result['research_policy'].to_dict()
                    return result
            observe = lambda: run_connected(SameBrainRoutes, root,
                                            config=config, max_symbols=3, fetch_news=False)
            tools.append('observe')
        def turn(text, *, session_id='owner', mode='auto'):
            report = brain.converse(text, model=model, session_id=session_id,
                                    allowed_tools=tools, workspace=workspace,
                                    observe=observe, sources=sources, mode=mode)
            brain.control.checkpoint()
            return report
        yield turn
    finally:
        try:
            if memory is not None:
                memory.close()
        finally:
            try:
                if context is not None:
                    context.db.close()
            finally:
                lock.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Katarina dialog — LIVE OFF')
    parser.add_argument('--model-config', required=True)
    parser.add_argument('--state-dir')
    parser.add_argument('--session', default='owner')
    parser.add_argument('--workspace', help='Folder whose UTF-8 files the model may read')
    parser.add_argument('--connection-config')
    parser.add_argument('--sources-config')
    parser.add_argument('--mode', choices=['auto', 'fast', 'deep'], default='auto')
    parser.add_argument('--prompt', help='One turn, then exit; otherwise interactive console')
    parser.add_argument('--serve', action='store_true', help='Foreground browser interface')
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--cert')
    parser.add_argument('--key')
    args = parser.parse_args(argv)
    model = JSONDialogModel(ModelConfig.load(args.model_config))
    root = state_directory(args.state_dir)
    with assistant_runtime(root, model, workspace=args.workspace, connection_config=args.connection_config, sources_config=args.sources_config) as turn:
        if args.serve:
            from katarina.adapters.owner_dialog_server import serve
            serve(turn, bind=args.bind, port=args.port, cert=args.cert, key=args.key)
            return 0
        print('KATARINA_DIALOG_READY · LIVE OFF · /keluar untuk berhenti', flush=True)
        while True:
            try:
                text = args.prompt if args.prompt is not None else input('Owner> ')
            except EOFError:
                break
            if text.strip() in ('/keluar', '/exit'):
                break
            if not text.strip():
                if args.prompt is not None:
                    return 2
                continue
            report = turn(text, session_id=args.session, mode=args.mode)
            print('Katarina> ' + report['answer'], flush=True)
            print('Status:', report['status'], '· mode:', report['mode'], flush=True)
            if args.prompt is not None:
                return 0 if report['status'] != 'BLOCKED' else 2
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, RuntimeError):
        print('DIALOG_BLOCKED: periksa konfigurasi dan kesiapan lingkungan. LIVE OFF.', file=sys.stderr)
        raise SystemExit(2)
