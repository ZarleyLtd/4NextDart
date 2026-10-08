"""End-to-end handler tests: synthetic Alexa envelopes -> Lambda handler -> speech, with a fake store."""
import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("NTA_API_KEY", "test-key")

from src.common import rt_cache
from src.common.gtfs_time import DUBLIN, parse_gtfs_time
from src.common.models import Departure, RealtimeFeed, StopTimeUpdate, StopTimetable, TripUpdate
from src.common.rt_cache import RealtimeCache
from src.common.stations import split_raw_platforms, build_station
from src.skill import app, service as service_mod
from src.skill.service import DartService

NOW = datetime(2026, 10, 6, 20, 6, tzinfo=DUBLIN)
USER = "amzn1.ask.account.TEST"
PEARSE_ID = "8220IR0134"


def pease_station():
    return build_station("Dublin Pearse", split_raw_platforms(
        PEARSE_ID, "8220", "Dublin Pearse",
        ["Howth", "Malahide", "Dublin Connolly", "Bray (Daly)", "Greystones", "Grand Canal Dock"],
    )).as_dict()


class FakeStore:
    def __init__(self):
        self.stops = {
            PEARSE_ID: StopTimetable(PEARSE_ID, "8220", "Dublin Pearse", [
                Departure("t1", "DART", "Howth", parse_gtfs_time("20:13:00"), "S1", 10),
                Departure("t2", "DART", "Malahide", parse_gtfs_time("20:15:00"), "S1", 12),
                Departure("t3", "DART", "Howth", parse_gtfs_time("20:40:00"), "S1", 10),
                Departure("t4", "DART", "Bray (Daly)", parse_gtfs_time("20:12:00"), "S1", 8),
                Departure("t5", "DART", "Greystones", parse_gtfs_time("20:18:00"), "S1", 9),
            ]),
        }
        self.stations = [pease_station()]
        self.calendar = {"20261005": {"S1"}, "20261006": {"S1"}}
        self.favourites = {}
        self.last_fetch = None

    def get_stations(self): return self.stations
    def get_calendar(self): return self.calendar
    def get_stop(self, stop_id): return self.stops.get(stop_id)
    def get_favourite(self, uid): return self.favourites.get(uid)
    def set_favourite(self, uid, stop_id, code, name, heads=None, label=""):
        self.favourites[uid] = {
            "stop_id": stop_id, "stop_code": code, "stop_name": name,
            "heads": heads or [], "label": label,
        }
    def try_acquire_rt_lock(self, now_epoch, min_interval=60):
        if self.last_fetch is None or self.last_fetch <= now_epoch - min_interval:
            self.last_fetch = now_epoch
            return True
        return False


def fake_feed(api_key, **kw):
    return RealtimeFeed(datetime.now(timezone.utc), None, {
        "t1": TripUpdate("t1", "r", "SCHEDULED",
                         [StopTimeUpdate(10, PEARSE_ID, None, None, 345, None, "SCHEDULED")]),
    })


@pytest.fixture(autouse=True)
def wired(monkeypatch):
    store = FakeStore()
    monkeypatch.setattr(rt_cache, "fetch_trip_updates", fake_feed)
    monkeypatch.setattr(service_mod, "now_dublin", lambda: NOW)
    monkeypatch.setattr(app, "_service", DartService(store, RealtimeCache(store, "k")))
    return store


def envelope(request: dict, session_attrs=None, new=True) -> dict:
    session = {
        "new": new, "sessionId": "s1",
        "application": {"applicationId": "amzn1.ask.skill.test"},
        "user": {"userId": USER},
    }
    if session_attrs:
        session["attributes"] = session_attrs
    return {
        "version": "1.0",
        "session": session,
        "context": {"System": {"application": {"applicationId": "amzn1.ask.skill.test"}, "user": {"userId": USER},
                               "device": {"deviceId": "d1", "supportedInterfaces": {}}}},
        "request": {"requestId": "r1", "timestamp": "2026-10-06T19:06:00Z", "locale": "en-GB", **request},
    }


def intent(name, *, session_attrs=None, new=True, **slots):
    return envelope({"type": "IntentRequest", "intent": {
        "name": name, "confirmationStatus": "NONE",
        "slots": {k: {"name": k, "value": v, "confirmationStatus": "NONE"} for k, v in slots.items()},
    }}, session_attrs=session_attrs, new=new)


def speech(resp: dict) -> str:
    return resp["response"]["outputSpeech"]["ssml"]


