"""MQTT client for publishing Twickenham Events data.

Enhancements:
 - AI error and publish error tracking
 - Explicit AI enabled flag (from config + provided processor)
 - sw_version surfaced in status payload
 - TypedDict definitions for payload shapes for clarity
 - Structured debug logging summary
"""

import logging
from typing import Any, TypedDict

from .config import Config

try:  # version import (safe fallback if not installed as package)
    from . import __version__ as PACKAGE_VERSION  # type: ignore
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
    sw_version: Package/app version
        last_updated: ISO timestamp of publish
        errors: (optional) list of scrape / processing error strings (bounded upstream)
        error_count: (optional) convenience numeric length of errors list
        last_command: (optional) summary of most recent command (id/name/outcome)
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


class TodayPayload(TypedDict):
    date: str
    has_event_today: bool
    events_today: int
    last_updated: str


logger = logging.getLogger(__name__)

try:  # Local development dependency (path) for ha-mqtt-publisher
    from ha_mqtt_publisher.publisher import MQTTPublisher  # type: ignore

    MQTT_AVAILABLE = True
except ImportError:  # pragma: no cover - defensive
    MQTT_AVAILABLE = False
    logger.warning("ha-mqtt-publisher not available")

    class MQTTPublisher:  # type: ignore
        """Fallback stub so references remain valid even if package missing."""

        def __init__(self, *_, **__):
            raise RuntimeError(
                "ha-mqtt-publisher not installed. Install dependency to enable MQTT publishing."
            )

        def __enter__(self):  # pragma: no cover - not used when missing
            return self

        def __exit__(self, exc_type, exc, tb):  # pragma: no cover
            return False

        def publish(self, *_args, **_kwargs):  # pragma: no cover - stub only
            return None


class MQTTClient:
    """MQTT client for event publishing."""

    def __init__(self, config: Config):
        """Initialize MQTT client with configuration."""
        self.config = config

        if not MQTT_AVAILABLE:
            raise ImportError(
                "MQTT publisher not available. Install mqtt_publisher package."
            )

    def publish_events(
        self,
        events: list[dict[str, Any]],
        ai_processor=None,
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
        logger.info(
            "mqtt_connection broker=%s port=%s security=%s tls_enabled=%s",
            mqtt_config.get("broker_url"),
            mqtt_config.get("broker_port"),
            mqtt_config.get("security"),
            bool(mqtt_config.get("tls")),
        )
        topics = self.config.get_mqtt_topics()

        # Enhance events minimally (add AI emoji/icon if available)
        enhanced_events: list[dict[str, Any]] = []
        ai_errors = 0
        for raw in events:
            # Drop any legacy/display-only keys that should not be exposed via MQTT attributes
            # (e.g., 'title' can conflict with HA card/title usages). Keep only meaningful fields.
            e = {k: v for k, v in raw.items() if k != "title"}
            # Prefer AI emoji, but the published key should always be 'emoji'
            raw_emoji = e.get("emoji")
            if ai_processor and "fixture" in e:
                try:
                    _etype, emoji_ai, mdi_icon = ai_processor.get_event_type_and_icons(
                        e["fixture"]
                    )
                    if emoji_ai:
                        e["emoji"] = emoji_ai
                    elif raw_emoji:
                        e["emoji"] = raw_emoji
                    # Standardize icon key
                    e["icon"] = mdi_icon
                except Exception:  # pragma: no cover - non-fatal
                    ai_errors += 1
            enhanced_events.append(e)

        next_event = enhanced_events[0] if enhanced_events else None

        if not MQTT_AVAILABLE:  # Extra safety
            logger.warning("Skipping publish; MQTT library unavailable")
            return

        publish_errors = 0
        with MQTTPublisher(**mqtt_config) as publisher:
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
            def _safe_strptime(d: str):
                try:
                    from datetime import datetime as _dt_local

                    return _dt_local.strptime(d, "%Y-%m-%d")
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
                days_map = month["_days"]  # type: ignore[index]
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
                days = m.pop("_days")  # type: ignore[index]
                day_objs = [days[k] for k in sorted(days.keys())]
                by_month.append({**m, "days": day_objs})

            events_json: dict[str, Any] = {
                "count": len(enhanced_events),
                # last_updated intentionally omitted to avoid duplication inside events_json
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
                    }
                )
            if "next" in topics:
                try:
                    publisher.publish(topics["next"], next_payload, retain=True)
                except Exception:  # pragma: no cover
                    publish_errors += 1
            # Base status; may be overridden to 'error' by extra_status logic.
            base_status = "active" if enhanced_events else "no_events"
            status_payload: StatusPayload = {
                "status": base_status,
                "event_count": len(enhanced_events),
                "ai_error_count": ai_errors,
                "publish_error_count": publish_errors,
                "ai_enabled": bool(ai_processor) and self.config.ai_enabled,
                "sw_version": PACKAGE_VERSION,
                "last_updated": ts,
            }  # type: ignore[assignment]
            if extra_status:
                # Merge but don't overwrite core keys unless explicitly intended
                for k, v in extra_status.items():
                    status_payload[k] = v  # type: ignore
                # If caller supplied errors but no explicit status override and we have no events
                # AND errors exist, automatically promote to 'error'. Caller can still override.
                if (
                    "status" not in extra_status
                    and not enhanced_events
                    and extra_status.get("errors")
                ):
                    status_payload["status"] = "error"  # type: ignore[index]
                # Provide convenience error_count if errors list present and count missing
                if "errors" in status_payload and "error_count" not in status_payload:
                    try:
                        status_payload["error_count"] = len(  # type: ignore[index]
                            status_payload["errors"]  # type: ignore[index]
                        )
                    except Exception:  # pragma: no cover - defensive
                        pass
            if "status" in topics:
                logger.debug("status_payload_pre_publish=%s", status_payload)
                # Guarantee last_updated key for validator
                if "last_updated" not in status_payload:  # type: ignore
                    from datetime import datetime as _dt

                    status_payload["last_updated"] = _dt.now().isoformat()  # type: ignore[index]
                try:
                    publisher.publish(topics["status"], status_payload, retain=True)
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
