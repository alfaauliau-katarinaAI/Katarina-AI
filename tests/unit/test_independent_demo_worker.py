from pathlib import Path
from types import SimpleNamespace
import tempfile
import threading
import unittest
from katarina.intelligence.independent_demo_worker import run_demo_worker,ExecutorLease

class IndependentDemoTests(unittest.TestCase):
    def config(self,enabled=True):return SimpleNamespace(demo_experiments=enabled,priority=('local',))
    def test_work_advances_while_central_scanner_is_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            blocked=threading.Event();started=threading.Event()
            def scan():started.set();blocked.wait(3)
            central=threading.Thread(target=scan);central.start();started.wait(1)
            calls=[]
            class Runtime:
                def __init__(self,*_):pass
                def step(self,*,execute):calls.append(execute);return {'status':'PROTECTED_VARIANT_NOT_QUALIFIED'}
            try:
                state=run_demo_worker(d,self.config(),runtime_factory=Runtime,wait=lambda _:None,max_cycles=3)
                self.assertEqual(state['cycles'],3);self.assertTrue(central.is_alive());self.assertEqual(calls,[True]*3)
                self.assertFalse(state['live_authorized'])
            finally:blocked.set();central.join()
    def test_audit_and_owner_stop_are_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            class Runtime:
                def __init__(self,*_):pass
                def step(self,*,execute):calls.append(execute);(Path(d)/'continuous.stop').touch();return {'status':'WAIT'}
            state=run_demo_worker(d,self.config(),runtime_factory=Runtime,wait=lambda _:None,audit_only=True)
            self.assertEqual(calls,[False]);self.assertEqual(state['cycles'],1)
    def test_singleton_and_explicit_demo_configuration(self):
        with tempfile.TemporaryDirectory() as d:
            with ExecutorLease(Path(d)/'executor.lock'):
                with self.assertRaises(RuntimeError):
                    with ExecutorLease(Path(d)/'executor.lock'):pass
            with self.assertRaises(ValueError):run_demo_worker(d,self.config(False))
