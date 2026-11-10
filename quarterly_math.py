"""
Quarterly utilization rollup. Python mirror of deluge/generate_quarterly.dg.

Dustin 2026-11-10: he tallies the weekly Utilization Actuals emails by hand
for the quarterly all-hands and asked for a report that does it for him,
out on the first of the month at the start of each quarter.

Nothing new is pulled from CRM or iSolved. The rollup reads the rows the
Monday actuals run already stores in Utilization_Actuals_History
(docs/actuals_history_form_schema.md) and re-applies the weekly rules.

Rules (docs/decisions.md, 2026-11-10):
- A week belongs to the quarter its Monday actuals email went out in. The
  email goes out 9 days after the Sun-Sat lag week ends, so Q4 2026 is the
  13 weeks ending Sat Sep 26 through Sat Dec 19. This is the same set of
  emails Dustin tallies, every week lands in exactly one quarter, and the
  report is complete on the first of the next quarter. (Calendar-quarter
  weeks would always be missing the last week on the 1st: its actuals are
  not out yet.)
- A re-run writes a second set of rows for the same week. The latest run
  wins, whole run at a time, so a tech dropped by a fix does not leak back
  in from the older run.
- Weeks that do not end on a Saturday are ignored (the 2026-10-07 manual
  re-run stored a Tue-Mon week under the old fixed offsets).
- Weekly company utilization is the mean of per-tech utilizations, with
  ramp-up techs and missing-timecard rows left out, same as the weekly
  email. The quarter's company number is the mean of those weekly numbers,
  which is what tallying the emails gives.
- A tech's quarter utilization is hours billed / actual hours paid over
  the weeks that had a timecard (hours-weighted, so a short week does not
  count as much as a full one).
"""

from datetime import date, timedelta

# Days from the Saturday a lag week ends to the Monday its actuals email
# goes out (scheduled_actuals.dg).
REPORT_LAG_DAYS = 9

# Keep in sync with generate_actuals.dg.
TECH_UTILIZATION_TARGET = 0.80
SERVICE_TECH_UTILIZATION_TARGET = 0.675
SERVICE_TECH_NAMES = {"Jim Zimmerman"}
RAMP_UP_BILLABLE_FROM = {
    "Elijah Good": date(2026, 10, 1),
    "Cameron Lloyd": date(2026, 12, 16),
    "Isaiah Luna": date(2026, 12, 20),
}
# History rows written before a name was excluded still carry it (Joshua
# McDonough in the 9/20-9/26 run). Sales-role users never reach the
# actuals history, so the name list is enough here.
EXCLUDED_NON_TECH_NAMES = {
    "Dustin Roskam", "Josh McDonough", "Joshua McDonough", "David Hicks",
}


def quarter_start_for(day):
    """First day of the calendar quarter containing `day`."""
    return date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)


def completed_quarter_start(today):
    """First day of the most recently completed quarter. On Jan 1 2027
    that is Oct 1 2026."""
    return quarter_start_for(quarter_start_for(today) - timedelta(days=1))


def quarter_end_for(q_start):
    """Last day of the quarter starting on `q_start`."""
    if q_start.month == 10:
        nxt = date(q_start.year + 1, 1, 1)
    else:
        nxt = date(q_start.year, q_start.month + 3, 1)
    return nxt - timedelta(days=1)


def quarter_label(q_start):
    return f"Q{(q_start.month - 1) // 3 + 1} {q_start.year}"


def quarter_week_ends(q_start, as_of=None):
    """Saturdays ending the lag weeks reported in the quarter, in order.

    A week is in when its report Monday (week end + 9) falls inside the
    quarter and on or before `as_of` (default: the whole quarter).
    """
    q_end = quarter_end_for(q_start)
    last_day = q_end if as_of is None or as_of > q_end else as_of
    # weekday(): Monday is 0.
    monday = q_start + timedelta(days=(7 - q_start.weekday()) % 7)
    out = []
    while monday <= last_day:
        out.append(monday - timedelta(days=REPORT_LAG_DAYS))
        monday += timedelta(days=7)
    return out


def target_for(technician):
    if technician in SERVICE_TECH_NAMES:
        return SERVICE_TECH_UTILIZATION_TARGET
    return TECH_UTILIZATION_TARGET


