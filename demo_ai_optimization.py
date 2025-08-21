#!/usr/bin/env python3
"""
Demonstration of optimized AI processing using combined requests.

This shows how the new get_combined_ai_info() method can reduce API calls
from 2-3 calls per event down to 1 call per event.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from twickenham_events.ai_processor import AIProcessor
from twickenham_events.config import Config


def demo_api_optimization():
    """Demonstrate API call optimization."""
    # Sample events that would normally require multiple API calls
    events = [
        "England v Australia - Autumn International",
        "Rugby World Cup Final 2023",
        "Ed Sheeran Mathematics Tour",
        "Taylor Swift | The Eras Tour",
        "Harlequins vs Leicester Tigers",
        "Six Nations Championship Final",
    ]

    print("🚀 AI Processing Optimization Demo")
    print("=" * 50)
    print()

    # Load config
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        config = Config.from_file(config_path)
    else:
        print("⚠️  Config file not found, using empty config (fallback mode)")
        config = Config({})

    ai_processor = AIProcessor(config)

    # Check if AI features are enabled
    shortening_enabled = config.get("ai_processor.shortening.enabled", False)
    type_detection_enabled = config.get("ai_processor.type_detection.enabled", False)

    print("📊 Configuration:")
    print(f"   • Shortening enabled: {shortening_enabled}")
    print(f"   • Type detection enabled: {type_detection_enabled}")
    print(
        f"   • API key configured: {'Yes' if config.get('ai_processor.api_key') else 'No'}"
    )
    print()

    if not shortening_enabled and not type_detection_enabled:
        print("💡 To see the optimization benefits, enable AI features in config.yaml:")
        print("   ai_processor.shortening.enabled: true")
        print("   ai_processor.type_detection.enabled: true")
        print("   ai_processor.api_key: ${GEMINI_API_KEY}")
        print()

    print("🔄 Processing events...")
    print()

    total_api_calls_old = 0
    total_api_calls_new = 0

    for i, event in enumerate(events, 1):
        print(f"Event {i}: {event}")

        # Simulate OLD approach (separate API calls)
        print("   📊 OLD approach (separate calls):")
        if shortening_enabled:
            print("      • API call for shortening")
            total_api_calls_old += 1
        if type_detection_enabled:
            print("      • API call for type detection")
            total_api_calls_old += 1

        if not shortening_enabled and not type_detection_enabled:
            print("      • No API calls (features disabled)")

        # NEW approach (combined call)
        print("   ⚡ NEW approach (combined call):")
        result = ai_processor.get_combined_ai_info(event)

        if shortening_enabled and type_detection_enabled:
            print("      • Single API call for both shortening + type detection")
            if not result["had_error"]:
                total_api_calls_new += 1
        elif shortening_enabled or type_detection_enabled:
            print("      • Single API call (only one feature enabled)")
            if not result["had_error"]:
                total_api_calls_new += 1
        else:
            print("      • No API calls (using fallback patterns)")

        print("   📝 Results:")
        print(f"      • Short name: {result['short_name']}")
        print(f"      • Event type: {result['event_type']}")
        print(f"      • Emoji: {result['emoji']}")
        print(f"      • MDI icon: {result['mdi_icon']}")

        if result["had_error"]:
            print(f"      • ⚠️  Error: {result['error_message']}")

        print()

    # Summary
    print("📈 API Usage Summary:")
    print("=" * 30)
    print(f"Total events processed: {len(events)}")
    print(f"OLD approach API calls: {total_api_calls_old}")
    print(f"NEW approach API calls: {total_api_calls_new}")

    if total_api_calls_old > 0:
        savings = total_api_calls_old - total_api_calls_new
        percentage = (savings / total_api_calls_old) * 100
        print(f"API calls saved: {savings} ({percentage:.1f}% reduction)")
        print(f"Quota efficiency: {percentage:.1f}% improvement")
    else:
        print("No API calls made (features disabled or errors occurred)")

    print()
    print("💡 Benefits of combined approach:")
    print("   • Reduced API quota usage")
    print("   • Faster processing (fewer network calls)")
    print("   • Better rate limit compliance")
    print("   • Consistent results (same model, same call)")


if __name__ == "__main__":
    demo_api_optimization()
