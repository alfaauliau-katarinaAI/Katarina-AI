"""Deprecated alias kept for one release; use ``katarina.body.economic_intelligence`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import economic_intelligence as _module

warnings.warn("katarina.body.stage29 moved to katarina.body.economic_intelligence", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
