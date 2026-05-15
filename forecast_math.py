"""
Python mirror of Deluge generate_forecast.dg.

Keep this file's logic line-for-line equivalent to the Deluge port. Any change
here must be reflected in deluge/generate_forecast.dg and vice versa. The
pytest suite under tests/ is the contract.

Reference: docs/spec_forecast.md Section 5.
"""

WEEKLY_CAP_HRS = 40
NON_TRIP_ADDER_HRS = 0.5


def is_assigned_to(event: dict, technician: str) -> bool:
    return event.get("Owner") == technician or event.get("Technician_2") == technician


def is_active_billable(event: dict) -> bool:
    return event.get("Event_Type") == "Billable" and event.get("Status") != "Cancelled"


def is_active_non_billable(event: dict) -> bool:
    return (
        event.get("Event_Type") in ("Non-Billable", "Training")
        and event.get("Status") != "Cancelled"
    )


def forecast_for_technician(technician: str, events: list[dict]) -> dict:
    """Apply spec Section 5 forecast math for a single tech."""
    tech_events = [e for e in events if is_assigned_to(e, technician)]

    billable_events = [e for e in tech_events if is_active_billable(e)]
    non_billable_events = [e for e in tech_events if is_active_non_billable(e)]

    billable_hours_scheduled = sum(e["Duration_Man_Hrs"] for e in billable_events)
    non_billable_hours = sum(e["Duration_Man_Hrs"] for e in non_billable_events)

    non_trip_event_count = sum(
        1 for e in tech_events if is_active_non_billable(e) and not e.get("has_trip_charge", True)
    )
    drive_time_adder = NON_TRIP_ADDER_HRS * non_trip_event_count

    raw_hours_scheduled = billable_hours_scheduled + non_billable_hours + drive_time_adder

    if raw_hours_scheduled > WEEKLY_CAP_HRS:
        hours_scheduled = WEEKLY_CAP_HRS
        forecast_ot = raw_hours_scheduled - WEEKLY_CAP_HRS
    else:
        hours_scheduled = raw_hours_scheduled
        forecast_ot = 0

    forecast_hours = hours_scheduled + forecast_ot
    forecast_utilization = hours_scheduled / WEEKLY_CAP_HRS

    training_hours = sum(
        e["Duration_Man_Hrs"] for e in non_billable_events if e.get("Event_Type") == "Training"
    )
    training_drove_ot = forecast_ot > 0 and training_hours > 0

    return {
        "technician": technician,
        "billable_hours_scheduled": billable_hours_scheduled,
        "non_billable_hours": non_billable_hours,
        "hours_scheduled": hours_scheduled,
        "forecast_ot": forecast_ot,
        "forecast_hours": forecast_hours,
        "forecast_utilization": forecast_utilization,
        "training_drove_ot": training_drove_ot,
    }
