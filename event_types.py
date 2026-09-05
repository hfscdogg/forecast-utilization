"""
Shared CRM event-type taxonomy. Mirrors deluge/config.dg EVENT_TYPES_* lists.

This is CRM metadata, not a "system". Both the forecast (scheduled hours) and
the actuals (timecard hours) classify events the same way. Dustin's "two
separate systems" rule is about the HOURS SOURCE (scheduled vs timecard), not
the event-type taxonomy, so sharing this module does not violate it. The
Deluge equivalent of this shared module is deluge/config.dg.

Reference: docs/field_mapping.md, docs/decisions.md (Dustin 2026-05-18).
"""

EVENT_TYPES_BILLABLE = {
    "Trim-Out ($$$)",
    "Rough-In ($$$)",
    "Finish-Out ($$$)",
    "Discovery - Payment Required ($$$)",
    "Service - Payment Required ($$$)",
    "Retrofit ($$$)",
    "In-House Electrical",
}

EVENT_TYPES_NON_BILLABLE = {
    "Service - Warranty / Punchout",
    "Install - Warranty / Punchout",
    "Package Overage - Non Billable",
    "Meeting -Non Billable",
    "Project Management",
    "Undersold - Not Billable",
}

EVENT_TYPE_TRAINING = "Training"

# Deliberate, known exclusions — these do NOT get flagged as unknown.
EVENT_TYPES_EXCLUDED = {
    "Scheduled Off",
    "Place Holder",
    "Service Location",
    "-None-",
    None,
    "",
}

# On-site types: tech drives to a customer location, so the drive-time adder
# can apply (when there is no trip charge). Shop-based types (Training,
# Meeting, Project Management) are intentionally absent.
EVENT_TYPES_ONSITE = {
    "Trim-Out ($$$)",
    "Rough-In ($$$)",
    "Finish-Out ($$$)",
    "Discovery - Payment Required ($$$)",
    "Service - Payment Required ($$$)",
    "Retrofit ($$$)",
    "In-House Electrical",
    "Service - Warranty / Punchout",
    "Install - Warranty / Punchout",
    "Package Overage - Non Billable",
    "Undersold - Not Billable",
}

TRIP_CHARGE_NONE_VALUES = {None, "", "-None-", "0"}

# SOP: each trip charge is worth 2 billable hours on a solo event and
# 1 billable hour per tech on a paired event ("trip charge x 2 for solo /
# x 1 per tech for paired"). Trip_Charge holds the count of charges (1-4).
TRIP_CHARGE_HOURS_SOLO = 2.0
TRIP_CHARGE_HOURS_PAIRED_PER_TECH = 1.0

# Dustin 2026-08-31 (actuals) and 2026-09-04 (forecast): the billable report
# carries TWO trip-charge fields — one on the meeting (Trip_Charge) and one on
# the related service potential. Service potentials auto-created from meetings
# (98% of service scheduling) never populate their trip-charge field, and
# finish-out meetings created from a potential can carry a blank event-side
# value, so the two drift. The fetch layer merges the potential-side value
# onto the event under this key; Dustin's rule — "if its the same, discard one
# result, but if its different then keep the positive result" — is a max() of
# the two counts. Never sum them: they describe the same trip.
FIELD_POTENTIAL_TRIP_CHARGE = "Potential_Trip_Charge"

HELPER_NONE_VALUES = {None, "", "No Helper", "-None-"}

# Cancelled events are shrunk to a 1-minute duration and set to
# "Incomplete - Job Not Ready" (Dustin 2026-05-18). The tiny duration
# self-neutralizes in the hours sums, but the event keeps its Trip_Charge,
# which must not bill hours. Genuinely-not-ready jobs carry the same status
# with real durations, so the duration bound is what marks a cancellation.
EVENT_STATUS_NOT_READY = "Incomplete - Job Not Ready"
CANCELLED_EVENT_MAX_HOURS = 0.1


def event_category(event):
    """Return billable / non_billable / training / excluded / unknown."""
    et = event.get("Event_Type")
    if et in EVENT_TYPES_BILLABLE:
        return "billable"
    if et == EVENT_TYPE_TRAINING:
        return "training"
    if et in EVENT_TYPES_NON_BILLABLE:
        return "non_billable"
    if et in EVENT_TYPES_EXCLUDED:
        return "excluded"
    return "unknown"


def is_assigned_to(event, technician):
    """Tech is the Owner (primary) or the Helper1 (paired) on the event."""
    return event.get("Owner") == technician or event.get("Helper1") == technician


def _trip_charge_count(value):
    """Parse one trip-charge field value to a count; malformed or none-ish
    values contribute nothing rather than raising."""
    if value in TRIP_CHARGE_NONE_VALUES:
        return 0.0
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def effective_trip_charge_count(event):
    """Merged trip-charge count across the event-side and potential-side
    fields (Dustin's 2026-08-31 rule: equal values collapse to one, differing
    values keep the positive one — both cases are a max())."""
    return max(
        _trip_charge_count(event.get("Trip_Charge")),
        _trip_charge_count(event.get(FIELD_POTENTIAL_TRIP_CHARGE)),
    )


def has_trip_charge(event):
    return effective_trip_charge_count(event) > 0


def is_paired(event):
    return event.get("Helper1") not in HELPER_NONE_VALUES


def is_heuristically_cancelled(event):
    return (
        event.get("Event_Status") == EVENT_STATUS_NOT_READY
        and (event.get("Duration_Hrs") or 0) <= CANCELLED_EVENT_MAX_HOURS
    )


def trip_charge_hours(event):
    """Per-tech billable hours contributed by the event's trip charge(s).

    Dustin 2026-08-25: trip charges labeled on events must count toward Hours
    Billed. The count is the merged event/potential value (Dustin 2026-08-31,
    see effective_trip_charge_count). Cancelled events keep their trip charge
    but bill nothing."""
    if is_heuristically_cancelled(event):
        return 0.0
    count = effective_trip_charge_count(event)
    if count == 0:
        return 0.0
    if is_paired(event):
        return count * TRIP_CHARGE_HOURS_PAIRED_PER_TECH
    return count * TRIP_CHARGE_HOURS_SOLO


def qualifies_for_drive_adder(event):
    """0.5 hr adder applies to on-site events with no trip charge (Dustin
    2026-05-18). Trip charge present means the drive is already accounted for."""
    return event.get("Event_Type") in EVENT_TYPES_ONSITE and not has_trip_charge(event)
