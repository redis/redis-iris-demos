"""Generated Context Surface models for the RedHealthConnect domain."""

from __future__ import annotations

from typing import Any

from context_surfaces.context_model import ContextField, ContextModel, ContextRelationship


class Location(ContextModel):
    """Location entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_location:{id}"

    id: str = ContextField(
        description="Location ID",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Facility name",
        index="text",
        weight=2.0,
    )

    address: str = ContextField(
        description="Street address",
        index="text",
    )

    city: str = ContextField(
        description="City",
        index="tag",
    )

    state: str = ContextField(
        description="State",
        index="tag",
    )

    phone: str = ContextField(
        description="Phone number",
        index="tag",
    )

    type: str = ContextField(
        description="Facility type: clinic, hospital",
        index="tag",
    )


class Provider(ContextModel):
    """Provider entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_provider:{id}"

    id: str = ContextField(
        description="Provider ID",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Full name",
        index="text",
        weight=2.0,
    )

    specialty: str = ContextField(
        description="Medical specialty",
        index="tag",
    )

    location_id: str = ContextField(
        description="Primary location",
        index="tag",
    )

    accepting_new_patients: str = ContextField(
        description="Accepting new patients: yes/no",
        index="tag",
    )

    languages: str = ContextField(
        description="Languages spoken",
        index="text",
    )

    email: str = ContextField(
        description="Email",
        index="text",
    )

    location: Any = ContextRelationship(
        description="Primary location",
        target="Location",
        source_field="location_id",
    )


class Patient(ContextModel):
    """Patient entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_patient:{id}"

    id: str = ContextField(
        description="Patient ID",
        is_key_component=True,
    )

    name: str = ContextField(
        description="Full name",
        index="text",
        weight=2.0,
    )

    email: str = ContextField(
        description="Email",
        index="text",
        no_stem=True,
    )

    phone: str = ContextField(
        description="Phone",
        index="tag",
    )

    dob: str = ContextField(
        description="Date of birth",
        index="tag",
    )

    preferred_language: str = ContextField(
        description="Preferred language",
        index="tag",
    )

    insurance_status: str = ContextField(
        description="Insurance: verified, pending, expired",
        index="tag",
    )

    primary_provider_id: str = ContextField(
        description="Primary provider",
        index="tag",
    )

    primary_provider: Any = ContextRelationship(
        description="Primary care provider",
        target="Provider",
        source_field="primary_provider_id",
    )


class Appointment(ContextModel):
    """Appointment entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_appointment:{id}"

    id: str = ContextField(
        description="Appointment ID",
        is_key_component=True,
    )

    patient_id: str = ContextField(
        description="Patient",
        index="tag",
    )

    provider_id: str = ContextField(
        description="Provider",
        index="tag",
    )

    location_id: str = ContextField(
        description="Location",
        index="tag",
    )

    datetime: str = ContextField(
        description="Date and time",
        index="tag",
    )

    type: str = ContextField(
        description="Type: checkup, follow_up, consultation, procedure",
        index="tag",
    )

    status: str = ContextField(
        description="Status: scheduled, completed, no_show, cancelled",
        index="tag",
    )

    notes: str = ContextField(
        description="Appointment notes",
        index="text",
    )

    patient: Any = ContextRelationship(
        description="Patient",
        target="Patient",
        source_field="patient_id",
    )

    provider: Any = ContextRelationship(
        description="Provider",
        target="Provider",
        source_field="provider_id",
    )

    location: Any = ContextRelationship(
        description="Location",
        target="Location",
        source_field="location_id",
    )


