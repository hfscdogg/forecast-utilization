"""
Render the Utilization Actuals (lagging) email as HTML.

Python mirror of deluge/send_actuals_email.dg. Keep in sync.

Two render modes:
- Full mode: iSolved time-card data present, all columns populated.
- iSolved-pending mode: time-card columns show as "—" with a banner
  explaining the data gap; CRM-side Hours Billed and Non-Billable still
  populate. This is the launch state until iSolved tenant API access lands.

Conventions: no em dashes (uses — = en dash for placeholders; em dash
specifically is banned), no Oxford commas, HTML <strong> for emphasis.
"""

from datetime import datetime

COMPANY_UTILIZATION_TARGET = 0.625

BRAND_PRIMARY_COLOR = "#222222"
BRAND_TABLE_BORDER = "#dddddd"
BRAND_TABLE_HEADER_BG = "#f4f4f4"
BRAND_PENDING_BG = "#fff8e1"
BRAND_FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)

PLACEHOLDER = "&mdash;"  # en dash, NOT em dash — used for missing iSolved data


def _fmt_hrs(x):
    if x is None:
        return PLACEHOLDER
    if x == 0:
        return "0"
    if abs(x - round(x)) < 0.005:
        return f"{int(round(x))}"
    return f"{x:.2f}"


def _fmt_pct(x):
    if x is None:
        return PLACEHOLDER
    return f"{x * 100:.2f}%"


def _join_no_oxford(items):
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _auto_notes(r):
    parts = []
    if r.get("timecard_missing"):
        parts.append("timecard missing in iSolved at run time")
    if r.get("non_billable_hours", 0) > 0:
        parts.append(f"{_fmt_hrs(r['non_billable_hours'])} non-billable hours")
    if r.get("ot") not in (None, 0):
        parts.append(f"{_fmt_hrs(r['ot'])} OT")
    return "; ".join(parts)


def _fmt_week_label(week_start, week_end):
    return f"{week_start.strftime('%a %b %-d')} to {week_end.strftime('%a %b %-d')}"


def render_actuals_email(per_tech_results, week_start, week_end, rollup):
    """Return HTML for the lagging actuals email body.

    per_tech_results: list of dicts from actuals_for_technician
    week_start, week_end: datetime instances bounding the lag week
    rollup: company_rollup output (must include isolved_pending flag)
    """
    isolved_pending = rollup.get("isolved_pending", True)
    week_label = _fmt_week_label(week_start, week_end)

    # Sort: by actual_utilization desc when present, else by hours_billed
    # desc. Rows with a missing timecard (util None in full mode) sink to
    # the bottom instead of racing hour counts against percentages.
    def sort_key(r):
        if r["actual_utilization"] is not None:
            return (1, r["actual_utilization"])
        return (0, r["hours_billed"])

    sorted_results = sorted(per_tech_results, key=sort_key, reverse=True)

    rows = []
    for r in sorted_results:
        rows.append(f"""
          <tr>
            <td>{r['technician']}</td>
            <td style="text-align:right">{_fmt_hrs(r['hours_billed'])}</td>
            <td style="text-align:right">{_fmt_hrs(r['hours_worked'])}</td>
            <td style="text-align:right">{_fmt_hrs(r['ot'])}</td>
            <td style="text-align:right">{_fmt_hrs(r['actual_hours_paid'])}</td>
            <td style="text-align:right"><strong>{_fmt_pct(r['actual_utilization'])}</strong></td>
            <td style="text-align:right">{_fmt_hrs(r['non_billable_hours'])}</td>
            <td style="font-size:11px;color:#666">{_auto_notes(r)}</td>
          </tr>""")

    rows_html = "".join(rows)

    if isolved_pending:
        banner = (
            f'<p style="background:{BRAND_PENDING_BG};padding:10px 14px;'
            f'border-left:3px solid #d4a017;font-size:13px;">'
            f"<strong>iSolved integration pending:</strong> Hours Worked, OT, "
            f"Actual Hours Paid, and Actual Utilization will populate once "
            f"the iSolved tenant API access is wired. Until then those "
            f"columns show {PLACEHOLDER}. Hours Billed and Non-Billable Hours "
            f"come straight from CRM and are correct as of this run."
            f"</p>"
        )
        lead_in = (
            f"<p>Last week we billed <strong>{_fmt_hrs(rollup['total_billable'])}</strong> "
            f"hours across <strong>{rollup['tech_count']}</strong> technicians, "
            f"averaging <strong>{_fmt_hrs(rollup['avg_billable_per_tech'])}</strong> "
            f"billable hours per tech. Non-billable hours totalled "
            f"<strong>{_fmt_hrs(rollup['total_non_billable'])}</strong>.</p>"
        )
        congrats_line = ""
    else:
        missing = rollup.get("timecard_missing_techs") or []
        if missing:
            banner = (
                f'<p style="background:{BRAND_PENDING_BG};padding:10px 14px;'
                f'border-left:3px solid #d4a017;font-size:13px;">'
                f"<strong>Timecard missing:</strong> "
                f"{_join_no_oxford(missing)} had billed hours but no iSolved "
                f"time when this run fired, so their utilization shows "
                f"{PLACEHOLDER} and they are left out of the company average. "
                f"Re-run once the time is entered for a corrected number."
                f"</p>"
            )
        else:
            banner = ""
        lead_in = (
            f"<p>Last week we billed <strong>{_fmt_hrs(rollup['total_billable'])}</strong> "
            f"hours across <strong>{rollup['tech_count']}</strong> technicians, "
            f"averaging <strong>{_fmt_hrs(rollup['avg_billable_per_tech'])}</strong> "
            f"billable hours per tech for a company utilization of "
            f"<strong>{_fmt_pct(rollup['company_utilization'])}</strong>.</p>"
        )
        above_target = rollup["techs_above_target"] or []
        if above_target:
            congrats_line = (
                f"<p>Congrats to <strong>{_join_no_oxford(above_target)}</strong> "
                f"for being above our {_fmt_pct(COMPANY_UTILIZATION_TARGET)} "
                f"utilization target.</p>"
            )
        else:
            congrats_line = (
                f"<p>No technician landed above the {_fmt_pct(COMPANY_UTILIZATION_TARGET)} "
                f"target last week.</p>"
            )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Utilization Actuals for {week_label}</title>
