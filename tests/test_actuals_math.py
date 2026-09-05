"""
Tests for the lagging actuals math. Spreadsheet-verified examples from Dustin's
live Billable Hours Reporting sheet (read 2026-05-15) drive the OT-premium
expectations. Event types are the real CRM picklist values (2026-05-18).

Run: pytest tests/test_actuals_math.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actuals_math import actuals_for_technician, company_rollup  # noqa: E402


def make_event(
    owner,
    duration_hrs,
    *,
    event_type="Finish-Out ($$$)",
    event_status=None,
    helper1="No Helper",
    trip_charge=None,
    potential_trip_charge=None,
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
    }


def test_grant_spreadsheet_example_with_ot_at_time_and_a_half():
    """Live spreadsheet: Grant Hours Worked 40, OT 2.88, Actual Hours Paid 44.32.
    40 + 2.88 * 1.5 = 44.32 exactly."""
    events = [make_event("Grant", 29.11)]
    result = actuals_for_technician("Grant", events, time_card_total=42.88)
    assert result["hours_worked"] == 40
    assert result["ot"] == pytest.approx(2.88)
    assert result["actual_hours_paid"] == pytest.approx(44.32)
    assert result["actual_utilization"] == pytest.approx(29.11 / 44.32, rel=1e-3)


def test_stephen_spreadsheet_example_with_ot():
    """Live spreadsheet: Stephen Hours Worked 40, OT 3.92, Actual Hours Paid 45.88."""
    events = [make_event("Stephen", 29.0)]
    result = actuals_for_technician("Stephen", events, time_card_total=43.92)
    assert result["hours_worked"] == 40
    assert result["ot"] == pytest.approx(3.92)
    assert result["actual_hours_paid"] == pytest.approx(45.88)


def test_josh_spreadsheet_example_no_ot():
    """Live spreadsheet: Josh Hours Worked 35.57, no OT, Actual Hours Paid 35.57."""
    events = [make_event("Josh", 26.61)]
    result = actuals_for_technician("Josh", events, time_card_total=35.57)
    assert result["hours_worked"] == pytest.approx(35.57)
    assert result["ot"] == 0
    assert result["actual_hours_paid"] == pytest.approx(35.57)
    assert result["actual_utilization"] == pytest.approx(26.61 / 35.57, rel=1e-3)


def test_zero_time_card_does_not_divide_by_zero():
    result = actuals_for_technician("Ghost", [], time_card_total=0)
    assert result["actual_utilization"] == 0
    assert result["worked_utilization"] == 0


def test_hours_billed_can_exceed_forty():
    """Per SOP: Hours Billed CAN exceed 40 (no cap on the billed side)."""
    events = [make_event("Joe", 45.0)]
    result = actuals_for_technician("Joe", events, time_card_total=50.0)
    assert result["hours_billed"] == pytest.approx(45.0)
    assert result["hours_worked"] == 40
    assert result["ot"] == pytest.approx(10.0)


def test_cancelled_event_self_neutralizes():
    """Cancelled events get a 1-minute duration — no status filter needed."""
    events = [
        make_event("Ben", 30.0),
        make_event("Ben", 0.0167, event_status="Incomplete - Job Not Ready"),
    ]
    result = actuals_for_technician("Ben", events, time_card_total=38.0)
    assert result["hours_billed"] == pytest.approx(30.0167, abs=0.001)


def test_non_billable_event_type_tracked_separately():
    events = [
        make_event("Sam", 30.0, event_type="Finish-Out ($$$)"),
        make_event("Sam", 6.0, event_type="Project Management"),
    ]
    result = actuals_for_technician("Sam", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(30.0)
    assert result["non_billable_hours"] == pytest.approx(6.0)


def test_paired_tech_counted_via_helper1():
    events = [make_event("Jordan", 4.0, helper1="Jim")]
    result = actuals_for_technician("Jim", events, time_card_total=20.0)
    assert result["hours_billed"] == pytest.approx(4.0)


def test_isolved_pending_returns_none_for_timecard_fields():
    """When time_card_total is None (iSolved access not yet wired), the
    timecard-derived fields all come back None but Hours Billed and
    Non-Billable Hours still populate from CRM."""
    events = [
        make_event("Sam", 30.0, event_type="Finish-Out ($$$)"),
        make_event("Sam", 6.0, event_type="Project Management"),
    ]
    result = actuals_for_technician("Sam", events, time_card_total=None)
    assert result["hours_billed"] == pytest.approx(30.0)
    assert result["non_billable_hours"] == pytest.approx(6.0)
    assert result["hours_worked"] is None
    assert result["ot"] is None
    assert result["actual_hours_paid"] is None
    assert result["actual_utilization"] is None
    assert result["worked_utilization"] is None


def test_trip_charge_adds_two_hours_per_charge_for_solo_tech():
    """SOP: trip charge x 2 for solo. Trip_Charge is a count, so a
    "2" on a solo event adds 4 billed hours on top of wall-clock."""
    events = [make_event("Andre", 8.0, trip_charge="2")]
    result = actuals_for_technician("Andre", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(8.0 + 4.0)


def test_trip_charge_adds_one_hour_per_charge_per_tech_when_paired():
    """SOP: trip charge x 1 per tech for paired."""
    events = [make_event("Jason", 4.0, helper1="Josh Brown", trip_charge="1")]
    for tech in ("Jason", "Josh Brown"):
        result = actuals_for_technician(tech, events, time_card_total=40.0)
        assert result["hours_billed"] == pytest.approx(4.0 + 1.0)


def test_no_trip_charge_values_add_nothing():
    for tc in (None, "", "-None-", "0"):
        events = [make_event("Jim", 6.0, trip_charge=tc)]
        result = actuals_for_technician("Jim", events, time_card_total=40.0)
        assert result["hours_billed"] == pytest.approx(6.0)


def test_trip_charge_on_non_billable_event_not_billed():
    """A warranty visit's trip charge doesn't create billed hours; Hours
    Billed comes from the Billable Report only (SOP)."""
    events = [
        make_event("Sam", 3.0, event_type="Service - Warranty / Punchout", trip_charge="1"),
    ]
    result = actuals_for_technician("Sam", events, time_card_total=40.0)
    assert result["hours_billed"] == 0
    assert result["non_billable_hours"] == pytest.approx(3.0)


def test_sop_jim_zimmerman_trip_charge_walkthrough():
    """SOP example: two solo trip-charge jobs at 2 hrs each plus one paired
    with Jordan at 1 hr = 5 trip-charge hours for Jim."""
    events = [
        make_event("Jim", 0.0, trip_charge="1"),
        make_event("Jim", 0.0, trip_charge="1"),
        make_event("Jim", 0.0, helper1="Jordan", trip_charge="1"),
    ]
    result = actuals_for_technician("Jim", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(5.0)


def test_trip_charge_on_cancelled_event_not_billed():
    """Cancelled events (1-minute duration, Incomplete - Job Not Ready) keep
    their Trip_Charge but must not bill trip hours."""
    events = [
        make_event(
            "Ben",
            0.0167,
            event_status="Incomplete - Job Not Ready",
            trip_charge="2",
        ),
    ]
    result = actuals_for_technician("Ben", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(0.0167, abs=0.001)


def test_potential_only_trip_charge_is_billed():
    """Dustin 2026-08-31 (Jim's 8/17-8/23 trip charges): finish-out meetings
    created from a potential can carry a blank event-side Trip_Charge while
    the potential holds the real value. The merged count must bill it."""
    events = [make_event("Jim", 6.0, trip_charge=None, potential_trip_charge="1")]
    result = actuals_for_technician("Jim", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(8.0)  # 6 + 1 charge x 2 solo


def test_matching_event_and_potential_trip_charges_count_once():
    """Dustin's rule: "if its the same, discard one result" — the two fields
    describe the same trip, so they must never sum."""
    events = [make_event("Andre", 8.0, trip_charge="2", potential_trip_charge="2")]
    result = actuals_for_technician("Andre", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(12.0)  # 8 + 2 charges x 2, once


def test_differing_trip_charges_keep_the_positive_result():
    """Dustin's rule: "if its different then keep the positive result" —
    covers both a blank potential (event value wins) and a larger value on
    either side."""
    events = [make_event("Jason", 4.0, trip_charge="1", potential_trip_charge=None)]
    result = actuals_for_technician("Jason", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(6.0)  # event-side "1" x 2

    events = [make_event("Jason", 4.0, trip_charge="1", potential_trip_charge="2")]
    result = actuals_for_technician("Jason", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(8.0)  # positive max "2" x 2


def test_potential_trip_charge_on_cancelled_event_not_billed():
    """The cancellation guard applies to the merged count too — a cancelled
    out-of-town job must not bill its potential-side trip hours forever."""
    events = [
        make_event(
            "Ben",
            0.0167,
            event_status="Incomplete - Job Not Ready",
            potential_trip_charge="2",
        ),
    ]
    result = actuals_for_technician("Ben", events, time_card_total=40.0)
    assert result["hours_billed"] == pytest.approx(0.0167, abs=0.001)


def test_missing_timecard_with_billed_hours_flags_instead_of_zero_percent():
    """Josh Brown week of 8/10: billed hours in CRM but his iSolved time
    wasn't entered when the run fired. That's a data gap, not 0%."""
    events = [make_event("Josh Brown", 31.47)]
    result = actuals_for_technician("Josh Brown", events, time_card_total=0)
    assert result["timecard_missing"] is True
    assert result["actual_utilization"] is None
    assert result["hours_billed"] == pytest.approx(31.47)
    assert result["hours_worked"] == 0
    assert result["actual_hours_paid"] == 0


def test_zero_timecard_with_zero_billed_is_not_flagged():
    result = actuals_for_technician("Ghost", [], time_card_total=0)
    assert result["timecard_missing"] is False
    assert result["actual_utilization"] == 0


def test_rollup_excludes_missing_timecard_from_company_mean():
    per_tech = [
        actuals_for_technician("A", [make_event("A", 30.0)], time_card_total=40.0),
        actuals_for_technician("B", [make_event("B", 35.0)], time_card_total=40.0),
        actuals_for_technician("Josh Brown", [make_event("Josh Brown", 31.47)], time_card_total=0),
    ]
    rollup = company_rollup(per_tech)
    # A per-tech missing timecard is not the iSolved-pending state.
    assert rollup["isolved_pending"] is False
    assert rollup["timecard_missing_techs"] == ["Josh Brown"]
    # Mean over A and B only; Josh's data-gap 0% doesn't drag it down.
    assert rollup["company_utilization"] == pytest.approx((0.75 + 0.875) / 2)
    # His billed hours still count in the totals.
    assert rollup["total_billable"] == pytest.approx(30 + 35 + 31.47)
    assert "Josh Brown" not in rollup["techs_above_target"]


def test_company_rollup_aggregates_correctly_when_timecards_present():
    per_tech = [
        {"technician": "A", "hours_billed": 30, "non_billable_hours": 5,
         "hours_worked": 38, "ot": 0, "actual_hours_paid": 38, "actual_utilization": 30 / 38},
        {"technician": "B", "hours_billed": 20, "non_billable_hours": 10,
         "hours_worked": 40, "ot": 5, "actual_hours_paid": 47.5, "actual_utilization": 20 / 47.5},
        {"technician": "C", "hours_billed": 35, "non_billable_hours": 0,
         "hours_worked": 40, "ot": 0, "actual_hours_paid": 40, "actual_utilization": 0.875},
    ]
    rollup = company_rollup(per_tech)
    assert rollup["total_billable"] == 85
    assert rollup["total_non_billable"] == 15
    assert rollup["total_hours"] == 100
    assert rollup["delta"] == 70
    assert rollup["avg_billable_per_tech"] == pytest.approx(85 / 3)
    assert rollup["isolved_pending"] is False
    # Mean of per-tech utilizations
    expected_util = ((30 / 38) + (20 / 47.5) + 0.875) / 3
    assert rollup["company_utilization"] == pytest.approx(expected_util)
    # A and C are above 0.625; B is not
    assert set(rollup["techs_above_target"]) == {"A", "C"}


def test_company_rollup_marks_pending_when_any_tech_has_no_timecard():
    per_tech = [
        {"technician": "A", "hours_billed": 30, "non_billable_hours": 5,
         "hours_worked": None, "ot": None, "actual_hours_paid": None, "actual_utilization": None},
        {"technician": "B", "hours_billed": 20, "non_billable_hours": 10,
         "hours_worked": None, "ot": None, "actual_hours_paid": None, "actual_utilization": None},
    ]
    rollup = company_rollup(per_tech)
    assert rollup["isolved_pending"] is True
    # CRM-side totals still populate
    assert rollup["total_billable"] == 50
    assert rollup["total_non_billable"] == 15
    # Timecard-derived totals are None
    assert rollup["total_hours_worked"] is None
    assert rollup["total_ot"] is None
    assert rollup["total_actual_hours_paid"] is None
    assert rollup["company_utilization"] is None
    assert rollup["techs_above_target"] is None
