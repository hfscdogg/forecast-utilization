"""
Tests for the lagging actuals math. Spreadsheet-verified examples from Dustin's
live Billable Hours Reporting sheet (read 2026-05-15) drive the OT-premium
expectations.

Run: pytest tests/test_actuals_math.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actuals_math import actuals_for_technician, company_rollup  # noqa: E402


def make_event(
    technician_1: str,
    duration_hrs: float,
    *,
    event_type: str = "Billable",
    status: str = "Scheduled",
    technician_2: str | None = None,
) -> dict:
    return {
        "Owner": technician_1,
        "Technician_2": technician_2,
        "Duration_Man_Hrs": duration_hrs,
        "Event_Type": event_type,
        "Status": status,
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
    events = []
    result = actuals_for_technician("Ghost", events, time_card_total=0)
    assert result["actual_utilization"] == 0
    assert result["worked_utilization"] == 0


def test_hours_billed_can_exceed_forty():
    """Per SOP: Hours Billed CAN exceed 40 (no cap on the billed side)."""
    events = [make_event("Joe", 45.0)]
    result = actuals_for_technician("Joe", events, time_card_total=50.0)
    assert result["hours_billed"] == pytest.approx(45.0)
    assert result["hours_worked"] == 40
    assert result["ot"] == pytest.approx(10.0)


def test_cancelled_events_excluded_from_billed():
    events = [
        make_event("Ben", 30.0),
        make_event("Ben", 5.0, status="Cancelled"),
    ]
    result = actuals_for_technician("Ben", events, time_card_total=38.0)
    assert result["hours_billed"] == pytest.approx(30.0)


def test_company_rollup_aggregates_correctly():
    per_tech = [
        {"technician": "A", "hours_billed": 30, "non_billable_hours": 5, "actual_utilization": 0.7},
        {"technician": "B", "hours_billed": 20, "non_billable_hours": 10, "actual_utilization": 0.5},
        {"technician": "C", "hours_billed": 35, "non_billable_hours": 0, "actual_utilization": 0.8},
    ]
    rollup = company_rollup(per_tech)
    assert rollup["total_billable"] == 85
    assert rollup["total_non_billable"] == 15
    assert rollup["total_hours"] == 100
    assert rollup["delta"] == 70
    assert rollup["avg_billable_per_tech"] == pytest.approx(85 / 3)
    assert rollup["company_utilization"] == pytest.approx(0.85)
    assert set(rollup["techs_above_target"]) == {"A", "C"}  # only those at or above 62.5%
