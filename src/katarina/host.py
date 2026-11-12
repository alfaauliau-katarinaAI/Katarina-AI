"""Portable host policy. Resource budgets never grant trading authority.

Detection is local only: no terminal initialization, network probe or scheduler.
Unknown capacity uses a conservative observation budget. Existing state is never
moved or silently imported from a different machine's directory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import importlib.util
import os
from pathlib import Path
import platform
import shutil
import tempfile


MiB = 1024 * 1024


def state_directory(explicit=None, *, env=None, system=None, home=None):
    env = os.environ if env is None else env
    system = platform.system() if system is None else system
    home = Path.home() if home is None else Path(home)
    chosen = explicit if explicit is not None else env.get('KATARINA_STATE_DIR')
    if chosen is not None:
        if not str(chosen).strip():
            raise ValueError('empty_state_directory')
        return Path(chosen).expanduser().resolve()
    if system == 'Windows':
        base = Path(env.get('LOCALAPPDATA') or home / 'AppData' / 'Local')
    elif system == 'Darwin':
        base = home / 'Library' / 'Application Support'
    else:
        configured = env.get('XDG_STATE_HOME')
        base = Path(configured) if configured and Path(configured).is_absolute() else home / '.local' / 'state'
    return (base / 'Katarina' / 'contextual-observer').resolve()


def _linux_limit(path):
    try:
        value = Path(path).read_text().strip()
        return int(value) if value != 'max' and int(value) > 0 else None
    except (OSError, ValueError):
        return None


def windows_memory():
    """Return (total, available) physical memory from native Windows API.

    None means unknown; never treat detection failure as abundant RAM.
    Does not require psutil or a broker connection.
    """
    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_uint32),
                ("dwMemoryLoad", ctypes.c_uint32),
                ("ullTotalPhys", ctypes.c_uint64),
                ("ullAvailPhys", ctypes.c_uint64),
                ("ullTotalPageFile", ctypes.c_uint64),
                ("ullAvailPageFile", ctypes.c_uint64),
                ("ullTotalVirtual", ctypes.c_uint64),
                ("ullAvailVirtual", ctypes.c_uint64),
                ("ullAvailExtendedVirtual", ctypes.c_uint64),
            ]

        state = MEMORYSTATUSEX()
        state.dwLength = ctypes.sizeof(state)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
            return None
        if state.ullTotalPhys <= 0 or state.ullAvailPhys > state.ullTotalPhys:
            return None
        return int(state.ullTotalPhys), int(state.ullAvailPhys)
    except (AttributeError, OSError, ValueError, TypeError):
        return None


def detect_capacity():
    cpus = os.cpu_count() or 1
    try:
        cpus = min(cpus, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        pass
    memory = None
    try:
        memory = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
    except (AttributeError, OSError, ValueError):
        pass
    if platform.system() == 'Windows':
        native = windows_memory()
        if native is not None:
            memory = native[0]
    if platform.system() == 'Linux':
        limit = _linux_limit('/sys/fs/cgroup/memory.max')
        if limit is not None:
            memory = min(memory, limit) if memory is not None else limit
        try:
            quota, period = Path('/sys/fs/cgroup/cpu.max').read_text().split()
            if quota != 'max' and int(quota) > 0 and int(period) > 0:
                cpus = min(cpus, max(1, int(quota) // int(period)))
        except (OSError, ValueError):
            pass
    return max(1, cpus), memory


@dataclass(frozen=True)
class HostBudget:
    profile: str
    max_symbols: int
    background_workers: int = 0
    live_authorized: bool = False


def observation_budget(cpus, memory_bytes):
    """Scheduling heuristics only; no research/risk thresholds are changed."""
    if memory_bytes is None or memory_bytes < 2 * 1024 * MiB or cpus < 2:
        return HostBudget('constrained', 3)
    if memory_bytes < 8 * 1024 * MiB or cpus < 4:
        return HostBudget('balanced', 8)
    return HostBudget('standard', 17)


def inspect_host(root):
    """Explicit preflight: verify state writes; never disclose host IDs or secrets."""
    cpus, memory = detect_capacity()
    root = Path(root)
    writable = False
    free = None
    try:
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=root) as probe:
            probe.write(b'katarina-preflight')
            probe.flush()
        free = shutil.disk_usage(root).free
        writable = True
    except OSError:
        pass
    try:
        native_adapter = importlib.util.find_spec('MetaTrader5') is not None
    except (ImportError, ValueError):
        native_adapter = False
    blockers = [] if writable else ['STATE_DIRECTORY_NOT_WRITABLE']
    if free is not None and free < 64 * MiB:
        blockers.append('STATE_DISK_SPACE_LOW')
    return {
        'schema_version': 1, 'system': platform.system(),
        'cpu_budget': cpus, 'memory_limit_bytes': memory,
        'state_directory': str(root.resolve()), 'state_writable': writable,
        'disk_free_bytes': free, 'budget': asdict(observation_budget(cpus, memory)),
        'offline_research_available': not blockers,
        'native_mt5_package_available': native_adapter,
        'broker_connection_verified': False, 'network_verified': False,
        'blockers': blockers, 'orders_sent': 0, 'live_authorized': False,
        'risk_governor_independent': True,
    }
