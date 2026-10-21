"""Deprecated alias kept for one release; use ``katarina.body.model_promotion`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import model_promotion as _module

warnings.warn("katarina.body.stage28 moved to katarina.body.model_promotion", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
