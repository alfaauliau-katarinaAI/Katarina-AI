import json
import os
from pathlib import Path
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from katarina.adapters.dialog_model import JSONDialogModel, ModelConfig, ModelUnavailable
from katarina.intelligence.public_language_research import review_one
from katarina.adapters.continuous_owner_surface import owner_surface

NOW = datetime(2026,10,20,0,tzinfo=timezone.utc)
BODY = 'The central bank maintains its interest rate. ' * 60
CANDIDATE = {'summary':'Bank sentral mempertahankan suku bunga.',
    'claims':[{'claim':'Suku bunga dipertahankan.','quote':'The central bank maintains its interest rate.'}],
    'questions':['Apakah keputusan berikutnya berubah?']}

class FakeModel:
    def __init__(self, result=None):
        self.config = SimpleNamespace(data_scope='PUBLIC_RESEARCH_ONLY', fast_model='gemini-2.5-flash-lite')
        self.calls=[]
        self.result=CANDIDATE if result is None else result
    def complete(self,messages,*,mode):
        self.calls.append(messages)
        if isinstance(self.result,Exception):raise self.result
        return self.result

def database():
    db=sqlite3.connect(':memory:')
    db.execute('CREATE TABLE research_news_documents(id TEXT PRIMARY KEY,source TEXT,url TEXT,published TEXT,known_utc TEXT,body TEXT,body_sha256 TEXT,summary TEXT)')
    db.execute('CREATE TABLE private_credentials(secret TEXT)')
    db.execute('INSERT INTO private_credentials VALUES(?)',('PRIVATE_SENTINEL_61932',))
    db.execute('INSERT INTO research_news_documents VALUES(?,?,?,?,?,?,?,?)',
        ('doc1','fed','https://www.federalreserve.gov/newsevents/pressreleases/example.htm',
         (NOW-timedelta(hours=1)).isoformat(),(NOW-timedelta(minutes=1)).isoformat(),
         BODY,sha256(BODY.encode()).hexdigest(),'public summary'))
    db.commit()
    return db

class PublicLanguageResearchTests(unittest.TestCase):
    def test_real_public_excerpt_only_and_unverified_candidate_persisted(self):
        db=database();m=FakeModel()
        r=review_one(db,NOW,model=m)
        self.assertEqual(r['status'],'CANDIDATE_RECORDED')
        self.assertNotIn('PRIVATE_SENTINEL',json.dumps(m.calls))
        self.assertEqual(db.execute('SELECT COUNT(*) FROM public_language_reviews').fetchone()[0],1)
        self.assertEqual(db.execute('SELECT COUNT(*) FROM private_credentials').fetchone()[0],1)
        self.assertFalse(r['semantic_claims_verified'])
        self.assertFalse(r['model_training_verified'])
        self.assertFalse(r['live_execution_authorized'])
        self.assertEqual(m.calls[0][0]['role'],'system')
        self.assertIn(BODY,json.loads(m.calls[0][1]['content'])['public_article_excerpt'])

    def test_interval_and_deduplication_never_make_extra_calls(self):
        db=database();m=FakeModel()
        review_one(db,NOW,model=m)
        self.assertEqual(review_one(db,NOW+timedelta(seconds=899),model=m)['status'],'WAITING_PUBLIC_MODEL_INTERVAL')
        self.assertEqual(review_one(db,NOW+timedelta(seconds=901),model=m)['status'],'NO_ELIGIBLE_PUBLIC_DOCUMENT')
        self.assertEqual(len(m.calls),1)

    def test_invalid_quote_cannot_be_saved_and_retry_is_bounded(self):
        db=database();m=FakeModel({'summary':'x','claims':[{'claim':'x','quote':'INVENTED QUOTE NOT IN THE SOURCE'}],'questions':[]})
        self.assertEqual(review_one(db,NOW,model=m)['status'],'MODEL_REVIEW_UNAVAILABLE')
        self.assertEqual(db.execute('SELECT COUNT(*) FROM public_language_reviews').fetchone()[0],0)
        self.assertEqual(review_one(db,NOW+timedelta(seconds=1),model=m)['status'],'WAITING_PUBLIC_MODEL_INTERVAL')
        self.assertEqual(len(m.calls),1)

    def test_unapproved_host_bad_digest_and_future_document_are_not_sent(self):
        for field,value in [('url','https://private.example/secret'),('body_sha256','forged'),
                            ('known_utc',(NOW+timedelta(seconds=1)).isoformat())]:
            with self.subTest(field=field):
                db=database();db.execute('UPDATE research_news_documents SET '+field+'=?',(value,));db.commit();m=FakeModel()
                self.assertEqual(review_one(db,NOW,model=m)['status'],'NO_ELIGIBLE_PUBLIC_DOCUMENT')
                self.assertEqual(m.calls,[])

    def test_daily_attempt_limit_and_failures_do_not_export_error_text(self):
        db=database();m=FakeModel(RuntimeError('PRIVATE_PROVIDER_SENTINEL'))
        r=review_one(db,NOW,model=m)
        self.assertNotIn('PRIVATE_PROVIDER_SENTINEL',json.dumps(r))
        for i in range(23):
            db.execute('INSERT INTO public_language_attempts VALUES(?,?,?,?,?,?)',
                (str(i),(NOW+timedelta(seconds=i)).isoformat(),'doc','hash','model','FAILED'))
        db.commit()
        self.assertEqual(review_one(db,NOW+timedelta(hours=1),model=m)['status'],'PUBLIC_MODEL_DAILY_BUDGET_REACHED')
        self.assertEqual(len(m.calls),1)

    def test_owner_dialog_cannot_send_private_recall_to_public_model(self):
        m=FakeModel();brain=SimpleNamespace()
        with patch('katarina.adapters.continuous_owner_surface.create_server') as make:
            with owner_surface(m)(brain):
                turn=make.call_args.args[0]
                r=turn('PRIVATE OWNER TEXT',session_id='owner')
                self.assertEqual(r['status'],'BLOCKED_EXTERNAL_MODEL_PUBLIC_ONLY')
                self.assertEqual(m.calls,[])
                self.assertIs(brain.public_research_model,m)

    def test_private_token_file_is_used_only_in_authenticated_transport(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'key';secret='credential-only-for-test';path.write_text(secret)
            cfg=ModelConfig('https://generativelanguage.googleapis.com/v1beta/openai/chat/completions',
                'gemini-2.5-flash-lite','gemini-2.5-flash-lite',data_scope='PUBLIC_RESEARCH_ONLY',
                token_env='GEMINI_TEST_NONEXISTENT',token_file=str(path))
            m=JSONDialogModel(cfg)
            with patch.dict(os.environ,{'GEMINI_TEST_NONEXISTENT':''}), patch('katarina.adapters.dialog_model.build_opener') as opener:
                response=opener.return_value.open.return_value.__enter__.return_value
                response.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps(CANDIDATE)}}]}).encode()
                self.assertEqual(m.complete([{'role':'user','content':'public test'}],mode='fast'),CANDIDATE)
                req=opener.return_value.open.call_args.args[0]
                self.assertEqual(req.get_header('Authorization'),'Bearer '+secret)
                self.assertNotIn(secret,json.dumps(m.telemetry()))
            path.write_text('x'*513)
            with self.assertRaisesRegex(ModelUnavailable,'MODEL_CREDENTIAL_UNAVAILABLE'):
                m.complete([],mode='fast')
