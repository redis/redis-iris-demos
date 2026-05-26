"""Generated Context Surface models for the Aurora Air domain."""

from __future__ import annotations

from context_surfaces.context_model import ContextField, ContextModel, ContextRelationship


class CustomerProfile(ContextModel):
    """CustomerProfile entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_customer_profile:{customer_id}"

    customer_id: str = ContextField(
        description="Public-safe demo customer identifier",
        is_key_component=True,
    )

    profile_reference: str = ContextField(
        description="Traveller profile reference",
        index="tag",
        no_stem=True,
    )

    display_name: str = ContextField(
        description="Traveller display name",
        index="text",
        weight=2.0,
    )

    ticket_name_masked: str = ContextField(
        description="Masked name as shown on the ticket",
    )

    loyalty_member_id_masked: str = ContextField(
        description="Masked loyalty member identifier",
        index="tag",
        no_stem=True,
    )

    salutation: str = ContextField(
        description="Passenger salutation",
        index="tag",
    )

    birth_date: str = ContextField(
        description="Passenger birth date",
    )

    gender: str = ContextField(
        description="Passenger gender",
        index="tag",
    )

    status_tier: str = ContextField(
        description="Current passenger status tier",
        index="tag",
    )

    preferred_language: str = ContextField(
        description="Preferred language for service",
        index="tag",
    )

    customer_program: str = ContextField(
        description="Passenger loyalty program",
        index="tag",
    )

    customer_usage: str = ContextField(
        description="Passenger usage classification",
        index="tag",
    )

    enrollment_carrier: str = ContextField(
        description="Carrier tied to enrollment",
        index="tag",
    )

    service_permissions: dict[str, bool] = ContextField(
        description="Service-permission flags available to the passenger",
    )

    email: str = ContextField(
        description="Read-only email on file",
        index="text",
        weight=1.4,
        no_stem=True,
    )

    bookings: list[Booking] = ContextRelationship(
        description="Bookings belonging to this traveller",
        source_field="customer_id",
    )

    support_cases: list[SupportCase] = ContextRelationship(
        description="Support cases opened for this traveller",
        source_field="customer_id",
    )


class Booking(ContextModel):
    """Booking entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_booking:{booking_id}"

    booking_id: str = ContextField(
        description="Unique booking identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    booking_locator: str = ContextField(
        description="Booking locator / PNR",
        index="tag",
        no_stem=True,
    )

    passenger_display_name: str = ContextField(
        description="Passenger display name",
        index="text",
        weight=1.6,
    )

    trip_status: str = ContextField(
        description="Overall trip status",
        index="tag",
    )

    created_at: str = ContextField(
        description="Booking creation timestamp",
    )

    fare_family: str = ContextField(
        description="Fare family name",
        index="tag",
    )

    cabin: str = ContextField(
        description="Cabin class",
        index="tag",
    )

    itinerary_segments: list[ItinerarySegment] = ContextRelationship(
        description="Booked itinerary segments belonging to this booking",
        source_field="booking_id",
    )

    reaccommodation_records: list[ReaccommodationRecord] = ContextRelationship(
        description="Reaccommodation records tied to this booking",
        source_field="booking_id",
    )

    support_cases: list[SupportCase] = ContextRelationship(
        description="Support cases tied to this booking",
        source_field="booking_id",
    )


class ItinerarySegment(ContextModel):
    """ItinerarySegment entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_itinerary_segment:{segment_id}"

    segment_id: str = ContextField(
        description="Unique itinerary segment identifier",
        is_key_component=True,
    )

    booking_id: str = ContextField(
        description="Parent booking identifier",
        index="tag",
    )

    segment_sequence: int = ContextField(
        description="Position of the segment in the itinerary",
    )

    operating_flight_id: str = ContextField(
        description="Linked operating flight identifier",
        index="tag",
        no_stem=True,
    )

    flight_number: str = ContextField(
        description="Booked marketing flight number",
        index="tag",
        no_stem=True,
    )

    segment_role: str = ContextField(
        description="original, updated, or unaffected",
        index="tag",
    )

    origin_airport: str = ContextField(
        description="Origin airport code",
        index="tag",
    )

    origin_city: str = ContextField(
        description="Origin city",
        index="text",
    )

    destination_airport: str = ContextField(
        description="Destination airport code",
        index="tag",
    )

    destination_city: str = ContextField(
        description="Destination city",
        index="text",
    )

    scheduled_departure: str = ContextField(
        description="Scheduled departure timestamp",
    )

    scheduled_arrival: str = ContextField(
        description="Scheduled arrival timestamp",
    )

    cabin: str = ContextField(
        description="Cabin on the segment",
        index="tag",
    )

    booking: Booking = ContextRelationship(
        description="Booking containing this segment",
        source_field="booking_id",
    )

    operating_flight: OperatingFlight = ContextRelationship(
        description="Operating flight linked to this itinerary segment",
        source_field="operating_flight_id",
    )


class OperatingFlight(ContextModel):
    """OperatingFlight entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_operating_flight:{operating_flight_id}"

    operating_flight_id: str = ContextField(
        description="Unique operating flight identifier",
        is_key_component=True,
    )

    flight_number: str = ContextField(
        description="Operating flight number",
        index="tag",
        no_stem=True,
    )

    service_date: str = ContextField(
        description="Operating flight service date",
        index="tag",
    )

    origin_airport: str = ContextField(
        description="Origin airport code",
        index="tag",
    )

    destination_airport: str = ContextField(
        description="Destination airport code",
        index="tag",
    )

    scheduled_departure: str = ContextField(
        description="Scheduled departure timestamp",
    )

    estimated_departure: str = ContextField(
        description="Current estimated departure timestamp",
    )

    scheduled_arrival: str = ContextField(
        description="Scheduled arrival timestamp",
    )

    estimated_arrival: str = ContextField(
        description="Current estimated arrival timestamp",
    )

    operating_status: str = ContextField(
        description="Current operating flight status",
        index="tag",
    )

    terminal: str | None = ContextField(
        description="Departure terminal if known",
    )

    gate: str | None = ContextField(
        description="Departure gate if assigned close to departure",
    )

    status_source: str = ContextField(
        description="System providing current flight status",
        index="tag",
    )


