"""Deprecated alias kept for one release; use ``katarina.body.automated_testing`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import automated_testing as _module

warnings.warn("katarina.body.stage33 moved to katarina.body.automated_testing", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
