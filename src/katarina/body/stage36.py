"""Deprecated alias kept for one release; use ``katarina.body.live_preflight`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import live_preflight as _module

warnings.warn("katarina.body.stage36 moved to katarina.body.live_preflight", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
