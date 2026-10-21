"""Deprecated alias kept for one release; use ``katarina.body.learning`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import learning as _module

warnings.warn("katarina.body.stage26 moved to katarina.body.learning", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
