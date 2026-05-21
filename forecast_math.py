"""
Python mirror of Deluge generate_forecast.dg.

Keep this logic line-for-line equivalent to the Deluge port. The event-type
taxonomy lives in event_types.py (Deluge equivalent: deluge/config.dg).

Reference: docs/spec_forecast.md Section 5, docs/field_mapping.md,
docs/decisions.md (Dustin 2026-05-18, sheet-derived corrections 2026-05-19).

NOTE on the utilization formula: the spec said hours_scheduled / 40, but
every row of Dustin's live spreadsheet computes it as billable_hours_scheduled
/ hours_scheduled. The sheet is authoritative — it IS Dustin's manual output.
See docs/decisions.md "2026-05-19 — sheet-derived corrections".
"""

from event_types import (
    event_category,
    is_assigned_to,
    qualifies_for_drive_adder,
)

WEEKLY_OT_THRESHOLD_HRS = 40
DRIVE_TIME_ADDER_HRS = 0.5


def forecast_for_technician(technician, events):
    """Apply the forecast math for a single tech.

    No status filter: cancelled events carry a 1-minute duration by Livewire
    convention, so they self-neutralize in the hours sum.

    hours_scheduled is uncapped (matches the sheet's "Hours Scheduled" column).
    The 40-hour threshold only feeds forecast_ot.
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

    # "Hours Scheduled" on the sheet — uncapped total of all counted time.
    hours_scheduled = (
        billable_hours + non_billable_hours + training_hours + drive_adder
    )

    forecast_ot = max(0.0, hours_scheduled - WEEKLY_OT_THRESHOLD_HRS)
    forecast_hours = hours_scheduled

    # Sheet formula: billable scheduled / total scheduled.
    if hours_scheduled > 0:
        forecast_utilization = billable_hours / hours_scheduled
    else:
        forecast_utilization = 0

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
