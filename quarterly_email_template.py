"""
Render the Quarterly Utilization email as HTML.

Python mirror of deluge/send_quarterly_email.dg. Keep in sync. Input is the
dict from quarterly_math.quarterly_summary.

Conventions match actuals_email_template.py: no em dashes in copy, no
Oxford commas, HTML <strong> for emphasis.
"""

from actuals_email_template import (
    BRAND_FONT_STACK,
    BRAND_PENDING_BG,
    BRAND_PRIMARY_COLOR,
    BRAND_TABLE_BORDER,
    BRAND_TABLE_HEADER_BG,
    PLACEHOLDER,
)


def _hrs(x):
    return f"{x:.2f}"


def _pct(x):
    if x is None:
        return PLACEHOLDER
    return f"{x * 100:.2f}%"


def _span(week):
    return (
        f"{week['week_start'].strftime('%b %-d')} to "
        f"{week['week_end'].strftime('%b %-d')}"
    )


def quarterly_title(summary):
    title = f"Quarterly Utilization for {summary['quarter_label']}"
    if summary["partial"]:
        title += " to date"
    return title


def _tech_notes(t):
    parts = []
    if t["ramp_up_weeks"] > 0:
        parts.append(
            f"ramp-up, counts from {t['billable_from'].isoformat()} "
            f"({t['ramp_up_weeks']} wk left out of the company average)"
        )
    if t["weeks_missing_timecard"] > 0:
        parts.append(
            f"{t['weeks_missing_timecard']} wk with no timecard, "
            f"left out of the percentage"
        )
    return "; ".join(parts)


