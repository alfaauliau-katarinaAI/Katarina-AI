import io
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from katarina.adapters.dialog_model import JSONDialogModel,ModelConfig,ModelUnavailable

class ProviderConcurrencyTests(unittest.TestCase):
    def test_models_share_one_provider_channel(self):
        config=ModelConfig('http://localhost/chat','fixture','fixture')
        models=[JSONDialogModel(config),JSONDialogModel(config)]
        counts={'active':0,'maximum':0};guard=threading.Lock();start=threading.Barrier(3);errors=[]
        def provider(self,payload):
            with guard:
                counts['active']+=1;counts['maximum']=max(counts['maximum'],counts['active'])
            threading.Event().wait(.03)
            with guard:counts['active']-=1
            return {'choices':[{'message':{'content':'{"hypothesis":"fixture"}'}}]}
        def run(model):
            start.wait()
            try:model.complete([{'role':'user','content':'fixture'}],mode='fast')
            except Exception as exc:errors.append(type(exc).__name__)
        with patch.object(JSONDialogModel,'_http_serial',provider):
            threads=[threading.Thread(target=run,args=(m,)) for m in models]
            for t in threads:t.start()
            start.wait()
            for t in threads:t.join(timeout=2)
        self.assertEqual(errors,[])
        self.assertEqual(counts['maximum'],1)
        self.assertTrue(all(m.telemetry()['successful_calls']==1 for m in models))

    def test_error_telemetry_contains_status_without_provider_body(self):
        m=JSONDialogModel(ModelConfig('http://localhost/chat','fixture','fixture'))
        error=HTTPError('http://localhost/chat',429,'limited',{},io.BytesIO(b'PRIVATE_PROVIDER_BODY'))
        with patch('katarina.adapters.dialog_model.build_opener') as build:
            build.return_value.open.side_effect=error
            with self.assertRaisesRegex(ModelUnavailable,'MODEL_HTTP_429'):
                m.complete([{'role':'user','content':'fixture'}],mode='fast')
        self.assertEqual(m.telemetry()['last_error'],'MODEL_HTTP_429')
        self.assertNotIn('PRIVATE_PROVIDER_BODY',str(m.telemetry()))
