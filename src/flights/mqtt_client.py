"""
MQTT client for Flights CLI.

Adapted from twickenham_events MQTT functionality for flight data publishing.
"""

import json
import logging
from typing import Any, Dict, List

try:
    from ha_mqtt_publisher.publisher import MQTTPublisher as LibMQTTPublisher
except Exception:
    class LibMQTTPublisher:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("ha_mqtt_publisher not available")


class FlightMQTTClient:
    """MQTT client for publishing flight data."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def publish_flights(self, flights: List[Dict[str, Any]]) -> bool:
        """Publish flight data to MQTT topics."""
        if not self.config.get("mqtt.enabled", False):
            self.logger.info("MQTT disabled, skipping publish")
            return True
        
        try:
            mqtt_config = self.config.get_mqtt_config()
            
            with LibMQTTPublisher(**mqtt_config) as publisher:
                # Publish flight summary
                summary = self._create_flight_summary(flights)
                self._publish_topic(publisher, "status", summary)
                
                # Publish departures
                departures = [f for f in flights if f["type"] == "departure"]
                self._publish_topic(publisher, "departures", {"flights": departures})
                
                # Publish arrivals  
                arrivals = [f for f in flights if f["type"] == "arrival"]
                self._publish_topic(publisher, "arrivals", {"flights": arrivals})
                
                # Publish next flight
                next_flight = self._find_next_flight(flights)
                if next_flight:
                    self._publish_topic(publisher, "next", next_flight)
                
                self.logger.info("Successfully published flight data to MQTT")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to publish to MQTT: {e}")
            return False
    
    def _publish_topic(self, publisher, topic_key: str, payload: Dict[str, Any]) -> None:
        """Publish payload to a specific topic."""
        topic = self.config.get(f"mqtt.topics.{topic_key}")
        if topic:
            publisher.publish(topic, json.dumps(payload), retain=True)
            self.logger.debug(f"Published to {topic}: {len(json.dumps(payload))} bytes")
    
    def _create_flight_summary(self, flights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a summary of flight data."""
        summary = {
            "total_flights": len(flights),
            "departures_count": len([f for f in flights if f["type"] == "departure"]),
            "arrivals_count": len([f for f in flights if f["type"] == "arrival"]),
            "on_time_count": len([f for f in flights if f["status"] == "On Time"]),
            "delayed_count": len([f for f in flights if f["status"] == "Delayed"]),
            "cancelled_count": len([f for f in flights if f["status"] == "Cancelled"]),
            "last_updated": flights[0].get("last_updated") if flights else None
        }
        return summary
    
    def _find_next_flight(self, flights: List[Dict[str, Any]]) -> Dict[str, Any] | None:
        """Find the next upcoming flight."""
        from datetime import datetime
        
        if not flights:
            return None
        
        now = datetime.now()
        upcoming = []
        
        for flight in flights:
            time_key = "scheduled_departure" if flight["type"] == "departure" else "scheduled_arrival"
            flight_time = datetime.fromisoformat(flight[time_key].replace("Z", "+00:00"))
            
            if flight_time > now:
                upcoming.append((flight_time, flight))
        
        if not upcoming:
            return None
        
        upcoming.sort(key=lambda x: x[0])
        return upcoming[0][1]