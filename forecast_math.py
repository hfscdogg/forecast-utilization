"""
Python mirror of Deluge generate_forecast.dg.

Keep this logic line-for-line equivalent to the Deluge port. The event-type
taxonomy lives in event_types.py (Deluge equivalent: deluge/config.dg).

Reference: docs/spec_forecast.md Section 5, docs/field_mapping.md,
docs/decisions.md (Dustin 2026-05-18, sheet-derived corrections 2026-05-19).

NOTE on the utilization formula: the spec said hours_scheduled / 40. The real
formula (confirmed by Dustin 2026-05-19) is billable_hours_scheduled divided
by Forecast Hours, where Forecast Hours is the within-40 portion of scheduled
time (hours_scheduled minus the OT overflow). For a tech under 40 hours
Forecast Hours equals hours_scheduled. See docs/decisions.md.
"""

from datetime import datetime

from event_types import (
    event_category,
    is_assigned_to,
    qualifies_for_drive_adder,
    trip_charge_hours,
)

WEEKLY_OT_THRESHOLD_HRS = 40
DRIVE_TIME_ADDER_HRS = 0.5


def _parse_dt(s):
    if s is None:
        return None
    return datetime.fromisoformat(s)


def event_hours_in_window(event, window_start, window_end):
    """Pro-rate the event's wall-clock to the slice that falls inside
    [window_start, window_end]. Used to handle multi-day off-time markers
    (e.g., a 24h "Meeting -Non Billable" spanning Sun-Mon)."""
    start = _parse_dt(event.get("Start_DateTime"))
    end = _parse_dt(event.get("End_DateTime"))
    full = event.get("Duration_Hrs") or 0
    if start is None or end is None:
        return full
    overlap_start = max(start, window_start)
    overlap_end = min(end, window_end)
    if overlap_end <= overlap_start:
        return 0
    return (overlap_end - overlap_start).total_seconds() / 3600.0


def forecast_for_technician(technician, events, window_start=None, window_end=None):
    """Apply the forecast math for a single tech.

    No status filter: cancelled events carry a 1-minute duration by Livewire
    convention, so they self-neutralize in the hours sum.

    hours_scheduled is uncapped (matches the sheet's "Hours Scheduled" column).
    The 40-hour threshold only feeds forecast_ot.

    If window_start and window_end are provided, each event's hours are
    pro-rated to the slice that falls within the window. Otherwise the full
    Duration_Hrs is used (synthetic tests use this path).
    """
    tech_events = [e for e in events if is_assigned_to(e, technician)]

    billable_hours = 0.0
    non_billable_hours = 0.0
    training_hours = 0.0
    unknown_types = set()

    for e in tech_events:
        # Duration_Hrs is wall-clock per tech. Duration_Man_Hrs is the TOTAL
        # across all techs on the event (= wall × tech_count), so summing it
        # per-tech double-counts paired jobs.
        if window_start is not None and window_end is not None:
            hrs = event_hours_in_window(e, window_start, window_end)
        else:
            hrs = e.get("Duration_Hrs") or 0
        cat = event_category(e)
        if cat == "billable":
            # Trip charges labeled on the event are scheduled billable hours
            # on top of the wall-clock (Dustin 2026-08-07 and 2026-08-13:
            # the forecast "isn't factoring in trip charges"). Flat, so not
            # pro-rated to the window.
            billable_hours += hrs + trip_charge_hours(e)
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
    # "Forecast Hours" on the sheet — the within-40 portion (Hours Scheduled
    # minus the OT overflow). Equals hours_scheduled when the tech is under 40.
    forecast_hours = hours_scheduled - forecast_ot

    # Sheet formula (Dustin 2026-05-19): billable scheduled / Forecast Hours.
    if forecast_hours > 0:
        forecast_utilization = billable_hours / forecast_hours
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
