"""Deprecated location; use ``katarina.intelligence.shadow.shadow_gold_intraday``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import shadow_gold_intraday as _module

warnings.warn("katarina.intelligence.shadow_gold_intraday moved to katarina.intelligence.shadow.shadow_gold_intraday",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
