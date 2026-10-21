"""Deprecated alias kept for one release; use ``katarina.body.decision`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import decision as _module

warnings.warn("katarina.body.stage15 moved to katarina.body.decision", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
