"""Deprecated alias kept for one release; use ``katarina.body.backtesting`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import backtesting as _module

warnings.warn("katarina.body.stage22 moved to katarina.body.backtesting", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
