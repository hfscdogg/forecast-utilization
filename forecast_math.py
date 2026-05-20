"""
Python mirror of Deluge generate_forecast.dg.

Keep this logic line-for-line equivalent to the Deluge port. The event-type
taxonomy lives in event_types.py (Deluge equivalent: deluge/config.dg).

Reference: docs/spec_forecast.md Section 5, docs/field_mapping.md,
docs/decisions.md (Dustin 2026-05-18 answers).
"""

from event_types import (
    EVENT_TYPE_TRAINING,
    event_category,
    is_assigned_to,
    qualifies_for_drive_adder,
)

WEEKLY_CAP_HRS = 40
DRIVE_TIME_ADDER_HRS = 0.5


def forecast_for_technician(technician, events):
    """Apply spec Section 5 forecast math for a single tech.

    No status filter: cancelled events carry a 1-minute duration by Livewire
    convention, so they self-neutralize in the hours sum.
    """
    tech_events = [e for e in events if is_assigned_to(e, technician)]

    billable_hours = 0.0
    non_billable_hours = 0.0
    training_hours = 0.0
    unknown_types = set()

    for e in tech_events:
        hrs = e.get("Duration_Man_Hrs") or 0
        cat = event_category(e)
        if cat == "billable":
            billable_hours += hrs
        elif cat == "non_billable":
            non_billable_hours += hrs
        elif cat == "training":
            training_hours += hrs
        elif cat == "unknown":
            unknown_types.add(e.get("Event_Type"))
        # excluded: contributes no hours

    drive_adder = DRIVE_TIME_ADDER_HRS * sum(
        1 for e in tech_events if qualifies_for_drive_adder(e)
    )

    raw_hours_scheduled = (
        billable_hours + non_billable_hours + training_hours + drive_adder
    )

    if raw_hours_scheduled > WEEKLY_CAP_HRS:
        hours_scheduled = WEEKLY_CAP_HRS
        forecast_ot = raw_hours_scheduled - WEEKLY_CAP_HRS
    else:
        hours_scheduled = raw_hours_scheduled
        forecast_ot = 0

    forecast_hours = hours_scheduled + forecast_ot
    forecast_utilization = hours_scheduled / WEEKLY_CAP_HRS

    training_drove_ot = forecast_ot > 0 and training_hours > 0

    return {
        "technician": technician,
        "billable_hours_scheduled": billable_hours,
        "non_billable_hours": non_billable_hours,
        "training_hours": training_hours,
        "drive_time_adder": drive_adder,
        "hours_scheduled": hours_scheduled,
        "forecast_ot": forecast_ot,
        "forecast_hours": forecast_hours,
        "forecast_utilization": forecast_utilization,
        "training_drove_ot": training_drove_ot,
        "unknown_event_types": sorted(t for t in unknown_types if t is not None),
    }
