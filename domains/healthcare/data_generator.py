"""Generate sample data for the Healthcare demo.

Adapted from healthcare_context_surface_example/healthcare_sample_data.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from hashlib import sha256
from pathlib import Path

import openai

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.domain_contract import GeneratedDataset  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
#  DATE ANCHORING
#
#  All appointment/referral/waitlist dates are expressed as offsets (in days)
#  from "today" so the dataset stays centered on the current date no matter
#  when `make setup` / `make reset` is run. Scheduled appointments stay in the
#  future; completed / no-show / cancelled ones stay in the past.
# ═══════════════════════════════════════════════════════════════════════════

TODAY = datetime.now().date()


def appt_dt(days_from_today: int, hour: int, minute: int = 0) -> str:
    """Naive local timestamp 'YYYY-MM-DDTHH:MM:SS' offset from today."""
    day = TODAY + timedelta(days=days_from_today)
    return f"{day.isoformat()}T{hour:02d}:{minute:02d}:00"


def day_str(days_from_today: int) -> str:
    """Date-only string 'YYYY-MM-DD' offset from today."""
    return (TODAY + timedelta(days=days_from_today)).isoformat()


def fake_embedding(text: str) -> list[float]:
    digest = sha256(text.encode("utf-8")).digest()
    return [digest[i % len(digest)] / 255.0 for i in range(1536)]


def embed(texts: list[str]) -> list[list[float]]:
    if not os.getenv("OPENAI_API_KEY"):
        return [fake_embedding(text) for text in texts]
    client = openai.OpenAI()
    response = client.embeddings.create(
        input=texts,
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    return [item.embedding for item in response.data]

OUTPUT_DIR = ROOT / "output" / "healthcare"

DEMO_USER_ID = "P001"

# ═══════════════════════════════════════════════════════════════════════════
#  LOCATIONS (2)
# ═══════════════════════════════════════════════════════════════════════════

LOCATIONS = [
    {
        "id": "LOC001",
        "name": "Downtown Medical Center",
        "address": "100 Main Street, Suite 200",
        "city": "San Francisco",
        "state": "CA",
        "phone": "415-555-1000",
        "type": "clinic",
    },
    {
        "id": "LOC002",
        "name": "Westside Family Health",
        "address": "2500 Ocean Avenue",
        "city": "San Francisco",
        "state": "CA",
        "phone": "415-555-2000",
        "type": "clinic",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  PROVIDERS (5)
# ═══════════════════════════════════════════════════════════════════════════

PROVIDERS = [
    {
        "id": "DR001",
        "name": "Dr. Sofia Martinez",
        "specialty": "primary_care",
        "location_id": "LOC001",
        "accepting_new_patients": "yes",
        "languages": "en,es",
        "email": "s.martinez@downtownmed.com",
    },
    {
        "id": "DR002",
        "name": "Dr. Raj Patel",
        "specialty": "internal_medicine",
        "location_id": "LOC001",
        "accepting_new_patients": "yes",
        "languages": "en,hi",
        "email": "r.patel@downtownmed.com",
    },
    {
        "id": "DR003",
        "name": "Dr. Jennifer Kim",
        "specialty": "obstetrics",
        "location_id": "LOC002",
        "accepting_new_patients": "no",
        "languages": "en,ko",
        "email": "j.kim@westsidehealth.com",
    },
    {
        "id": "DR004",
        "name": "Dr. Marcus Thompson",
        "specialty": "cardiology",
        "location_id": "LOC001",
        "accepting_new_patients": "yes",
        "languages": "en",
        "email": "m.thompson@downtownmed.com",
    },
    {
        "id": "DR005",
        "name": "Dr. Linda Chen",
        "specialty": "orthopedics",
        "location_id": "LOC002",
        "accepting_new_patients": "yes",
        "languages": "en,zh",
        "email": "l.chen@westsidehealth.com",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  PATIENTS (8)
# ═══════════════════════════════════════════════════════════════════════════

PATIENTS = [
    {
        "id": "P001",
        "name": "John Smith",
        "email": "john.smith@email.com",
        "phone": "555-0101",
        "dob": "1985-03-15",
        "preferred_language": "en",
        "insurance_status": "verified",
        "primary_provider_id": "DR001",
    },
    {
        "id": "P002",
        "name": "Sarah Johnson",
        "email": "sarah.j@email.com",
        "phone": "555-0102",
        "dob": "1990-07-22",
        "preferred_language": "en",
        "insurance_status": "verified",
        "primary_provider_id": "DR002",
    },
    {
        "id": "P003",
        "name": "Maria Garcia",
        "email": "maria.garcia@email.com",
        "phone": "555-0103",
        "dob": "1978-11-08",
        "preferred_language": "es",
        "insurance_status": "verified",
        "primary_provider_id": "DR001",
    },
    {
        "id": "P004",
        "name": "James Wilson",
        "email": "jwilson@email.com",
        "phone": "555-0104",
        "dob": "1965-01-30",
        "preferred_language": "en",
        "insurance_status": "expired",
        "primary_provider_id": "DR002",
    },
    {
        "id": "P005",
        "name": "Emily Chen",
        "email": "emily.chen@email.com",
        "phone": "555-0105",
        "dob": "1992-09-12",
        "preferred_language": "zh",
        "insurance_status": "verified",
        "primary_provider_id": "DR005",
    },
    {
        "id": "P006",
        "name": "Michael Brown",
        "email": "mbrown@email.com",
        "phone": "555-0106",
        "dob": "1955-04-18",
        "preferred_language": "en",
        "insurance_status": "pending",
        "primary_provider_id": "DR001",
    },
    {
        "id": "P007",
        "name": "Ana Rodriguez",
        "email": "ana.rod@email.com",
        "phone": "555-0107",
        "dob": "1988-12-03",
        "preferred_language": "es",
        "insurance_status": "verified",
        "primary_provider_id": "DR003",
    },
    {
        "id": "P008",
        "name": "David Lee",
        "email": "david.lee@email.com",
        "phone": "555-0108",
        "dob": "1972-06-25",
        "preferred_language": "en",
        "insurance_status": "verified",
        "primary_provider_id": "DR002",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  APPOINTMENTS (10)
# ═══════════════════════════════════════════════════════════════════════════

APPOINTMENTS = [
    {
        "id": "A001",
        "patient_id": "P001",
        "provider_id": "DR001",
        "location_id": "LOC001",
        "datetime": appt_dt(-8, 9, 0),
        "type": "checkup",
        "status": "completed",
        "notes": "Annual physical, all vitals normal",
    },
    {
        "id": "A002",
        "patient_id": "P001",
        "provider_id": "DR001",
        "location_id": "LOC001",
        "datetime": appt_dt(6, 10, 0),
        "type": "follow_up",
        "status": "scheduled",
        "notes": "Follow up on blood work",
    },
    {
        "id": "A003",
        "patient_id": "P002",
        "provider_id": "DR002",
        "location_id": "LOC001",
        "datetime": appt_dt(-7, 14, 0),
        "type": "consultation",
        "status": "no_show",
        "notes": "Patient did not arrive, no call",
    },
    {
        "id": "A004",
        "patient_id": "P003",
        "provider_id": "DR001",
        "location_id": "LOC001",
        "datetime": appt_dt(-6, 11, 0),
        "type": "checkup",
        "status": "completed",
        "notes": "Diabetes management review",
    },
    {
        "id": "A005",
        "patient_id": "P004",
        "provider_id": "DR003",
        "location_id": "LOC002",
        "datetime": appt_dt(-7, 15, 30),
        "type": "procedure",
        "status": "cancelled",
        "notes": "Insurance expired, rescheduling needed",
    },
    {
        "id": "A006",
        "patient_id": "P005",
        "provider_id": "DR005",
        "location_id": "LOC002",
        "datetime": appt_dt(3, 9, 30),
        "type": "follow_up",
        "status": "scheduled",
        "notes": "Post-surgery check",
    },
    {
        "id": "A007",
        "patient_id": "P006",
        "provider_id": "DR001",
        "location_id": "LOC001",
        "datetime": appt_dt(-8, 16, 0),
        "type": "consultation",
        "status": "no_show",
        "notes": "New patient intake - missed",
    },
    {
        "id": "A008",
        "patient_id": "P007",
        "provider_id": "DR003",
        "location_id": "LOC002",
        "datetime": appt_dt(5, 10, 0),
        "type": "checkup",
        "status": "scheduled",
        "notes": "Prenatal visit",
    },
    {
        "id": "A009",
        "patient_id": "P008",
        "provider_id": "DR002",
        "location_id": "LOC001",
        "datetime": appt_dt(-9, 11, 0),
        "type": "procedure",
        "status": "completed",
        "notes": "Minor procedure completed successfully",
    },
    {
        "id": "A010",
        "patient_id": "P002",
        "provider_id": "DR002",
        "location_id": "LOC001",
        "datetime": appt_dt(9, 14, 0),
        "type": "consultation",
        "status": "scheduled",
        "notes": "Rescheduled from no-show",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  REFERRALS (6)
# ═══════════════════════════════════════════════════════════════════════════

REFERRALS = [
    {
        "id": "R001",
        "patient_id": "P001",
        "referring_provider_id": "DR001",
        "to_specialty": "cardiology",
        "to_provider_id": "DR004",
        "status": "pending",
        "urgency": "routine",
        "notes": "Elevated cholesterol, recommend cardiac evaluation",
        "received_date": day_str(-8),
    },
    {
        "id": "R002",
        "patient_id": "P003",
        "referring_provider_id": "DR001",
        "to_specialty": "endocrinology",
        "to_provider_id": "",
        "status": "scheduled",
        "urgency": "routine",
        "notes": "Diabetes specialist consultation",
        "received_date": day_str(-13),
    },
    {
        "id": "R003",
        "patient_id": "P004",
        "referring_provider_id": "DR002",
        "to_specialty": "orthopedics",
        "to_provider_id": "DR005",
        "status": "pending",
        "urgency": "urgent",
        "notes": "Severe knee pain, possible surgery needed",
        "received_date": day_str(-10),
    },
    {
        "id": "R004",
        "patient_id": "P006",
        "referring_provider_id": "DR002",
        "to_specialty": "oncology",
        "to_provider_id": "",
        "status": "pending",
        "urgency": "stat",
        "notes": "Abnormal lab results, immediate evaluation needed",
        "received_date": day_str(-7),
    },
    {
        "id": "R005",
        "patient_id": "P008",
        "referring_provider_id": "DR002",
        "to_specialty": "neurology",
        "to_provider_id": "",
        "status": "completed",
        "urgency": "routine",
        "notes": "Headache evaluation completed",
        "received_date": day_str(-28),
    },
    {
        "id": "R006",
        "patient_id": "P005",
        "referring_provider_id": "DR005",
        "to_specialty": "physical_therapy",
        "to_provider_id": "",
        "status": "scheduled",
        "urgency": "routine",
        "notes": "Post-surgery rehabilitation",
        "received_date": day_str(-9),
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  WAITLIST (4)
# ═══════════════════════════════════════════════════════════════════════════

WAITLIST = [
    {
        "id": "W001",
        "patient_id": "P002",
        "preferred_provider_id": "DR001",
        "location_id": "LOC001",
        "appointment_type": "consultation",
        "flexibility": "mornings",
        "added_date": day_str(-10),
        "notes": "Wants to switch from Dr. Patel",
    },
    {
        "id": "W002",
        "patient_id": "P004",
        "preferred_provider_id": "DR003",
        "location_id": "LOC002",
        "appointment_type": "procedure",
        "flexibility": "any_time",
        "added_date": day_str(-7),
        "notes": "Waiting for insurance to be resolved",
    },
    {
        "id": "W003",
        "patient_id": "P006",
        "preferred_provider_id": "DR001",
        "location_id": "LOC001",
        "appointment_type": "checkup",
        "flexibility": "afternoons",
        "added_date": day_str(-8),
        "notes": "Missed first appointment, wants to reschedule",
    },
    {
        "id": "W004",
        "patient_id": "P007",
        "preferred_provider_id": "DR003",
        "location_id": "LOC002",
        "appointment_type": "follow_up",
        "flexibility": "specific_days",
        "added_date": day_str(-6),
        "notes": "Only available Tuesdays and Thursdays",
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  HEALTH DOCS (5) — patient guides, FAQs, policies
# ═══════════════════════════════════════════════════════════════════════════

HEALTHDOC_TEXT = [
    {
        "doc_id": "DOC001",
        "title": "Appointment Cancellation Policy",
        "category": "policy",
        "content": (
            "Patients must cancel or reschedule appointments at least 24 hours in advance. "
            "Late cancellations or no-shows may incur a $50 fee. If you miss two consecutive "
            "appointments without notice, your provider may require a phone consultation before "
            "scheduling a new in-person visit. Emergency situations are handled on a case-by-case basis."
        ),
    },
    {
        "doc_id": "DOC002",
        "title": "Insurance Verification and Coverage",
        "category": "faq",
        "content": (
            "We verify insurance coverage before your first visit. Please bring your insurance card "
            "and a valid photo ID. If your insurance has expired or changed, contact our front desk "
            "at least 48 hours before your appointment. We accept most major insurance plans including "
            "Blue Cross, Aetna, UnitedHealthcare, and Kaiser. Self-pay options are available with a "
            "10% discount for upfront payment."
        ),
    },
    {
        "doc_id": "DOC003",
        "title": "Referral Process Guide",
        "category": "care_guide",
        "content": (
            "When your primary care provider refers you to a specialist, our referral coordinator "
            "will contact you within 2 business days to schedule the appointment. Urgent referrals "
            "are processed same-day. You can check the status of your referral by calling our "
            "referral line at 415-555-3000 or through the patient portal. Referrals are valid for "
            "90 days from the date of issue."
        ),
    },
    {
        "doc_id": "DOC004",
        "title": "Patient Portal and Telehealth Guide",
        "category": "care_guide",
        "content": (
            "Access your medical records, lab results, and appointment history through the patient "
            "portal at portal.downtownmed.com. Telehealth visits are available for follow-ups and "
            "non-emergency consultations. To start a telehealth visit, log into the portal and click "
            "'Start Virtual Visit' at your scheduled appointment time. You'll need a device with a "
            "camera and stable internet connection."
        ),
    },
    {
        "doc_id": "DOC005",
        "title": "Prescription Refill Policy",
        "category": "policy",
        "content": (
            "Prescription refills can be requested through the patient portal, by calling your "
            "provider's office, or through your pharmacy. Allow 48 hours for refill processing. "
            "Controlled substances require an in-person or telehealth visit every 3 months. "
            "If you're running low on medication, contact us at least one week before you run out "
            "to ensure uninterrupted treatment."
        ),
    },
]


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN — write JSONL files
# ═══════════════════════════════════════════════════════════════════════════


def write_jsonl(output_dir: Path, filename: str, rows: list[dict]) -> None:
    path = output_dir / filename
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"  {path.name}: {len(rows)} records")


def update_env(key: str, value: str) -> None:
    env_path = ROOT / ".env"
    safe_value = f'"{value}"' if " " in value else value
    if not env_path.exists():
        env_path.write_text(f"{key}={safe_value}\n")
        return
    lines = env_path.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={safe_value}"
            found = True
            break
    if not found:
        lines.append(f"{key}={safe_value}")
    env_path.write_text("\n".join(lines) + "\n")


def generate_demo_data(
    *,
    output_dir: Path | None = None,
    seed: int | None = None,
    update_env_file: bool = False,
) -> GeneratedDataset:
    del seed
    resolved_output_dir = output_dir or OUTPUT_DIR
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating embeddings for health docs...")
    embeddings = embed([doc["content"] for doc in HEALTHDOC_TEXT])
    healthdocs = [{**doc, "content_embedding": emb} for doc, emb in zip(HEALTHDOC_TEXT, embeddings)]

    print("Writing JSONL files:")
    write_jsonl(resolved_output_dir, "locations.jsonl", LOCATIONS)
    write_jsonl(resolved_output_dir, "providers.jsonl", PROVIDERS)
    write_jsonl(resolved_output_dir, "patients.jsonl", PATIENTS)
    write_jsonl(resolved_output_dir, "appointments.jsonl", APPOINTMENTS)
    write_jsonl(resolved_output_dir, "referrals.jsonl", REFERRALS)
    write_jsonl(resolved_output_dir, "waitlist.jsonl", WAITLIST)
    write_jsonl(resolved_output_dir, "healthdocs.jsonl", healthdocs)

    demo = PATIENTS[0]
    if update_env_file:
        update_env("DEMO_USER_ID", demo["id"])
        update_env("DEMO_USER_NAME", demo["name"])
        update_env("DEMO_USER_EMAIL", demo["email"])
    print(f"\nDemo user: {demo['name']} ({demo['id']})")
    print("Done.")

    return GeneratedDataset(
        output_dir=str(resolved_output_dir),
        env_updates={
            "DEMO_USER_ID": demo["id"],
            "DEMO_USER_NAME": demo["name"],
            "DEMO_USER_EMAIL": demo["email"],
        },
        summary={
            "locations": len(LOCATIONS),
            "providers": len(PROVIDERS),
            "patients": len(PATIENTS),
            "appointments": len(APPOINTMENTS),
            "referrals": len(REFERRALS),
            "waitlist": len(WAITLIST),
            "healthdocs": len(healthdocs),
        },
    )


def main() -> None:
    generate_demo_data(output_dir=OUTPUT_DIR, update_env_file=True)


if __name__ == "__main__":
    main()
