"""
Python mirror of Deluge generate_actuals.dg.

Per Dustin's "two different systems" rule, the actuals math is intentionally
separate from forecast_math.py — no shared HOURS source. The lagging report
takes Hours Billed from CRM (same event-type taxonomy as the forecast) and
Hours Worked from iSolved (a payroll timecard, not a schedule).

The event-type taxonomy in event_types.py IS shared — it is CRM metadata, not
a "system". Reference: docs/spec_lagging.md, docs/decisions.md (2026-05-18).
"""

from event_types import event_category, is_assigned_to

WEEKLY_CAP_HRS = 40
OT_PAY_MULTIPLIER = 1.5
COMPANY_UTILIZATION_TARGET = 0.625


def actuals_for_technician(technician, events, time_card_total):
    """Apply lagging actuals math for a single tech.

    Hours Billed sums Duration_Man_Hrs from CRM billable events (no cap).
    Hours Worked is split: capped at 40, overflow into OT.
    Actual Hours Paid applies the time-and-a-half OT multiplier (verified
    from Dustin's spreadsheet 2026-05-15).

    No status filter: cancelled events carry a 1-minute duration by Livewire
    convention, so they self-neutralize in the hours sum.
    """
    tech_events = [e for e in events if is_assigned_to(e, technician)]

    hours_billed = 0.0
    non_billable_hours = 0.0
    for e in tech_events:
        hrs = e.get("Duration_Man_Hrs") or 0
        cat = event_category(e)
        if cat == "billable":
            hours_billed += hrs
        elif cat == "non_billable":
            non_billable_hours += hrs

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

    if WEEKLY_CAP_HRS > 0:
        worked_utilization = hours_worked / WEEKLY_CAP_HRS
    else:
        worked_utilization = 0

    return {
        "technician": technician,
        "hours_billed": hours_billed,
        "hours_worked": hours_worked,
        "ot": ot,
        "actual_hours_paid": actual_hours_paid,
        "actual_utilization": actual_utilization,
        "worked_utilization": worked_utilization,
        "non_billable_hours": non_billable_hours,
    }


def company_rollup(per_tech_results):
    total_billable = sum(r["hours_billed"] for r in per_tech_results)
    total_non_billable = sum(r["non_billable_hours"] for r in per_tech_results)
    tech_count = len(per_tech_results)

    avg_billable_per_tech = total_billable / tech_count if tech_count else 0
    total_hours = total_billable + total_non_billable
    company_utilization = total_billable / total_hours if total_hours else 0

    techs_above_target = [
        r["technician"]
        for r in per_tech_results
        if r["actual_utilization"] >= COMPANY_UTILIZATION_TARGET
    ]

    return {
        "total_billable": total_billable,
        "total_non_billable": total_non_billable,
        "total_hours": total_hours,
        "delta": total_billable - total_non_billable,
        "avg_billable_per_tech": avg_billable_per_tech,
        "company_utilization": company_utilization,
        "techs_above_target": techs_above_target,
    }
