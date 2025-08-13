from twickenham_events.flatten import flatten_with_date


def test_flatten_injects_date():
    summarized = [
        {
            "date": "2099-01-01",
            "events": [{"fixture": "Test Match", "start_time": "12:00"}],
        }
    ]
    flat = flatten_with_date(summarized)
    assert flat[0]["date"] == "2099-01-01"


def test_flatten_preserves_existing_date():
    summarized = [
        {
            "date": "2099-01-02",
            "events": [
                {"fixture": "With Date", "date": "2099-01-03", "start_time": "10:00"},
                {"fixture": "No Date", "start_time": "11:00"},
            ],
        }
    ]
    flat = flatten_with_date(summarized)
    assert any(e["date"] == "2099-01-03" and e["fixture"] == "With Date" for e in flat)
    assert any(e["date"] == "2099-01-02" and e["fixture"] == "No Date" for e in flat)