def quarterly_summary(rows, q_start, as_of=None):
    """Roll Utilization_Actuals_History rows up into one quarter.

    rows: dicts with run_id, generated_at (sortable), lag_week_start,
        lag_week_end (dates), technician, hours_billed,
        non_billable_hours, actual_hours_paid, actual_utilization. The
        last two are None when the timecard was missing or iSolved was
        pending.
    q_start: first day of the quarter.
    as_of: stop at weeks reported on or before this date (a quarter in
        progress). None means the whole quarter.
    """
    q_end = quarter_end_for(q_start)
    week_ends = quarter_week_ends(q_start, as_of)
    wanted = set(week_ends)

    # Latest run per week wins.
    latest = {}
    for r in rows:
        we = r["lag_week_end"]
        if we not in wanted:
            continue
        cur = latest.get(we)
        if cur is None or r["generated_at"] > cur[0]:
            latest[we] = (r["generated_at"], r["run_id"])

    weeks = []
    missing_week_ends = []
    techs = {}
    for we in week_ends:
        if we not in latest:
            missing_week_ends.append(we)
            continue
        run_id = latest[we][1]
        wk = {
            "week_start": we - timedelta(days=6),
            "week_end": we,
            "tech_count": 0,
            "total_billable": 0.0,
            "total_non_billable": 0.0,
            "total_actual_hours_paid": 0.0,
            "company_utilization": None,
        }
        util_sum = 0.0
        util_count = 0
        for r in rows:
            if r["lag_week_end"] != we or r["run_id"] != run_id:
                continue
            name = r["technician"]
            if name in EXCLUDED_NON_TECH_NAMES:
                continue
            billed = r.get("hours_billed") or 0.0
            non_billable = r.get("non_billable_hours") or 0.0
            paid = r.get("actual_hours_paid") or 0.0
            util = r.get("actual_utilization")
            billable_from = RAMP_UP_BILLABLE_FROM.get(name)
            ramp_up = billable_from is not None and we < billable_from

            wk["tech_count"] += 1
            wk["total_billable"] += billed
            wk["total_non_billable"] += non_billable
            wk["total_actual_hours_paid"] += paid

            t = techs.setdefault(name, {
                "technician": name,
                "target": target_for(name),
                "weeks_reported": 0,
                "weeks_missing_timecard": 0,
                "ramp_up_weeks": 0,
                "weeks_counted": 0,
                "weeks_on_target": 0,
                "hours_billed": 0.0,
                "non_billable_hours": 0.0,
                "actual_hours_paid": 0.0,
                "_billed_with_timecard": 0.0,
                "billable_from": None,
            })
            t["weeks_reported"] += 1
            t["hours_billed"] += billed
            t["non_billable_hours"] += non_billable
            t["actual_hours_paid"] += paid
            if util is None:
                t["weeks_missing_timecard"] += 1
                continue
            t["_billed_with_timecard"] += billed
            if ramp_up:
                t["ramp_up_weeks"] += 1
                t["billable_from"] = billable_from
                continue
            util_sum += util
            util_count += 1
            t["weeks_counted"] += 1
            if util >= t["target"]:
                t["weeks_on_target"] += 1
        if util_count:
            wk["company_utilization"] = util_sum / util_count
        weeks.append(wk)

    tech_list = []
    for t in techs.values():
        billed_tc = t.pop("_billed_with_timecard")
        t["utilization"] = (
            billed_tc / t["actual_hours_paid"] if t["actual_hours_paid"] > 0 else None
        )
        tech_list.append(t)
    tech_list.sort(
        key=lambda t: (t["utilization"] is not None, t["utilization"] or 0.0),
        reverse=True,
    )

    scored = [w for w in weeks if w["company_utilization"] is not None]
    company_utilization = (
        sum(w["company_utilization"] for w in scored) / len(scored) if scored else None
    )
    best_week = max(scored, key=lambda w: w["company_utilization"]) if scored else None
    low_week = min(scored, key=lambda w: w["company_utilization"]) if scored else None

    return {
        "quarter_label": quarter_label(q_start),
        "quarter_start": q_start,
        "quarter_end": q_end,
        "partial": as_of is not None and as_of < q_end,
        "weeks": weeks,
        "techs": tech_list,
        "rollup": {
            "weeks_expected": len(week_ends),
            "weeks_reported": len(weeks),
            "missing_week_ends": missing_week_ends,
            "total_billable": sum(w["total_billable"] for w in weeks),
            "total_non_billable": sum(w["total_non_billable"] for w in weeks),
            "total_actual_hours_paid": sum(w["total_actual_hours_paid"] for w in weeks),
            "company_utilization": company_utilization,
            "best_week": best_week,
            "low_week": low_week,
        },
    }
