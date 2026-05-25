"""Tests for the forecast email rendering."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from email_template import (  # noqa: E402
    company_rollup_forecast,
    render_forecast_email,
    _join_no_oxford,
)


def make_tech(name, billable, scheduled, ot=0, util=None, training=0, non_billable=0):
    forecast_hours = scheduled - ot
    if util is None:
        util = billable / forecast_hours if forecast_hours > 0 else 0
    return {
        "technician": name,
        "billable_hours_scheduled": billable,
        "hours_scheduled": scheduled,
        "non_billable_hours": non_billable,
        "training_hours": training,
        "drive_time_adder": 0,
        "forecast_ot": ot,
        "forecast_hours": forecast_hours,
        "forecast_utilization": util,
        "training_drove_ot": False,
        "unknown_event_types": [],
    }


def test_company_rollup_uses_mean_of_per_tech_utilizations():
    """Sheet-confirmed (5/17-5/23 tab): company forecast utilization is the
    mean of per-tech utilizations, not total_billable/total_scheduled.
    Row 11 of that tab shows 71.63% = (76.92+19.61+111.11+90.32+88.89+9.09+105.45)/7.
    The naive total_billable/total_scheduled would be 83/126 = 65.87%."""
    techs = [
        make_tech("Josh B", 5, 6.5),     # 76.92%
        make_tech("Jason", 5, 25.5),     # 19.61%
        make_tech("Patrick", 10, 9),     # 111.11%
        make_tech("Andre", 28, 31),      # 90.32%
        make_tech("Jeffrey", 4, 4.5),    # 88.89%
        make_tech("Thomas", 2, 22),      # 9.09%
        make_tech("Jim", 29, 27.5),      # 105.45%
    ]
    rollup = company_rollup_forecast(techs)
    assert rollup["total_billable"] == pytest.approx(83.0)
    assert rollup["total_scheduled"] == pytest.approx(126.0)
    assert rollup["company_utilization"] == pytest.approx(0.7163, abs=0.001)


def test_techs_above_target_list():
    techs = [
        make_tech("A", 30, 32),  # 0.9375 - above
        make_tech("B", 20, 40),  # 0.50 - below
        make_tech("C", 25, 40),  # 0.625 - at target
    ]
    rollup = company_rollup_forecast(techs)
    assert "A" in rollup["techs_above_target"]
    assert "C" in rollup["techs_above_target"]
    assert "B" not in rollup["techs_above_target"]


def test_join_no_oxford():
    assert _join_no_oxford([]) == ""
    assert _join_no_oxford(["A"]) == "A"
    assert _join_no_oxford(["A", "B"]) == "A and B"
    assert _join_no_oxford(["A", "B", "C"]) == "A, B and C"
    assert _join_no_oxford(["A", "B", "C", "D"]) == "A, B, C and D"


def test_render_contains_all_tech_names_and_totals():
    techs = [
        make_tech("Jim", 20, 27.5),
        make_tech("Andre", 24, 26.5),
        make_tech("Bill", 30, 32),
    ]
    ws = datetime.fromisoformat("2026-05-18T00:00:00-04:00")
    we = datetime.fromisoformat("2026-05-24T23:59:59-04:00")
    html = render_forecast_email(techs, ws, we)
    assert "Jim" in html
    assert "Andre" in html
    assert "Bill" in html
    assert "Total" in html
    assert "May 18" in html


def test_no_em_dashes_or_oxford_commas():
    techs = [make_tech("A", 10, 12), make_tech("B", 8, 16), make_tech("C", 5, 10)]
    ws = datetime.fromisoformat("2026-05-18T00:00:00-04:00")
    we = datetime.fromisoformat("2026-05-24T23:59:59-04:00")
    html = render_forecast_email(techs, ws, we)
    assert "—" not in html  # em dash
    assert ", and " not in html


def test_rows_sorted_by_utilization_descending():
    techs = [
        make_tech("Low", 5, 40),    # 12.5%
        make_tech("High", 35, 40),  # 87.5%
        make_tech("Mid", 20, 40),   # 50%
    ]
    ws = datetime.fromisoformat("2026-05-18T00:00:00-04:00")
    we = datetime.fromisoformat("2026-05-24T23:59:59-04:00")
    html = render_forecast_email(techs, ws, we)
    # Find each row's index in the string; High should come before Mid before Low
    assert html.index("High") < html.index("Mid") < html.index("Low")


def test_auto_notes_synthesize_training_and_unknown_types():
    techs = [
        {
            "technician": "Pat",
            "billable_hours_scheduled": 30,
            "hours_scheduled": 38,
            "non_billable_hours": 2,
            "training_hours": 6,
            "drive_time_adder": 0,
            "forecast_ot": 0,
            "forecast_hours": 38,
            "forecast_utilization": 30 / 38,
            "training_drove_ot": False,
            "unknown_event_types": ["Remote Assistance (Payment Required)"],
        }
    ]
    ws = datetime.fromisoformat("2026-05-18T00:00:00-04:00")
    we = datetime.fromisoformat("2026-05-24T23:59:59-04:00")
    html = render_forecast_email(techs, ws, we)
    assert "6 training hours" in html
    assert "2 non-billable hours" in html
    assert "Remote Assistance" in html
