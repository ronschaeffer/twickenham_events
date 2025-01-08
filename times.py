import re
from datetime import datetime
from typing import Optional, Dict, Tuple

def normalize_time(time_str: str) -> Optional[str]:
    """Normalize time strings to 24-hour format HH:mm."""
    if not isinstance(time_str, str) or not time_str.strip():
        return None
        
    if time_str.lower() == 'tbc':
        return None

    # Check if already in 24-hour format
    if re.match(r'^([0-1][0-9]|2[0-3]):[0-5][0-9]$', time_str):
        return time_str

    # Replace periods with colons and normalize spaces
    cleaned = time_str.replace('.', ':').strip()
    
    # Handle multiple times
    if ' & ' in cleaned:
        parts = [part.strip() for part in cleaned.split(' & ')]
        converted = []
        for part in parts:
            norm = convert_single_time(part)
            if norm:
                converted.append(norm)
        return ' & '.join(converted) if converted else None
    
    return convert_single_time(cleaned)

def convert_single_time(time_str: str) -> Optional[str]:
    """Convert a single time string to 24-hour format."""
    # Add :00 if no minutes specified
    if re.match(r'^\d{1,2}(am|pm)$', time_str.lower()):
        time_str = time_str.replace('pm', ':00pm').replace('am', ':00am')
    
    try:
        return datetime.strptime(time_str, '%I:%M%p').strftime('%H:%M')
    except ValueError:
        return None

def run_tests() -> Tuple[int, int]:
    """Run test suite with comprehensive cases."""
    test_cases: Dict[str, Optional[str]] = {
        # 12-hour format
        "3:10pm": "15:10",
        "3.10pm": "15:10",
        "3pm": "15:00",
        "11am": "11:00",
        "12pm": "12:00",
        "12am": "00:00",
        
        # 24-hour format
        "15:10": "15:10",
        "03:10": "03:10",
        "00:00": "00:00",
        
        # Multiple times
        "3pm & 6pm": "15:00 & 18:00",
        "3:10pm & 5:40pm": "15:10 & 17:40",
        "3.10pm & 5.40pm": "15:10 & 17:40",
        
        # Edge cases
        "TBC": None,
        "tbc": None,
        "": None,
        "Invalid": None,
        "25:00": None,
        "13pm": None,
        
        # Real examples
        "3.10pm": "15:10",
        "5.40pm": "17:40",
        "4.10pm": "16:10",
        "3pm and 6pm": None,  # Invalid format
        "4.45pm": "16:45",
        "3pm": "15:00"
    }

    passed = total = 0
    print("\n=== Time Normalizer Test Suite ===")
    
    for input_time, expected in test_cases.items():
        total += 1
        result = normalize_time(input_time)
        success = result == expected
        passed += int(success)
        status = "✓" if success else "✗"
        print(f"{status} {input_time or '(empty)'}: {result or 'None'}")

    return passed, total

if __name__ == "__main__":
    passed, total = run_tests()
    print(f"\nTests Passed: {passed}/{total} ({passed/total*100:.1f}%)\n")