def test_next_dart_with_station_and_direction():
    resp = app.handler(intent("NextDartIntent", station="Pearse", direction="northbound"), None)
    text = speech(resp)
    assert "At Pearse:" in text
    assert "to Howth" in text
    assert "Bray" not in text
    assert resp["response"]["shouldEndSession"] is True


def test_next_dart_southbound():
    resp = app.handler(intent("NextDartIntent", station="Pearse", direction="southbound"), None)
    text = speech(resp)
    assert "At Pearse:" in text
    assert "to Bray" in text
    assert "Howth" not in text
    assert resp["response"]["shouldEndSession"] is True


def test_next_dart_to_bray():
    resp = app.handler(intent("NextDartIntent", station="Pearse", direction="to Bray"), None)
    text = speech(resp)
    assert "to Bray" in text
    assert "to Greystones" not in text
    assert resp["response"]["shouldEndSession"] is True


def test_next_dart_going_south():
    resp = app.handler(intent("NextDartIntent", station="Pearse", direction="going south"), None)
    text = speech(resp)
    assert "to Bray" in text
    assert resp["response"]["shouldEndSession"] is True


def test_next_dart_going_north_glued():
    resp = app.handler(intent("NextDartIntent", station="Pearse going north"), None)
    text = speech(resp)
    assert "to Howth" in text
    assert resp["response"]["shouldEndSession"] is True


def test_next_dart_direction_glued_to_station_slot():
    resp = app.handler(intent("NextDartIntent", station="Pearse southbound"), None)
    text = speech(resp)
    assert "to Bray" in text
    assert "Which direction" not in text
    assert resp["response"]["shouldEndSession"] is True


def test_slot_value_reads_slot_value_payload():
    event = envelope({"type": "IntentRequest", "intent": {
        "name": "NextDartIntent", "confirmationStatus": "NONE",
        "slots": {
            "station": {
                "name": "station", "confirmationStatus": "NONE",
                "slotValue": {"type": "Simple", "value": "Pearse southbound"},
            },
            "direction": {"name": "direction", "confirmationStatus": "NONE"},
        },
    }})
    resp = app.handler(event, None)
    assert "to Bray" in speech(resp)


def test_unknown_station():
    resp = app.handler(intent("NextDartIntent", station="Narnia"), None)
    assert "don't know a DART station called Narnia" in speech(resp)


def test_station_without_direction_elicits():
    resp = app.handler(intent("NextDartIntent", station="Pearse"), None)
    assert resp["response"]["shouldEndSession"] is False
    assert resp["response"]["directives"][0]["type"] == "Dialog.ElicitSlot"
    assert resp["response"]["directives"][0]["slotToElicit"] == "direction"
    assert "northbound" in speech(resp)


def test_bad_cardinal_elicits():
    resp = app.handler(intent("NextDartIntent", station="Pearse", direction="eastbound"), None)
    assert "doesn't have a eastbound platform" in speech(resp)
    assert resp["response"]["directives"][0]["slotToElicit"] == "direction"


def test_towards_the_city_at_pearse_is_ambiguous():
    resp = app.handler(intent("NextDartIntent", station="Pearse", direction="the city"), None)
    assert "ambiguous" in speech(resp).lower()


def test_query_intent_parses_station_and_direction():
    resp = app.handler(intent("NextDartQueryIntent", query="Pearse southbound"), None)
    text = speech(resp)
    assert "to Bray" in text
    assert resp["response"]["shouldEndSession"] is True


def test_next_dart_without_favourite_elicits_station():
    resp = app.handler(intent("NextDartIntent"), None)
    assert resp["response"]["shouldEndSession"] is False
    assert "didn't catch which station" in speech(resp)


def test_set_favourite_without_stop_keeps_session_open():
    resp = app.handler(intent("SetFavouriteStopIntent"), None)
    assert "Which stop should I save" in speech(resp)
    assert resp["response"]["shouldEndSession"] is False
    directives = resp["response"].get("directives") or []
    assert not any("ElicitSlot" in str(d.get("type", d)) for d in directives)
    assert (resp.get("sessionAttributes") or {}).get("pending_action") == "set_favourite"


def test_set_favourite_follow_up_glued_direction(wired):
    first = app.handler(intent("SetFavouriteStopIntent"), None)
    attrs = first.get("sessionAttributes") or {}
    resp = app.handler(
        intent("NextDartIntent", station="Pearse southbound", session_attrs=attrs, new=False),
        None,
    )
    assert "Your favourite stop is now Pearse, southbound" in speech(resp)
    assert wired.favourites[USER]["stop_id"] == PEARSE_ID
    assert "Bray (Daly)" in wired.favourites[USER]["heads"]
    assert "Howth" not in wired.favourites[USER]["heads"]


