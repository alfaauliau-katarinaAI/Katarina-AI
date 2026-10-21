"""Deprecated alias kept for one release; use ``katarina.body.risk_governor`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import risk_governor as _module

warnings.warn("katarina.body.stage16 moved to katarina.body.risk_governor", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
