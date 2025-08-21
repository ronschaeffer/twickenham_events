#!/usr/bin/env python3
"""
Ultimate AI Processing Optimization: Batch Processing Demo

This demonstrates the new get_batch_ai_info() method that processes
ALL events in a SINGLE API call instead of one call per event.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from twickenham_events.ai_processor import AIProcessor
from twickenham_events.config import Config


def demo_ultimate_optimization():
    """Demonstrate ultimate API call optimization with batch processing."""
    # Sample events that would normally require multiple API calls
    events = [
        "England v Australia - Autumn International",
        "Rugby World Cup Final 2023",
        "Ed Sheeran Mathematics Tour",
        "Taylor Swift | The Eras Tour",
        "Harlequins vs Leicester Tigers",
        "Six Nations Championship Final",
        "Coldplay Music of the Spheres Tour",
        "Wales v Ireland - Six Nations",
        "Champions Cup Final",
    ]

    print("🚀 ULTIMATE AI Processing Optimization Demo")
    print("=" * 55)
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

    print("🔄 Processing optimization comparison...")
    print()

    # Calculate API calls for different approaches
    event_count = len(events)

    print("📈 API Usage Comparison:")
    print("=" * 40)
    print(f"Total events to process: {event_count}")
    print()

    # OLD approach - individual API calls per event
    old_api_calls = 0
    if shortening_enabled and type_detection_enabled:
        old_api_calls = event_count * 2  # 2 calls per event
        print("❌ OLD approach (individual calls):")
        print(f"   • Shortening: {event_count} API calls")
        print(f"   • Type detection: {event_count} API calls")
        print(f"   • TOTAL: {old_api_calls} API calls")
    elif shortening_enabled or type_detection_enabled:
        old_api_calls = event_count  # 1 call per event
        print("❌ OLD approach (individual calls):")
        print(f"   • Single feature: {event_count} API calls")
        print(f"   • TOTAL: {old_api_calls} API calls")
    else:
        print("❌ OLD approach: No API calls (features disabled)")

    print()

    # COMBINED approach - one call per event
    combined_api_calls = 0
    if shortening_enabled and type_detection_enabled:
        combined_api_calls = event_count  # 1 call per event
        print("⚡ COMBINED approach (get_combined_ai_info):")
        print(f"   • Combined processing: {event_count} API calls")
        print(f"   • TOTAL: {combined_api_calls} API calls")
        if old_api_calls > 0:
            savings1 = old_api_calls - combined_api_calls
            percentage1 = (savings1 / old_api_calls) * 100
            print(f"   • Savings: {savings1} calls ({percentage1:.0f}% reduction)")
    elif shortening_enabled or type_detection_enabled:
        combined_api_calls = event_count
        print(
            f"⚡ COMBINED approach: {combined_api_calls} API calls (same as individual)"
        )
    else:
        print("⚡ COMBINED approach: No API calls (features disabled)")

    print()

    # ULTIMATE BATCH approach - ONE total API call
    batch_api_calls = 0
    if shortening_enabled and type_detection_enabled:
        batch_api_calls = 1  # Just 1 call for ALL events
        print("🎯 ULTIMATE BATCH approach (get_batch_ai_info):")
        print(f"   • Batch processing: 1 API call for ALL {event_count} events")
        print(f"   • TOTAL: {batch_api_calls} API call")
        if old_api_calls > 0:
            savings2 = old_api_calls - batch_api_calls
            percentage2 = (savings2 / old_api_calls) * 100
            print(
                f"   • Savings vs OLD: {savings2} calls ({percentage2:.1f}% reduction)"
            )
        if combined_api_calls > 0:
            savings3 = combined_api_calls - batch_api_calls
            percentage3 = (savings3 / combined_api_calls) * 100
            print(
                f"   • Savings vs COMBINED: {savings3} calls ({percentage3:.1f}% reduction)"
            )
    elif shortening_enabled or type_detection_enabled:
        batch_api_calls = 1
        print(f"🎯 ULTIMATE BATCH approach: {batch_api_calls} API call")
        if old_api_calls > 0:
            savings = old_api_calls - batch_api_calls
            percentage = (savings / old_api_calls) * 100
            print(f"   • Savings: {savings} calls ({percentage:.1f}% reduction)")
    else:
        print("🎯 ULTIMATE BATCH approach: No API calls (features disabled)")

    print()
    print("🧪 Testing batch processing...")
    print()

    # Test the batch method
    results = ai_processor.get_batch_ai_info(events)

    print("📋 Batch Processing Results:")
    print("-" * 40)
    for i, event in enumerate(events, 1):
        result = results[event]
        print(f"{i:2d}. {event}")
        print(f"    📝 Short: {result['short_name']}")
        print(f"    🏷️  Type: {result['event_type']} {result['emoji']}")
        print(f"    🎯 Icon: {result['mdi_icon']}")
        if result["had_error"]:
            print(f"    ⚠️  Error: {result['error_message']}")
        print()

    print("🎉 Ultimate Optimization Summary:")
    print("=" * 45)
    if old_api_calls > 0 and batch_api_calls == 1:
        total_savings = old_api_calls - batch_api_calls
        efficiency = (total_savings / old_api_calls) * 100
        print(f"🔥 Reduced from {old_api_calls} API calls to just 1!")
        print(f"📊 That's a {efficiency:.1f}% reduction in API usage")
        print(f"⚡ {event_count}x improvement in quota efficiency")
        print(f"🚀 {event_count}x faster processing (fewer network calls)")

        # Calculate quota impact
        print()
        print("💡 Quota Impact Examples:")
        print(
            f"   • Free tier (2 req/min): Process {event_count} events in 30 seconds instead of {old_api_calls // 2} minutes"
        )
        print("   • With rate limits: No more waiting between events")
        print("   • Batch processing: Consistent results for all events")
    else:
        print("Batch processing ready - enable AI features to see full benefits!")

    print()
    print("🎯 Integration Tips:")
    print("   1. Use batch processing during scraping for maximum efficiency")
    print("   2. Store results to avoid re-processing during display/MQTT")
    print("   3. Perfect for working within free tier quota limits")


if __name__ == "__main__":
    demo_ultimate_optimization()
