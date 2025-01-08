import re
from datetime import datetime
from typing import Optional, Dict, Tuple

def normalize_date_range(date_str: str) -> Optional[str]:
    """Normalize UK date formats to YYYY-MM-DD."""
    if not isinstance(date_str, str) or not date_str.strip():
        return None

    cleaned = date_str.strip()
    
    weekday_pattern = (r'^(Mon|Tue|Wed|Thu|Fri|Sat|Sun|'
                      r'Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|'
                      r'Weekend|Wknd)\s+')
    cleaned = re.sub(weekday_pattern, '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', cleaned, flags=re.IGNORECASE)
    
    if '/' in cleaned and not re.match(r'\d+/\d+/\d+', cleaned):
        parts = cleaned.split()
        if len(parts) >= 3:
            day = parts[0].split('/')[0]
            cleaned = f"{day} {' '.join(parts[1:])}"

    formats = [
        '%d %B %Y',      # 16 May 2025
        '%d %b %Y',      # 16 May 2025
        '%d-%b-%Y',      # 16-May-2025
        '%d-%b-%y',      # 16-May-25
        '%d/%m/%Y',      # 16/05/2025
        '%d/%m/%y',      # 16/05/25
        '%d-%m-%Y',      # 16-05-2025
        '%d-%m-%y',      # 16-05-25
        '%d.%m.%Y',      # 16.05.2025
        '%d.%m.%y',      # 16.05.25
        '%e %B %Y',      # single digit day
        '%e %b %Y',      # single digit day abbreviated month
        '%e-%b-%y',      # 7-May-25
        '%e/%m/%y',      # 7/5/25
        '%e.%m.%y'       # 7.5.25
    ]

    for fmt in formats:
        try:
            date_obj = datetime.strptime(cleaned, fmt)
            if '%y' in fmt:  # Handle 2-digit years
                if date_obj.year < 2000:
                    date_obj = date_obj.replace(year=date_obj.year + 100)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return None

def run_tests() -> Tuple[int, int]:
    """Run test suite with comprehensive cases."""
    test_cases: Dict[str, Optional[str]] = {
        # Full weekday names
        "Monday 1st December 2024": "2024-12-01",
        "Tuesday 2nd December 2024": "2024-12-02",
        "Wednesday 3rd December 2024": "2024-12-03",
        "Thursday 4th December 2024": "2024-12-04",
        "Friday 5th December 2024": "2024-12-05",
        "Saturday 6th December 2024": "2024-12-06",
        "Sunday 7th December 2024": "2024-12-07",
        
        # Abbreviated weekdays
        "Mon 8th Dec 2024": "2024-12-08",
        "Tue 9th Dec 2024": "2024-12-09",
        "Wed 10th Dec 2024": "2024-12-10",
        "Thu 11th Dec 2024": "2024-12-11",
        "Fri 12th Dec 2024": "2024-12-12",
        "Sat 13th Dec 2024": "2024-12-13",
        "Sun 14th Dec 2024": "2024-12-14",
        
        # Weekend ranges
        "Weekend 16/17 May 2025": "2025-05-16",
        "Wknd 23/24 May 2025": "2025-05-23",
        
        # UK date formats
        "7-Jan-25": "2025-01-07",
        "7/1/2025": "2025-01-07",
        "07-01-25": "2025-01-07",
        "07.01.2025": "2025-01-07",
        "7.1.25": "2025-01-07",
        "7-May-25": "2025-05-07",
        
        # Ordinal variations
        "1st May 2025": "2025-05-01",
        "2nd May 2025": "2025-05-02",
        "3rd May 2025": "2025-05-03",
        "4th May 2025": "2025-05-04",
        "21st June 2025": "2025-06-21",
        
        # With weekday prefixes
        "Mon 7-Jan-25": "2025-01-07",
        "Tuesday 07/01/2025": "2025-01-07",
        "Wed 7.1.25": "2025-01-07",
        
        # Edge cases
        "": None,
        "Invalid Date": None,
        "32/13/25": None,
        "Weekend": None,
        
        # Real examples
        "Saturday 2nd November 2024": "2024-11-02",
        "Sunday 24th November 2024": "2024-11-24",
        "Saturday 28th December 2024": "2024-12-28",
        "Saturday 8th February 2025": "2025-02-08",
        "Saturday 21st June 2025": "2025-06-21"
    }

    passed = total = 0
    print("\n=== Date Normalizer Test Suite ===")
    
    if not test_cases:
        print("No test cases defined!")
        return 0, 0
    
    for input_date, expected in test_cases.items():
        total += 1
        result = normalize_date_range(input_date)
        success = result == expected
        passed += int(success)
        print(f"{'✓' if success else '✗'} {input_date or '(empty)'}")

    return passed, total

if __name__ == "__main__":
    passed, total = run_tests()
    if total > 0:
        print(f"\nTests Passed: {passed}/{total} ({passed/total*100:.1f}%)\n")
    else:
        print("\nNo tests were run!\n")