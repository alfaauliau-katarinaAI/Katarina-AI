"""Deprecated alias kept for one release; use ``katarina.body.robustness`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import robustness as _module

warnings.warn("katarina.body.stage24 moved to katarina.body.robustness", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
