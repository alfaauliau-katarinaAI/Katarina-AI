"""Deprecated alias kept for one release; use ``katarina.body.research`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import research as _module

warnings.warn("katarina.body.stage21 moved to katarina.body.research", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
