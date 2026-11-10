"""
Tests for the quarterly utilization rollup (Dustin 2026-11-10) and its
email. The Oct 25-31 rows are the real numbers from the 2026-11-09 actuals
email.

Run: pytest tests/test_quarterly.py
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from quarterly_email_template import (  # noqa: E402
    quarterly_title,
    render_quarterly_email,
)
from quarterly_math import (  # noqa: E402
    completed_quarter_start,
    quarter_label,
    quarter_week_ends,
    quarterly_summary,
)

Q4 = date(2026, 10, 1)


def row(tech, week_end, billed, paid, *, non_billable=0.0, run="run-1",
        generated=None, util="auto"):
    if util == "auto":
        util = billed / paid if paid else 0.0
    return {
        "run_id": run,
        "generated_at": generated or datetime.combine(
            week_end + timedelta(days=9), datetime.min.time()
        ),
        "lag_week_start": week_end - timedelta(days=6),
        "lag_week_end": week_end,
        "technician": tech,
        "hours_billed": billed,
        "non_billable_hours": non_billable,
        "actual_hours_paid": paid,
        "actual_utilization": util,
    }


def oct_25_week():
    """The 2026-11-09 email: company utilization 78.69% over seven techs.
    Utilization is as Creator stores it, rounded to two decimals; averaging
    those gives 78.86%, the defect in the 2026-11-10 preview."""
    we = date(2026, 10, 31)
    return [
        row("Jordan Toppin", we, 13.19, 13.65, util=0.97),
        row("Patrick Jones", we, 33.22, 37.35, non_billable=2.0, util=0.89),
        row("Elijah Good", we, 45.35, 51.65, util=0.88),
        row("Jason Good", we, 57.35, 65.40, util=0.88),
        row("Thomas Payne", we, 44.51, 54.55, util=0.82),
        row("Andre Smith", we, 33.17, 44.65, non_billable=0.67, util=0.74),
        row("Jim Zimmerman", we, 15.07, 44.50, non_billable=10.46, util=0.34),
        row("Cameron Lloyd", we, 12.17, 47.92, util=0.25),
        row("Isaiah Luna", we, 13.27, 0.0, util=None),
    ]


def sep_27_week():
    """The 2026-10-12 email: 73.22%. The preview showed 73.00%."""
    we = date(2026, 10, 3)
    return [
        row("Elijah Good", we, 25.95, 22.67, util=1.14),
        row("Thomas Payne", we, 30.20, 36.10, util=0.84),
        row("Patrick Jones", we, 27.72, 35.32, non_billable=0.88, util=0.78),
        row("Jordan Toppin", we, 21.60, 29.42, util=0.73),
        row("Jason Good", we, 28.93, 42.30, util=0.68),
        row("Andre Smith", we, 19.97, 29.35, non_billable=2.0, util=0.68),
        row("Jim Zimmerman", we, 22.06, 84.75, non_billable=0.5, util=0.26),
        row("Cameron Lloyd", we, 4.87, 36.03, util=0.14),
        row("Isaiah Luna", we, 0.0, 0.0, util=0.0),
    ]


def test_completed_quarter_on_jan_1_is_q4():
    assert completed_quarter_start(date(2027, 1, 1)) == Q4
    assert completed_quarter_start(date(2027, 1, 2)) == Q4
    assert completed_quarter_start(date(2027, 4, 1)) == date(2027, 1, 1)
    assert quarter_label(Q4) == "Q4 2026"


def test_q4_2026_is_the_13_weeks_reported_in_the_quarter():
    ends = quarter_week_ends(Q4)
    assert len(ends) == 13
    assert ends[0] == date(2026, 9, 26)   # reported Mon Oct 5
    assert ends[-1] == date(2026, 12, 19)  # reported Mon Dec 28
    assert all(d.weekday() == 5 for d in ends)


def test_every_week_lands_in_exactly_one_quarter():
    seen = []
    q = date(2026, 10, 1)
    for _ in range(8):
        seen += quarter_week_ends(q)
        q = (q + timedelta(days=95)).replace(day=1)
    assert len(seen) == len(set(seen))
    assert all(b - a == timedelta(days=7) for a, b in zip(seen, seen[1:]))


def test_quarter_in_progress_stops_at_as_of():
    ends = quarter_week_ends(Q4, as_of=date(2026, 11, 10))
    assert ends[-1] == date(2026, 10, 31)  # reported Mon Nov 9
    assert len(ends) == 6


def test_weekly_company_number_matches_the_weekly_email():
    s = quarterly_summary(oct_25_week(), Q4, as_of=date(2026, 11, 10))
    week = s["weeks"][-1]
    assert week["week_start"] == date(2026, 10, 25)
    assert week["tech_count"] == 9
    assert week["total_billable"] == pytest.approx(267.30)
    assert week["total_actual_hours_paid"] == pytest.approx(359.67)
    assert week["total_non_billable"] == pytest.approx(13.13)
    # Cameron (ramp-up) and Isaiah (no timecard) are out of the mean.
    assert week["company_utilization"] == pytest.approx(0.7869, abs=5e-5)


def test_stored_rounded_utilization_is_not_trusted():
    s = quarterly_summary(sep_27_week(), Q4, as_of=date(2026, 11, 10))
    week = next(w for w in s["weeks"] if w["week_end"] == date(2026, 10, 3))
    # Hours are stored to two decimals too, so the recomputed number can
    # sit 0.01 of a point off the email (73.21 vs 73.22), not 0.22 off.
    assert week["company_utilization"] == pytest.approx(0.7322, abs=2e-4)


def test_missing_weeks_are_named_and_partial_flag_set():
    s = quarterly_summary(oct_25_week(), Q4, as_of=date(2026, 11, 10))
    assert s["partial"] is True
    assert s["rollup"]["weeks_expected"] == 6
    assert s["rollup"]["weeks_reported"] == 1
    assert s["rollup"]["missing_week_ends"][0] == date(2026, 9, 26)
    assert len(s["rollup"]["missing_week_ends"]) == 5


def test_quarter_company_number_is_dustins_month_then_quarter_average():
    """Dustin 2026-11-10: average the weeks within each month, then
    average the three monthly results."""
    w1, w2 = date(2026, 10, 17), date(2026, 10, 24)
    rows = [
        row("Jason Good", w1, 36.0, 40.0),   # 90%
        row("Thomas Payne", w1, 28.0, 40.0),  # 70%  -> week 80%
        row("Jason Good", w2, 24.0, 40.0),   # 60%  -> week 60%
        row("Jason Good", date(2026, 10, 31), 36.0, 40.0),  # 90%
        row("Jason Good", date(2026, 12, 5), 20.0, 40.0),   # 50%
    ]
    s = quarterly_summary(rows, Q4)
    assert [w["company_utilization"] for w in s["weeks"]] == pytest.approx(
        [0.8, 0.6, 0.9, 0.5]
    )
    # Reported Mon Oct 26 | Mon Nov 2 and Nov 9 | Mon Dec 14.
    assert [(m["month"], m["weeks_reported"]) for m in s["months"]] == [
        ("October", 1), ("November", 2), ("December", 1),
    ]
    assert [m["average_utilization"] for m in s["months"]] == pytest.approx(
        [0.8, 0.75, 0.5]
    )
    # (0.8 + 0.75 + 0.5) / 3, not the 0.70 mean of the four weeks.
    assert s["rollup"]["company_utilization"] == pytest.approx(2.05 / 3)
    assert s["rollup"]["best_week"]["week_end"] == date(2026, 10, 31)
    assert s["rollup"]["low_week"]["week_end"] == date(2026, 12, 5)
    assert s["partial"] is False


def test_tech_quarter_utilization_is_hours_weighted():
    w1, w2 = date(2026, 10, 17), date(2026, 10, 24)
    rows = [
        row("Jason Good", w1, 36.0, 40.0),  # 90%
        row("Jason Good", w2, 5.0, 10.0),   # 50% on a short week
    ]
    jason = quarterly_summary(rows, Q4)["techs"][0]
    assert jason["utilization"] == pytest.approx(41.0 / 50.0)
    assert jason["weeks_reported"] == 2
    assert jason["weeks_counted"] == 2
    assert jason["weeks_on_target"] == 1


def test_service_tech_is_scored_against_the_service_target():
    we = date(2026, 10, 17)
    rows = [row("Jim Zimmerman", we, 28.0, 40.0), row("Andre Smith", we, 28.0, 40.0)]
    techs = {t["technician"]: t for t in quarterly_summary(rows, Q4)["techs"]}
    assert techs["Jim Zimmerman"]["target"] == 0.675
    assert techs["Jim Zimmerman"]["weeks_on_target"] == 1
    assert techs["Andre Smith"]["weeks_on_target"] == 0


def test_ramp_up_weeks_stay_out_of_company_mean_until_billable_from():
    before, after = date(2026, 12, 12), date(2026, 12, 19)
    rows = [
        row("Jason Good", before, 32.0, 40.0),
        row("Cameron Lloyd", before, 10.0, 40.0),  # ramp-up until 12/16
        row("Jason Good", after, 32.0, 40.0),
        row("Cameron Lloyd", after, 20.0, 40.0),   # counts
    ]
    s = quarterly_summary(rows, Q4)
    assert s["weeks"][0]["company_utilization"] == pytest.approx(0.8)
    assert s["weeks"][1]["company_utilization"] == pytest.approx(0.65)
    cam = next(t for t in s["techs"] if t["technician"] == "Cameron Lloyd")
    assert cam["ramp_up_weeks"] == 1
    assert cam["weeks_counted"] == 1
    assert cam["billable_from"] == date(2026, 12, 16)
    assert cam["utilization"] == pytest.approx(30.0 / 80.0)


def test_missing_timecard_week_keeps_hours_but_not_percentage():
    w1, w2 = date(2026, 10, 17), date(2026, 10, 24)
    rows = [
        row("Andre Smith", w1, 30.0, 40.0),
        row("Andre Smith", w2, 20.0, 0.0, util=None),
    ]
    s = quarterly_summary(rows, Q4)
    andre = s["techs"][0]
    assert andre["hours_billed"] == pytest.approx(50.0)
    assert andre["utilization"] == pytest.approx(0.75)
    assert andre["weeks_missing_timecard"] == 1
    assert s["weeks"][1]["company_utilization"] is None
    # November's only week has no number, so the month is left out.
    assert s["months"][1]["average_utilization"] is None
    assert s["rollup"]["company_utilization"] == pytest.approx(0.75)


def test_rerun_replaces_the_whole_week():
    we = date(2026, 10, 17)
    first = datetime(2026, 10, 26, 16, 0)
    rerun = datetime(2026, 10, 28, 9, 0)
    rows = [
        row("Jason Good", we, 20.0, 40.0, run="a", generated=first),
        row("Joshua Brown", we, 10.0, 40.0, run="a", generated=first),
        row("Jason Good", we, 36.0, 40.0, run="b", generated=rerun),
    ]
    s = quarterly_summary(rows, Q4)
    assert [t["technician"] for t in s["techs"]] == ["Jason Good"]
    assert s["weeks"][0]["company_utilization"] == pytest.approx(0.9)
    assert s["weeks"][0]["total_billable"] == pytest.approx(36.0)


def test_non_saturday_weeks_and_excluded_names_are_ignored():
    we = date(2026, 10, 17)
    rows = [
        row("Jason Good", we, 32.0, 40.0),
        row("Joshua McDonough", we, 4.0, 40.0),
        # The 2026-10-07 re-run's Tue-Mon week.
        row("Jason Good", date(2026, 9, 28), 99.0, 40.0),
    ]
    s = quarterly_summary(rows, Q4)
    assert len(s["weeks"]) == 1
    assert s["weeks"][0]["tech_count"] == 1
    assert s["rollup"]["total_billable"] == pytest.approx(32.0)


def test_rows_outside_the_quarter_are_ignored():
    rows = [
        row("Jason Good", date(2026, 9, 19), 32.0, 40.0),   # reported in Q3
        row("Jason Good", date(2026, 12, 26), 32.0, 40.0),  # reported in Q1
    ]
    s = quarterly_summary(rows, Q4)
    assert s["weeks"] == []
    assert s["rollup"]["company_utilization"] is None


def test_email_renders_headline_tables_and_notes():
    s = quarterly_summary(oct_25_week(), Q4, as_of=date(2026, 11, 10))
    assert quarterly_title(s) == "Quarterly Utilization for Q4 2026 to date"
    html = render_quarterly_email(s)
    assert "78.69%" in html
    assert "78.86%" not in html
    assert "By month" in html
    assert "<td>November</td>" in html
    assert "Oct 25 to Oct 31" in html
    assert "Weeks missing" in html
    assert "ramp-up, counts from 2026-12-16" in html
    assert "1 wk with no timecard" in html
    # Highest quarter utilization first, no-timecard tech last.
    assert html.index("Jordan Toppin") < html.index("Jim Zimmerman") < html.index("Isaiah Luna")
    # House style: no em dash characters in copy.
    assert "—" not in html


def test_full_quarter_title_and_no_banner():
    rows = [row("Jason Good", d, 32.0, 40.0) for d in quarter_week_ends(Q4)]
    s = quarterly_summary(rows, Q4)
    html = render_quarterly_email(s)
    assert quarterly_title(s) == "Quarterly Utilization for Q4 2026"
    assert "Weeks missing" not in html
    assert "<strong>13</strong> weekly actuals reports" in html
    assert "Sun Sep 20 through Sat Dec 19" in html
