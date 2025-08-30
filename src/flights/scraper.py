"""
Flight data scraper for Flights CLI.

Adapted from twickenham_events scraper for flight tracking functionality.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import requests


class FlightScraper:
    """Flight data scraper and processor."""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def scrape_flights(self) -> List[Dict[str, Any]]:
        """Scrape flight data from configured sources."""
        self.logger.info("Starting flight data scrape")
        
        # For demonstration, return mock flight data
        # In a real implementation, this would connect to flight APIs
        mock_flights = self._generate_mock_flights()
        
        self.logger.info(f"Retrieved {len(mock_flights)} flight records")
        return mock_flights
    
    def _generate_mock_flights(self) -> List[Dict[str, Any]]:
        """Generate mock flight data for demonstration."""
        now = datetime.now()
        flights = []
        
        # Mock departures
        departure_flights = [
            {
                "flight_number": "AA123",
                "airline": "American Airlines",
                "destination": "Los Angeles",
                "scheduled_departure": (now + timedelta(hours=2)).isoformat(),
                "gate": "A15",
                "status": "On Time",
                "type": "departure"
            },
            {
                "flight_number": "DL456",
                "airline": "Delta Air Lines", 
                "destination": "New York",
                "scheduled_departure": (now + timedelta(hours=4)).isoformat(),
                "gate": "B22",
                "status": "Delayed",
                "type": "departure"
            }
        ]
        
        # Mock arrivals
        arrival_flights = [
            {
                "flight_number": "UA789",
                "airline": "United Airlines",
                "origin": "Chicago",
                "scheduled_arrival": (now + timedelta(hours=1)).isoformat(),
                "gate": "C10",
                "status": "On Time",
                "type": "arrival"
            },
            {
                "flight_number": "SW101",
                "airline": "Southwest Airlines",
                "origin": "Denver",
                "scheduled_arrival": (now + timedelta(hours=3)).isoformat(),
                "gate": "A5",
                "status": "On Time", 
                "type": "arrival"
            }
        ]
        
        flights.extend(departure_flights)
        flights.extend(arrival_flights)
        
        return flights
    
    def summarize_flights(self, flights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Summarize flight data by type and status."""
        summary = {
            "total_flights": len(flights),
            "departures": [],
            "arrivals": [],
            "by_status": {
                "on_time": 0,
                "delayed": 0,
                "cancelled": 0
            },
            "last_updated": datetime.now().isoformat()
        }
        
        for flight in flights:
            if flight["type"] == "departure":
                summary["departures"].append(flight)
            elif flight["type"] == "arrival":
                summary["arrivals"].append(flight)
            
            status = flight["status"].lower().replace(" ", "_")
            if status in summary["by_status"]:
                summary["by_status"][status] += 1
        
        return summary
    
    def find_next_flight(self, flights: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find the next upcoming flight (earliest departure or arrival)."""
        if not flights:
            return None
        
        now = datetime.now()
        upcoming_flights = []
        
        for flight in flights:
            time_key = "scheduled_departure" if flight["type"] == "departure" else "scheduled_arrival"
            flight_time = datetime.fromisoformat(flight[time_key].replace("Z", "+00:00"))
            
            if flight_time > now:
                upcoming_flights.append((flight_time, flight))
        
        if not upcoming_flights:
            return None
        
        # Sort by time and return the earliest
        upcoming_flights.sort(key=lambda x: x[0])
        return upcoming_flights[0][1]