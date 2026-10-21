"""Deprecated alias kept for one release; use ``katarina.body.live_micro_risk`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import live_micro_risk as _module

warnings.warn("katarina.body.stage38 moved to katarina.body.live_micro_risk", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