<style>
  body {{ font-family: {BRAND_FONT_STACK}; color: {BRAND_PRIMARY_COLOR}; max-width: 880px; margin: 24px auto; padding: 0 16px; }}
  h2 {{ margin-top: 0; font-size: 18px; }}
  p {{ line-height: 1.5; font-size: 14px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 16px; font-size: 13px; }}
  th, td {{ border: 1px solid {BRAND_TABLE_BORDER}; padding: 8px 10px; }}
  th {{ background: {BRAND_TABLE_HEADER_BG}; text-align: left; font-weight: 600; }}
  tfoot td {{ font-weight: 600; background: {BRAND_TABLE_HEADER_BG}; }}
</style>
</head>
<body>
<h2>Utilization Actuals for {week_label}</h2>
{banner}
{lead_in}
{congrats_line}
<table>
  <thead>
    <tr>
      <th>Technician</th>
      <th style="text-align:right">Hours Billed</th>
      <th style="text-align:right">Hours Worked</th>
      <th style="text-align:right">OT</th>
      <th style="text-align:right">Actual Hours Paid</th>
      <th style="text-align:right">Actual Utilization</th>
      <th style="text-align:right">Non-Billable Hours</th>
      <th>Notes</th>
    </tr>
  </thead>
  <tbody>{rows_html}
  </tbody>
  <tfoot>
    <tr>
      <td>Total</td>
      <td style="text-align:right">{_fmt_hrs(rollup['total_billable'])}</td>
      <td style="text-align:right">{_fmt_hrs(rollup.get('total_hours_worked'))}</td>
      <td style="text-align:right">{_fmt_hrs(rollup.get('total_ot'))}</td>
      <td style="text-align:right">{_fmt_hrs(rollup.get('total_actual_hours_paid'))}</td>
      <td style="text-align:right">{_fmt_pct(rollup.get('company_utilization'))}</td>
      <td style="text-align:right">{_fmt_hrs(rollup['total_non_billable'])}</td>
      <td></td>
    </tr>
  </tfoot>
</table>
</body>
</html>"""
