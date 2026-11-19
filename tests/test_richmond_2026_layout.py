"""Regressions for the Nov 2026 Richmond page layout (no table caption, multi-day rows)."""

from unittest import mock

from bs4 import BeautifulSoup

import twickenham_events.scraper as scraper_mod
from twickenham_events.scraper import EventScraper

HTML = b"""
<html><body>
<p>Zone hours are <strong>11am to 11pm</strong> on event days.</p>
<table class="table"><tbody>
<tr><th><p>Date</p></th><th><p>Fixture</p></th><th><p>Kick off</p></th><th><p>Crowd</p></th></tr>
<tr><td><p>Saturday 21 November 2099</p></td><td><p>England v New Zealand</p></td><td><p>2.10pm</p></td><td><p>82,000</p></td></tr>
<tr><td><p>Friday 27, Saturday 28 and Sunday 29&nbsp;November 2099</p></td><td><p>Nations Cup Final weekend</p></td>
<td><p>Friday 27:&nbsp; 4.40pm and 8.10pm</p><p>Saturday 28: 1.10pm and 4.40pm</p><p>Sunday 29: 1.10pm and 4.40pm</p></td>
<td><p>82,000 each day on Saturday and Sunday</p><p>Friday attendance is TBC</p></td></tr>
</tbody></table>
<table class="table"><tbody><tr><th>Zone</th><th>Hours</th></tr><tr><td>R</td><td>x</td><td>y</td></tr></tbody></table>
</body></html>
"""


class _Cfg(dict):
    def get(self, key, default=None):
        return default


class _Resp:
    content = HTML

    def raise_for_status(self):
        pass


def _raw():
    sc = EventScraper(_Cfg())
    with mock.patch.object(scraper_mod.requests, "get", return_value=_Resp()):
        return sc, sc._fetch_events_single_attempt("http://example")


def test_uncaptioned_table_found_by_headers():
    soup = BeautifulSoup(HTML, "html.parser")
    assert len(EventScraper._find_event_tables(soup)) == 1


def test_multi_day_row_expands_with_per_day_times():
    sc, raw = _raw()
    assert [r["date"] for r in raw] == [
        "Saturday 21 November 2099",
        "27 November 2099",
        "28 November 2099",
        "29 November 2099",
    ]
    assert raw[1]["time"] == "4.40pm and 8.10pm"
    assert raw[2]["time"] == "1.10pm and 4.40pm"
    days = sc.summarize_events(raw)
    assert [d["date"] for d in days] == [
        "2099-11-21",
        "2099-11-27",
        "2099-11-28",
        "2099-11-29",
    ]
    assert [e["start_time"] for e in days[1]["events"]] == ["16:40", "20:10"]
    assert sc.error_log == []


def test_ranges_keep_single_event():
    sc = EventScraper(_Cfg())
    ev = {"date": "16/17 May 2099", "title": "x", "time": "3pm", "crowd": None}
    assert sc.expand_multi_day_event(ev) == [ev]
