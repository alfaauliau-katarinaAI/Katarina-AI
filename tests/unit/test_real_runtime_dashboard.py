"""Real observation evidence, secret filtering and actual model-call counters."""
import json
import unittest
from katarina.monitoring.runtime_details import runtime_details
from katarina.monitoring.agent_projection import project_agent_board
from katarina.adapters.dialog_model import JSONDialogModel, ModelConfig, ModelUnavailable


class RealRuntimeDashboardTests(unittest.TestCase):
    def fixture(self):
        return dict(symbols={'XAUUSD': dict(selected_method='PULLBACK',
            market_state='TREND_UP', action='WAIT', research_only=True,
            live_execution_authorized=False, blocking_reasons=['RISK_BLOCKED'],
            private_account='NEVER_EXPORT')},
            broker_account_monitor=dict(connected=True, algo_trading_off=True,
                positions_read_success=True, orders_read_success=True,
                positions_count=2, pending_orders_count=0, login='NEVER_EXPORT'))

    def test_only_real_technical_records_and_book_counts_are_projected(self):
        detail=runtime_details({'pid':42},self.fixture(),fresh=True)
        self.assertEqual(len(detail['technical_evaluations']),1)
        self.assertTrue(detail['account_book_observed'])
        board=project_agent_board(dict(result='PASS_READONLY_SNAPSHOT_ONLY',
                                      operational=detail))
        lanes={r['id']:r['status'] for r in board['lanes']}
        self.assertEqual(lanes['ANALYST'],'TECHNICAL_EVALUATED')
        self.assertEqual(lanes['STRATEGY'],'RESEARCH_EVALUATED')
        self.assertEqual(lanes['BALANCE'],'BOOK_OBSERVED')
        self.assertFalse(detail['risk_clearance'])
        self.assertFalse(detail['language_model_inferred'])
        self.assertNotIn('NEVER_EXPORT',json.dumps(board))

    def test_stale_records_and_incomplete_cards_never_claim_work(self):
        d=self.fixture()
        for fresh in (False,True):
            if fresh: del d['symbols']['XAUUSD']['selected_method']
            detail=runtime_details({},d,fresh=fresh)
            self.assertEqual(detail['technical_evaluations'],[])
        detail=runtime_details({},self.fixture(),fresh=False)
        self.assertFalse(detail['account_book_observed'])
        self.assertIsNone(detail['positions_count'])

    def test_missing_or_boolean_book_counters_are_not_real_counts(self):
        d=self.fixture();d['broker_account_monitor']['positions_count']=False
        self.assertFalse(runtime_details({},d,fresh=True)['account_book_observed'])

    def test_responses_protocol_counts_only_successful_decoded_json(self):
        config=ModelConfig(endpoint='https://api.openai.com/v1/responses',
            fast_model='gpt-6.1-sol',deep_model='gpt-6-astra',api_format='responses')
        seen=[]
        def exchange(payload):
            seen.append(payload)
            return dict(status='completed',output=[dict(type='reasoning'),
                dict(type='message',content=[dict(type='output_text',text='{"answer":"WAIT"}')])])
        model=JSONDialogModel(config,exchange=exchange)
        self.assertEqual(model.telemetry()['successful_calls'],0)
        self.assertEqual(model.complete([{'role':'user','content':'JSON PRIVATE_PROMPT'}],mode='fast'),
                         {'answer':'WAIT'})
        self.assertFalse(seen[0]['store'])
        self.assertNotIn('max_tokens',seen[0])
        self.assertEqual(seen[0]['model'],'gpt-6.1-sol')
        self.assertEqual(model.telemetry()['successful_calls'],1)
        self.assertNotIn('PRIVATE_PROMPT',json.dumps(model.telemetry()))
        self.assertEqual(model.telemetry()['transport'],'INJECTED_TEST_EXCHANGE')

    def test_incomplete_response_fails_without_claiming_a_model_success(self):
        c=ModelConfig(endpoint='https://api.openai.com/v1/responses',
            fast_model='gpt-6.1-sol',deep_model='gpt-6-astra',api_format='responses')
        model=JSONDialogModel(c,exchange=lambda p:dict(status='incomplete',output=[]))
        with self.assertRaises(ModelUnavailable):model.complete([],mode='deep')
        self.assertEqual(model.telemetry()['successful_calls'],0)
        self.assertEqual(model.telemetry()['failed_calls'],1)

    def test_legacy_chat_protocol_still_works(self):
        c=ModelConfig(endpoint='http://127.0.0.1:1',fast_model='fixture',deep_model='fixture')
        model=JSONDialogModel(c,exchange=lambda p: {'choices':[{'message':{'content':'{"answer":"ok"}'}}]})
        self.assertEqual(model.complete([],mode='fast'),{'answer':'ok'})
