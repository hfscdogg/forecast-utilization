"""
Tests for the forecast math. Event types are the real CRM picklist values
confirmed by the inspector run (2026-05-18) and categorized by Dustin.

Forecast utilization = billable_hours_scheduled / hours_scheduled, confirmed
from Dustin's live spreadsheet (2026-05-19). hours_scheduled is uncapped.

Run: pytest tests/test_forecast_math.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from forecast_math import forecast_for_technician  # noqa: E402


def make_event(
    owner,
    duration_hrs,
    *,
    event_type="Finish-Out ($$$)",
    event_status=None,
    helper1="No Helper",
    trip_charge=None,
    start_iso="2026-05-18T09:00:00-04:00",
):
    return {
        "Owner": owner,
        "Helper1": helper1,
        "Duration_Man_Hrs": duration_hrs,
        "Event_Type": event_type,
        "Event_Status": event_status,
        "Trip_Charge": trip_charge,
        "Start_DateTime": start_iso,
    }


def test_jim_zimmerman_example_solo_plus_paired_sums_to_five():
    """SOP Section 5.1: 2hr + 2hr solo + 1hr paired with Jordan = 5 billable hrs.
    All carry trip charges so no drive adder applies."""
    events = [
        make_event("Jim", 2.0, trip_charge="1", start_iso="2026-05-12T09:00:00-04:00"),
        make_event("Jim", 2.0, trip_charge="1", start_iso="2026-05-15T09:00:00-04:00"),
        make_event("Jim", 1.0, helper1="Jordan", trip_charge="1"),
    ]
    result = forecast_for_technician("Jim", events)
    assert result["billable_hours_scheduled"] == pytest.approx(5.0)
    assert result["drive_time_adder"] == 0


def test_utilization_is_billable_over_scheduled():
    """Sheet-confirmed formula: billable_hours_scheduled / hours_scheduled.
    20 billable + 5 non-billable -> 20 / 25 = 0.80."""
    events = [
        make_event("Sam", 20.0, event_type="Finish-Out ($$$)", trip_charge="1"),
        make_event("Sam", 5.0, event_type="Project Management"),
    ]
    result = forecast_for_technician("Sam", events)
    assert result["forecast_utilization"] == pytest.approx(0.80)


def test_over_forty_hours_splits_into_forecast_hours_and_ot():
    """Hours Scheduled is uncapped. Forecast Hours is the within-40 portion
    (Hours Scheduled minus the OT overflow). Utilization uses Forecast Hours."""
    events = [make_event("Andy", 45.0, trip_charge="1")]
    result = forecast_for_technician("Andy", events)
    assert result["hours_scheduled"] == pytest.approx(45.0)
    assert result["forecast_ot"] == pytest.approx(5.0)
    assert result["forecast_hours"] == pytest.approx(40.0)
    assert result["forecast_utilization"] == pytest.approx(45.0 / 40.0)  # 112.5%


def test_under_forty_hours_no_ot():
    events = [make_event("Ben", 30.0, trip_charge="1")]
    result = forecast_for_technician("Ben", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)
    assert result["forecast_ot"] == 0
    assert result["forecast_utilization"] == pytest.approx(1.0)  # all billable


def test_scheduled_off_excluded_entirely():
    """Dustin 2026-05-18: Scheduled Off means the tech is not working — do not count."""
    events = [
        make_event("Drake", 30.0, trip_charge="1"),
        make_event("Drake", 8.0, event_type="Scheduled Off"),
    ]
    result = forecast_for_technician("Drake", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)


def test_service_location_excluded_entirely():
    """Service Location is Dustin's online-booking blocker — not counted at all."""
    events = [
        make_event("Greg", 30.0, trip_charge="1"),
        make_event("Greg", 8.0, event_type="Service Location"),
    ]
    result = forecast_for_technician("Greg", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)


def test_cancelled_event_self_neutralizes_via_one_minute_duration():
    """Dustin 2026-05-18: cancelled events get a 1-minute duration and status
    Incomplete - Job Not Ready. No status filter needed."""
    events = [
        make_event("Greg", 30.0, trip_charge="1"),
        make_event(
            "Greg",
            0.0167,
            event_status="Incomplete - Job Not Ready",
            trip_charge="1",
        ),
    ]
    result = forecast_for_technician("Greg", events)
    assert result["hours_scheduled"] == pytest.approx(30.0167, abs=0.001)


