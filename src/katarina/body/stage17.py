"""Deprecated alias kept for one release; use ``katarina.body.position_sizing`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import position_sizing as _module

warnings.warn("katarina.body.stage17 moved to katarina.body.position_sizing", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
