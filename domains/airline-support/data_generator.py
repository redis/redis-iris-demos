"""Generate sample data for the airline-support demo."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path

import openai
from dotenv import load_dotenv

from backend.app.core.domain_contract import GeneratedDataset

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUTPUT_DIR = ROOT / "output" / "airline-support"


def ts(dt: datetime) -> str:
    return dt.isoformat()


BASE_NOW = datetime.now(timezone.utc).replace(second=0, microsecond=0)


def fake_embedding(text: str) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(1536)]


def embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [fake_embedding(text) for text in texts]
    try:
        client = openai.OpenAI()
        response = client.embeddings.create(
            input=texts,
            model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
        return [item.embedding for item in response.data]
    except Exception:
        return [fake_embedding(text) for text in texts]


def write_jsonl(output_dir: Path, file_name: str, rows: list[dict[str, object]]) -> None:
    path = output_dir / file_name
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def update_env(key: str, value: str) -> None:
    env_path = ROOT / ".env"
    safe_value = f'"{value}"' if " " in value else value
    if not env_path.exists():
        env_path.write_text(f"{key}={safe_value}\n")
        return
    lines = env_path.read_text().splitlines()
    for index, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[index] = f"{key}={safe_value}"
            break
    else:
        lines.append(f"{key}={safe_value}")
    env_path.write_text("\n".join(lines) + "\n")


DEMO_PROFILE = {
    "customer_id": "AIRCUST_001",
    "profile_reference": "PROFILE-001",
    "display_name": "Mara Beck",
    "ticket_name_masked": "Bxxxxxxxxxxxxxxxxxxx",
    "loyalty_member_id_masked": "AM••••9532",
    "salutation": "Ms.",
    "birth_date": "1936-01-01",
    "gender": "F",
    "status_tier": "Senator",
    "preferred_language": "EN",
    "customer_program": "AuroraMiles",
    "customer_usage": "private",
    "enrollment_carrier": "Aurora Air",
    "service_permissions": {
        "operational_alerts": True,
        "self_service_rebooking": True,
        "priority_service_routing": True,
    },
    "cache_group_id": "senator_en",
    "email": "mara.beck@example.com",
}

CUSTOMER_PROFILES = [
    DEMO_PROFILE,
    {
        "customer_id": "AIRCUST_002",
        "profile_reference": "PROFILE-002",
        "display_name": "Lena Hartmann",
        "ticket_name_masked": "Hxxxxxxxxxxxxxxxxx",
        "loyalty_member_id_masked": "AM••••2104",
        "salutation": "Ms.",
        "birth_date": "1988-06-14",
        "gender": "F",
        "status_tier": "Senator",
        "preferred_language": "EN",
        "customer_program": "AuroraMiles",
        "customer_usage": "private",
        "enrollment_carrier": "Aurora Air",
        "service_permissions": {
            "operational_alerts": True,
            "self_service_rebooking": True,
            "priority_service_routing": True,
        },
        "cache_group_id": "senator_en",
        "email": "lena.hartmann@example.com",
    },
    {
        "customer_id": "AIRCUST_003",
        "profile_reference": "PROFILE-003",
        "display_name": "Jonas Klein",
        "ticket_name_masked": "Kxxxxxxxxxxxxxxx",
        "loyalty_member_id_masked": "AM••••8841",
        "salutation": "Mr.",
        "birth_date": "1979-02-28",
        "gender": "M",
        "status_tier": "Frequent",
        "preferred_language": "EN",
        "customer_program": "AuroraMiles",
        "customer_usage": "private",
        "enrollment_carrier": "Aurora Air",
        "service_permissions": {
            "operational_alerts": True,
            "self_service_rebooking": True,
            "priority_service_routing": False,
        },
        "cache_group_id": "frequent_en",
        "email": "jonas.klein@example.com",
    },
    {
        "customer_id": "AIRCUST_004",
        "profile_reference": "PROFILE-004",
        "display_name": "Sophie Laurent",
        "ticket_name_masked": "Lxxxxxxxxxxxxxxxx",
        "loyalty_member_id_masked": "AM••••6617",
        "salutation": "Ms.",
        "birth_date": "1991-11-09",
        "gender": "F",
        "status_tier": "Ambassador",
        "preferred_language": "EN",
        "customer_program": "AuroraMiles",
        "customer_usage": "private",
        "enrollment_carrier": "Aurora Air",
        "service_permissions": {
            "operational_alerts": True,
            "self_service_rebooking": True,
            "priority_service_routing": True,
        },
        "cache_group_id": "ambassador_en",
        "email": "sophie.laurent@example.com",
    },
]

FLAGSHIP_BOOKING_ID = "BOOK_001"
FLAGSHIP_LOCATOR = "ZX73QF"
STATUS_BOOKING_ID = "BOOK_002"

cancelled_departure = BASE_NOW + timedelta(hours=7)
cancelled_arrival = BASE_NOW + timedelta(hours=15)
updated_departure = BASE_NOW + timedelta(hours=11, minutes=20)
updated_arrival = BASE_NOW + timedelta(hours=19, minutes=10)
status_departure = BASE_NOW + timedelta(days=6, hours=4)
status_arrival = BASE_NOW + timedelta(days=6, hours=5, minutes=5)

BOOKINGS = [
    {
        "booking_id": FLAGSHIP_BOOKING_ID,
        "customer_id": DEMO_PROFILE["customer_id"],
        "booking_locator": FLAGSHIP_LOCATOR,
        "passenger_display_name": DEMO_PROFILE["display_name"],
        "trip_status": "disrupted_rebooked",
        "created_at": ts(BASE_NOW - timedelta(days=24)),
        "fare_family": "Economy Flex",
        "cabin": "Economy",
    },
    {
        "booking_id": STATUS_BOOKING_ID,
        "customer_id": DEMO_PROFILE["customer_id"],
        "booking_locator": "ZX19MP",
        "passenger_display_name": DEMO_PROFILE["display_name"],
        "trip_status": "confirmed",
        "created_at": ts(BASE_NOW - timedelta(days=8)),
        "fare_family": "Business Saver",
        "cabin": "Business",
    },
    {
        "booking_id": "BOOK_003",
        "customer_id": "AIRCUST_002",
        "booking_locator": "ZX55DV",
        "passenger_display_name": "Lena Hartmann",
        "trip_status": "confirmed",
        "created_at": ts(BASE_NOW - timedelta(days=12)),
        "fare_family": "Economy Classic",
        "cabin": "Economy",
    },
]

ITINERARY_SEGMENTS = [
    {
        "segment_id": "SEG_001",
        "booking_id": FLAGSHIP_BOOKING_ID,
        "segment_sequence": 1,
        "operating_flight_id": "OF_001",
        "flight_number": "ZX402",
        "segment_role": "original",
        "origin_airport": "FRA",
        "origin_city": "Frankfurt",
        "destination_airport": "JFK",
        "destination_city": "New York",
        "scheduled_departure": ts(cancelled_departure),
        "scheduled_arrival": ts(cancelled_arrival),
        "cabin": "Economy",
    },
    {
        "segment_id": "SEG_002",
        "booking_id": FLAGSHIP_BOOKING_ID,
        "segment_sequence": 1,
        "operating_flight_id": "OF_002",
        "flight_number": "ZX406",
        "segment_role": "updated",
        "origin_airport": "FRA",
        "origin_city": "Frankfurt",
        "destination_airport": "JFK",
        "destination_city": "New York",
        "scheduled_departure": ts(updated_departure),
        "scheduled_arrival": ts(updated_arrival),
        "cabin": "Economy",
    },
    {
        "segment_id": "SEG_003",
        "booking_id": STATUS_BOOKING_ID,
        "segment_sequence": 1,
        "operating_flight_id": "OF_003",
        "flight_number": "ZX018",
        "segment_role": "unaffected",
        "origin_airport": "FRA",
        "origin_city": "Frankfurt",
        "destination_airport": "HAM",
        "destination_city": "Hamburg",
        "scheduled_departure": ts(status_departure),
        "scheduled_arrival": ts(status_arrival),
        "cabin": "Business",
    },
    {
        "segment_id": "SEG_004",
        "booking_id": "BOOK_003",
        "segment_sequence": 1,
        "operating_flight_id": "OF_004",
        "flight_number": "ZX1872",
        "segment_role": "unaffected",
        "origin_airport": "MUC",
        "origin_city": "Munich",
        "destination_airport": "FCO",
        "destination_city": "Rome",
        "scheduled_departure": ts(BASE_NOW + timedelta(days=3, hours=3)),
        "scheduled_arrival": ts(BASE_NOW + timedelta(days=3, hours=4, minutes=25)),
        "cabin": "Economy",
    },
]

OPERATING_FLIGHTS = [
    {
        "operating_flight_id": "OF_001",
        "flight_number": "ZX402",
        "service_date": cancelled_departure.date().isoformat(),
        "origin_airport": "FRA",
        "destination_airport": "JFK",
        "scheduled_departure": ts(cancelled_departure),
        "estimated_departure": ts(cancelled_departure),
        "scheduled_arrival": ts(cancelled_arrival),
        "estimated_arrival": ts(cancelled_arrival),
        "operating_status": "cancelled",
        "terminal": "1",
        "gate": None,
        "status_source": "ops_control",
    },
    {
        "operating_flight_id": "OF_002",
        "flight_number": "ZX406",
        "service_date": updated_departure.date().isoformat(),
        "origin_airport": "FRA",
        "destination_airport": "JFK",
        "scheduled_departure": ts(updated_departure),
        "estimated_departure": ts(updated_departure + timedelta(minutes=10)),
        "scheduled_arrival": ts(updated_arrival),
        "estimated_arrival": ts(updated_arrival + timedelta(minutes=15)),
        "operating_status": "confirmed",
        "terminal": "1",
        "gate": None,
        "status_source": "ops_control",
    },
    {
        "operating_flight_id": "OF_003",
        "flight_number": "ZX018",
        "service_date": status_departure.date().isoformat(),
        "origin_airport": "FRA",
        "destination_airport": "HAM",
        "scheduled_departure": ts(status_departure),
        "estimated_departure": ts(status_departure),
        "scheduled_arrival": ts(status_arrival),
        "estimated_arrival": ts(status_arrival),
        "operating_status": "on_time",
        "terminal": "1",
        "gate": None,
        "status_source": "ops_control",
    },
    {
        "operating_flight_id": "OF_004",
        "flight_number": "ZX1872",
        "service_date": (BASE_NOW + timedelta(days=3, hours=3)).date().isoformat(),
        "origin_airport": "MUC",
        "destination_airport": "FCO",
        "scheduled_departure": ts(BASE_NOW + timedelta(days=3, hours=3)),
        "estimated_departure": ts(BASE_NOW + timedelta(days=3, hours=3)),
        "scheduled_arrival": ts(BASE_NOW + timedelta(days=3, hours=4, minutes=25)),
        "estimated_arrival": ts(BASE_NOW + timedelta(days=3, hours=4, minutes=25)),
        "operating_status": "on_time",
        "terminal": "2",
        "gate": None,
        "status_source": "ops_control",
    },
]

OPERATIONAL_DISRUPTIONS = [
    {
        "operational_disruption_id": "OD_001",
        "operating_flight_id": "OF_001",
        "disrupted_flight_number": "ZX402",
        "origin_airport": "FRA",
        "destination_airport": "JFK",
        "scheduled_departure": ts(cancelled_departure),
        "scheduled_arrival": ts(cancelled_arrival),
        "disruption_type": "cancellation",
        "disruption_reason_code": "ROTATION_DELAY",
        "disruption_reason_category": "aircraft_rotation",
        "impact_status": "cancelled",
        "recorded_at": ts(cancelled_departure - timedelta(hours=2, minutes=15)),
        "source_system": "ops_control",
    },
]

REACCOMMODATION_RECORDS = [
    {
        "reaccommodation_record_id": "REAC_001",
        "customer_id": DEMO_PROFILE["customer_id"],
        "booking_id": FLAGSHIP_BOOKING_ID,
        "original_segment_id": "SEG_001",
        "replacement_segment_id": "SEG_002",
        "reaccommodation_status": "confirmed",
        "action_source": "automatic",
        "reaccommodated_at": ts(cancelled_departure - timedelta(hours=1, minutes=40)),
        "reaccommodation_reason_code": "SAME_DAY_ALT_ASSIGNED",
    },
]

SUPPORT_CASES = [
    {
        "support_case_id": "CASE_001",
        "customer_id": DEMO_PROFILE["customer_id"],
        "booking_id": FLAGSHIP_BOOKING_ID,
        "case_type": "disruption_follow_up",
        "status": "open",
        "opened_at": ts(BASE_NOW - timedelta(minutes=35)),
        "channel": "chat",
        "summary": "Traveller asked for confirmation that the rebooked flight is active.",
        "latest_note": "Automatic rebooking confirmed. Advised traveller to use the original booking locator for check-in.",
    },
    {
        "support_case_id": "CASE_002",
        "customer_id": DEMO_PROFILE["customer_id"],
        "booking_id": STATUS_BOOKING_ID,
        "case_type": "profile_question",
        "status": "resolved",
        "opened_at": ts(BASE_NOW - timedelta(days=2)),
        "channel": "web_form",
        "summary": "Traveller profile lookup assistance.",
        "latest_note": "Resolved after verifying the traveller's email address on file.",
    },
]

POLICY_DOCS_TEXT = [
    {
        "doc_id": "POL_001",
        "category": "profile",
        "title": "Traveller profile basics",
        "content": (
            "The traveller profile stores the traveller's profile ID, language, contact email, and loyalty status summary. "
            "In this demo the profile is read-only and can be used to confirm what details are already on file."
        ),
    },
    {
        "doc_id": "POL_002",
        "category": "disruptions",
        "title": "Flight disruptions and what they usually mean",
        "content": (
            "If a traveller says their flight was disrupted, that can mean the service was delayed, cancelled, "
            "or moved to a different departure time. In general, the airline may automatically rebook the booking onto "
            "another flight when a same-day alternative exists. Without access to the live booking record, the assistant "
            "can explain the general disruption process but cannot confirm what happened to a specific trip."
        ),
    },
    {
        "doc_id": "POL_003",
        "category": "rebooking",
        "title": "Rebooking after a cancellation",
        "content": (
            "When an airline cancels a flight, the booking may be automatically rebooked onto another service. "
            "The assistant should distinguish confirmed rebooking facts from broader rebooking policy. "
            "If a replacement flight is already assigned, the traveller normally keeps the same booking locator. "
            "If no replacement flight exists, self-service rebooking or agent support may be required."
        ),
    },
    {
        "doc_id": "POL_004",
        "category": "refunds",
        "title": "Refund guidance for disrupted trips",
        "content": (
            "Refund eligibility depends on ticket rules and whether the flight disruption resulted in an unused trip. "
            "For this demo, refund questions are answered from policy guidance unless the booking record explicitly states otherwise."
        ),
    },
    {
        "doc_id": "POL_005",
        "category": "baggage",
        "title": "Checked and cabin baggage overview",
        "content": (
            "Carry-on and checked baggage allowances vary by route, cabin, and fare. During a same-day automatic rebooking, "
            "checked baggage normally continues with the updated itinerary when the booking remains active."
        ),
    },
    {
        "doc_id": "POL_006",
        "category": "check_in",
        "title": "Online check-in timing",
        "content": (
            "Online check-in typically opens 23 hours before departure. Travellers can use their booking locator or profile ID "
            "to access boarding passes for the currently confirmed itinerary."
        ),
    },
    {
        "doc_id": "POL_007",
        "category": "disruptions",
        "title": "What to do after automatic rebooking",
        "content": (
            "After an automatic rebooking, the traveller should review the updated departure time and airport terminal, "
            "then check in again if needed. Seat assignments can change during reaccommodation. If the traveller prefers "
            "a different option, they may need to use self-service rebooking tools or contact support."
        ),
    },
    {
        "doc_id": "POL_008",
        "category": "seat_selection",
        "title": "Seat selection guidance",
        "content": (
            "Seat selection depends on fare, cabin, status tier, and aircraft availability. "
            "If a traveller is rebooked, prior seat assignments may change and should be reconfirmed during check-in."
        ),
    },
    {
        "doc_id": "POL_009",
        "category": "airport_help",
        "title": "Airport help and service desks",
        "content": (
            "Airport service counters can help with same-day disruptions, document checks, and baggage questions. "
            "If gate details are not yet assigned, the assistant should say so and refer the traveller to terminal screens or service desks."
        ),
    },
    {
        "doc_id": "POL_010",
        "category": "status_benefits",
        "title": "Tier-aware disruption support",
        "content": (
            "Aurora Air tailors disruption help by status tier. Traveller members receive standard self-service rebooking guidance "
            "and app notifications. Frequent members receive the same guidance plus quicker queue placement for digital servicing. "
            "Senator members receive priority airport and contact-center assistance, faster reaccommodation review, and proactive alerts. "
            "Ambassador members receive the highest-priority servicing path, dedicated premium disruption handling, and white-glove airport support."
        ),
    },
    {
        "doc_id": "POL_011",
        "category": "status_benefits",
        "title": "Tier-aware baggage and airport assistance",
        "content": (
            "Baggage and airport-help guidance can vary by cabin and status tier. Frequent members may receive streamlined service routing. "
            "Senator members typically receive stronger baggage tracing support and priority airport desks. Ambassador members receive the most "
            "expedited premium support. The assistant should state these as program-level benefits unless a live booking record adds trip-specific detail."
        ),
    },
]

DATASET_SUMMARY = {
    "customer_profiles": len(CUSTOMER_PROFILES),
    "bookings": len(BOOKINGS),
    "itinerary_segments": len(ITINERARY_SEGMENTS),
    "operating_flights": len(OPERATING_FLIGHTS),
    "operational_disruptions": len(OPERATIONAL_DISRUPTIONS),
    "reaccommodation_records": len(REACCOMMODATION_RECORDS),
    "support_cases": len(SUPPORT_CASES),
    "travel_policy_docs": len(POLICY_DOCS_TEXT),
}


def generate_demo_data(
    *,
    output_dir: Path | None = None,
    seed: int | None = None,
    update_env_file: bool = False,
) -> GeneratedDataset:
    del seed
    resolved_output_dir = output_dir or OUTPUT_DIR
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating embeddings for travel policy documents...")
    embeddings = embed([doc["content"] for doc in POLICY_DOCS_TEXT])
    policy_docs = [
        {**doc, "content_embedding": embedding}
        for doc, embedding in zip(POLICY_DOCS_TEXT, embeddings)
    ]

    print("Writing JSONL files:")
    write_jsonl(resolved_output_dir, "customer_profiles.jsonl", CUSTOMER_PROFILES)
    write_jsonl(resolved_output_dir, "bookings.jsonl", BOOKINGS)
    write_jsonl(resolved_output_dir, "itinerary_segments.jsonl", ITINERARY_SEGMENTS)
    write_jsonl(resolved_output_dir, "operating_flights.jsonl", OPERATING_FLIGHTS)
    write_jsonl(resolved_output_dir, "operational_disruptions.jsonl", OPERATIONAL_DISRUPTIONS)
    write_jsonl(resolved_output_dir, "reaccommodation_records.jsonl", REACCOMMODATION_RECORDS)
    write_jsonl(resolved_output_dir, "support_cases.jsonl", SUPPORT_CASES)
    write_jsonl(resolved_output_dir, "travel_policy_docs.jsonl", policy_docs)

    env_updates = {
        "DEMO_USER_ID": DEMO_PROFILE["customer_id"],
        "DEMO_USER_NAME": DEMO_PROFILE["display_name"],
        "DEMO_USER_EMAIL": DEMO_PROFILE["email"],
    }
    if update_env_file:
        for key, value in env_updates.items():
            update_env(key, value)

    print(f"\nDemo traveller: {DEMO_PROFILE['display_name']} ({DEMO_PROFILE['customer_id']})")
    print(f"Flagship disrupted booking: {FLAGSHIP_LOCATOR}")
    print("Done.")

    return GeneratedDataset(
        output_dir=str(resolved_output_dir),
        env_updates=env_updates,
        summary=dict(DATASET_SUMMARY),
    )


def main() -> None:
    generate_demo_data(output_dir=OUTPUT_DIR, update_env_file=True)


if __name__ == "__main__":
    main()
