"""Adaptive, read-only research concurrency budget for heterogeneous hosts.

The budget never changes observation cadence, strategy thresholds, risk limits,
account permissions or trading authority. Unknown sensors fail closed for research.
No broker, model, scheduler, or network access.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from pathlib import Path
import platform
import shutil
import threading
import time

from katarina.host import MiB, detect_capacity, windows_memory
from katarina.intelligence.lab.research_capacity import MIN_FREE, WRITE_RESERVE

MAX_RESEARCH_JOBS = 9
PER_JOB_RESERVE = 192 * MiB
BASE_MEMORY_RESERVE = 512 * MiB
REFRESH_SECONDS = 5


@dataclass(frozen=True)
class ResourceSnapshot:
    cpus: int
    memory_total: int | None
    memory_available: int | None
    disk_free: int | None
    cpu_load_fraction: float | None = None


@dataclass(frozen=True)
class ResearchAllowance:
    slots: int
    status: str
    live_authorized: bool = False


def decide_allowance(snapshot: ResourceSnapshot) -> ResearchAllowance:
    """Recompute bounded simultaneous jobs; never assume missing sensors mean free."""
    if (type(snapshot.cpus) is not int or snapshot.cpus < 1
            or type(snapshot.memory_total) is not int or snapshot.memory_total <= 0
            or type(snapshot.memory_available) is not int or snapshot.memory_available < 0
            or type(snapshot.disk_free) is not int or snapshot.disk_free < 0):
        return ResearchAllowance(0, "PAUSED_RESOURCE_UNVERIFIED")
    if snapshot.disk_free < MIN_FREE + WRITE_RESERVE:
        return ResearchAllowance(0, "PAUSED_LOW_DISK")
    total = snapshot.memory_total
    available = min(snapshot.memory_available, total)
    # Leave room for the OS, MT5 and the independent canonical observer.
    reserve = max(BASE_MEMORY_RESERVE, total // 4)
    if available <= reserve:
        return ResearchAllowance(0, "PAUSED_MEMORY_PRESSURE")
    by_memory = (available - reserve) // PER_JOB_RESERVE
    by_cpu = max(1, snapshot.cpus - 1)
    slots = min(MAX_RESEARCH_JOBS, by_memory, by_cpu)
    load = snapshot.cpu_load_fraction
    if load is not None:
        if not isinstance(load, (int, float)) or not 0 <= load <= 1:
            return ResearchAllowance(0, "PAUSED_RESOURCE_UNVERIFIED")
        if load >= 0.95:
            return ResearchAllowance(0, "PAUSED_CPU_PRESSURE")
        if load >= 0.75:
            slots = min(slots, 1)
    else:
        # Without a trustworthy CPU-usage reading, do not launch a large pool.
        slots = min(slots, 2)
    return ResearchAllowance(max(0, slots),
                             "READY" if slots > 0 else "PAUSED_MEMORY_PRESSURE")


def _linux_available() -> int | None:
    try:
        values = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            if ":" in line:
                name, value = line.split(":", 1)
                parts = value.split()
                if name == "MemAvailable" and len(parts) == 2 and parts[1] == "kB":
                    values[name] = int(parts[0]) * 1024
        available = values.get("MemAvailable")
        # Respect effective cgroup v2 memory remaining, where supplied.
        base = Path("/sys/fs/cgroup")
        limit = (base / "memory.max").read_text().strip()
        current = int((base / "memory.current").read_text().strip())
        if limit != "max":
            constrained = max(0, int(limit) - current)
            available = min(available, constrained) if available is not None else constrained
        return available
    except (OSError, ValueError):
        return available if "available" in locals() else None


def _available_memory() -> int | None:
    system = platform.system()
    if system == "Windows":
        result = windows_memory()
        return result[1] if result is not None else None
    if system == "Linux":
        return _linux_available()
    try:
        return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        return None


_WINDOWS_CPU_LAST = None
_WINDOWS_CPU_LOCK = threading.Lock()


def _windows_cpu_load() -> float | None:
    """CPU utilization from successive Windows system-time samples, if available."""
    global _WINDOWS_CPU_LAST
    try:
        import ctypes

        class FILETIME(ctypes.Structure):
            _fields_ = [("low", ctypes.c_uint32), ("high", ctypes.c_uint32)]

        idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(
                ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            return None
        def number(value):
            return (value.high << 32) | value.low
        now = (number(idle), number(kernel), number(user))
        with _WINDOWS_CPU_LOCK:
            old = _WINDOWS_CPU_LAST
            _WINDOWS_CPU_LAST = now
        if old is None:
            return None
        busy = (now[1] - old[1]) + (now[2] - old[2])
        idle_delta = now[0] - old[0]
        if busy <= 0 or idle_delta < 0 or idle_delta > busy:
            return None
        return max(0.0, min(1.0, (busy - idle_delta) / busy))
    except (AttributeError, OSError, ValueError, TypeError):
        return None


def _cpu_load(cpus: int) -> float | None:
    if platform.system() == "Windows":
        return _windows_cpu_load()
    try:
        # Conservative 1-minute average; not an instantaneous CPU utilization.
        return max(0.0, min(1.0, os.getloadavg()[0] / cpus))
    except (AttributeError, OSError, ValueError):
        return None


def sample_resources(root: Path) -> ResourceSnapshot:
    cpus, memory_total = detect_capacity()
    try:
        disk_free = shutil.disk_usage(root).free
    except OSError:
        disk_free = None
    return ResourceSnapshot(cpus, memory_total, _available_memory(),
                            disk_free, _cpu_load(cpus))


class AdaptiveResearchLimiter:
    """Nonblocking shared budget; active jobs finish, no catch-up burst follows.

    Each worker/reviewer asks for a permit before its next piece of work.
    A reduced budget stops *new* experiments, never interrupts a transaction.
    The monitor is rechecked on a short interval and after the next retry.
    """
    def __init__(self, root, *, measure=sample_resources, clock=time.monotonic,
                 refresh_seconds=REFRESH_SECONDS):
        if not 0 < refresh_seconds <= 60:
            raise ValueError("invalid_refresh_seconds")
        self.root = Path(root)
        self.measure = measure
        self.clock = clock
        self.refresh_seconds = refresh_seconds
        self._lock = threading.Lock()
        self._next = 0.0
        self._active = 0
        self._allowance = ResearchAllowance(0, "PAUSED_RESOURCE_UNVERIFIED")

    def try_acquire(self) -> bool:
        with self._lock:
            now = self.clock()
            if now >= self._next:
                try:
                    self._allowance = decide_allowance(self.measure(self.root))
                except (OSError, RuntimeError, ValueError):
                    self._allowance = ResearchAllowance(0, "PAUSED_RESOURCE_UNVERIFIED")
                self._next = now + self.refresh_seconds
            if self._active >= self._allowance.slots:
                return False
            self._active += 1
            return True

    def release(self) -> None:
        with self._lock:
            if self._active <= 0:
                raise RuntimeError("research_permit_not_held")
            self._active -= 1

    def telemetry(self) -> dict:
        with self._lock:
            return dict(asdict(self._allowance), active_jobs=self._active)
