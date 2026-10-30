"""Portable behavioral acceptance; synthetic model/broker explicitly identified."""
from pathlib import Path
import argparse
import json
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
sys.path.insert(0, str(ROOT))
from scripts.pc.run_pc_acceptance import run as pc_run, write_report
from scripts.pc.run_assistant import assistant_runtime
from katarina.adapters.automatic_connection import BoundLocalBroker, ConnectionConfig
from katarina.adapters.pc_simulation import PCSimulationBroker
from katarina.adapters.dialog_model import JSONDialogModel, ModelConfig
from katarina.engines.risk import RiskGovernor, RiskRequest
from katarina.host import state_directory
from katarina.intelligence.cognition.unified_brain import UnifiedKatarinaBrain
from katarina.intelligence.news.public_context import ContextStore
from katarina.memory.store import MemoryStore


def require(condition):
    if not condition:
        raise RuntimeError('pretrial_check_failed')


class FixtureModel:
    def __init__(self, *replies):
        self.replies = iter(replies)

    def complete(self, messages, *, mode):
        return next(self.replies)


class FixtureBroker(PCSimulationBroker):
    def account_info(self):
        result = super().account_info()
        result.login, result.server = 12345, 'SYNTHETIC_DEMO'
        return result


def run(root, *, model_config=None):
    work = Path(root)/'pretrial'/uuid.uuid4().hex
    work.mkdir(parents=True)
    report = {'schema_version':1, 'status':'BLOCKED', 'input':'SYNTHETIC_MODEL_AND_BROKER',
              'run_directory':str(work), 'checks':[], 'orders_sent':0,
              'live_authorized':False, 'profitability_proven':False,
              'real_broker_verified':False, 'configured_model_connection_verified':False,
              'remaining_real_checks':['configured model quality', 'bound MT5 data and feedback',
                                       'broker execution on demo', 'phone/PC interface on destination host']}
    try:
        pc = pc_run(work/'pc')
        require(pc['status'] == 'PASS_SYNTHETIC_PC_ONLY')
        report['checks'].append('PASS: real research lifecycle on synthetic market data')
        workspace = work/'workspace'; workspace.mkdir()
        (workspace/'facts.txt').write_text('Owner test: 2 + 3 = 5', encoding='utf-8')
        model = FixtureModel({'tool':'read_file','arguments':{'path':'facts.txt'}}, {'answer':'Hasil 5.'})
        with assistant_runtime(work/'brain', model, workspace=workspace) as turn:
            a = turn('Baca facts.txt')
            require(a['status'] != 'BLOCKED' and a['trace'][0]['result']['text'] == 'Owner test: 2 + 3 = 5')
        report['checks'].append('PASS: granted file read with hash provenance; scripted answer is not model intelligence proof')
        with assistant_runtime(work/'brain', FixtureModel({'answer':'Fixture recall'})) as turn:
            b = turn('Apa tugas sebelumnya?')
            require('dialog:'+a['turn_id'] in b['recalled_turn_ids'])
        report['checks'].append('PASS: prior turn and source ID available after restart')
        with assistant_runtime(work/'brain', FixtureModel({'tool':'order_send','arguments':{}})) as turn:
            blocked = turn('Coba order')
            require(blocked['status'] == 'BLOCKED' and blocked['orders_submitted'] == 0)
        report['checks'].append('PASS: model cannot acquire an execution tool')
        sensor = BoundLocalBroker(FixtureBroker(), ConnectionConfig(12345,'SYNTHETIC_DEMO'))
        UnifiedKatarinaBrain.observe_once(work/'roundtrip', broker=sensor, max_symbols=3, fetch_news=False)
        market = json.loads((work/'roundtrip/latest.json').read_text())
        require(len(market['brain_hands_feedback']['receipts']) == 3)
        require(market['orders_submitted'] == 0)
        report['checks'].append('PASS: sensor -> brain -> WAIT feedback -> ACK; no broker order API')
        context = ContextStore(work/'veto-context.sqlite3')
        try:
            with MemoryStore(work/'veto-memory.sqlite3') as memory:
                brain = UnifiedKatarinaBrain(context.db, memory)
                request = RiskRequest(.01,0,0,.1,2,False,False)
                veto = brain.review_delivery('pretrial',request,governor=RiskGovernor())
                require(not veto['risk_allows_review'] and veto['delivery_status'] == 'BLOCKED_LIVE_OFF')
        finally:
            context.db.close()
        report['checks'].append('PASS: independent Risk Governor veto and disabled delivery')
        from datetime import datetime, timezone, timedelta
        from scripts.pc.run_owner_research import research_runtime
        with research_runtime(work/'roundtrip') as review:
            now = datetime.now(timezone.utc)
            review.register('fixture', 'v1', dict(hypothesis='Synthetic test',
                entry_reason='Fixture reason', invalidation='Fixture invalidation',
                exit_plan='Fixture exit', source_sha256='a'*64), now=now)
            trial = review.record_trial('fixture', 'v1', trial_id='fixture-run',
                evidence_kind='SYNTHETIC', dataset_sha256='b'*64,
                evaluation=dict(result='PASS', costs='Fixture costs only',
                    limitations='Not broker evidence', policy_sha256='c'*64), now=now)
            try:
                review.owner_review('fixture-run', trial['review_sha256'],
                    decision='ACCEPT_FOR_CONTROLLED_TEST_REVIEW', reason='Must block', now=now)
            except ValueError:
                pass
            else:
                raise RuntimeError('synthetic_trial_was_accepted')
            weekly = review.weekly_report(as_of=now+timedelta(seconds=1))
            require(weekly['trial_count'] == 1 and not weekly['strategy_activated'])
        report['checks'].append('PASS: same-brain research review, weekly evidence separation and synthetic promotion refusal')
        if model_config:
            with assistant_runtime(work/'real-model', JSONDialogModel(ModelConfig.load(model_config))) as turn:
                real = turn('Balas dengan satu kalimat: ini uji koneksi, live trading OFF.')
                require(real['status'] != 'BLOCKED')
            report['configured_model_connection_verified'] = True
            report['checks'].append('PASS: configured model replied; answer quality remains unverified')
        report['status'] = 'PASS_SYNTHETIC_PRETRIAL_ONLY'
    except Exception as exc:
        report['error_type'] = type(exc).__name__
        report['checks'].append('BLOCKED: inspect test/configuration; no live clearance')
    output = Path(root)/'pretrial-report'
    write_report(output,report)
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--state-dir')
    parser.add_argument('--model-config')
    args=parser.parse_args()
    report=run(state_directory(args.state_dir),model_config=args.model_config)
    print('KATARINA_PRETRIAL',report['status'])
    print('Bukti:',state_directory(args.state_dir)/'pretrial-report/latest-pc-test.html')
    return 0 if report['status'].startswith('PASS_') else 2


if __name__=='__main__':
    raise SystemExit(main())
