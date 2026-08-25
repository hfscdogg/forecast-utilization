"""
Python mirror of Deluge generate_actuals.dg.

Per Dustin's "two different systems" rule, the actuals math is intentionally
separate from forecast_math.py — no shared HOURS source. The lagging report
takes Hours Billed from CRM (same event-type taxonomy as the forecast) and
Hours Worked from iSolved (a payroll timecard, not a schedule).

The event-type taxonomy in event_types.py IS shared — it is CRM metadata, not
a "system". Reference: docs/spec_lagging.md, docs/decisions.md (2026-05-18).

iSolved-pending mode: when time_card_total is None, all timecard-dependent
fields (hours_worked, ot, actual_hours_paid, actual_utilization,
worked_utilization) come back as None. The email and history layer render
those as "—" until iSolved tenant API access lands. Hours Billed and
Non-Billable Hours still come through from CRM in that mode.
"""

from event_types import event_category, is_assigned_to, trip_charge_hours

WEEKLY_CAP_HRS = 40
OT_PAY_MULTIPLIER = 1.5
COMPANY_UTILIZATION_TARGET = 0.625


def actuals_for_technician(technician, events, time_card_total=None):
    """Apply lagging actuals math for a single tech.

    Hours Billed sums Duration_Hrs from CRM billable events (no cap).
    If time_card_total is provided: Hours Worked capped at 40, overflow
    into OT, Actual Hours Paid applies the 1.5x OT multiplier (verified
    from Dustin's spreadsheet 2026-05-15).
    If time_card_total is None: timecard-dependent fields stay None.

    No status filter: cancelled events carry a 1-minute duration by Livewire
    convention, so they self-neutralize in the hours sum.
    """
    tech_events = [e for e in events if is_assigned_to(e, technician)]

    hours_billed = 0.0
    non_billable_hours = 0.0
    for e in tech_events:
        # Duration_Hrs is wall-clock per tech. Duration_Man_Hrs is the TOTAL
        # across all techs on the event (= wall × tech_count); using it
        # per-tech would double-count paired jobs.
        hrs = e.get("Duration_Hrs") or 0
        cat = event_category(e)
        if cat == "billable":
            # Trip charges labeled on the event are billed hours on top of
            # the wall-clock (SOP "including trip charges"; Dustin 2026-08-25
            # flagged Jason and Josh B trip charges the report missed).
            hours_billed += hrs + trip_charge_hours(e)
        elif cat == "non_billable":
            non_billable_hours += hrs

    if time_card_total is None:
        return {
            "technician": technician,
            "hours_billed": hours_billed,
            "non_billable_hours": non_billable_hours,
            "hours_worked": None,
            "ot": None,
            "actual_hours_paid": None,
            "actual_utilization": None,
            "worked_utilization": None,
            "timecard_missing": False,
        }

    # A tech with billed CRM hours but a zero timecard didn't work for free:
    # their iSolved time wasn't entered when the run fired (Josh Brown week
    # of 8/10, Dustin 2026-08-25). Averaging in the resulting 0% craters the
    # company number, so flag the row and let the rollup leave it out.
    if time_card_total == 0 and hours_billed > 0:
        return {
            "technician": technician,
            "hours_billed": hours_billed,
            "non_billable_hours": non_billable_hours,
            "hours_worked": 0,
            "ot": 0,
            "actual_hours_paid": 0,
            "actual_utilization": None,
            "worked_utilization": 0,
            "timecard_missing": True,
        }

    if time_card_total > WEEKLY_CAP_HRS:
        hours_worked = WEEKLY_CAP_HRS
        ot = time_card_total - WEEKLY_CAP_HRS
    else:
        hours_worked = time_card_total
        ot = 0

    actual_hours_paid = hours_worked + (ot * OT_PAY_MULTIPLIER)

    if actual_hours_paid > 0:
        actual_utilization = hours_billed / actual_hours_paid
    else:
        actual_utilization = 0

    worked_utilization = hours_worked / WEEKLY_CAP_HRS

    return {
        "technician": technician,
        "hours_billed": hours_billed,
        "non_billable_hours": non_billable_hours,
        "hours_worked": hours_worked,
        "ot": ot,
        "actual_hours_paid": actual_hours_paid,
        "actual_utilization": actual_utilization,
        "worked_utilization": worked_utilization,
        "timecard_missing": False,
    }


def company_rollup(per_tech_results):
    """Company-wide rollup. Timecard-derived totals (hours_worked, ot,
    actual_hours_paid, company_utilization, techs_above_target) come back
    None when any per-tech actual_utilization is None — that's the
    iSolved-pending state where we can't yet say who hit the target.
    """
    total_billable = sum(r["hours_billed"] for r in per_tech_results)
    total_non_billable = sum(r["non_billable_hours"] for r in per_tech_results)
    tech_count = len(per_tech_results)

    avg_billable_per_tech = total_billable / tech_count if tech_count else 0
    total_hours = total_billable + total_non_billable
    delta = total_billable - total_non_billable

    # A None utilization means iSolved-pending only when the row isn't a
    # per-tech missing timecard — those also carry None but the run itself
    # had timecard data.
    isolved_pending = any(
        r["actual_utilization"] is None and not r.get("timecard_missing")
        for r in per_tech_results
    )
    timecard_missing_techs = [
        r["technician"] for r in per_tech_results if r.get("timecard_missing")
    ]

    if isolved_pending:
        return {
            "tech_count": tech_count,
            "total_billable": total_billable,
            "total_non_billable": total_non_billable,
            "total_hours": total_hours,
            "delta": delta,
            "avg_billable_per_tech": avg_billable_per_tech,
            "total_hours_worked": None,
            "total_ot": None,
            "total_actual_hours_paid": None,
            "company_utilization": None,
            "techs_above_target": None,
            "isolved_pending": True,
            "timecard_missing_techs": [],
        }

    total_hours_worked = sum(r["hours_worked"] for r in per_tech_results)
    total_ot = sum(r["ot"] for r in per_tech_results)
    total_actual_hours_paid = sum(r["actual_hours_paid"] for r in per_tech_results)

    # Sheet convention (matches forecast company rollup): mean of per-tech
    # utilizations, not total_billable / total_paid. Techs with a missing
    # timecard stay in the table and hour totals but out of the mean —
    # their 0% is a data gap, not a performance number.
    utils = [
        r["actual_utilization"]
        for r in per_tech_results
        if not r.get("timecard_missing")
    ]
    company_utilization = sum(utils) / len(utils) if utils else 0

    techs_above_target = [
        r["technician"]
        for r in per_tech_results
        if not r.get("timecard_missing")
        and r["actual_utilization"] >= COMPANY_UTILIZATION_TARGET
    ]

    return {
        "tech_count": tech_count,
        "total_billable": total_billable,
        "total_non_billable": total_non_billable,
        "total_hours": total_hours,
        "delta": delta,
        "avg_billable_per_tech": avg_billable_per_tech,
        "total_hours_worked": total_hours_worked,
        "total_ot": total_ot,
        "total_actual_hours_paid": total_actual_hours_paid,
        "company_utilization": company_utilization,
        "techs_above_target": techs_above_target,
        "isolved_pending": False,
        "timecard_missing_techs": timecard_missing_techs,
    }
