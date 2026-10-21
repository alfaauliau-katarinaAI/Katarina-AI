"""Deprecated alias kept for one release; use ``katarina.body.performance_monitoring`` (see ``katarina.body.STAGE_MODULES``)."""
import sys
import warnings

from katarina.body import performance_monitoring as _module

warnings.warn("katarina.body.stage39 moved to katarina.body.performance_monitoring", DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
