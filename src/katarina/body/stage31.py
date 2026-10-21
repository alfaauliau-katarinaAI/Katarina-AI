"""Deprecated alias kept for one release; use ``katarina.body.exposure`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import exposure as _module

warnings.warn("katarina.body.stage31 moved to katarina.body.exposure", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
