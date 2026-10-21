"""Stdlib-only private environment recovery. Never edits source or research state."""
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import uuid
import venv


class RecoveryBlocked(RuntimeError):
    pass


def python_at(folder):
    return Path(folder)/('Scripts/python.exe' if os.name=='nt' else 'bin/python')


def clean_environment(root):
    env=dict(os.environ)
    env.pop('PYTHONHOME',None)
    env['PYTHONUTF8']='1'
    env['PYTHONPATH']=str(root/'src')+os.pathsep+str(root)
    return env


@contextmanager
def recovery_lock(base):
    stream=(base/'recovery.lock').open('a+b')
    try:
        try:
            if os.name=='nt':
                import msvcrt
                stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
                msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            raise RecoveryBlocked('RECOVERY_ALREADY_RUNNING') from None
        yield
    finally:
        stream.close()


class EnvironmentManager:
    def __init__(self,root,*,base=None,runner=None,builder=None,clock=None):
        self.root=Path(root).resolve()
        self.base=Path(base).resolve() if base is not None else self._choose_base()
        self.runner=runner or subprocess.run
        self.builder=builder or (lambda folder:venv.EnvBuilder(with_pip=True).create(folder))
        self.clock=clock or time.time
        self.pointer=self.base/'active.json'

    def _choose_base(self):
        explicit=os.environ.get('KATARINA_ENV_HOME')
        if explicit:
            candidates=[Path(explicit).expanduser()]
        else:
            key=sha256(str(self.root).encode()).hexdigest()[:16]
            candidates=[self.root/'.katarina-envs',Path.home()/'.katarina'/'environments'/key]
        for base in candidates:
            try:
                base.mkdir(parents=True,exist_ok=True)
                with tempfile.TemporaryFile(dir=base): pass
                return base.resolve()
            except OSError:
                continue
        raise RecoveryBlocked('NO_WRITABLE_PRIVATE_ENVIRONMENT_LOCATION')

    def _read(self):
        if not self.pointer.exists():
            return None
        try:
            data=json.loads(self.pointer.read_text())
            if (set(data)!={'version','active','previous','mt5_required'} or data['version']!=1
                    or type(data['mt5_required']) is not bool):
                raise ValueError()
            for name in (data['active'],data['previous']):
                if name is not None and (not isinstance(name,str) or len(name)!=36
                        or not name.startswith('env-') or any(c not in '0123456789abcdef' for c in name[4:])):
                    raise ValueError()
            if data['active'] is None:
                raise ValueError()
            return data
        except (ValueError,TypeError,OSError,KeyError):
            raise RecoveryBlocked('ENVIRONMENT_POINTER_INVALID') from None

    def _event(self,event,reason=None):
        with (self.base/'recovery-audit.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps({'version':1,'at':self.clock(),'event':event,'reason':reason,
                'live_authorized':False,'source_modified':False,'existing_memory_modified':False})+'\n')

    def _activate(self,active,previous,mt5):
        data={'version':1,'active':active,'previous':previous,'mt5_required':mt5}
        path=self.base/('pointer-'+uuid.uuid4().hex+'.tmp')
        path.write_text(json.dumps(data,sort_keys=True),encoding='utf-8')
        path.replace(self.pointer)

    def _run(self,command,*,timeout):
        return self.runner([str(x) for x in command],cwd=self.root,
            env=clean_environment(self.root),capture_output=True,text=True,
            encoding="utf-8",errors="replace",timeout=timeout)

    def healthy(self,folder,*,mt5=False):
        python=python_at(folder)
        if not python.is_file():
            return False
        versions=json.loads((self.root/'config/runtime_dependencies_v1.json').read_text())['packages']
        code=('import sys,importlib.metadata as m; import numpy; '
              'assert sys.version_info[:2]==(3,12); '
              'assert m.version("numpy")==sys.argv[1]; '
              + ('import MetaTrader5; assert m.version("MetaTrader5")==sys.argv[2]' if mt5 else ''))
        try:
            return self._run([python,'-c',code,versions['numpy'],versions['MetaTrader5']],timeout=30).returncode==0
        except (OSError,subprocess.TimeoutExpired):
            return False

    def _accept(self,folder):
        with tempfile.TemporaryDirectory(prefix='katarina-candidate-test-') as state:
            result=self._run([python_at(folder),self.root/'scripts/pc/run_pc_acceptance.py',
                              '--mode','demo','--state-dir',state],timeout=90)
            if result.returncode!=0:
                return False
            try:
                report=json.loads((Path(state)/'latest-pc-test.json').read_text())
                return (report['status']=='PASS_SYNTHETIC_PC_ONLY' and report['orders_sent']==0
                        and report['live_authorized'] is False and report['broker_verified'] is False)
            except (OSError,ValueError,KeyError,TypeError):
                return False

    def status(self):
        data=self._read()
        folder=self.base/data['active'] if data else self.root/'.venv-pc'
        return {'active_environment':str(folder),'healthy':self.healthy(folder,mt5=data['mt5_required'] if data else False),
                'registered':data is not None,'live_authorized':False,
                'audit_file':str(self.base/'recovery-audit.jsonl')}

    def ensure(self,*,mt5=False,explicit=False,force=False,auto=True):
        self.base.mkdir(parents=True,exist_ok=True)
        with recovery_lock(self.base):
            data=self._read()
            required=mt5 or bool(data and data['mt5_required'])
            if required and (platform.system()!='Windows' or sys.maxsize<=2**32):
                raise RecoveryBlocked('NATIVE_MT5_REQUIRES_WINDOWS_64BIT')
            current=self.base/data['active'] if data else self.root/'.venv-pc'
            if not force and self.healthy(current,mt5=required):
                return python_at(current)
            if not auto and not explicit:
                raise RecoveryBlocked('ENVIRONMENT_REPAIR_REQUIRED')
            if not force and data and data['previous']:
                previous=self.base/data['previous']
                if self.healthy(previous,mt5=required) and self._accept(previous):
                    self._event('ROLLBACK_VALIDATED')
                    self._activate(data['previous'],data['active'],required)
                    return python_at(previous)
            failure=self.base/'last-failure.json'
            if not explicit and failure.exists():
                try:
                    age=self.clock()-json.loads(failure.read_text())['at']
                    if age<300:
                        raise RecoveryBlocked('RECOVERY_COOLDOWN_USE_EXPLICIT_REPAIR')
                except (ValueError,KeyError,TypeError,OSError):
                    raise RecoveryBlocked('RECOVERY_FAILURE_RECORD_INVALID') from None
            name='env-'+uuid.uuid4().hex
            candidate=self.base/name
            self._event('CANDIDATE_STARTED')
            print('Menyiapkan kandidat environment; versi dependensi mengikuti repository ...',flush=True)
            phase='CREATE_ENVIRONMENT_FAILED'
            try:
                self.builder(candidate)
                phase='DEPENDENCY_INSTALL_FAILED'
                print('Memasang dependensi pada kandidat; environment aktif belum diganti ...',flush=True)
                command=[python_at(candidate),'-m','pip','install','--disable-pip-version-check',
                         '-r',self.root/'requirements-pc.txt']
                if self._run(command,timeout=600).returncode!=0:
                    raise RecoveryBlocked(phase)
                if required:
                    version=json.loads((self.root/'config/runtime_dependencies_v1.json').read_text())['packages']['MetaTrader5']
                    if self._run([python_at(candidate),'-m','pip','install','--disable-pip-version-check',
                                  'MetaTrader5=='+version],timeout=600).returncode!=0:
                        raise RecoveryBlocked(phase)
                phase='CANDIDATE_ACCEPTANCE_FAILED'
                print('Menguji import, pipeline sintetis dan checkpoint kandidat ...',flush=True)
                if not self.healthy(candidate,mt5=required) or not self._accept(candidate):
                    raise RecoveryBlocked(phase)
                # Virtualenvs are never renamed: their absolute entry points remain valid.
                self._event('CANDIDATE_VALIDATED')
                self._activate(name,data['active'] if data else None,required)
                self._event('ACTIVE_ENVIRONMENT_SELECTED')
                if failure.exists(): failure.unlink()
                return python_at(candidate)
            except Exception:
                # Retain failed candidate/old envs for inspection. Never delete research state.
                failure.write_text(json.dumps({'at':self.clock(),'reason':phase}))
                self._event('RECOVERY_BLOCKED',phase)
                raise RecoveryBlocked(phase) from None
