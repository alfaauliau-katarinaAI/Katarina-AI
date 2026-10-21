"""Deprecated alias kept for one release; use ``katarina.body.tester_evaluation`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import tester_evaluation as _module

warnings.warn("katarina.body.stage25 moved to katarina.body.tester_evaluation", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
