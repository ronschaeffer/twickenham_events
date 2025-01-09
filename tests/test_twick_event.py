import sys
from pathlib import Path
import pytest
from datetime import datetime, timedelta
import yaml

sys.path.append(str(Path(__file__).parent.parent))

from core.twick_event import normalize_date_range, normalize_time, validate_crowd_size, extract_date_range

# Update the test cases for date ranges
@pytest.mark.parametrize("input_date,expected_dates", [
    # Single date cases remain the same
    ("16 May 2025", ["2025-05-16"]),
    ("Mon 16 May 2025", ["2025-05-16"]),
    ("16th May 2025", ["2025-05-16"]),
    
    # Date range cases now expect list of two dates
    ("16/17 May 2025", ["2025-05-16", "2025-05-17"]),
    ("Weekend 16/17 May 2025", ["2025-05-16", "2025-05-17"]),
    ("Wknd 23/24 May 2025", ["2025-05-23", "2025-05-24"]),
    
    # Invalid cases
    ("Invalid Date", []),
    ("", []),
    (None, []),
])
def test_date_range_extraction(input_date, expected_dates):
    """Test the extract_date_range function with various inputs."""
    result = extract_date_range(input_date)
    assert result == expected_dates

@pytest.mark.parametrize("input_date,expected_date", [
    # Keep existing single date test cases
    ("16 May 2025", "2025-05-16"),
    ("Mon 16 May 2025", "2025-05-16"),
    ("16th May 2025", "2025-05-16"),
    ("01 January 2023", "2023-01-01"),
    ("31 December 2023", "2023-12-31"),
    ("29 February 2024", "2024-02-29"),  # Leap year
    ("30 Feb 2023", None),  # Invalid date
    ("15-08-2023", "2023-08-15"),
    ("15/08/2023", "2023-08-15"),
    ("15.08.2023", "2023-08-15"),
    ("15-Aug-2023", "2023-08-15"),
    ("15-Aug-23", "2023-08-15"),
    ("15/08/23", "2023-08-15"),
    ("15.08.23", "2023-08-15"),
    ("15-08-23", "2023-08-15"),
    ("15th August 2023", "2023-08-15"),
    ("15th Aug 2023", "2023-08-15"),
    ("15th Aug 23", "2023-08-15"),
    ("15th August 23", "2023-08-15"),
    ("Invalid Date", None),
    ("Monday 1st December 2024", "2024-12-01"),
    ("Tuesday 2nd December 2024", "2024-12-02"),
    ("Wednesday 3rd December 2024", "2024-12-03"),
    ("Thursday 4th December 2024", "2024-12-04"),
    ("Friday 5th December 2024", "2024-12-05"),
    ("Saturday 6th December 2024", "2024-12-06"),
    ("Sunday 7th December 2024", "2024-12-07"),
    ("Mon 8th Dec 2024", "2024-12-08"),
    ("Tue 9th Dec 2024", "2024-12-09"),
    ("Wed 10th Dec 2024", "2024-12-10"),
    ("Thu 11th Dec 2024", "2024-12-11"),
    ("Fri 12th Dec 2024", "2024-12-12"),
    ("Sat 13th Dec 2024", "2024-12-13"),
    ("Sun 14th Dec 2024", "2024-12-14"),
    ("7-Jan-25", "2025-01-07"),
    ("7/1/2025", "2025-01-07"),
    ("07-01-25", "2025-01-07"),
    ("07.01.2025", "2025-01-07"),
    ("7.1.25", "2025-01-07"),
    ("7-May-25", "2025-05-07"),
    ("1st May 2025", "2025-05-01"),
    ("2nd May 2025", "2025-05-02"),
    ("3rd May 2025", "2025-05-03"),
    ("4th May 2025", "2025-05-04"),
    ("21st June 2025", "2025-06-21"),
    ("Mon 7-Jan-25", "2025-01-07"),
    ("Tuesday 07/01/2025", "2025-01-07"),
    ("Wed 7.1.25", "2025-01-07"),
    ("", None),
    ("32/13/25", None),
    ("Weekend", None),
    ("Saturday 2nd November 2024", "2024-11-02"),
    ("Sunday 24th November 2024", "2024-11-24"),
    ("Saturday 28th December 2024", "2024-12-28"),
    ("Saturday 8th February 2025", "2025-02-08"),
    ("Saturday 21st June 2025", "2025-06-21"),
])
def test_normalize_date_range(input_date, expected_date):
    """Test the normalize_date_range function for single dates only."""
    result = normalize_date_range(input_date)
    assert result == expected_date

