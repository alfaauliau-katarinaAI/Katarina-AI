"""Compatibility CLI: all observation lifecycle is owned by one Katarina brain."""
from pathlib import Path
import argparse
import json
import os
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.host import inspect_host, state_directory
from katarina.adapters.automatic_connection import ConnectionConfig, run_connected


def observe(root, *, max_symbols=17, fetch_news=True, universe=None):
    return UnifiedKatarinaBrain.observe_once(
        Path(root), max_symbols=max_symbols, fetch_news=fetch_news,
        **({'universe': universe} if universe is not None else {}))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--connection-config", help="Allowed account/routes JSON; default KATARINA_CONNECTION_CONFIG")
    parser.add_argument("--state-dir", help="State location; overrides KATARINA_STATE_DIR and OS default")
    parser.add_argument("--offline-research", action="store_true", help="One local evidence cycle; no MT5 or network")
    parser.add_argument("--doctor", action="store_true", help="Local preflight only; no broker connection")
    parser.add_argument("--max-symbols",type=int, help="Explicit observation budget (1..17); default adapts to host")
    parser.add_argument("--universe", help="JSON with exact broker core symbols; no implicit aliasing")
    parser.add_argument("--no-fetch",action="store_true")
    parser.add_argument('--extended-news-research',action='store_true',help='Opt in to additional official research feeds on the same brain')
    parser.add_argument("--require-market-data", action="store_true",
                        help="Exit blocked when no usable bound sensor data was received")
    parser.add_argument('--continuous', action='store_true', help='One persistent foreground brain; LIVE OFF')
    parser.add_argument('--interval-seconds', type=int, default=60)
    parser.add_argument('--max-cycles', type=int, help='Optional bounded observation soak')
    parser.add_argument('--owner-model-config', help='Optional dialog on the same continuous brain')
    parser.add_argument('--owner-status-ui', action='store_true', help='Authenticated status on the same brain; model optional')
    parser.add_argument('--owner-public-status', action='store_true', help='Opt-in token-free technical dashboard only; Owner commands stay authenticated')
    parser.add_argument('--owner-access-config', help='Private revocable Owner/analyst token hash policy')
    parser.add_argument('--owner-workspace', help='Owner-granted read-only folder')
    parser.add_argument('--owner-sources-config', help='Owner-granted HTTPS research sources')
    parser.add_argument('--owner-bind', default='127.0.0.1')
    parser.add_argument('--owner-port', type=int, default=8765)
    parser.add_argument('--owner-cert')
    parser.add_argument('--owner-key')
    parser.add_argument("--all-market-research", action="store_true", help="Rotate full eligible broker catalog and run bounded research; LIVE OFF")
    args=parser.parse_args()
    if args.all_market_research:
        os.environ["KATARINA_ALL_MARKET_RESEARCH"]="1"
    universe = None
    if args.universe:
        from katarina.intelligence.broker.observer_universe import load_universe
        try:
            universe = load_universe(args.universe)
        except ValueError as exc:
            parser.error(str(exc))
    if universe is not None and os.environ.get("KATARINA_ALL_MARKET_RESEARCH") == "1":
        parser.error("universe_and_all_market_research_exclusive")
    if args.owner_public_status and not (args.continuous and args.owner_status_ui):
        parser.error('public status requires --continuous --owner-status-ui')
    if args.extended_news_research:
        if not args.continuous or args.no_fetch:
            parser.error('extended news requires continuous observation with fetching enabled')
        os.environ['KATARINA_EXTENDED_NEWS_RESEARCH']='1'
    if (args.owner_model_config or args.owner_status_ui) and not args.continuous:
        parser.error('Owner surface requires --continuous')
    if args.continuous and (args.doctor or args.offline_research):
        parser.error('--continuous requires a configured sensor')
    if args.require_market_data and (args.doctor or args.offline_research):
        parser.error('--require-market-data requires a sensor observation pass')
    if args.max_symbols is not None and not 1<=args.max_symbols<=17:
        parser.error("max 17 broker markets")
    try:
        root=state_directory(args.state_dir)
    except ValueError as exc:
        parser.error(str(exc))
    host=inspect_host(root)
    if args.doctor:
        print(json.dumps(host,sort_keys=True),flush=True)
        return 0 if not host["blockers"] else 2
    if host["blockers"]:
        parser.error(",".join(host["blockers"]))
    if args.offline_research:
        result=UnifiedKatarinaBrain.research_once(root)
        print(json.dumps(result,sort_keys=True),flush=True)
        return 0
    symbols=args.max_symbols if args.max_symbols is not None else host["budget"]["max_symbols"]
    host["effective_max_symbols"]=symbols
    host["observation_budget_source"]="explicit" if args.max_symbols is not None else "host_policy"
    config_path=args.connection_config or os.environ.get("KATARINA_CONNECTION_CONFIG")
    try:
        config=ConnectionConfig.load(config_path) if config_path else None
    except ValueError as exc:
        parser.error(str(exc))
    if args.continuous:
        from katarina.intelligence.cognition.continuous_observation import run_continuous
        try:
            surface = None
            if args.owner_model_config or args.owner_status_ui:
                from katarina.adapters.dialog_model import JSONDialogModel, ModelConfig
                from katarina.adapters.continuous_owner_surface import owner_surface
                model = JSONDialogModel(ModelConfig.load(args.owner_model_config)) if args.owner_model_config else None
                surface = owner_surface(model, state_dir=root,
                    bind=args.owner_bind, port=args.owner_port, cert=args.owner_cert,
                    key=args.owner_key, access_config=args.owner_access_config,
                    workspace=args.owner_workspace, sources_config=args.owner_sources_config,
                    public_status=args.owner_public_status)
            result = run_continuous(root, config=config, max_symbols=symbols,
                interval_seconds=args.interval_seconds, max_cycles=args.max_cycles,
                surface_factory=surface, fetch_news=not args.no_fetch,
                **({'universe': universe} if universe is not None else {}))
        except (ValueError, RuntimeError, OSError):
            print('CONTINUOUS_BLOCKED_LIVE_OFF', file=sys.stderr, flush=True)
            return 2
        print(json.dumps(result, sort_keys=True), flush=True)
        return 0
    result=run_connected(UnifiedKatarinaBrain,root,config=config,
                         max_symbols=symbols,fetch_news=not args.no_fetch,
                         **({'universe': universe} if universe is not None else {}))
    result["host_environment"]=host
    print("KATARINA_CONTEXTUAL_ONE_PASS",json.dumps(result,sort_keys=True),flush=True)
    return 2 if args.require_market_data and not result['connection']['receiving_market_data'] else 0


if __name__=="__main__":
    raise SystemExit(main())
