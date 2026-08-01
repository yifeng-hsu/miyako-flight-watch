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
