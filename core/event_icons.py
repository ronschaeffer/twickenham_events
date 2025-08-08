#!/usr/bin/env python3
"""
Event emoji and icon assignment utility.

This module provides functionality to assign appropriate emojis and MDI icons
to events based on their names and characteristics.
"""


def get_event_emoji_and_icon(fixture_name: str) -> tuple[str, str]:
    """
    Determine emoji and MDI icon based on event/fixture name.

    Args:
        fixture_name (str): The name of the fixture/event

    Returns:
        tuple: (emoji, mdi_icon) where emoji is unicode and mdi_icon is Material Design Icon name
    """
    fixture_lower = fixture_name.lower()

    # International rugby teams for pattern matching
    rugby_countries = [
        "england",
        "wales",
        "scotland",
        "ireland",
        "france",
        "italy",
        "australia",
        "wallabies",
        "new zealand",
        "all blacks",
        "south africa",
        "springboks",
        "argentina",
        "fiji",
        "japan",
    ]

    # Check if it's an international rugby match (country vs country)
    country_mentions = sum(1 for country in rugby_countries if country in fixture_lower)
    is_vs_match = any(vs in fixture_lower for vs in [" v ", " vs ", " V "])

    # Major finals get trophy emoji first (before sport-specific emojis)
    # Only actual finals, not semi-finals, quarter-finals, etc.
    if any(
        phrase in fixture_lower
        for phrase in [
            "world cup final",
            "champions cup final",
            "championship final",
            "grand final",
            "cup final",
            "playoff final",
        ]
    ) or (
        fixture_lower.endswith(" final")
        and not any(prefix in fixture_lower for prefix in ["semi ", "quarter "])
    ):
        return "🏆", "mdi:trophy"

    # Rugby-specific patterns - use rugby ball emoji for regular rugby matches
    elif (
        any(word in fixture_lower for word in ["rugby", "six nations"])
        or (country_mentions >= 2 and is_vs_match)
        or any(
            word in fixture_lower
            for word in ["harlequins", "quins", "premiership", "union"]
        )
        or ("big game" in fixture_lower)  # Harlequins Big Game is a famous rugby event
        or
        # Only match semi/quarter finals if NOT football related
        (
            any(
                word in fixture_lower
                for word in [
                    "semi final",
                    "quarter final",
                    "semi-final",
                    "quarter-final",
                ]
            )
            and not any(
                word in fixture_lower
                for word in ["fa cup", "premier league", "soccer", "football"]
            )
        )
    ):  # Rugby tournament stages
        return "🏉", "mdi:rugby"

    # American Football (check before regular football to avoid conflicts)
    elif any(word in fixture_lower for word in ["nfl", "american football"]):
        return "🏈", "mdi:football-american"

    # Football/Soccer-specific patterns (but not American football)
    elif any(
        word in fixture_lower for word in ["soccer", "premier league", "fa cup"]
    ) or ("football" in fixture_lower and "american" not in fixture_lower):
        return "⚽", "mdi:soccer"

    # Concert/music patterns - be more specific to avoid false matches
    elif (
        any(word in fixture_lower for word in ["concert", "music", "band"])
        or any(
            phrase in fixture_lower
            for phrase in ["live tour", "music tour", "world tour"]
        )
        or (
            "live" in fixture_lower
            and any(word in fixture_lower for word in ["performance", "show"])
        )
    ):
        return "🎵", "mdi:music"

    # Default fallback
    else:
        return "📅", "mdi:calendar"


def get_emoji_character_count(text: str) -> int:
    """
    Count the display units of a string, counting emojis as 2 units each.

    Args:
        text (str): The text to count

    Returns:
        int: The number of display units
    """
    import unicodedata

    emoji_count = 0
    regular_chars = 0

    for char in text:
        # Check if character is an emoji using more comprehensive detection
        # This covers most emoji ranges including older ones like ⚽
        if (
            ord(char) >= 0x1F600  # Emoticons, symbols, and misc
            or ord(char) in range(0x2600, 0x27BF)  # Misc symbols including ⚽
            or ord(char) in range(0x1F300, 0x1F5FF)  # Misc symbols and pictographs
            or ord(char) in range(0x1F680, 0x1F6FF)  # Transport and map symbols
            or ord(char) in range(0x1F700, 0x1F77F)  # Alchemical symbols
            or ord(char) in range(0x1F780, 0x1F7FF)  # Geometric shapes extended
            or ord(char) in range(0x1F800, 0x1F8FF)  # Supplemental arrows C
            or ord(char)
            in range(0x1F900, 0x1F9FF)  # Supplemental symbols and pictographs
            or ord(char) in range(0x1FA00, 0x1FA6F)  # Chess symbols, etc
            or ord(char)
            in range(0x1FA70, 0x1FAFF)  # Symbols and pictographs extended A
            or unicodedata.category(char) == "So"  # Other symbols
        ):
            emoji_count += 1
        else:
            regular_chars += 1

    # Each emoji counts as 2 units, regular chars as 1 unit
    return regular_chars + (emoji_count * 2)


def get_event_with_emoji_length_check(
    fixture_name: str, short_name: str, max_length: int = 25
) -> tuple[str, str, str, bool]:
    """
    Get emoji, icon, and check if short_name + emoji fits within length limit.

    Args:
        fixture_name (str): The original fixture name
        short_name (str): The AI-shortened name
        max_length (int): Maximum allowed display units

    Returns:
        tuple: (emoji, icon, final_short_name, length_exceeded)
    """
    emoji, icon = get_event_emoji_and_icon(fixture_name)

    # Check if short_name + emoji exceeds limit
    test_string = short_name + emoji
    total_length = get_emoji_character_count(test_string)

    if total_length > max_length:
        # If it exceeds, don't include emoji in the short name
        return emoji, icon, short_name, True
    else:
        # If it fits, we could optionally add emoji to short name
        return emoji, icon, short_name, False
