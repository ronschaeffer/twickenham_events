#!/usr/bin/env python3
import re
from core.event_shortener import calculate_visual_width
import sys
sys.path.append('.')

test_text = '🇳🇿 NZ v 🇦🇺 AUS'
print(f'Text: "{test_text}"')
print(f'Character count: {len(test_text)}')
width = calculate_visual_width(test_text)
print(f'Visual width: {width}')

# Let's debug the regex
flag_pattern = r'[\U0001F1E6-\U0001F1FF][\U0001F1E6-\U0001F1FF]|\U0001F3F4[\U000E0060-\U000E007F]+'
flags = re.findall(flag_pattern, test_text)
print(f'Flags found: {flags}')
print(f'Flag count: {len(flags)}')

text_without_flags = re.sub(flag_pattern, '', test_text)
print(f'Text without flags: "{text_without_flags}"')
print(f'Char count without flags: {len(text_without_flags)}')
