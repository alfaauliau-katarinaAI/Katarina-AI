"""Deprecated alias kept for one release; use ``katarina.body.strategy_tester`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import strategy_tester as _module

warnings.warn("katarina.body.stage35 moved to katarina.body.strategy_tester", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