class Referral(ContextModel):
    """Referral entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_referral:{id}"

    id: str = ContextField(
        description="Referral ID",
        is_key_component=True,
    )

    patient_id: str = ContextField(
        description="Patient being referred",
        index="tag",
    )

    referring_provider_id: str = ContextField(
        description="Referring provider",
        index="tag",
    )

    to_specialty: str = ContextField(
        description="Target specialty",
        index="tag",
    )

    to_provider_id: str = ContextField(
        description="Target provider (if known)",
        index="tag",
    )

    status: str = ContextField(
        description="Status: pending, scheduled, completed",
        index="tag",
    )

    urgency: str = ContextField(
        description="Urgency: routine, urgent, stat",
        index="tag",
    )

    notes: str = ContextField(
        description="Referral notes",
        index="text",
    )

    received_date: str = ContextField(
        description="Date received",
        index="tag",
    )

    patient: Any = ContextRelationship(
        description="Patient",
        target="Patient",
        source_field="patient_id",
    )

    referring_provider: Any = ContextRelationship(
        description="Referring provider",
        target="Provider",
        source_field="referring_provider_id",
    )


class Waitlist(ContextModel):
    """Waitlist entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_waitlist:{id}"

    id: str = ContextField(
        description="Waitlist entry ID",
        is_key_component=True,
    )

    patient_id: str = ContextField(
        description="Patient",
        index="tag",
    )

    preferred_provider_id: str = ContextField(
        description="Preferred provider",
        index="tag",
    )

    location_id: str = ContextField(
        description="Preferred location",
        index="tag",
    )

    appointment_type: str = ContextField(
        description="Appointment type needed",
        index="tag",
    )

    flexibility: str = ContextField(
        description="Schedule flexibility: mornings, afternoons, any_time, specific_days",
        index="tag",
    )

    added_date: str = ContextField(
        description="Date added to waitlist",
        index="tag",
    )

    notes: str = ContextField(
        description="Additional notes",
        index="text",
    )

    patient: Any = ContextRelationship(
        description="Patient",
        target="Patient",
        source_field="patient_id",
    )

    preferred_provider: Any = ContextRelationship(
        description="Preferred provider",
        target="Provider",
        source_field="preferred_provider_id",
    )


class LabResult(ContextModel):
    """LabResult entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_labresult:{id}"

    id: str = ContextField(
        description="Lab result ID",
        is_key_component=True,
    )

    patient_id: str = ContextField(
        description="Patient",
        index="tag",
    )

    provider_id: str = ContextField(
        description="Ordering provider",
        index="tag",
    )

    appointment_id: str = ContextField(
        description="Associated appointment",
        index="tag",
    )

    test_name: str = ContextField(
        description="Test name",
        index="text",
        weight=2.0,
    )

    result_value: str = ContextField(
        description="Result value",
        index="text",
    )

    reference_range: str = ContextField(
        description="Normal reference range",
        index="text",
    )

    flag: str = ContextField(
        description="Flag: normal, high, low, abnormal",
        index="tag",
    )

    status: str = ContextField(
        description="Status: final, preliminary, pending",
        index="tag",
    )

    collected_date: str = ContextField(
        description="Date specimen collected",
        index="tag",
    )

    resulted_date: str = ContextField(
        description="Date result reported",
        index="tag",
    )

    notes: str = ContextField(
        description="Result notes",
        index="text",
    )

    patient: Any = ContextRelationship(
        description="Patient",
        target="Patient",
        source_field="patient_id",
    )

    provider: Any = ContextRelationship(
        description="Ordering provider",
        target="Provider",
        source_field="provider_id",
    )

    appointment: Any = ContextRelationship(
        description="Associated appointment",
        target="Appointment",
        source_field="appointment_id",
    )


class Prescription(ContextModel):
    """Prescription entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_prescription:{id}"

    id: str = ContextField(
        description="Prescription ID",
        is_key_component=True,
    )

    patient_id: str = ContextField(
        description="Patient",
        index="tag",
    )

    provider_id: str = ContextField(
        description="Prescribing provider",
        index="tag",
    )

    medication: str = ContextField(
        description="Medication name",
        index="text",
        weight=2.0,
    )

    dosage: str = ContextField(
        description="Dosage",
        index="tag",
    )

    frequency: str = ContextField(
        description="Frequency / directions",
        index="text",
    )

    status: str = ContextField(
        description="Status: active, completed, discontinued, expired",
        index="tag",
    )

    prescribed_date: str = ContextField(
        description="Date prescribed",
        index="tag",
    )

    refills_remaining: str = ContextField(
        description="Refills remaining",
        index="tag",
    )

    pharmacy: str = ContextField(
        description="Dispensing pharmacy",
        index="text",
    )

    notes: str = ContextField(
        description="Prescription notes",
        index="text",
    )

    patient: Any = ContextRelationship(
        description="Patient",
        target="Patient",
        source_field="patient_id",
    )

    provider: Any = ContextRelationship(
        description="Prescribing provider",
        target="Provider",
        source_field="provider_id",
    )


class HealthDoc(ContextModel):
    """HealthDoc entity for the RedHealthConnect domain."""

    __redis_key_template__ = "healthcare_healthdoc:{doc_id}"

    doc_id: str = ContextField(
        description="Document ID",
        is_key_component=True,
    )

    title: str = ContextField(
        description="Document title",
        index="text",
        weight=2.0,
    )

    category: str = ContextField(
        description="Category: policy, faq, care_guide",
        index="tag",
    )

    content: str = ContextField(
        description="Full document text",
        index="text",
    )

    content_embedding: list[float] = ContextField(
        description="Vector embedding of document content",
        index="vector",
        vector_dim=1536,
        distance_metric="cosine",
    )
