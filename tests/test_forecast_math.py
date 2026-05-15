"""
Python mirror of the Deluge forecast math. Tests live here; the production
implementation will be ported to deluge/generate_forecast.dg once it matches
Dustin's manual output for a known historical week.

Run: pytest tests/

Reference: docs/spec_forecast.md Section 5 (forecast math) and the OT/40-hour
cap rules.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecast_math import forecast_for_technician  # noqa: E402


def make_event(
    technician_1: str,
    duration_hrs: float,
    *,
    event_type: str = "Billable",
    status: str = "Scheduled",
    technician_2: str | None = None,
    start_iso: str = "2026-05-18T09:00:00",
    has_trip_charge: bool = True,
) -> dict:
    return {
        "Owner": technician_1,
        "Technician_2": technician_2,
        "Duration_Man_Hrs": duration_hrs,
        "Event_Type": event_type,
        "Status": status,
        "Start_DateTime": start_iso,
        "has_trip_charge": has_trip_charge,
    }


def test_jim_zimmerman_example_solo_plus_paired_sums_to_five():
    """SOP Section 5.1 worked example: 2hr May 12 + 2hr May 15 + 1hr paired with
    Jordan on May 14 = 5 billable hours for Jim."""
    events = [
        make_event("Jim", 2.0, start_iso="2026-05-12T09:00:00"),
        make_event("Jim", 2.0, start_iso="2026-05-15T09:00:00"),
        make_event("Jim", 1.0, technician_2="Jordan", start_iso="2026-05-14T09:00:00"),
    ]
    result = forecast_for_technician("Jim", events)
    assert result["billable_hours_scheduled"] == pytest.approx(5.0)


def test_forty_hour_cap_overflows_into_ot():
    events = [make_event("Andy", 45.0)]
    result = forecast_for_technician("Andy", events)
    assert result["hours_scheduled"] == 40
    assert result["forecast_ot"] == pytest.approx(5.0)
    assert result["forecast_hours"] == pytest.approx(45.0)
    assert result["forecast_utilization"] == pytest.approx(1.0)


def test_under_forty_hours_no_ot():
    events = [make_event("Ben", 30.0)]
    result = forecast_for_technician("Ben", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)
    assert result["forecast_ot"] == 0
    assert result["forecast_utilization"] == pytest.approx(0.75)


def test_pto_excluded_entirely():
    """Dustin 2026-05-13: PTO does not factor into the forecast at all."""
    events = [
        make_event("Drake", 30.0, event_type="Billable"),
        make_event("Drake", 8.0, event_type="PTO"),
    ]
    result = forecast_for_technician("Drake", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)


def test_cancelled_events_excluded():
    events = [
        make_event("Greg", 30.0),
        make_event("Greg", 8.0, status="Cancelled"),
    ]
    result = forecast_for_technician("Greg", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)


def test_paired_tech_counted_when_technician_2_matches():
    events = [
        make_event("Jordan", 2.0, technician_2="Jim"),
        make_event("Patrick", 3.0, technician_2="Jim"),
    ]
    result = forecast_for_technician("Jim", events)
    assert result["billable_hours_scheduled"] == pytest.approx(5.0)


def test_training_counts_as_worked_and_flagged_if_drives_ot():
    """Spec Section 5.5: training counts as worked hours, flag it if it drives OT."""
    events = [
        make_event("Anthony", 36.0, event_type="Billable"),
        make_event("Anthony", 6.0, event_type="Training"),
    ]
    result = forecast_for_technician("Anthony", events)
    assert result["hours_scheduled"] == 40
    assert result["forecast_ot"] == pytest.approx(2.0)
    assert result.get("training_drove_ot") is True
