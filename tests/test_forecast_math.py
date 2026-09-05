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
    potential_trip_charge=None,
    start_iso="2026-05-18T09:00:00-04:00",
):
    return {
        "Owner": owner,
        "Helper1": helper1,
        "Duration_Hrs": duration_hrs,
        "Duration_Man_Hrs": duration_hrs,  # equal for solo events in tests
        "Event_Type": event_type,
        "Event_Status": event_status,
        "Trip_Charge": trip_charge,
        "Potential_Trip_Charge": potential_trip_charge,
        "Start_DateTime": start_iso,
    }


def test_jim_zimmerman_example_solo_plus_paired_sums_to_five():
    """SOP Section 5.1 trip-charge walkthrough: one charge is worth 2 hrs on
    each solo event and 1 hr on the event paired with Jordan = 5 billable
    hrs from trip charges alone. No drive adder on trip-charged events."""
    events = [
        make_event("Jim", 0.0, trip_charge="1", start_iso="2026-05-12T09:00:00-04:00"),
        make_event("Jim", 0.0, trip_charge="1", start_iso="2026-05-15T09:00:00-04:00"),
        make_event("Jim", 0.0, helper1="Jordan", trip_charge="1"),
    ]
    result = forecast_for_technician("Jim", events)
    assert result["billable_hours_scheduled"] == pytest.approx(5.0)
    assert result["drive_time_adder"] == 0


def test_trip_charge_adds_two_hours_per_charge_for_solo_tech():
    """SOP: trip charge x 2 for solo. A "2" on a solo event adds 4 scheduled
    billable hours on top of wall-clock (Dustin 2026-08-07: Andre's time was
    right "except it didnt account for a trip charge 2")."""
    events = [make_event("Andre", 8.0, trip_charge="2")]
    result = forecast_for_technician("Andre", events)
    assert result["billable_hours_scheduled"] == pytest.approx(8.0 + 4.0)
    assert result["drive_time_adder"] == 0


def test_trip_charge_adds_one_hour_per_charge_per_tech_when_paired():
    events = [make_event("Jason", 4.0, helper1="Josh Brown", trip_charge="1")]
    for tech in ("Jason", "Josh Brown"):
        result = forecast_for_technician(tech, events)
        assert result["billable_hours_scheduled"] == pytest.approx(4.0 + 1.0)


def test_utilization_is_billable_over_scheduled():
    """Sheet-confirmed formula: billable_hours_scheduled / hours_scheduled.
    20 billable + 5 non-billable -> 20 / 25 = 0.80."""
    events = [
        make_event("Sam", 18.0, event_type="Finish-Out ($$$)", trip_charge="1"),  # +2 trip hrs = 20
        make_event("Sam", 5.0, event_type="Project Management"),
    ]
    result = forecast_for_technician("Sam", events)
    assert result["forecast_utilization"] == pytest.approx(0.80)


def test_over_forty_hours_splits_into_forecast_hours_and_ot():
    """Hours Scheduled is uncapped. Forecast Hours is the within-40 portion
    (Hours Scheduled minus the OT overflow). Utilization divides by the
    uncapped Hours Scheduled — dividing by the capped Forecast Hours gave
    over-40 techs a false 100%+ (matches generate_forecast.dg, verified
    against Dustin's 8/10-8/16 sheet: Patrick and Thomas at 95.24%)."""
    events = [make_event("Andy", 43.0, trip_charge="1")]  # +2 trip hrs = 45
    result = forecast_for_technician("Andy", events)
    assert result["hours_scheduled"] == pytest.approx(45.0)
    assert result["forecast_ot"] == pytest.approx(5.0)
    assert result["forecast_hours"] == pytest.approx(40.0)
    assert result["forecast_utilization"] == pytest.approx(1.0)  # all billable, bounded at 100%


def test_under_forty_hours_no_ot():
    events = [make_event("Ben", 28.0, trip_charge="1")]  # +2 trip hrs = 30
    result = forecast_for_technician("Ben", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)
    assert result["forecast_ot"] == 0
    assert result["forecast_utilization"] == pytest.approx(1.0)  # all billable


def test_scheduled_off_excluded_entirely():
    """Dustin 2026-05-18: Scheduled Off means the tech is not working — do not count."""
    events = [
        make_event("Drake", 28.0, trip_charge="1"),  # +2 trip hrs = 30
        make_event("Drake", 8.0, event_type="Scheduled Off"),
    ]
    result = forecast_for_technician("Drake", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)


def test_service_location_excluded_entirely():
    """Service Location is Dustin's online-booking blocker — not counted at all."""
    events = [
        make_event("Greg", 28.0, trip_charge="1"),  # +2 trip hrs = 30
        make_event("Greg", 8.0, event_type="Service Location"),
    ]
    result = forecast_for_technician("Greg", events)
    assert result["hours_scheduled"] == pytest.approx(30.0)


