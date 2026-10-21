"""Deprecated alias kept for one release; use ``katarina.body.constitution_guard`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import constitution_guard as _module

warnings.warn("katarina.body.stage34 moved to katarina.body.constitution_guard", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
