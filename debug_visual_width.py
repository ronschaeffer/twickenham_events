#!/usr/bin/env python3
from core.event_shortener import calculate_visual_width
import sys
sys.path.append('.')

# Test cases with detailed breakdown
test_cases = [
    '🇳🇿 NZ v 🇦🇺 AUS',  # Expected 2 flags + 9 chars = 13
    '🇦🇷 ARG V 🇿🇦 RSA',  # Expected 2 flags + 11 chars = 15
]

for text in test_cases:
    width = calculate_visual_width(text)
    char_count = len(text)
    print(f'Text: "{text}"')
    print(f'  Length: {char_count} chars')
    print(f'  Visual width: {width} units')

    # Manual breakdown
    import re
    flag_pattern = r'[\U0001F1E6-\U0001F1FF][\U0001F1E6-\U0001F1FF]|\U0001F3F4[\U000E0060-\U000E007F]+'
    flags = re.findall(flag_pattern, text)
    text_without_flags = re.sub(flag_pattern, '', text)

    print(f'  Flags found: {len(flags)} -> {flags}')
    print(
        f'  Text without flags: "{text_without_flags}" ({len(text_without_flags)} chars)')
    print(
        f'  Expected: {len(flags)} * 2 + {len(text_without_flags)} = {len(flags) * 2 + len(text_without_flags)}')
    print()
