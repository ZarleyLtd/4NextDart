"""Build skill-package/interactionModels/custom/en-GB.json from the DART station catalog.

Uses a local GTFS extract if present (.cache/gtfs), otherwise a fallback list of
spoken names so the file can still be regenerated.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.stations import LINE_ORDER, Station, alexa_direction_values, alexa_station_values, spoken_name

OUT = ROOT / "skill-package" / "interactionModels" / "custom" / "en-GB.json"

FALLBACK_GTFS_NAMES = list(LINE_ORDER)

NEXT_SAMPLES = [
    "from {station} {direction}",
    "from {station} towards {direction}",
    "from {station} toward {direction}",
    "from {station} to {direction}",
    "{station} towards {direction}",
    "{station} to {direction}",
    "{direction} from {station}",
    "{station} {direction}",
    "{direction}",
    "to get trains from {station} {direction}",
    "to get the next train from {station} {direction}",
    "to get the next dart from {station} {direction}",
    "trains from {station} {direction}",
    "dart from {station} {direction}",
    "the next train from {station} {direction}",
    "the next dart from {station} {direction}",
    "when is the next train from {station} {direction}",
    "when is the next dart from {station} {direction}",
    "what's the next train from {station} {direction}",
    "next train from {station} {direction}",
    "next dart from {station} {direction}",
    "from {station} going {direction}",
    "from {station} heading {direction}",
    "{station} going {direction}",
    "{station} heading {direction}",
    "from station {station} {direction}",
    "next train",
    "next trains",
    "next dart",
    "the next train",
    "the next dart",
    "for the next train",
    "for the next dart",
    "when is the next train",
    "when is my next train",
    "what's the next train",
    "what time is the next train",
    "from my favourite stop",
    "from my stop",
    "for my stop",
    "trains from my favourite stop",
    "the next train from my favourite stop",
]

QUERY_SAMPLES = [
    "for {query}",
    "from {query}",
    "about {query}",
    "trains from {query}",
    "dart from {query}",
    "the next train from {query}",
    "the next dart from {query}",
    "next train from {query}",
    "from station {query}",
    "to get trains from {query}",
]

SET_SAMPLES = [
    "to set my favourite stop to {station}",
    "set my favourite stop to {station}",
    "set my favourite stop to {station} {direction}",
    "set favourite stop {station} {direction}",
    "set my favourite stop",
    "to set my favourite stop",
    "to set my favorite stop",
    "set my favorite stop",
    "change my favourite stop to {station}",
    "to change my favourite stop to {station}",
    "change my favourite stop to {station} {direction}",
    "make {station} my favourite stop",
    "make {station} {direction} my favourite",
    "remember {station}",
    "to remember {station} {direction}",
    "save {station}",
    "to save {station} as my favourite",
    "my stop is {station}",
    "my stop is {station} {direction}",
    "to set my favorite stop to {station}",
    "set my favorite stop to {station}",
    "to set my favourite stop to {station} {direction}",
    "to set my favorite stop to {station} {direction}",
]

SET_QUERY_SAMPLES = [
    "to set my favourite stop to {query}",
    "set my favourite stop to {query}",
    "to set my favorite stop to {query}",
    "set my favorite stop to {query}",
    "remember {query}",
    "to remember {query}",
]

GET_SAMPLES = [
    "for my favourite stop",
    "what is my favourite stop",
    "what's my favourite stop",
    "which stop is my favourite",
    "to remind me of my favourite stop",
    "what stop is saved",
    "for my favorite stop",
    "what is my favorite stop",
]


def load_stations() -> list[Station]:
    path = ROOT / ".cache" / "gtfs"
    if (path / "stops.txt").exists() and (path / "stop_times.txt").exists():
        from ingest.gtfs_static import GtfsStatic
        gtfs = GtfsStatic(path)
        rows = gtfs.station_catalog()
        print(f"catalog from {path}: {len(rows)} stations")
        return [Station.from_dict(r) for r in rows]
    print("no GTFS cache; using fallback station names")
    return [Station(name=n, spoken=spoken_name(n), city_centre=False, platforms=[]) for n in FALLBACK_GTFS_NAMES]


def main() -> None:
    stations = load_stations()
    model = {
        "interactionModel": {
            "languageModel": {
                "invocationName": "four next dart",
                "intents": [
                    {
                        "name": "NextDartIntent",
                        "slots": [
                            {"name": "station", "type": "DART_STATION"},
                            {"name": "direction", "type": "DART_DIRECTION"},
                        ],
                        "samples": NEXT_SAMPLES,
                    },
                    {
                        "name": "NextDartQueryIntent",
                        "slots": [
                            {"name": "query", "type": "AMAZON.SearchQuery"},
                        ],
                        "samples": QUERY_SAMPLES,
                    },
                    {
                        "name": "SetFavouriteStopIntent",
                        "slots": [
                            {"name": "station", "type": "DART_STATION"},
                            {"name": "direction", "type": "DART_DIRECTION"},
                        ],
                        "samples": SET_SAMPLES,
                    },
                    {
                        "name": "SetFavouriteQueryIntent",
                        "slots": [
                            {"name": "query", "type": "AMAZON.SearchQuery"},
                        ],
                        "samples": SET_QUERY_SAMPLES,
                    },
                    {"name": "GetFavouriteStopIntent", "slots": [], "samples": GET_SAMPLES},
                    {"name": "AMAZON.HelpIntent", "samples": []},
                    {"name": "AMAZON.StopIntent", "samples": []},
                    {"name": "AMAZON.CancelIntent", "samples": []},
                    {"name": "AMAZON.FallbackIntent", "samples": []},
                    {"name": "AMAZON.NavigateHomeIntent", "samples": []},
                ],
                "types": [
                    {"name": "DART_STATION", "values": alexa_station_values(stations)},
                    {"name": "DART_DIRECTION", "values": alexa_direction_values()},
                ],
            },
            "dialog": {
                "intents": [
                    {
                        "name": "NextDartIntent",
                        "confirmationRequired": False,
                        "prompts": {},
                        "slots": [
                            {
                                "name": "station", "type": "DART_STATION",
                                "confirmationRequired": False, "elicitationRequired": False,
                                "prompts": {"elicitation": "Elicit.Slot.station"},
                            },
                            {
                                "name": "direction", "type": "DART_DIRECTION",
                                "confirmationRequired": False, "elicitationRequired": False,
                                "prompts": {"elicitation": "Elicit.Slot.direction"},
                            },
                        ],
                    },
                    {
                        "name": "SetFavouriteStopIntent",
                        "confirmationRequired": False,
                        "prompts": {},
                        "slots": [
                            {
                                "name": "station", "type": "DART_STATION",
                                "confirmationRequired": False, "elicitationRequired": False,
                                "prompts": {"elicitation": "Elicit.Slot.station"},
                            },
                            {
                                "name": "direction", "type": "DART_DIRECTION",
                                "confirmationRequired": False, "elicitationRequired": False,
                                "prompts": {"elicitation": "Elicit.Slot.direction"},
                            },
                        ],
                    },
                ],
                "delegationStrategy": "SKILL_RESPONSE",
            },
            "prompts": [
                {
                    "id": "Elicit.Slot.station",
                    "variations": [
                        {"type": "PlainText", "value": "Which DART station?"},
                        {"type": "PlainText", "value": "What's the name of the station?"},
                    ],
                },
                {
                    "id": "Elicit.Slot.direction",
                    "variations": [
                        {"type": "PlainText", "value": "Which direction?"},
                        {"type": "PlainText", "value": "Northbound, southbound, towards the city, or towards Howth, Malahide, Bray, or Greystones?"},
                    ],
                },
            ],
        }
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(stations)} stations)")


if __name__ == "__main__":
    main()
