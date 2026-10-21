"""Deprecated alias kept for one release; use ``katarina.body.multi_timeframe`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import multi_timeframe as _module

warnings.warn("katarina.body.stage12 moved to katarina.body.multi_timeframe", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
