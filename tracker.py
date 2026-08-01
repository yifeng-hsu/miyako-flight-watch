from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "docs" / "data"
DATA_FILE = DATA_DIR / "prices.json"
TPE_TZ = ZoneInfo("Asia/Taipei")
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
NO_RESULTS_TEXT = "目前沒有查到可售的直飛來回組合，可能尚未開賣。"

ORIGIN = "TPE"
DESTINATION = "SHI"
ADULTS = int(os.getenv("ADULTS", "4"))
TARGET_TOTAL_TWD = int(os.getenv("TARGET_TOTAL_TWD", "48000"))
DROP_ALERT_PERCENT = float(os.getenv("DROP_ALERT_PERCENT", "5"))

ITINERARIES = [
    {"label": "5/24－5/27", "departure_date": "2027-05-24", "return_date": "2027-05-27"},
    {"label": "5/25－5/28", "departure_date": "2027-05-25", "return_date": "2027-05-28"},
]


@dataclass
class PriceRecord:
    checked_at: str
    label: str
    origin: str
    destination: str
    departure_date: str
    return_date: str
    adults: int
    total_price_twd: int | None
    per_person_twd: int | None
    airline: str | None
    outbound_flight: str | None
    outbound_departure: str | None
    outbound_arrival: str | None
    return_flight: str | None
    return_departure: str | None
    return_arrival: str | None
    nonstop: bool | None
    price_level: str | None
    typical_low_twd: int | None
    typical_high_twd: int | None
    google_flights_url: str | None
    status: str
    error: str | None = None


