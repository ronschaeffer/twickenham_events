"""MQTT client for publishing Twickenham Events data.

Enhancements:
 - AI error and publish error tracking
 - Explicit AI enabled flag (from config + provided processor)
 - sw_version surfaced in status payload
 - TypedDict definitions for payload shapes for clarity
 - Structured debug logging summary
"""

from datetime import datetime as _datetime
import logging
from typing import Any, Optional, TypedDict, cast

from .config import Config
from .network_utils import build_smart_external_url

try:  # version import (safe fallback if not installed as package)
    from . import __version__ as PACKAGE_VERSION
except Exception:  # pragma: no cover
    PACKAGE_VERSION = "unknown"


class StatusPayload(TypedDict, total=False):
    """Retained status JSON published to twickenham_events/status.

    Fields:
        status: active | no_events | error
        event_count: number of future events (0 when none or on error)
        ai_error_count: AI icon/shortening errors for this publish cycle
        publish_error_count: MQTT publish attempt failures (network, auth)
        ai_enabled: Whether AI enrichment is active
        sw_version: Software version string (e.g., "0.1.2")
        last_updated: ISO timestamp of publish
        errors: (optional) list of scrape / processing error strings (bounded upstream)
        error_count: (optional) convenience numeric length of errors list
        last_command: (optional) summary of most recent command (id/name/outcome)
        web_server: (optional) web server status and URLs for Home Assistant integration
    """

    status: str
    event_count: int
    ai_error_count: int
    publish_error_count: int
    ai_enabled: bool
    sw_version: str
    last_updated: str
    errors: list[str]
    error_count: int
    last_command: dict[str, Any]
    # Optional AI circuit breaker fields
    ai_status: str
    ai_retry_at: str
    ai_retry_in_seconds: int
    # Optional web server information
    web_server: dict[str, Any]


class TodayPayload(TypedDict):
    date: str
    has_event_today: bool
    events_today: int
    last_updated: str


logger = logging.getLogger(__name__)

try:  # Import ha_mqtt_publisher from PyPI package
    import importlib

    _pub_mod = importlib.import_module("ha_mqtt_publisher.publisher")
    # Runtime alias to the upstream implementation. Typed as Any so mypy won't
    # complain about dynamic binding to a package-provided class.
    PublisherImpl: Any = _pub_mod.MQTTPublisher
    MQTT_AVAILABLE = True
except Exception:
    MQTT_AVAILABLE = False
    logger.warning("ha-mqtt-publisher not available")

    class MQTTPublisher:  # fallback stub
        """Fallback stub so references remain valid even if package missing."""

        def __init__(self, *_: object, **__: object) -> None:
            # Permissive fallback: tests may monkeypatch this class or expect a
            # context-manager that yields an object with a publish() method.
            self._args = _
            self._kwargs = __

        def __enter__(self) -> "MQTTPublisher":
            return self

        def __exit__(
            self, exc_type: object | None, exc: object | None, tb: object | None
        ) -> None:
            return None

        def publish(self, *_args: object, **_kwargs: object) -> object | None:
            # Minimal behavior: return True to indicate success when possible,
            # otherwise None. Tests generally patch this class or the module
            # so behavior can be overridden.
            return True

    # Bind PublisherImpl to our fallback so call sites can refer to either name.
    PublisherImpl = MQTTPublisher

# Public alias expected by tests and call sites
MQTTPublisher = PublisherImpl


def _get_web_server_status(config: Config) -> dict[str, Any]:
    """Get web server status and URL information for MQTT publishing.

    This function checks if the web server is enabled and attempts to gather
    URL information that can be used by Home Assistant for calendar integration.

    Args:
        config: Application configuration

    Returns:
        Dictionary with web server status and URLs, or empty dict if disabled
    """
    if not config.web_enabled:
        return {}

    try:
        # Build URL information using smart external URL detection
        base_url = build_smart_external_url(
            config.web_host,
            config.web_port,
            external_url_base=config.web_external_url_base,
        )

        # Only include essential URLs for Home Assistant integration
        return {
            "enabled": True,
            "base_url": base_url,
            "calendar_url": f"{base_url}/calendar",
            "events_url": f"{base_url}/events",
        }
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("Failed to build web server status: %s", e)
        return {"enabled": True, "error": str(e)}


