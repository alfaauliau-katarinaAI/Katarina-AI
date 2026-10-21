"""Deprecated alias kept for one release; use ``katarina.body.position_manager`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import position_manager as _module

warnings.warn("katarina.body.stage19 moved to katarina.body.position_manager", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
