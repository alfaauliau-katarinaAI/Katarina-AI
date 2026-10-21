"""Deprecated alias kept for one release; use ``katarina.body.market_intelligence`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import market_intelligence as _module

warnings.warn("katarina.body.stage11 moved to katarina.body.market_intelligence", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
