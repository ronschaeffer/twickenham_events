"""
MQTT client for publishing Twickenham Events data.

Handles MQTT publishing with proper error handling and reconnection.
"""

import logging
from typing import Any

from .config import Config

logger = logging.getLogger(__name__)

try:
    from mqtt_publisher.publisher import MQTTPublisher

    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.warning("MQTT publisher not available")


class MQTTClient:
    """MQTT client for event publishing."""

    def __init__(self, config: Config):
        """Initialize MQTT client with configuration."""
        self.config = config

        if not MQTT_AVAILABLE:
            raise ImportError(
                "MQTT publisher not available. Install mqtt_publisher package."
            )

    def publish_events(self, events: list[dict[str, Any]], ai_processor=None) -> None:
        """Publish events to MQTT broker with event type and icon information."""
        if not self.config.mqtt_enabled:
            logger.info("MQTT publishing disabled")
            return

        logger.info("Publishing events to MQTT")

        mqtt_config = self.config.get_mqtt_config()
        topics = self.config.get_mqtt_topics()

        # Enhance events with icon information if AI shortener is available
        enhanced_events = []
        for event in events:
            enhanced_event = event.copy()
            if ai_processor and "fixture" in event:
                event_type, emoji, mdi_icon = ai_processor.get_event_type_and_icons(
                    event["fixture"]
                )
                enhanced_event.update(
                    {
                        "event_type": event_type,
                        "icon_emoji": emoji,
                        "icon_mdi": mdi_icon,
                    }
                )
            enhanced_events.append(enhanced_event)

        with MQTTPublisher(**mqtt_config) as publisher:
            # Publish all events
            all_events_payload = {
                "events": enhanced_events,
                "count": len(enhanced_events),
                "last_updated": self._get_timestamp(),
            }

            if "all_upcoming" in topics:
                publisher.publish(
                    topics["all_upcoming"], all_events_payload, retain=True
                )
                logger.info("Published all events to %s", topics["all_upcoming"])

            # Publish next event
            next_event = enhanced_events[0] if enhanced_events else None
            next_event_payload = {
                "event": next_event,
                "last_updated": self._get_timestamp(),
            }

            if "next" in topics:
                publisher.publish(topics["next"], next_event_payload, retain=True)
                logger.info("Published next event to %s", topics["next"])

            # Publish status
            status_payload = {
                "status": "active" if enhanced_events else "no_events",
                "event_count": len(enhanced_events),
                "last_updated": self._get_timestamp(),
            }

            if "status" in topics:
                publisher.publish(topics["status"], status_payload, retain=True)
                logger.info("Published status to %s", topics["status"])

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()
