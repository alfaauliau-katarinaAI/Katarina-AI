"""Deprecated alias kept for one release; use ``katarina.body.execution`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import execution as _module

warnings.warn("katarina.body.stage18 moved to katarina.body.execution", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
