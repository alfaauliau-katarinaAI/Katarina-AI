"""Deprecated location; use ``katarina.intelligence.lab.research_signal_ablation``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.lab import research_signal_ablation as _module

warnings.warn("katarina.intelligence.research_signal_ablation moved to katarina.intelligence.lab.research_signal_ablation",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
