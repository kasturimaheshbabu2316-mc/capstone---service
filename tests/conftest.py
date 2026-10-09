"""PyTest Global Configuration and Clean Teardown.

Track: Business Operations / Customer Support (Ola)
Suppresses third-party atexit closed file errors and deprecation warnings during testing.
"""

import sys
import warnings

# Suppress deprecation warnings during testing
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*InMemoryChatMessageHistory was deprecated.*")

# Prevent colorama / crewai atexit reset_all from failing on closed stdout
try:
    import colorama

    _orig_reset_all = colorama.initialise.reset_all

    def _safe_reset_all():
        try:
            if sys.stdout and not sys.stdout.closed and hasattr(sys.stdout, "isatty"):
                _orig_reset_all()
        except Exception:
            pass

    colorama.initialise.reset_all = _safe_reset_all
except ImportError:
    pass
