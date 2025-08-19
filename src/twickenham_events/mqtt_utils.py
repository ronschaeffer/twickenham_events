"""Small helpers to normalize paho-mqtt callback signatures.

paho-mqtt uses different callback signatures across versions (v1 vs v2). These
helpers extract commonly-needed pieces (like reason_code/properties) from the
variable args/kwargs so application callbacks can be simpler and robust.
"""

from typing import Any, Callable, Optional


def extract_reason_code(*args: tuple[Any, ...], **kwargs: dict) -> Optional[Any]:
    """Extract a likely reason_code from positional args or kwargs.

    Rules (best-effort):
    - Search positional args from right-to-left for an int-like value.
    - Fall back to kwargs 'reason_code' or 'rc' if present.
    - Return None if nothing found.
    """
    # Search positional args from right to left for int-like value
    for a in reversed(args):
        if isinstance(a, int) and not isinstance(a, bool):
            return a
        # Some paho types provide an int-like ReasonCode/Enum
        if hasattr(a, "__int__"):
            try:
                val = int(a)
            except Exception:
                val = None
            else:
                return val

    # Check common kw names
    for key in ("reason_code", "rc"):
        if key in kwargs and kwargs[key] is not None:
            return kwargs[key]

    return None


def extract_properties(*args: tuple[Any, ...], **kwargs: dict) -> Optional[Any]:
    """Extract MQTT v5 properties object from args/kwargs if present.

    Best-effort: prefer explicit kw 'properties', else take the last positional
    arg if it doesn't look like an int-like reason code.
    """
    if "properties" in kwargs and kwargs["properties"] is not None:
        return kwargs["properties"]

    if args:
        last = args[-1]
        # if last is not int-like, treat as properties
        if not (isinstance(last, int) or hasattr(last, "__int__")):
            return last
        # else maybe properties is second to last
        if len(args) >= 2:
            cand = args[-2]
            if not (isinstance(cand, int) or hasattr(cand, "__int__")):
                return cand

    return None


def safe_on_connect(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to normalize on_connect callbacks to (client, userdata, reason_code, properties).

    Use like:
        @safe_on_connect
        def on_connect(client, userdata, reason_code, properties):
            ...
    """

    def wrapper(client: Any, userdata: Any, *args: Any, **kwargs: Any) -> Any:
        reason_code = extract_reason_code(*args, **kwargs)
        properties = extract_properties(*args, **kwargs)
        return func(client, userdata, reason_code, properties)

    return wrapper