@pytest.mark.parametrize("input_time, expected", [
    ("3pm", "15:00"),
    ("3:30pm", "15:30"),
    ("3 & 5pm", "15:00 & 17:00"),
    ("TBC", None),
    ("3:10pm", "15:10"),
    ("3.10pm", "15:10"),
    ("11am", "11:00"),
    ("12pm", "12:00"),
    ("12am", "00:00"),
    ("15:10", "15:10"),
    ("03:10", "03:10"),
    ("00:00", "00:00"),
    ("3pm & 6pm", "15:00 & 18:00"),
    ("3:10pm & 5:40pm", "15:10 & 17:40"),
    ("3.10pm & 5.40pm", "15:10 & 17:40"),
    ("tbc", None),
    ("", None),
    ("Invalid", None),
    ("25:00", None),
    ("13pm", None),
    ("3pm and 6pm", "15:00 & 18:00"),  # Changed expected value
    ("5.40pm", "17:40"),
    ("4.10pm", "16:10"),
    ("4.45pm", "16:45"),
])
def test_normalize_time(input_time, expected):
    assert normalize_time(input_time) == expected

@pytest.mark.parametrize("input_crowd, expected", [
    ("10,000", "10,000"),
    ("10000", "10,000"),
    ("TBC", None),
    ("Estimate 10000", "10,000"),
    ("Est. 10000", "10,000"),
    ("Approx. 10000", "10,000"),
    ("~10000", "10,000"),
    ("Invalid", None),
])
def test_validate_crowd_size(input_crowd, expected):
    assert validate_crowd_size(input_crowd) == expected

# Add new test class for event duration calculations
class TestEventDuration:
    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a temporary config file for testing."""
        config_content = {
            'default_duration': 6
        }
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_content, f)
        return str(config_file)

    def test_end_time_calculation(self, mock_config):
        """Test that end times are correctly calculated based on config duration."""
        from core.config import Config
        from core.twick_event import normalize_time
        
        config = Config(mock_config)
        
        test_cases = [
            ("15:00", "21:00"),  # Simple 6-hour duration
            ("3pm", "21:00"),    # PM time
            ("9:30", "15:30"),   # With minutes
            ("23:00", "05:00"),  # Crossing midnight
            ("3pm & 6pm", "21:00 & 00:00"),  # Multiple times
        ]

        for start_time, expected_end in test_cases:
            # First normalize the time
            normalized_start = normalize_time(start_time)
            # Calculate end times
            end_times = []
            for time in normalized_start.split(' & '):
                start = datetime.strptime(time, '%H:%M')
                end = start + timedelta(hours=config.default_duration)
                end_times.append(end.strftime('%H:%M'))
            calculated_end = ' & '.join(end_times)
            assert calculated_end == expected_end

    def test_invalid_duration_config(self, tmp_path):
        """Test handling of missing or invalid duration configuration."""
        from core.config import Config
        
        # Test with missing duration
        config_file = tmp_path / "bad_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump({}, f)
        
        with pytest.raises(AttributeError) as exc_info:
            config = Config(str(config_file))
            _ = config.default_duration
        
        assert "Configuration key 'default_duration' not found" in str(exc_info.value)

def test_adjust_end_times():
    """Test that event end times are adjusted to prevent overlaps."""
    from core.twick_event import adjust_end_times
    
    # Test cases for overlapping events - all on same date
    events = [
        {
            'date': '2025-02-08',
            'fixture': 'Event 1',
            'start_time': '14:00',
            'end_time': '20:00',  # Would overlap with next event
            'crowd': '10,000'
        },
        {
            'date': '2025-02-08',
            'fixture': 'Event 2',
            'start_time': '19:00',
            'end_time': '23:00',
            'crowd': '10,000'
        }
    ]
    
    adjusted = adjust_end_times(events)
    
    # Check that end times were adjusted properly
    assert len(adjusted) == 2
    assert adjusted[0]['end_time'] == '19:00'  # First event shortened to start of second event
    assert adjusted[1]['end_time'] == '23:00'  # Last event remains unchanged

    # Test multiple times per event
    events = [
        {
            'date': '2025-02-08',
            'fixture': 'Event 1',
            'start_time': '14:00 & 16:00',
            'end_time': '20:00 & 22:00',  # Both would overlap with next event
            'crowd': '10,000'
        },
        {
            'date': '2025-02-08',
            'fixture': 'Event 2',
            'start_time': '19:00',
            'end_time': '23:00',
            'crowd': '10,000'
        }
    ]
    
    adjusted = adjust_end_times(events)
    assert adjusted[0]['end_time'] == '19:00 & 19:00'  # Both end times adjusted to next event's start
