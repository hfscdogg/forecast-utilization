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
    "Service - Warranty / Punchout",
    "Install - Warranty / Punchout",
    "Package Overage - Non Billable",
    "Undersold - Not Billable",
}

TRIP_CHARGE_NONE_VALUES = {None, "", "-None-", "0"}


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


def has_trip_charge(event):
    return event.get("Trip_Charge") not in TRIP_CHARGE_NONE_VALUES


def qualifies_for_drive_adder(event):
    """0.5 hr adder applies to on-site events with no trip charge (Dustin
    2026-05-18). Trip charge present means the drive is already accounted for."""
    return event.get("Event_Type") in EVENT_TYPES_ONSITE and not has_trip_charge(event)
