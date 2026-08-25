"""Tests for the lagging actuals email rendering."""

import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from actuals_email_template import render_actuals_email  # noqa: E402
from actuals_math import company_rollup  # noqa: E402


def make_tech_full(name, billed, worked, ot=0, non_billable=0):
    """Tech result with full iSolved time-card data."""
    paid = worked + ot * 1.5
    util = billed / paid if paid > 0 else 0
    return {
        "technician": name,
        "hours_billed": billed,
        "non_billable_hours": non_billable,
        "hours_worked": worked,
        "ot": ot,
        "actual_hours_paid": paid,
        "actual_utilization": util,
        "worked_utilization": worked / 40,
    }


def make_tech_pending(name, billed, non_billable=0):
    """Tech result with iSolved data pending — timecard fields None."""
    return {
        "technician": name,
        "hours_billed": billed,
        "non_billable_hours": non_billable,
        "hours_worked": None,
        "ot": None,
        "actual_hours_paid": None,
        "actual_utilization": None,
        "worked_utilization": None,
    }


WS = datetime.fromisoformat("2026-05-18T00:00:00-04:00")
WE = datetime.fromisoformat("2026-05-24T23:59:59-04:00")


def test_pending_mode_renders_placeholders_and_banner():
    techs = [
        make_tech_pending("A", 30, non_billable=5),
        make_tech_pending("B", 20, non_billable=10),
    ]
    rollup = company_rollup(techs)
    html = render_actuals_email(techs, WS, WE, rollup)

    # Banner present
    assert "iSolved integration pending" in html
    # Placeholder character present for missing fields
    assert "&mdash;" in html
    # CRM-side numbers populated
    assert "30" in html
    assert "20" in html
    # No congrats line in pending mode
    assert "Congrats" not in html


def test_full_mode_renders_congrats_and_no_banner():
    techs = [
        make_tech_full("A", 30, 38),  # 30/38 ~= 0.789, above 62.5%
        make_tech_full("B", 20, 47.5, ot=5),  # 20/55 ~= 0.364, below
        make_tech_full("C", 35, 40),  # 35/40 = 0.875, above
    ]
    rollup = company_rollup(techs)
    html = render_actuals_email(techs, WS, WE, rollup)

    assert "iSolved integration pending" not in html
    assert "Congrats" in html
    assert "A" in html and "C" in html
    # Total billable
    assert "85" in html


def test_no_em_dashes():
    """House style: em dash is banned. The placeholder is &mdash; (entity for
    en/em variants) — verify the literal '—' character does not appear."""
    techs = [make_tech_full("A", 30, 38)]
    rollup = company_rollup(techs)
    html = render_actuals_email(techs, WS, WE, rollup)
    assert "—" not in html  # literal em dash


def test_rows_sort_desc_by_utilization_in_full_mode():
    techs = [
        make_tech_full("Low", 5, 40),       # 0.125
        make_tech_full("High", 35, 40),     # 0.875
        make_tech_full("Mid", 20, 40),      # 0.5
    ]
    rollup = company_rollup(techs)
    html = render_actuals_email(techs, WS, WE, rollup)
    assert html.index("High") < html.index("Mid") < html.index("Low")


def make_tech_missing_timecard(name, billed):
    """Tech with billed CRM hours but no iSolved time at run time."""
    return {
        "technician": name,
        "hours_billed": billed,
        "non_billable_hours": 0,
        "hours_worked": 0,
        "ot": 0,
        "actual_hours_paid": 0,
        "actual_utilization": None,
        "worked_utilization": 0,
        "timecard_missing": True,
    }


def test_missing_timecard_renders_banner_note_and_sinks_row():
    techs = [
        make_tech_missing_timecard("Josh Brown", 31.47),
        make_tech_full("Thomas", 35, 40),
        make_tech_full("Jordan", 9, 10.45),
    ]
    rollup = company_rollup(techs)
    html = render_actuals_email(techs, WS, WE, rollup)

    assert "Timecard missing" in html
    assert "timecard missing in iSolved at run time" in html
    # Full mode, not pending mode
    assert "iSolved integration pending" not in html
    # Missing row sorts below real percentages despite high billed hours.
    # Scope to the table body since the banner also names the tech.
    body = html[html.index("<tbody>"):]
    assert body.index("Thomas") < body.index("Josh Brown")
    assert body.index("Jordan") < body.index("Josh Brown")


def test_rows_sort_desc_by_hours_billed_in_pending_mode():
    """No utilization to sort by — fall back to hours_billed desc."""
    techs = [
        make_tech_pending("Low", 5),
        make_tech_pending("High", 35),
        make_tech_pending("Mid", 20),
    ]
    rollup = company_rollup(techs)
    html = render_actuals_email(techs, WS, WE, rollup)
    assert html.index("High") < html.index("Mid") < html.index("Low")
