from datetime import datetime, timedelta

from src.common.gtfs_time import DUBLIN
from src.common.models import Prediction
from src.common.speech import humanise, next_trains_speech

NOW = datetime(2026, 10, 6, 20, 0, tzinfo=DUBLIN)


def pred(route, head, mins, realtime=True):
    when = NOW + timedelta(minutes=mins)
    return Prediction(route, head, when, when, realtime, 0, f"t-{route}-{mins}")


def test_humanise_expands_abbreviations():
    assert humanise("Fairfield Rd") == "Fairfield Road"


def test_speech_lists_trains_without_route_names():
    text = next_trains_speech(
        "Pearse",
        [pred("DART", "Bray (Daly)", 4), pred("DART", "Greystones", 7)],
        NOW,
    )
    assert text == "At Pearse: Train in 4 minutes to Bray, then in 7 minutes to Greystones."
    assert "DART" not in text


def test_minutes_round_half_up_not_truncate():
    p = pred("DART", "Greystones", 0)
    p.predicted = NOW + timedelta(seconds=29)
    assert p.minutes_from(NOW) == 0
    p.predicted = NOW + timedelta(seconds=30)
    assert p.minutes_from(NOW) == 1
    p.predicted = NOW + timedelta(minutes=18, seconds=50)
    assert p.minutes_from(NOW) == 19
    assert next_trains_speech("Blackrock", [p], NOW) == "At Blackrock: Train in 19 minutes to Greystones."


def test_speech_due_now_and_scheduled():
    text = next_trains_speech("X", [pred("DART", "Howth", 0), pred("DART", "Howth", 12, realtime=False)], NOW)
    assert text == "At X: Train due now to Howth, then scheduled in 12 minutes."


def test_speech_omits_repeated_destination():
    text = next_trains_speech(
        "Blackrock, southbound towards Bray",
        [
            pred("DART", "Bray (Daly)", 12),
            pred("DART", "Bray (Daly)", 27, realtime=False),
            pred("DART", "Bray (Daly)", 42, realtime=False),
        ],
        NOW,
    )
    assert text == (
        "At Blackrock, southbound towards Bray: Train in 12 minutes to Bray, "
        "then scheduled in 27 minutes, then scheduled in 42 minutes."
    )


def test_speech_names_destination_when_it_changes_again():
    text = next_trains_speech(
        "Howth Junction",
        [
            pred("DART", "Howth", 4),
            pred("DART", "Malahide", 9),
            pred("DART", "Malahide", 14),
        ],
        NOW,
    )
    assert text == "At Howth Junction: Train in 4 minutes to Howth, then in 9 minutes to Malahide, then in 14 minutes."


def test_speech_empty_and_no_realtime():
    assert next_trains_speech("Pearse", [], NOW).startswith("I can't find any DART trains due at Pearse")
    text = next_trains_speech("X", [pred("DART", "Howth", 3, realtime=False)], NOW, realtime_available=False)
    assert text.startswith("At X: Train scheduled in 3 minutes to Howth.")
    assert text.endswith("Live times are unavailable right now, so these are timetable times.")
