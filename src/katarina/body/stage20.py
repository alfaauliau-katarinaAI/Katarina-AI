"""Deprecated alias kept for one release; use ``katarina.body.trade_evaluation`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import trade_evaluation as _module

warnings.warn("katarina.body.stage20 moved to katarina.body.trade_evaluation", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