def render_quarterly_email(summary):
    """Return HTML for the quarterly utilization email body."""
    weeks = summary["weeks"]
    rollup = summary["rollup"]
    title = quarterly_title(summary)

    week_rows = "".join(
        "<tr>"
        f"<td>{_span(w)}</td>"
        f"<td style='text-align:right'>{w['tech_count']}</td>"
        f"<td style='text-align:right'>{_hrs(w['total_billable'])}</td>"
        f"<td style='text-align:right'>{_hrs(w['total_actual_hours_paid'])}</td>"
        f"<td style='text-align:right'>{_hrs(w['total_non_billable'])}</td>"
        f"<td style='text-align:right'><strong>{_pct(w['company_utilization'])}</strong></td>"
        "</tr>"
        for w in weeks
    )

    month_rows = "".join(
        "<tr>"
        f"<td>{m['month']}</td>"
        f"<td style='text-align:right'>{m['weeks_reported']}</td>"
        f"<td style='text-align:right'><strong>{_pct(m['average_utilization'])}</strong></td>"
        "</tr>"
        for m in summary["months"]
    )

    tech_rows = ""
    for t in summary["techs"]:
        on_target = PLACEHOLDER
        if t["weeks_counted"] > 0:
            on_target = f"{t['weeks_on_target']} of {t['weeks_counted']}"
        tech_rows += (
            "<tr>"
            f"<td>{t['technician']}</td>"
            f"<td style='text-align:right'>{t['weeks_reported']}</td>"
            f"<td style='text-align:right'>{_hrs(t['hours_billed'])}</td>"
            f"<td style='text-align:right'>{_hrs(t['actual_hours_paid'])}</td>"
            f"<td style='text-align:right'><strong>{_pct(t['utilization'])}</strong></td>"
            f"<td style='text-align:right'>{_pct(t['target'])}</td>"
            f"<td style='text-align:right'>{on_target}</td>"
            f"<td style='text-align:right'>{_hrs(t['non_billable_hours'])}</td>"
            f"<td style='font-size:11px;color:#666'>{_tech_notes(t)}</td>"
            "</tr>"
        )

    span_text = ""
    if weeks:
        span_text = (
            f" (weeks of {weeks[0]['week_start'].strftime('%a %b %-d')} through "
            f"{weeks[-1]['week_end'].strftime('%a %b %-d')})"
        )
    lead_in = (
        f"<p>Across the <strong>{rollup['weeks_reported']}</strong> weekly actuals "
        f"reports sent in {summary['quarter_label']}{span_text}, company utilization "
        f"averaged <strong>{_pct(rollup['company_utilization'])}</strong>. We billed "
        f"<strong>{_hrs(rollup['total_billable'])}</strong> hours against "
        f"<strong>{_hrs(rollup['total_actual_hours_paid'])}</strong> actual hours paid, "
        f"with <strong>{_hrs(rollup['total_non_billable'])}</strong> non-billable hours.</p>"
    )

    range_line = ""
    best, low = rollup["best_week"], rollup["low_week"]
    if best is not None and low is not None and len(weeks) > 1:
        range_line = (
            f"<p>Best week: <strong>{_span(best)}</strong> at "
            f"<strong>{_pct(best['company_utilization'])}</strong>. Lowest week: "
            f"<strong>{_span(low)}</strong> at "
            f"<strong>{_pct(low['company_utilization'])}</strong>.</p>"
        )

    banner = ""
    if rollup["missing_week_ends"]:
        missing_text = ", ".join(
            d.strftime("%b %-d") for d in rollup["missing_week_ends"]
        )
        banner = (
            f"<p style='background:{BRAND_PENDING_BG};padding:10px 14px;"
            f"border-left:3px solid #d4a017;font-size:13px;'>"
            f"<strong>Weeks missing:</strong> no stored actuals for the week ending "
            f"{missing_text}. This rollup covers {rollup['weeks_reported']} of "
            f"{rollup['weeks_expected']} weeks.</p>"
        )

    method_note = (
        "<p style='font-size:12px;color:#666;'>How this is figured: a week counts in "
        "the quarter its Monday actuals email went out, so every weekly email lands in "
        "exactly one quarter and one month. Company utilization is the weekly company "
        "numbers averaged within each month, then the monthly averages averaged for the "
        "quarter. A technician's quarter utilization is hours billed "
        "divided by actual hours paid over the quarter. Ramp-up weeks and weeks with no "
        "timecard are left out of the company average, same as the weekly report. If a "
        "week was re-run, the latest run is used.</p>"
    )

    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>"
        f"body {{ font-family: {BRAND_FONT_STACK}; color: {BRAND_PRIMARY_COLOR}; max-width: 880px; margin: 24px auto; padding: 0 16px; }}"
        "h2 { margin-top: 0; font-size: 18px; }"
        "h3 { margin: 24px 0 0; font-size: 15px; }"
        "p { line-height: 1.5; font-size: 14px; }"
        "table.actuals { border-collapse: collapse; width: 100%; margin-top: 12px; font-size: 13px; }"
        f"table.actuals th, table.actuals td {{ border: 1px solid {BRAND_TABLE_BORDER}; padding: 8px 10px; }}"
        f"table.actuals th {{ background: {BRAND_TABLE_HEADER_BG}; text-align: left; font-weight: 600; }}"
        f"table.actuals tfoot td {{ font-weight: 600; background: {BRAND_TABLE_HEADER_BG}; }}"
        "</style></head><body>"
        f"<h2>{title}</h2>"
        f"{banner}{lead_in}{range_line}"
        "<h3>By month</h3>"
        "<table class='actuals'><thead><tr>"
        "<th>Month</th>"
        "<th style='text-align:right'>Weekly Reports</th>"
        "<th style='text-align:right'>Average Utilization</th>"
        f"</tr></thead><tbody>{month_rows}</tbody>"
        "<tfoot><tr><td>Quarter</td><td></td>"
        f"<td style='text-align:right'>{_pct(rollup['company_utilization'])}</td>"
        "</tr></tfoot></table>"
        "<h3>By week</h3>"
        "<table class='actuals'><thead><tr>"
        "<th>Week</th>"
        "<th style='text-align:right'>Technicians</th>"
        "<th style='text-align:right'>Hours Billed</th>"
        "<th style='text-align:right'>Actual Hours Paid</th>"
        "<th style='text-align:right'>Non-Billable Hours</th>"
        "<th style='text-align:right'>Company Utilization</th>"
        f"</tr></thead><tbody>{week_rows}</tbody>"
        "<tfoot><tr><td>Quarter</td><td></td>"
        f"<td style='text-align:right'>{_hrs(rollup['total_billable'])}</td>"
        f"<td style='text-align:right'>{_hrs(rollup['total_actual_hours_paid'])}</td>"
        f"<td style='text-align:right'>{_hrs(rollup['total_non_billable'])}</td>"
        "<td></td>"
        "</tr></tfoot></table>"
        "<h3>By technician</h3>"
        "<table class='actuals'><thead><tr>"
        "<th>Technician</th>"
        "<th style='text-align:right'>Weeks</th>"
        "<th style='text-align:right'>Hours Billed</th>"
        "<th style='text-align:right'>Actual Hours Paid</th>"
        "<th style='text-align:right'>Quarter Utilization</th>"
        "<th style='text-align:right'>Target</th>"
        "<th style='text-align:right'>Weeks On Target</th>"
        "<th style='text-align:right'>Non-Billable Hours</th>"
        "<th>Notes</th>"
        f"</tr></thead><tbody>{tech_rows}</tbody></table>"
        f"{method_note}</body></html>"
    )
