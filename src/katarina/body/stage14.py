"""Deprecated alias kept for one release; use ``katarina.body.xauusd_specialist`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import xauusd_specialist as _module

warnings.warn("katarina.body.stage14 moved to katarina.body.xauusd_specialist", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