def load_records() -> list[dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        records = payload if isinstance(payload, list) else []
        for record in records:
            if not isinstance(record, dict):
                continue
            if _is_no_results_error(record.get("error")):
                record["status"] = "no_result"
                record["error"] = NO_RESULTS_TEXT
        return records
    except (OSError, json.JSONDecodeError):
        return []


def save_records(records: list[dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _request(params: dict[str, Any], api_key: str) -> dict[str, Any]:
    request_params = {**params, "api_key": api_key}
    response = requests.get(SERPAPI_ENDPOINT, params=request_params, timeout=90)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        error = str(payload["error"])
        if _is_no_results_error(error):
            return {"best_flights": [], "other_flights": []}
        raise RuntimeError(error)
    return payload


def _is_no_results_error(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.lower()
    return (
        "hasn't returned any results" in normalized
        or "has not returned any results" in normalized
    )


def _all_flights(payload: dict[str, Any]) -> list[dict[str, Any]]:
    flights: list[dict[str, Any]] = []
    for key in ("best_flights", "other_flights"):
        value = payload.get(key)
        if isinstance(value, list):
            flights.extend(item for item in value if isinstance(item, dict))
    return flights


def _price(item: dict[str, Any]) -> int | None:
    value = item.get("price")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(round(value))
    if isinstance(value, str):
        digits = "".join(ch for ch in value if ch.isdigit())
        return int(digits) if digits else None
    return None


def _segment_summary(item: dict[str, Any]) -> dict[str, str | None]:
    segments = item.get("flights")
    if not isinstance(segments, list) or not segments:
        return {
            "airline": None,
            "flight": None,
            "departure": None,
            "arrival": None,
        }

    airlines: list[str] = []
    flight_numbers: list[str] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        airline = segment.get("airline")
        flight_number = segment.get("flight_number")
        if airline and str(airline) not in airlines:
            airlines.append(str(airline))
        if flight_number:
            flight_numbers.append(str(flight_number))

    first = segments[0] if isinstance(segments[0], dict) else {}
    last = segments[-1] if isinstance(segments[-1], dict) else {}
    departure = first.get("departure_airport") if isinstance(first.get("departure_airport"), dict) else {}
    arrival = last.get("arrival_airport") if isinstance(last.get("arrival_airport"), dict) else {}

    return {
        "airline": " / ".join(airlines) or None,
        "flight": " + ".join(flight_numbers) or None,
        "departure": departure.get("time"),
        "arrival": arrival.get("time"),
    }


def _is_nonstop(item: dict[str, Any]) -> bool:
    segments = item.get("flights")
    return isinstance(segments, list) and len(segments) == 1 and not item.get("layovers")


def _google_flights_url(payload: dict[str, Any]) -> str | None:
    metadata = payload.get("search_metadata")
    if not isinstance(metadata, dict):
        return None
    for key in ("google_flights_url", "raw_html_file"):
        value = metadata.get(key)
        if isinstance(value, str) and value.startswith("http"):
            return value
    return None


def _price_insights(payload: dict[str, Any]) -> tuple[str | None, int | None, int | None]:
    insights = payload.get("price_insights")
    if not isinstance(insights, dict):
        return None, None, None
    typical = insights.get("typical_price_range")
    low = high = None
    if isinstance(typical, list) and len(typical) >= 2:
        if isinstance(typical[0], (int, float)):
            low = int(round(typical[0]))
        if isinstance(typical[1], (int, float)):
            high = int(round(typical[1]))
    level = insights.get("price_level")
    return str(level) if level else None, low, high


def _return_options(
    base_params: dict[str, Any],
    outbound_candidates: Iterable[dict[str, Any]],
    api_key: str,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    combinations: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for outbound in list(outbound_candidates)[:2]:
        token = outbound.get("departure_token")
        if not token:
            continue
        payload = _request({**base_params, "departure_token": token}, api_key)
        return_candidates = sorted(
            (
                item
                for item in _all_flights(payload)
                if _price(item) is not None and _is_nonstop(item)
            ),
            key=lambda item: _price(item) or 10**12,
        )
        if return_candidates:
            combinations.append((outbound, return_candidates[0]))
    return combinations


def search_itinerary(itinerary: dict[str, str], api_key: str) -> PriceRecord:
    checked_at = datetime.now(TPE_TZ).replace(microsecond=0).isoformat()
    base_params: dict[str, Any] = {
        "engine": "google_flights",
        "departure_id": ORIGIN,
        "arrival_id": DESTINATION,
        "outbound_date": itinerary["departure_date"],
        "return_date": itinerary["return_date"],
        "currency": "TWD",
        "gl": "tw",
        "hl": "zh-TW",
        "type": "1",
        "travel_class": "1",
        "adults": ADULTS,
        "stops": "1",
        "sort_by": "2",
        "deep_search": "true",
        "no_cache": "true",
    }

    try:
        payload = _request(base_params, api_key)
        candidates = sorted(
            (
                item
                for item in _all_flights(payload)
                if _price(item) is not None and _is_nonstop(item)
            ),
            key=lambda item: _price(item) or 10**12,
        )

        if not candidates:
            return PriceRecord(
                checked_at=checked_at,
                label=itinerary["label"],
                origin=ORIGIN,
                destination=DESTINATION,
                departure_date=itinerary["departure_date"],
                return_date=itinerary["return_date"],
                adults=ADULTS,
                total_price_twd=None,
                per_person_twd=None,
                airline=None,
                outbound_flight=None,
                outbound_departure=None,
                outbound_arrival=None,
                return_flight=None,
                return_departure=None,
                return_arrival=None,
                nonstop=True,
                price_level=None,
                typical_low_twd=None,
                typical_high_twd=None,
                google_flights_url=_google_flights_url(payload),
                status="no_result",
                error=NO_RESULTS_TEXT,
            )

        combinations = _return_options(base_params, candidates, api_key)
        if not combinations:
            return PriceRecord(
                checked_at=checked_at,
                label=itinerary["label"],
                origin=ORIGIN,
                destination=DESTINATION,
                departure_date=itinerary["departure_date"],
                return_date=itinerary["return_date"],
                adults=ADULTS,
                total_price_twd=None,
                per_person_twd=None,
                airline=None,
                outbound_flight=None,
                outbound_departure=None,
                outbound_arrival=None,
                return_flight=None,
                return_departure=None,
                return_arrival=None,
                nonstop=True,
                price_level=None,
                typical_low_twd=None,
                typical_high_twd=None,
                google_flights_url=_google_flights_url(payload),
                status="no_result",
                error="查到直飛去程，但目前沒有可售的直飛回程組合。",
            )

        outbound, return_option = min(
            combinations,
            key=lambda pair: _price(pair[1]) or 10**12,
        )
        total_price = _price(return_option)
        return_summary = _segment_summary(return_option)

        outbound_summary = _segment_summary(outbound)
        price_level, typical_low, typical_high = _price_insights(payload)
        airlines = [
            value
            for value in (outbound_summary["airline"], return_summary["airline"])
            if value
        ]
        airline = " / ".join(dict.fromkeys(airlines)) or None
        per_person = round(total_price / ADULTS) if total_price is not None else None

        return PriceRecord(
            checked_at=checked_at,
            label=itinerary["label"],
            origin=ORIGIN,
            destination=DESTINATION,
            departure_date=itinerary["departure_date"],
            return_date=itinerary["return_date"],
            adults=ADULTS,
            total_price_twd=total_price,
            per_person_twd=per_person,
            airline=airline,
            outbound_flight=outbound_summary["flight"],
            outbound_departure=outbound_summary["departure"],
            outbound_arrival=outbound_summary["arrival"],
            return_flight=return_summary["flight"],
            return_departure=return_summary["departure"],
            return_arrival=return_summary["arrival"],
            nonstop=True,
            price_level=price_level,
            typical_low_twd=typical_low,
            typical_high_twd=typical_high,
            google_flights_url=_google_flights_url(payload),
            status="ok",
        )
    except Exception as exc:  # noqa: BLE001
        return PriceRecord(
            checked_at=checked_at,
            label=itinerary["label"],
            origin=ORIGIN,
            destination=DESTINATION,
            departure_date=itinerary["departure_date"],
            return_date=itinerary["return_date"],
            adults=ADULTS,
            total_price_twd=None,
            per_person_twd=None,
            airline=None,
            outbound_flight=None,
            outbound_departure=None,
            outbound_arrival=None,
            return_flight=None,
            return_departure=None,
            return_arrival=None,
            nonstop=None,
            price_level=None,
            typical_low_twd=None,
            typical_high_twd=None,
            google_flights_url=None,
            status="error",
            error=f"{type(exc).__name__}: {exc}",
        )


def _previous_valid(records: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    matches = [
        item
        for item in records
        if item.get("label") == label and isinstance(item.get("total_price_twd"), int)
    ]
    return matches[-1] if matches else None


def _historical_low(records: list[dict[str, Any]], label: str) -> int | None:
    values = [
        item["total_price_twd"]
        for item in records
        if item.get("label") == label and isinstance(item.get("total_price_twd"), int)
    ]
    return min(values) if values else None


def _notification_lines(
    old_records: list[dict[str, Any]], new_records: list[PriceRecord]
) -> list[str]:
    lines: list[str] = []
    for record in new_records:
        if record.status != "ok" or record.total_price_twd is None:
            continue
        previous = _previous_valid(old_records, record.label)
        historic_low = _historical_low(old_records, record.label)
        reasons: list[str] = []

        if previous is None:
            reasons.append("首次查到可售票價")
        else:
            previous_price = previous.get("total_price_twd")
            if isinstance(previous_price, int) and previous_price > 0:
                drop = (previous_price - record.total_price_twd) / previous_price * 100
                if drop >= DROP_ALERT_PERCENT:
                    reasons.append(f"較上次下降 {drop:.1f}%")

        if historic_low is None or record.total_price_twd < historic_low:
            reasons.append("刷新歷史低價")
        if record.total_price_twd <= TARGET_TOTAL_TWD:
            reasons.append(f"低於目標總價 NT${TARGET_TOTAL_TWD:,}")

        if reasons:
            lines.append(
                f"{record.label}｜{record.adults} 人總價 NT${record.total_price_twd:,}｜"
                f"每人約 NT${record.per_person_twd:,}｜{'、'.join(reasons)}"
            )
    return lines


def send_telegram(lines: list[str]) -> None:
    if not lines:
        return
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    text = "✈️ 宮古島機票價格提醒\n\n" + "\n".join(lines)
    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
        timeout=30,
    )
    response.raise_for_status()


def main() -> int:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("缺少 SERPAPI_KEY。請在環境變數或 GitHub Actions Secrets 設定。", file=sys.stderr)
        return 2

    old_records = load_records()
    new_records = [search_itinerary(itinerary, api_key) for itinerary in ITINERARIES]
    updated_records = old_records + [asdict(record) for record in new_records]
    save_records(updated_records)

    lines = _notification_lines(old_records, new_records)
    try:
        send_telegram(lines)
    except Exception as exc:  # noqa: BLE001
        print(f"Telegram 通知失敗：{exc}", file=sys.stderr)

    for record in new_records:
        if record.total_price_twd is None:
            print(f"{record.label}: {record.status} - {record.error}")
        else:
            print(
                f"{record.label}: NT${record.total_price_twd:,} total / "
                f"NT${record.per_person_twd:,} per person / {record.airline or '航空公司未標示'}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
