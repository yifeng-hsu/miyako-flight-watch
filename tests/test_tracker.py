import tracker

from tracker import _all_flights, _is_nonstop, _price, _segment_summary


def test_helpers_parse_flight():
    payload = {
        "best_flights": [
            {
                "price": 42000,
                "flights": [
                    {
                        "airline": "STARLUX Airlines",
                        "flight_number": "JX 860",
                        "departure_airport": {"time": "2027-05-24 11:40"},
                        "arrival_airport": {"time": "2027-05-24 14:05"},
                    }
                ],
            }
        ]
    }
    item = _all_flights(payload)[0]
    summary = _segment_summary(item)
    assert _price(item) == 42000
    assert _is_nonstop(item)
    assert summary["airline"] == "STARLUX Airlines"
    assert summary["flight"] == "JX 860"


def test_search_ignores_connecting_return(monkeypatch):
    outbound = {
        "price": 42000,
        "departure_token": "outbound-token",
        "flights": [
            {
                "airline": "STARLUX Airlines",
                "flight_number": "JX 860",
                "departure_airport": {"time": "2027-05-24 11:40"},
                "arrival_airport": {"time": "2027-05-24 14:05"},
            }
        ],
    }
    connecting_return = {
        "price": 36000,
        "flights": [
            {"flight_number": "BC 618"},
            {"flight_number": "BC 511"},
        ],
        "layovers": [{"id": "OKA"}],
    }

    def fake_request(params, api_key):
        assert api_key == "test-key"
        if params.get("departure_token"):
            return {"best_flights": [connecting_return]}
        return {
            "best_flights": [outbound],
            "search_metadata": {"google_flights_url": "https://example.test/flights"},
        }

    monkeypatch.setattr(tracker, "_request", fake_request)
    record = tracker.search_itinerary(tracker.ITINERARIES[0], "test-key")

    assert record.status == "no_result"
    assert record.total_price_twd is None
    assert "直飛回程" in (record.error or "")


def test_search_uses_complete_direct_round_trip(monkeypatch):
    outbound = {
        "price": 44000,
        "departure_token": "outbound-token",
        "flights": [
            {
                "airline": "STARLUX Airlines",
                "flight_number": "JX 860",
                "departure_airport": {"time": "2027-05-24 11:40"},
                "arrival_airport": {"time": "2027-05-24 14:05"},
            }
        ],
    }
    direct_return = {
        "price": 40000,
        "flights": [
            {
                "airline": "STARLUX Airlines",
                "flight_number": "JX 861",
                "departure_airport": {"time": "2027-05-27 15:05"},
                "arrival_airport": {"time": "2027-05-27 15:35"},
            }
        ],
    }

    def fake_request(params, _api_key):
        if params.get("departure_token"):
            return {"best_flights": [direct_return]}
        return {"best_flights": [outbound]}

    monkeypatch.setattr(tracker, "_request", fake_request)
    record = tracker.search_itinerary(tracker.ITINERARIES[0], "test-key")

    assert record.status == "ok"
    assert record.total_price_twd == 40000
    assert record.per_person_twd == 10000
    assert record.outbound_flight == "JX 860"
    assert record.return_flight == "JX 861"
