"""Deprecated location; use ``katarina.intelligence.shadow.shadow_paper_book``. Removed after cleanup stage 3."""
import sys
import warnings

from katarina.intelligence.shadow import shadow_paper_book as _module

warnings.warn("katarina.intelligence.shadow_paper_book moved to katarina.intelligence.shadow.shadow_paper_book",
              DeprecationWarning, stacklevel=2)
sys.modules[__name__] = _module