class MQTTClient:
    """MQTT client for event publishing."""

    def __init__(self, config: Config):
        """Initialize MQTT client with configuration."""
        self.config = config

    # Do not raise at init time; tests may monkeypatch publisher classes or
    # the module-level MQTT_AVAILABLE flag. Raise only when attempting to
    # perform publishes if necessary.

    def publish_events(
        self,
        events: list[dict[str, Any]],
        ai_processor: Any = None,
        extra_status: dict[str, Any] | None = None,
    ) -> None:
        """Publish core Twickenham Events MQTT topics.

        Topics (retained):
          twickenham_events/events/all_upcoming
          twickenham_events/events/next
          twickenham_events/status
          twickenham_events/events/today   (new)
        """
        if not self.config.mqtt_enabled:
            logger.info("MQTT publishing disabled")
            return
        logger.info("Publishing events to MQTT")

        mqtt_config = self.config.get_mqtt_config()
        # Explicit connection log (do not enable TLS automatically)
        # Treat an empty dict ({} - explicit TLS settings) as enabled.
        tls_val = mqtt_config.get("tls")
        tls_enabled = tls_val is not None and tls_val is not False
        logger.info(
            "mqtt_connection broker=%s port=%s security=%s tls_enabled=%s",
            mqtt_config.get("broker_url"),
            mqtt_config.get("broker_port"),
            mqtt_config.get("security"),
            tls_enabled,
        )
        topics = self.config.get_mqtt_topics()

        # Enhance events minimally (add AI emoji/icon if available)
        enhanced_events: list[dict[str, Any]] = []
        ai_errors = 0
        for raw in events:
            # Drop any legacy/display-only keys that should not be exposed via MQTT attributes
            # (e.g., 'title' can conflict with HA card/title usages). Keep only meaningful fields.
            e = {k: v for k, v in raw.items() if k != "title"}

            # Prefer pre-computed AI data from batch processing (stored during scraping)
            if "ai_emoji" in e and "ai_mdi_icon" in e:
                e["emoji"] = e["ai_emoji"]
                e["icon"] = e["ai_mdi_icon"]
                # Remove the temporary AI keys
                e.pop("ai_emoji", None)
                e.pop("ai_mdi_icon", None)
                e.pop("ai_event_type", None)
            elif ai_processor and "fixture" in e:
                # Fallback to individual AI call only if no pre-computed data exists
                try:
                    _etype, emoji_ai, mdi_icon = ai_processor.get_event_type_and_icons(
                        e["fixture"]
                    )
                    if emoji_ai:
                        e["emoji"] = emoji_ai
                    # Standardize icon key
                    e["icon"] = mdi_icon
                except Exception:  # pragma: no cover - non-fatal
                    ai_errors += 1

            # Ensure sensible defaults so downstream attributes are always present
            # and consistent for Home Assistant templates/cards.
            if not e.get("emoji"):
                e["emoji"] = "🏟️"
            icon_val = e.get("icon")
            if not icon_val or not isinstance(icon_val, str):
                e["icon"] = "mdi:calendar-clock"
            elif not icon_val.startswith("mdi:"):
                # If AI returned a bare icon name, normalize to mdi: prefix
                e["icon"] = f"mdi:{icon_val}"

            enhanced_events.append(e)

        next_event = enhanced_events[0] if enhanced_events else None

        if not MQTT_AVAILABLE:  # Extra safety
            logger.debug(
                "MQTT library not available at import time; using fallback publisher if provided"
            )

        publish_errors = 0

        # Opportunistic permissive-TLS direct publish path for self-signed brokers.
        # If TLS is requested and verify is explicitly False, attempt a minimal
        # one-shot publish using paho-mqtt with tls_insecure_set(True). If this
        # succeeds, we can skip the upstream publisher path.
        try:
            _tls = mqtt_config.get("tls")
            _auth = (
                mqtt_config.get("auth")
                if isinstance(mqtt_config.get("auth"), dict)
                else None
            )
            if isinstance(_tls, dict) and _tls.get("verify") is False:
                import json as _json
                import ssl as _ssl

                import paho.mqtt.client as _mqtt

                # paho v2 exposes CallbackAPIVersion; handle v1 gracefully
                _CBV = getattr(_mqtt, "CallbackAPIVersion", None)

                if _CBV is not None:
                    _client = _mqtt.Client(
                        protocol=_mqtt.MQTTv5, callback_api_version=_CBV.VERSION2
                    )
                else:
                    _client = _mqtt.Client(protocol=_mqtt.MQTTv5)
                if _auth and _auth.get("username") and _auth.get("password"):
                    _client.username_pw_set(_auth["username"], _auth["password"])  # type: ignore[arg-type]
                # Permissive TLS for self-signed certs
                _client.tls_set(cert_reqs=_ssl.CERT_NONE)
                _client.tls_insecure_set(True)
                _client.connect(
                    host=str(mqtt_config.get("broker_url")),
                    port=int(mqtt_config.get("broker_port") or 8883),
                    keepalive=30,
                )
                _client.loop_start()
                # Compose payloads inline (mirrors below)
                ts = self._get_timestamp()
                months_map_direct: dict[str, dict[str, Any]] = {}

                def _safe_strptime_direct(d: str) -> Optional[_datetime]:
                    try:
                        return _datetime.strptime(d, "%Y-%m-%d")
                    except Exception:
                        return None

                for ev in enhanced_events:
                    d = ev.get("date")
                    if not isinstance(d, str):
                        continue
                    dt = _safe_strptime_direct(d)
                    if not dt:
                        continue
                    month_key = dt.strftime("%Y-%m")
                    month_label = dt.strftime("%B %Y")
                    day_label = dt.strftime("%a %d")
                    if month_key not in months_map_direct:
                        months_map_direct[month_key] = {
                            "key": month_key,
                            "label": month_label,
                            "_days": {},
                        }
                    month = months_map_direct[month_key]
                    days_map = month["_days"]
                    if d not in days_map:
                        days_map[d] = {"date": d, "label": day_label, "events": []}
                    days_map[d]["events"].append(
                        {
                            "fixture": ev.get("fixture") or "",
                            "start_time": ev.get("start_time"),
                            "emoji": ev.get("emoji"),
                            "icon": ev.get("icon"),
                            "fixture_short": ev.get("fixture_short"),
                            "crowd": ev.get("crowd")
                            or ev.get("crowd_size")
                            or ev.get("attendance"),
                        }
                    )
                by_month_direct: list[dict[str, Any]] = []
                for mk in sorted(months_map_direct.keys()):
                    m = months_map_direct[mk]
                    days = m.pop("_days")
                    day_objs = [days[k] for k in sorted(days.keys())]
                    by_month_direct.append({**m, "days": day_objs})
                events_json_direct = {
                    "count": len(enhanced_events),
                    "last_updated": ts,
                    "by_month": by_month_direct,
                }
                all_upcoming_payload_direct = {
                    "count": len(enhanced_events),
                    "last_updated": ts,
                    "events_json": events_json_direct,
                }
                # Do not include 'next' in the all_upcoming payload; keep next event on its own topic
                # Build next-event payload with flat attributes (no nested 'event')
                next_payload_direct: dict[str, Any] = {"last_updated": ts}
                if next_event:
                    next_payload_direct.update(
                        {
                            "fixture": next_event.get("fixture"),
                            "start_time": next_event.get("start_time"),
                            "crowd": next_event.get("crowd")
                            or next_event.get("crowd_size")
                            or next_event.get("attendance"),
                            "date": next_event.get("date"),
                            "fixture_short": next_event.get("fixture_short"),
                            "event_index": next_event.get("event_index"),
                            "event_count": next_event.get("event_count"),
                            "emoji": next_event.get("emoji"),
                            "icon": next_event.get("icon"),
                        }
                    )
                today_payload_direct: TodayPayload = {
                    "date": ts.split("T")[0],
                    "has_event_today": any(
                        ev.get("date") == ts.split("T")[0] for ev in enhanced_events
                    ),
                    "events_today": sum(
                        1
                        for ev in enhanced_events
                        if ev.get("date") == ts.split("T")[0]
                    ),
                    "last_updated": ts,
                }
                status_payload_direct: StatusPayload = {
                    "status": "active" if enhanced_events else "no_events",
                    "event_count": len(enhanced_events),
                    "ai_error_count": ai_errors,
                    "publish_error_count": 0,
                    "ai_enabled": bool(ai_processor),
                    "sw_version": PACKAGE_VERSION,
                    "last_updated": ts,
                }

                # Add web server status to direct path as well
                web_server_info = _get_web_server_status(self.config)
                if web_server_info:
                    status_payload_direct["web_server"] = web_server_info
                if extra_status:
                    try:
                        for _k, _v in cast(dict[str, Any], extra_status).items():
                            status_payload_direct[_k] = _v
                    except Exception:
                        pass
                # Publish retained topics
                _client.publish(
                    topics.get("all_upcoming", "twickenham_events/events/all_upcoming"),
                    _json.dumps(all_upcoming_payload_direct),
                    retain=True,
                )
                _client.publish(
                    topics.get("next", "twickenham_events/events/next"),
                    _json.dumps(next_payload_direct),
                    retain=True,
                )
                _client.publish(
                    topics.get("status", "twickenham_events/status"),
                    _json.dumps(status_payload_direct),
                    retain=True,
                )
                _client.publish(
                    topics.get("today", "twickenham_events/events/today"),
                    _json.dumps(today_payload_direct),
                    retain=True,
                )
                _client.loop_stop()
                _client.disconnect()
                logger.info(
                    "Published via direct permissive TLS path (self-signed broker)"
                )
                return
        except Exception:
            # Fall back to upstream publisher path
            pass

        # Use the module-level MQTTPublisher so tests can monkeypatch it.
        pub_ctx = MQTTPublisher(**mqtt_config)
        with pub_ctx as publisher:
            ts = self._get_timestamp()

            # Build an easy-to-parse JSON structure for HA markdown cards
            # events_json schema:
            # {
            #   "count": <int>,
            #   "last_updated": <iso8601>,
            #   "by_month": [
            #       {
            #           "key": "YYYY-MM",
            #           "label": "Month YYYY",
            #           "days": [
            #               {
            #                   "date": "YYYY-MM-DD",
            #                   "label": "Mon DD",
            #                   "events": [
            #                       {"fixture": str, "time": str|None, "emoji": str|None, "icon": str|None, "crowd": Any|None}
            #                   ]
            #               }
            #           ]
            #       }
            #   ]
            # }
            def _safe_strptime(d: str) -> Optional[_datetime]:
                try:
                    return _datetime.strptime(d, "%Y-%m-%d")
                except Exception:
                    return None

            months_map: dict[str, dict[str, Any]] = {}
            for ev in enhanced_events:
                d = ev.get("date")
                if not isinstance(d, str):
                    continue
                dt = _safe_strptime(d)
                if not dt:
                    continue
                month_key = dt.strftime("%Y-%m")
                month_label = dt.strftime("%B %Y")
                day_label = dt.strftime("%a %d")
                if month_key not in months_map:
                    months_map[month_key] = {
                        "key": month_key,
                        "label": month_label,
                        "_days": {},
                    }
                month = months_map[month_key]
                days_map = month["_days"]
                if d not in days_map:
                    days_map[d] = {"date": d, "label": day_label, "events": []}
                days_map[d]["events"].append(
                    {
                        # Never fall back to any 'title' key for fixture text; publish only canonical fixture
                        "fixture": ev.get("fixture") or "",
                        # Use consistent key name across all payloads
                        "start_time": ev.get("start_time"),
                        # The payload standardizes on 'emoji' (AI preferred set above)
                        "emoji": ev.get("emoji"),
                        # Standardized icon key
                        "icon": ev.get("icon"),
                        # Include short fixture consistently
                        "fixture_short": ev.get("fixture_short"),
                        "crowd": ev.get("crowd")
                        or ev.get("crowd_size")
                        or ev.get("attendance"),
                    }
                )

            # Convert maps to sorted lists
            by_month: list[dict[str, Any]] = []
            for mk in sorted(months_map.keys()):
                m = months_map[mk]
                days = m.pop("_days")
                day_objs = [days[k] for k in sorted(days.keys())]
                by_month.append({**m, "days": day_objs})

            events_json: dict[str, Any] = {
                "count": len(enhanced_events),
                # Include last_updated inside events_json to satisfy external validators that expect
                # a timestamp present within the events structure.
                "last_updated": ts,
                "by_month": by_month,
            }

            all_events_payload: dict[str, Any] = {
                # Removed top-level 'events' attribute; rely on events_json for cards/consumers
                "count": len(enhanced_events),
                "last_updated": ts,
                "events_json": events_json,
            }
            if "all_upcoming" in topics:
                try:
                    publisher.publish(
                        topics["all_upcoming"], all_events_payload, retain=True
                    )
                except Exception:  # pragma: no cover - publish resilience
                    publish_errors += 1
            # Build next-event payload with flat attributes for HA card use.
            # Removed nested 'event' attribute; expose only flattened attributes
            next_payload: dict[str, Any] = {"last_updated": ts}
            if next_event:
                next_payload.update(
                    {
                        # Provide full fixture for entity state
                        "fixture": next_event.get("fixture"),
                        "start_time": next_event.get("start_time"),
                        "crowd": next_event.get("crowd")
                        or next_event.get("crowd_size")
                        or next_event.get("attendance"),
                        "date": next_event.get("date"),
                        "fixture_short": next_event.get("fixture_short"),
                        "event_index": next_event.get("event_index"),
                        "event_count": next_event.get("event_count"),
                        # Emoji key always 'emoji' (AI-preferred already stored on event)
                        "emoji": next_event.get("emoji"),
                        # Icon standardized; ensure mdi: prefix value
                        "icon": next_event.get("icon"),
                        # Provide a duplicate attribute for HA display convenience
                        "mdi_icon": next_event.get("icon"),
                    }
                )
            if "next" in topics:
                try:
                    publisher.publish(topics["next"], next_payload, retain=True)
                except Exception:  # pragma: no cover
                    publish_errors += 1
            # Base status; may be overridden to 'error' by extra_status logic.
            base_status = "active" if enhanced_events else "no_events"
            status_payload: dict[str, Any] = {
                "status": base_status,
                "event_count": len(enhanced_events),
                "ai_error_count": ai_errors,
                "publish_error_count": publish_errors,
                "ai_enabled": bool(ai_processor) and self.config.ai_enabled,
                "sw_version": PACKAGE_VERSION,
                "last_updated": ts,
            }

            # Add web server status and URLs for Home Assistant integration
            web_server_info = _get_web_server_status(self.config)
            if web_server_info:
                status_payload["web_server"] = web_server_info
            # If AI circuit breaker is open, include explicit AI backoff info
            try:
                if ai_processor and hasattr(ai_processor, "get_shortener_backoff_info"):
                    info = ai_processor.get_shortener_backoff_info()
                    if info.get("open"):
                        status_payload["ai_status"] = "backoff"
                        if info.get("retry_at"):
                            status_payload["ai_retry_at"] = info.get("retry_at")
                        if info.get("retry_in_seconds") is not None:
                            status_payload["ai_retry_in_seconds"] = info.get(
                                "retry_in_seconds"
                            )
            except Exception:  # pragma: no cover - defensive
                pass
            if extra_status:
                # Merge but don't overwrite core keys unless explicitly intended
                for k, v in extra_status.items():
                    status_payload[k] = v
                # If caller supplied errors but no explicit status override and we have no events
                # AND errors exist, automatically promote to 'error'. Caller can still override.
                if (
                    "status" not in extra_status
                    and not enhanced_events
                    and extra_status.get("errors")
                ):
                    status_payload["status"] = "error"
                # Provide convenience error_count if errors list present and count missing
                if "errors" in status_payload and "error_count" not in status_payload:
                    try:
                        status_payload["error_count"] = len(status_payload["errors"])
                    except Exception:  # pragma: no cover - defensive
                        pass
            if "status" in topics:
                logger.debug("status_payload_pre_publish=%s", status_payload)
                # Guarantee last_updated key for validator
                if "last_updated" not in status_payload:
                    from datetime import datetime as _dt

                    status_payload["last_updated"] = _dt.now().isoformat()
                try:
                    publisher.publish(
                        topics["status"],
                        cast(StatusPayload, status_payload),
                        retain=True,
                    )
                except Exception:  # pragma: no cover
                    publish_errors += 1

            # New today summary topic
            from datetime import date as _date

            today_str = _date.today().strftime("%Y-%m-%d")
            events_today = sum(
                1 for ev in enhanced_events if ev.get("date") == today_str
            )
            today_payload: TodayPayload = {
                "date": today_str,
                "has_event_today": events_today > 0,
                "events_today": events_today,
                "last_updated": ts,
            }
            try:
                publisher.publish(
                    "twickenham_events/events/today", today_payload, retain=True
                )
            except Exception:  # pragma: no cover
                publish_errors += 1

            logger.debug(
                "publish_summary event_count=%s events_today=%s ai_errors=%s publish_errors=%s ai_enabled=%s version=%s",
                len(enhanced_events),
                sum(1 for ev in enhanced_events if ev.get("date") == today_str),
                ai_errors,
                publish_errors,
                status_payload.get("ai_enabled"),
                PACKAGE_VERSION,
            )

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime, timezone

        # Use UTC and seconds precision; HA timestamp device_class expects RFC3339 / ISO8601 with tzinfo
        return (
            datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