def test_paired_tech_counted_when_helper1_matches():
    events = [
        make_event("Jordan", 2.0, helper1="Jim", trip_charge="1"),
        make_event("Patrick", 3.0, helper1="Jim", trip_charge="1"),
    ]
    result = forecast_for_technician("Jim", events)
    assert result["billable_hours_scheduled"] == pytest.approx(5.0)


def test_training_counts_as_worked_and_flagged_if_drives_ot():
    """Training counts as worked hours, flag it if it drives OT. Training is
    shop-based so it gets no drive adder."""
    events = [
        make_event("Anthony", 36.0, trip_charge="1"),
        make_event("Anthony", 6.0, event_type="Training"),
    ]
    result = forecast_for_technician("Anthony", events)
    assert result["training_hours"] == pytest.approx(6.0)
    assert result["hours_scheduled"] == pytest.approx(42.0)
    assert result["forecast_ot"] == pytest.approx(2.0)
    assert result["forecast_hours"] == pytest.approx(40.0)
    assert result["training_drove_ot"] is True
    assert result["forecast_utilization"] == pytest.approx(36.0 / 40.0)


def test_drive_adder_applies_to_onsite_event_without_trip_charge():
    """Dustin 2026-05-18: 0.5 hr adder for on-site events with no trip charge."""
    events = [make_event("Tom", 8.0, event_type="Finish-Out ($$$)", trip_charge=None)]
    result = forecast_for_technician("Tom", events)
    assert result["drive_time_adder"] == pytest.approx(0.5)
    assert result["hours_scheduled"] == pytest.approx(8.5)
    assert result["forecast_utilization"] == pytest.approx(8.0 / 8.5)


def test_drive_adder_skipped_when_trip_charge_present():
    events = [make_event("Tom", 8.0, event_type="Finish-Out ($$$)", trip_charge="2")]
    result = forecast_for_technician("Tom", events)
    assert result["drive_time_adder"] == 0
    assert result["hours_scheduled"] == pytest.approx(8.0)


def test_drive_adder_skipped_for_shop_based_events():
    """Training / Meeting at the shop get no adder even with no trip charge."""
    events = [
        make_event("Tom", 4.0, event_type="Training", trip_charge=None),
        make_event("Tom", 2.0, event_type="Meeting -Non Billable", trip_charge=None),
    ]
    result = forecast_for_technician("Tom", events)
    assert result["drive_time_adder"] == 0
    assert result["hours_scheduled"] == pytest.approx(6.0)


def test_drive_adder_accumulates_per_qualifying_event():
    events = [
        make_event("Tom", 4.0, event_type="Trim-Out ($$$)", trip_charge=None),
        make_event("Tom", 4.0, event_type="Rough-In ($$$)", trip_charge=None),
        make_event("Tom", 4.0, event_type="Finish-Out ($$$)", trip_charge="1"),
    ]
    result = forecast_for_technician("Tom", events)
    assert result["drive_time_adder"] == pytest.approx(1.0)  # 2 qualifying events
    assert result["hours_scheduled"] == pytest.approx(13.0)


def test_non_billable_tracked_separately_from_billable():
    events = [
        make_event("Sam", 20.0, event_type="Finish-Out ($$$)", trip_charge="1"),
        make_event("Sam", 5.0, event_type="Project Management"),
    ]
    result = forecast_for_technician("Sam", events)
    assert result["billable_hours_scheduled"] == pytest.approx(20.0)
    assert result["non_billable_hours"] == pytest.approx(5.0)
    assert result["hours_scheduled"] == pytest.approx(25.0)


def test_unknown_event_type_flagged_not_silently_dropped():
    """Types Dustin confirmed unused (e.g. Remote Assistance) should surface
    if they appear — a data-entry mistake worth flagging."""
    events = [
        make_event("Pat", 10.0, event_type="Finish-Out ($$$)", trip_charge="1"),
        make_event("Pat", 3.0, event_type="Remote Assistance (Payment Required)"),
    ]
    result = forecast_for_technician("Pat", events)
    assert result["unknown_event_types"] == ["Remote Assistance (Payment Required)"]
    assert result["hours_scheduled"] == pytest.approx(10.0)