class OperationalDisruption(ContextModel):
    """OperationalDisruption entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_operational_disruption:{operational_disruption_id}"

    operational_disruption_id: str = ContextField(
        description="Unique operational disruption identifier",
        is_key_component=True,
    )

    operating_flight_id: str = ContextField(
        description="Linked operating flight identifier",
        index="tag",
        no_stem=True,
    )

    disrupted_flight_number: str = ContextField(
        description="Disrupted flight number",
        index="tag",
        no_stem=True,
    )

    origin_airport: str = ContextField(
        description="Origin airport code",
        index="tag",
    )

    destination_airport: str = ContextField(
        description="Destination airport code",
        index="tag",
    )

    scheduled_departure: str = ContextField(
        description="Scheduled departure timestamp",
    )

    scheduled_arrival: str = ContextField(
        description="Scheduled arrival timestamp",
    )

    disruption_type: str = ContextField(
        description="Type of disruption",
        index="tag",
    )

    disruption_reason_code: str = ContextField(
        description="Operational disruption reason code",
        index="tag",
    )

    disruption_reason_category: str = ContextField(
        description="Operational disruption reason category",
        index="tag",
    )

    impact_status: str = ContextField(
        description="Traveller-visible impact status",
        index="tag",
    )

    recorded_at: str = ContextField(
        description="Timestamp when the disruption was recorded",
    )

    source_system: str = ContextField(
        description="Source operational system or feed",
        index="tag",
    )

    operating_flight: OperatingFlight = ContextRelationship(
        description="Operating flight affected by this disruption",
        source_field="operating_flight_id",
    )


class ReaccommodationRecord(ContextModel):
    """ReaccommodationRecord entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_reaccommodation_record:{reaccommodation_record_id}"

    reaccommodation_record_id: str = ContextField(
        description="Unique reaccommodation identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    booking_id: str = ContextField(
        description="Booking identifier",
        index="tag",
    )

    original_segment_id: str = ContextField(
        description="Original affected segment identifier",
        index="tag",
    )

    replacement_segment_id: str = ContextField(
        description="Replacement segment identifier",
        index="tag",
    )

    reaccommodation_status: str = ContextField(
        description="Reaccommodation status",
        index="tag",
    )

    action_source: str = ContextField(
        description="Automatic or agent-driven reassignment source",
        index="tag",
    )

    reaccommodated_at: str = ContextField(
        description="Timestamp when the reassignment was applied",
    )

    reaccommodation_reason_code: str = ContextField(
        description="Why the reassignment was created",
        index="tag",
    )

    booking: Booking = ContextRelationship(
        description="Booking tied to this reaccommodation",
        source_field="booking_id",
    )

    original_segment: ItinerarySegment = ContextRelationship(
        description="Original disrupted segment",
        source_field="original_segment_id",
    )

    replacement_segment: ItinerarySegment = ContextRelationship(
        description="Replacement segment assigned to the traveller",
        source_field="replacement_segment_id",
    )


class SupportCase(ContextModel):
    """SupportCase entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_support_case:{support_case_id}"

    support_case_id: str = ContextField(
        description="Unique support case identifier",
        is_key_component=True,
    )

    customer_id: str = ContextField(
        description="Customer identifier",
        index="tag",
    )

    booking_id: str = ContextField(
        description="Related booking identifier",
        index="tag",
    )

    case_type: str = ContextField(
        description="Support case type",
        index="tag",
    )

    status: str = ContextField(
        description="Support case status",
        index="tag",
    )

    opened_at: str = ContextField(
        description="Case creation timestamp",
    )

    channel: str = ContextField(
        description="Channel used to open the case",
        index="tag",
    )

    summary: str = ContextField(
        description="Short support summary",
        index="text",
    )

    latest_note: str = ContextField(
        description="Most recent case note",
        index="text",
    )

    booking: Booking = ContextRelationship(
        description="Booking tied to this support case",
        source_field="booking_id",
    )


class TravelPolicyDoc(ContextModel):
    """TravelPolicyDoc entity for the Aurora Air domain."""

    __redis_key_template__ = "airline_support_travel_policy_doc:{doc_id}"

    doc_id: str = ContextField(
        description="Unique policy document identifier",
        is_key_component=True,
    )

    category: str = ContextField(
        description="Policy topic category",
        index="tag",
    )

    title: str = ContextField(
        description="Policy document title",
        index="text",
        weight=2.0,
    )

    content: str = ContextField(
        description="Policy document content",
        index="text",
    )

    content_embedding: list[float] = ContextField(
        description="Vector embedding for the document content",
        index="vector",
        vector_dim=1536,
        distance_metric="cosine",
    )
