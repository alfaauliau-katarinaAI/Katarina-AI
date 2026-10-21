"""Deprecated alias kept for one release; use ``katarina.body.market_regime`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import market_regime as _module

warnings.warn("katarina.body.stage13 moved to katarina.body.market_regime", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
