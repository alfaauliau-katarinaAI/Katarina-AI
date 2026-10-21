"""Deprecated alias kept for one release; use ``katarina.body.machine_learning`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import machine_learning as _module

warnings.warn("katarina.body.stage27 moved to katarina.body.machine_learning", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
