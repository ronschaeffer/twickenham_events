"""
Data change detection for meaningful alerts
"""


def detect_significant_changes(new_events, previous_events):
    """Detect significant changes worth alerting about."""
    changes = {
        "new_events": [],
        "cancelled_events": [],
        "time_changes": [],
        "significant": False,
    }

    # Convert to sets for comparison
    new_fixtures = {
        (e["date"], e["fixture"]) for day in new_events for e in day["events"]
    }
    old_fixtures = {
        (e["date"], e["fixture"]) for day in previous_events for e in day["events"]
    }

    # Detect new events
    new_events_found = new_fixtures - old_fixtures
    if new_events_found:
        changes["new_events"] = list(new_events_found)
        changes["significant"] = True

    # Detect cancelled events
    cancelled_events = old_fixtures - new_fixtures
    if cancelled_events:
        changes["cancelled_events"] = list(cancelled_events)
        changes["significant"] = True

    return changes


# Usage in main():
if previous_events:
    changes = detect_significant_changes(summarized_events, previous_events)
    if changes["significant"]:
        # Publish alert to special MQTT topic
        publisher.publish(
            "twickenham_events/alerts",
            {"type": "data_change", "changes": changes, "timestamp": timestamp},
        )
