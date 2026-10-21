"""Deprecated alias kept for one release; use ``katarina.body.walk_forward`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import walk_forward as _module

warnings.warn("katarina.body.stage23 moved to katarina.body.walk_forward", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