def test_set_favourite_station_then_south(wired):
    first = app.handler(intent("SetFavouriteStopIntent"), None)
    attrs = first.get("sessionAttributes") or {}
    second = app.handler(
        intent("NextDartIntent", station="Pearse", session_attrs=attrs, new=False),
        None,
    )
    assert "Which direction at Pearse" in speech(second)
    assert second["response"]["shouldEndSession"] is False
    directives = second["response"].get("directives") or []
    assert not any("ElicitSlot" in str(d.get("type", d)) for d in directives)
    attrs = second.get("sessionAttributes") or {}
    assert attrs.get("pending_station") == "Pearse"
    third = app.handler(
        intent("NextDartIntent", direction="south", session_attrs=attrs, new=False),
        None,
    )
    assert "Your favourite stop is now Pearse, southbound" in speech(third)
    assert "Bray (Daly)" in wired.favourites[USER]["heads"]


def test_set_favourite_follow_up_going_south(wired):
    first = app.handler(intent("SetFavouriteStopIntent"), None)
    attrs = first.get("sessionAttributes") or {}
    resp = app.handler(
        intent("NextDartIntent", station="Pearse", direction="going south",
               session_attrs=attrs, new=False),
        None,
    )
    assert "Your favourite stop is now Pearse, southbound" in speech(resp)
    assert "Bray (Daly)" in wired.favourites[USER]["heads"]


def test_set_favourite_follow_up_query_intent(wired):
    first = app.handler(intent("SetFavouriteStopIntent"), None)
    attrs = first.get("sessionAttributes") or {}
    resp = app.handler(
        intent("NextDartQueryIntent", query="Pearse going north", session_attrs=attrs, new=False),
        None,
    )
    assert "Your favourite stop is now Pearse, northbound" in speech(resp)
    assert "Howth" in wired.favourites[USER]["heads"]


def test_set_favourite_query_intent_one_shot(wired):
    resp = app.handler(intent("SetFavouriteQueryIntent", query="Pearse going south"), None)
    assert "Your favourite stop is now Pearse, southbound" in speech(resp)
    assert "Bray (Daly)" in wired.favourites[USER]["heads"]


def test_set_get_and_use_favourite():
    resp = app.handler(intent("SetFavouriteStopIntent", station="Pearse", direction="northbound"), None)
    assert "Your favourite stop is now Pearse, northbound" in speech(resp)
    resp = app.handler(intent("GetFavouriteStopIntent"), None)
    assert "Pearse, northbound" in speech(resp)
    resp = app.handler(intent("NextDartIntent"), None)
    assert "At Pearse:" in speech(resp)
    assert "to Howth" in speech(resp)
    assert "Bray" not in speech(resp)
    resp = app.handler(envelope({"type": "LaunchRequest"}), None)
    assert "At Pearse:" in speech(resp)


def test_launch_without_favourite_welcomes():
    resp = app.handler(envelope({"type": "LaunchRequest"}), None)
    assert "Welcome to four next dart" in speech(resp)
    assert resp["response"]["shouldEndSession"] is False


def test_help_stop_fallback():
    assert "set my favourite stop to" in speech(app.handler(intent("AMAZON.HelpIntent"), None))
    assert "Goodbye" in speech(app.handler(intent("AMAZON.StopIntent"), None))
    assert "didn't catch that" in speech(app.handler(intent("AMAZON.FallbackIntent"), None))


def test_timetable_not_loaded_is_graceful(wired):
    wired.stations = []
    resp = app.handler(intent("NextDartIntent", station="Pearse", direction="northbound"), None)
    assert "timetable isn't loaded yet" in speech(resp)


def test_skill_id_verification_accepts_any_listed_id(monkeypatch):
    monkeypatch.setattr(app.config, "SKILL_IDS", frozenset({"amzn1.ask.skill.other", "amzn1.ask.skill.test"}))
    assert "Goodbye" in speech(app.handler(intent("AMAZON.StopIntent"), None))


def test_skill_id_verification_rejects_unknown_id(monkeypatch):
    monkeypatch.setattr(app.config, "SKILL_IDS", frozenset({"amzn1.ask.skill.other"}))
    with pytest.raises(app.SkillIdVerificationError):
        app.handler(intent("AMAZON.StopIntent"), None)
