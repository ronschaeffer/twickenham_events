"""Plugin loader for dynamic command registration.

Searches a plugins/ directory for Python modules named cmd_*.py. Each module
may define a function:

    def register_commands(processor) -> None

that will be invoked with the active CommandProcessor instance.
"""

from __future__ import annotations

from importlib import util
import logging
from pathlib import Path
from typing import TYPE_CHECKING

# NOTE: Python 3.11+ preferred style uses built-in collection generics (list[str])
# Use TYPE_CHECKING for optional import to avoid runtime dependency cycles.
if TYPE_CHECKING:  # pragma: no cover
    from .command_processor import CommandProcessor


logger = logging.getLogger(__name__)


def load_command_plugins(
    processor: CommandProcessor, plugins_dir: str = "plugins"
) -> list[str]:
    loaded: list[str] = []
    base = Path(plugins_dir)
    if not base.exists() or not base.is_dir():
        return loaded
    for path in base.glob("cmd_*.py"):
        try:
            spec = util.spec_from_file_location(path.stem, path)
            if not spec or not spec.loader:
                continue
            module = util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore
            if hasattr(module, "register_commands"):
                module.register_commands(processor)
                loaded.append(path.stem)
                logger.info("loaded command plugin %s", path.name)
        except Exception as e:  # pragma: no cover
            logger.warning("failed loading plugin %s: %s", path, e)
    return loaded


__all__ = ["load_command_plugins"]