def test_cancelled_event_self_neutralizes_via_one_minute_duration():
    """Dustin 2026-05-18: cancelled events get a 1-minute duration and status
    Incomplete - Job Not Ready. No status filter needed."""
    events = [
        make_event("Greg", 28.0, trip_charge="1"),  # +2 trip hrs = 30
        # Cancelled events keep their Trip_Charge; it must not bill hours.
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
    # 2 + 3 wall-clock plus 1 trip hr per paired event
    assert result["billable_hours_scheduled"] == pytest.approx(7.0)


def test_training_counts_as_worked_and_flagged_if_drives_ot():
    """Training counts as worked hours, flag it if it drives OT. Training is
    shop-based so it gets no drive adder."""
    events = [
        make_event("Anthony", 34.0, trip_charge="1"),  # +2 trip hrs = 36
        make_event("Anthony", 6.0, event_type="Training"),
    ]
    result = forecast_for_technician("Anthony", events)
    assert result["training_hours"] == pytest.approx(6.0)
    assert result["hours_scheduled"] == pytest.approx(42.0)
    assert result["forecast_ot"] == pytest.approx(2.0)
    assert result["forecast_hours"] == pytest.approx(40.0)
    assert result["training_drove_ot"] is True
    # Denominator is the uncapped Hours Scheduled, not the capped 40.
    assert result["forecast_utilization"] == pytest.approx(36.0 / 42.0)


def test_potential_only_trip_charge_counts_and_suppresses_adder():
    """Dustin 2026-09-04 ("Trip charges" — his diagnosis of the 9/7-9/13
    forecast delta): a trip charge living only on the potential must add
    scheduled billable hours AND suppress the drive-time adder, exactly as
    an event-side charge would."""
    events = [
        make_event("Jim", 6.0, trip_charge=None, potential_trip_charge="1"),
    ]
    result = forecast_for_technician("Jim", events)
    assert result["billable_hours_scheduled"] == pytest.approx(8.0)  # 6 + 1 x 2
    assert result["drive_time_adder"] == 0.0


def test_matching_event_and_potential_trip_charges_count_once():
    """Dustin's rule: equal values on the two fields describe the same trip
    and collapse to one — never sum."""
    events = [make_event("Andre", 8.0, trip_charge="2", potential_trip_charge="2")]
    result = forecast_for_technician("Andre", events)
    assert result["billable_hours_scheduled"] == pytest.approx(12.0)  # 8 + 2 x 2


def test_differing_trip_charges_keep_the_positive_result():
    events = [make_event("Jason", 4.0, trip_charge="2", potential_trip_charge=None)]
    result = forecast_for_technician("Jason", events)
    assert result["billable_hours_scheduled"] == pytest.approx(8.0)  # event "2" x 2


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
    # 8 wall-clock + 4 trip hrs, no adder
    assert result["hours_scheduled"] == pytest.approx(12.0)


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
    # 12 wall-clock + 2 trip hrs + 1.0 adder
    assert result["hours_scheduled"] == pytest.approx(15.0)


def test_non_billable_tracked_separately_from_billable():
    events = [
        make_event("Sam", 18.0, event_type="Finish-Out ($$$)", trip_charge="1"),  # +2 trip hrs = 20
        make_event("Sam", 5.0, event_type="Project Management"),
    ]
    result = forecast_for_technician("Sam", events)
    assert result["billable_hours_scheduled"] == pytest.approx(20.0)
    assert result["non_billable_hours"] == pytest.approx(5.0)
    assert result["hours_scheduled"] == pytest.approx(25.0)


def test_prorate_event_to_window_slice():
    """A 24h event spanning Sun 8pm to Mon 8pm contributes only 4 hours to a
    Mon-Sun forecast week (the slice from Sun 8pm to Sun midnight)."""
    from datetime import datetime
    events = [
        {
            "Owner": "Jim",
            "Helper1": "No Helper",
            "Event_Type": "Meeting -Non Billable",
            "Trip_Charge": None,
            "Duration_Hrs": 24,
            "Start_DateTime": "2026-05-24T20:00:00-04:00",
            "End_DateTime": "2026-05-25T19:59:59-04:00",
        }
    ]
    window_start = datetime.fromisoformat("2026-05-18T00:00:00-04:00")
    window_end = datetime.fromisoformat("2026-05-24T23:59:59-04:00")
    result = forecast_for_technician("Jim", events, window_start, window_end)
    # 8pm to 23:59:59 on Sunday = ~4 hours of overlap
    assert result["non_billable_hours"] == pytest.approx(4.0, abs=0.05)
    assert result["hours_scheduled"] == pytest.approx(4.0, abs=0.05)


def test_unknown_event_type_flagged_not_silently_dropped():
    """Types Dustin confirmed unused (e.g. Remote Assistance) should surface
    if they appear — a data-entry mistake worth flagging."""
    events = [
        make_event("Pat", 8.0, event_type="Finish-Out ($$$)", trip_charge="1"),  # +2 trip hrs = 10
        make_event("Pat", 3.0, event_type="Remote Assistance (Payment Required)"),
    ]
    result = forecast_for_technician("Pat", events)
    assert result["unknown_event_types"] == ["Remote Assistance (Payment Required)"]
    assert result["hours_scheduled"] == pytest.approx(10.0)
