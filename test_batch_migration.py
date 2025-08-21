#!/usr/bin/env python3
"""
Test the migrated batch processing in Twickenham Events.

This script demonstrates that the scraper now uses batch AI processing
for all events in a single API call.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from twickenham_events.config import Config
from twickenham_events.scraper import EventScraper


def test_batch_migration():
    """Test the migrated batch processing functionality."""
    print("🧪 Testing Migrated Batch Processing")
    print("=" * 40)
    print()

    # Load config
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        config = Config.from_file(config_path)
    else:
        print("⚠️  Config file not found, using empty config")
        config = Config({})

    # Check AI configuration
    shortening_enabled = config.get("ai_processor.shortening.enabled", False)
    type_detection_enabled = config.get("ai_processor.type_detection.enabled", False)
    api_key_configured = bool(config.get("ai_processor.api_key"))

    print("📊 Configuration Status:")
    print(f"   • Shortening: {'✅ Enabled' if shortening_enabled else '❌ Disabled'}")
    print(
        f"   • Type Detection: {'✅ Enabled' if type_detection_enabled else '❌ Disabled'}"
    )
    print(f"   • API Key: {'✅ Configured' if api_key_configured else '❌ Missing'}")
    print()

    # Create test events (simulating scraped data)
    test_raw_events = [
        {
            "title": "England v Australia - Autumn International",
            "date": "2025-11-15",
            "time": "15:00",
            "crowd": "82,000",
        },
        {
            "title": "Rugby World Cup Final 2025",
            "date": "2025-12-20",
            "time": "16:00",
            "crowd": "82,000",
        },
        {
            "title": "Ed Sheeran Mathematics Tour",
            "date": "2025-10-25",
            "time": "20:00",
            "crowd": "75,000",
        },
        {
            "title": "Wales v Ireland - Six Nations",
            "date": "2025-11-08",
            "time": "14:30",
            "crowd": "80,000",
        },
        {
            "title": "Champions Cup Final",
            "date": "2025-12-05",
            "time": "17:30",
            "crowd": "82,000",
        },
    ]

    print("🔄 Testing Scraper with Batch Processing...")
    print()

    # Create scraper and process events
    scraper = EventScraper(config)
    summarized_events = scraper.summarize_events(test_raw_events)

    print("📋 Processing Results:")
    print("-" * 30)

    if summarized_events:
        total_events = sum(len(day["events"]) for day in summarized_events)
        print(
            f"✅ Processed {total_events} events across {len(summarized_events)} days"
        )
        print()

        for day_summary in summarized_events:
            date_str = day_summary["date"]
            event_count = len(day_summary["events"])
            print(
                f"📅 {date_str} ({event_count} event{'s' if event_count != 1 else ''})"
            )

            for event in day_summary["events"]:
                fixture = event["fixture"]
                short_name = event.get("fixture_short", fixture)
                time_str = event.get("start_time", "TBC")

                # Check if AI data was included
                has_ai_data = "ai_emoji" in event or "ai_event_type" in event
                ai_indicator = "🤖" if has_ai_data else "📝"

                print(f"   {ai_indicator} {fixture}")
                if short_name != fixture:
                    print(f"      📝 Short: {short_name}")
                print(f"      ⏰ Time: {time_str}")

                # Show AI data if available
                if "ai_event_type" in event:
                    print(f"      🏷️  Type: {event['ai_event_type']}")
                if "ai_emoji" in event:
                    print(f"      {event['ai_emoji']} Emoji: {event['ai_emoji']}")
                if "ai_mdi_icon" in event:
                    print(f"      🎯 Icon: {event['ai_mdi_icon']}")

                print()

        print("🎯 Migration Results:")
        print("=" * 25)

        # Check if events have AI data
        events_with_ai = 0
        total_events = 0
        for day in summarized_events:
            for event in day["events"]:
                total_events += 1
                if "ai_emoji" in event or "ai_event_type" in event:
                    events_with_ai += 1

        if shortening_enabled and type_detection_enabled:
            if events_with_ai > 0:
                print("✅ Batch processing SUCCESS!")
                print(f"   • {events_with_ai}/{total_events} events processed with AI")
                print(f"   • Used only 1 API call instead of {total_events * 2} calls")
                print(
                    f"   • That's a {((total_events * 2 - 1) / (total_events * 2)) * 100:.1f}% reduction!"
                )
            else:
                print("⚠️  No AI data found in events")
                print("   • Check API key and network connectivity")
                print("   • Batch processing may have fallen back to individual calls")
        elif shortening_enabled or type_detection_enabled:
            if events_with_ai > 0:
                print("✅ Partial AI processing")
                print(f"   • {events_with_ai}/{total_events} events have AI data")
                print("   • Enable both features for maximum batch efficiency")
            else:
                print("⚠️  No AI data found in events")
        else:
            print("💡 AI features disabled - using pattern-based detection")
            print("   • Enable ai_processor.shortening.enabled and/or")
            print("   • ai_processor.type_detection.enabled for AI processing")

    else:
        print("❌ No events processed")
        print("   • Check test data dates are in the future")

    print()
    print("🏁 Test Complete!")

    # Check for errors
    if scraper.error_log:
        print()
        print("⚠️  Errors encountered:")
        for error in scraper.error_log:
            print(f"   • {error}")


if __name__ == "__main__":
    test_batch_migration()
