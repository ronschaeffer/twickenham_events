# Lightweight package shim to allow `python -m twickenham_events.__main__`
# to find the source package located under `src/` during test subprocess runs.
# This file adds the repository `src/` directory to sys.path so the module
# import mechanism can locate the actual package implementation.

from __future__ import annotations

import os
import sys

# Resolve the repo root relative to this shim file and ensure `src` is on sys.path
_root = os.path.dirname(os.path.dirname(__file__))
_src = os.path.join(_root, "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

# Ensure submodule imports (e.g. `twickenham_events.config`) find the real
# package implementation under `src/twickenham_events` by extending this
# package's __path__ to include that directory. This allows `python -m
# twickenham_events.__main__` to import submodules correctly from a test
# subprocess where the console-script isn't installed.
_real_pkg = os.path.join(_src, "twickenham_events")
if os.path.isdir(_real_pkg) and _real_pkg not in __path__:
    __path__.insert(0, _real_pkg)

# Re-export minimal metadata
__all__ = []

# Try to surface package metadata (like __version__) from the real package
# implementation under src/twickenham_events so imports such as
# `from twickenham_events import __version__` work in test subprocesses.
try:
    import runpy

    _init_path = os.path.join(_real_pkg, "__init__.py")
    if os.path.isfile(_init_path):
        _g = runpy.run_path(_init_path)
        if "__version__" in _g:
            __version__ = _g["__version__"]
        if "__all__" in _g and isinstance(_g["__all__"], list):
            __all__ = list(_g["__all__"])
except Exception:
    # Best-effort only — falling back to no-version is acceptable for tests.
    pass
