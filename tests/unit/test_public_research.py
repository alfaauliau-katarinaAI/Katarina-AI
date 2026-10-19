"""Actual research provenance becomes stable nodes; broker data is entry-only."""
from datetime import datetime,timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as S
import unittest
from katarina.monitoring.public_research import graph_from_report,public_entries,read_public_research
from katarina.intelligence.broker_account_monitor import inspect_broker_account

class PublicResearchTests(unittest.TestCase):
    def report(self):
        now=datetime.now(timezone.utc).isoformat()
        return {'observed_at_utc':now,'research_news':{'total_documents':1,'document_contexts':[
            {'id':'a'*64,'source':'fed','known_utc':now,'topics':['RATES_INFLATION'],
             'paragraph_ids':['b'*64,'c'*64],'extractive_summary':'PRIVATE_BODY'}]},
            'broker_account_monitor':{'connected':True,'algo_trading_off':True,
                'positions_read_success':True,'positions_count':1,
                'entry_positions':[{'symbol':'EURUSD','side':'BUY','entry_price':1.2,
                  'opened_utc':now,'volume':99,'profit':'PRIVATE_ACCOUNT','ticket':'PRIVATE_ID'}]}}

    def test_stable_topology_grows_only_from_source_records(self):
        report=self.report();a=graph_from_report(report);b=graph_from_report(report)
        self.assertEqual(a,b)
        self.assertEqual(len(a['nodes']),5)
        self.assertTrue(all(e['a'] in {n['id'] for n in a['nodes']} and e['b'] in {n['id'] for n in a['nodes']} for e in a['edges']))
        report['research_news']['document_contexts'][0]['paragraph_ids'].append('d'*64)
        c=graph_from_report(report)
        self.assertEqual(len(c['nodes']),6)
        self.assertTrue({n['id'] for n in a['nodes']} <= {n['id'] for n in c['nodes']})
        self.assertNotIn('PRIVATE_BODY',json.dumps(c))
        self.assertFalse(c['neural_activation_measured'])

    def test_entries_exclude_every_other_broker_field(self):
        result=public_entries(self.report())
        self.assertEqual(set(result['positions'][0]),{'symbol','side','entry_price','opened_utc'})
        self.assertNotIn('PRIVATE',json.dumps(result))
        report=self.report();report['broker_account_monitor']['positions_read_success']=False
        self.assertEqual(public_entries(report)['status'],'NOT_ATTESTED')

    def test_read_snapshot_matching_and_bounds(self):
        report=self.report()
        with TemporaryDirectory() as root:
            Path(root,'latest.json').write_text(json.dumps(report),encoding='utf-8')
            graph,entries=read_public_research(root,report['observed_at_utc'])
            self.assertEqual(len(graph['nodes']),5)
            self.assertEqual(entries['status'],'OBSERVED')
            graph,entries=read_public_research(root,'mismatch')
            self.assertEqual(graph['nodes'],[])
            self.assertEqual(entries['status'],'NOT_ATTESTED')
        source=report['research_news']['document_contexts'][0]
        report['research_news']['document_contexts']=[dict(source,id=format(i,'064x'),paragraph_ids=[format(i*8+j,'064x') for j in range(8)]) for i in range(48)]
        graph=graph_from_report(report)
        self.assertLessEqual(len(graph['nodes']),384);self.assertLessEqual(len(graph['edges']),512)
        self.assertTrue(graph['truncated'])

    def test_account_adapter_never_submits_an_order(self):
        class Broker:
            ACCOUNT_TRADE_MODE_DEMO=0
            terminal_info=lambda self:S(connected=True,trade_allowed=False)
            account_info=lambda self:S(trade_mode=0,balance=10,equity=10,margin=0,margin_free=10)
            positions_get=lambda self:[S(symbol='EURUSD',type=0,price_open=1.2,time=int(datetime.now(timezone.utc).timestamp())-60,sl=1.1,ticket='PRIVATE_ID',profit='PRIVATE_ACCOUNT')]
            orders_get=lambda self:[]
        result=inspect_broker_account(Broker(),observed_at_utc=datetime.now(timezone.utc))
        self.assertEqual(result['entry_positions'][0]['entry_price'],1.2)
        self.assertEqual(result['orders_submitted'],0)
        self.assertNotIn('PRIVATE',json.dumps(result))
