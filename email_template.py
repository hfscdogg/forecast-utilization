"""
Render the Utilization Forecast email as HTML.

Python mirror of deluge/send_forecast_email.dg. Keep in sync. Tests in
tests/test_email_template.py cover the output structure and key derived
values; pixel rendering happens in Gmail/Outlook and is verified by eye.

Conventions enforced (per Henry):
- No em dashes anywhere in body text.
- No Oxford commas in lists.
- HTML <strong> for emphasis (renders correctly in every email client).
  Henry's "Unicode bold not Markdown" rule is for plain-text contexts;
  HTML email uses semantic tags.
- Whitelist event types; the email flags any "unknown" types so a
  data-entry mistake surfaces instead of being silently dropped.
"""

from datetime import datetime

COMPANY_UTILIZATION_TARGET = 0.625  # mirrors config.dg

# Brand placeholders (mirrors config.dg). Restyle when brand guide lands.
BRAND_PRIMARY_COLOR = "#222222"
BRAND_TABLE_BORDER = "#dddddd"
BRAND_TABLE_HEADER_BG = "#f4f4f4"
BRAND_FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)


def company_rollup_forecast(per_tech_results):
    """Compute the company-wide totals row + congrats list from per-tech
    forecasts. Matches Dustin's sheet conventions:
    - Total Billable, Total Scheduled, Total OT, Total Forecast Hours are
      straight sums.
    - Company forecast utilization is the MEAN of per-tech utilizations
      (excluding techs with zero forecast hours), NOT total_b/total_s.
      Verified from the 5/17-5/23 tab: 71.63% = mean of 7 per-tech values,
      while 83/126 = 65.87% would be the naive ratio.
    - Congrats list: techs at or above the 62.5% target.
    """
    total_billable = sum(r["billable_hours_scheduled"] for r in per_tech_results)
    total_scheduled = sum(r["hours_scheduled"] for r in per_tech_results)
    total_ot = sum(r["forecast_ot"] for r in per_tech_results)
    total_forecast_hours = sum(r["forecast_hours"] for r in per_tech_results)
    total_non_billable = sum(
        r["non_billable_hours"] + r.get("training_hours", 0)
        for r in per_tech_results
    )

    utils = [
        r["forecast_utilization"]
        for r in per_tech_results
        if r["forecast_hours"] > 0
    ]
    company_util = sum(utils) / len(utils) if utils else 0

    techs_above_target = [
        r["technician"]
        for r in per_tech_results
        if r["forecast_utilization"] >= COMPANY_UTILIZATION_TARGET
    ]

    tech_count = len(per_tech_results)
    avg_billable = total_billable / tech_count if tech_count else 0

    return {
        "tech_count": tech_count,
        "total_billable": total_billable,
        "total_scheduled": total_scheduled,
        "total_ot": total_ot,
        "total_forecast_hours": total_forecast_hours,
        "total_non_billable": total_non_billable,
        "company_utilization": company_util,
        "avg_billable_per_tech": avg_billable,
        "techs_above_target": techs_above_target,
    }


def _fmt_hrs(x):
    if x is None:
        return ""
    if x == 0:
        return "0"
    if abs(x - round(x)) < 0.005:
        return f"{int(round(x))}"
    return f"{x:.2f}"


def _fmt_pct(x):
    return f"{x * 100:.2f}%"


def _join_no_oxford(items):
    """Join a list of strings with commas, no Oxford comma. Trailing 'and'."""
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f" and {items[-1]}"


def _auto_notes(r):
    """Synthesize the Notes column from per-tech derived values. The manual
    process leaves these blank for the coordinator; the automation populates
    them so each row carries its own context."""
    parts = []
    if r.get("training_hours", 0) > 0:
        parts.append(f"{_fmt_hrs(r['training_hours'])} training hours")
    if r.get("non_billable_hours", 0) > 0:
        parts.append(f"{_fmt_hrs(r['non_billable_hours'])} non-billable hours")
    if r.get("drive_time_adder", 0) > 0:
        parts.append(f"{_fmt_hrs(r['drive_time_adder'])} drive-time adder")
    if r.get("training_drove_ot"):
        parts.append("training drove OT")
    if r.get("unknown_event_types"):
        unknowns = ", ".join(r["unknown_event_types"])
        parts.append(f"unknown event types: {unknowns}")
    return "; ".join(parts)


def _fmt_week_label(week_start, week_end):
    """Mon May 18 to Sun May 24."""
    return f"{week_start.strftime('%a %b %-d')} to {week_end.strftime('%a %b %-d')}"


def render_forecast_email(per_tech_results, week_start, week_end, rollup=None):
    """Return an HTML string for the forecast email body.

    per_tech_results: list of dicts from forecast_for_technician.
    week_start, week_end: datetime instances bounding the forecast week.
    rollup: optional precomputed company_rollup_forecast result; computed
        if not provided.
    """
    if rollup is None:
        rollup = company_rollup_forecast(per_tech_results)

    sorted_results = sorted(
        per_tech_results,
        key=lambda r: r["forecast_utilization"],
        reverse=True,
    )

    week_label = _fmt_week_label(week_start, week_end)

    rows = []
    for r in sorted_results:
        notes = _auto_notes(r)
        rows.append(f"""
          <tr>
            <td>{r['technician']}</td>
            <td style="text-align:right">{_fmt_hrs(r['billable_hours_scheduled'])}</td>
            <td style="text-align:right">{_fmt_hrs(r['hours_scheduled'])}</td>
            <td style="text-align:right">{_fmt_hrs(r['forecast_ot'])}</td>
            <td style="text-align:right">{_fmt_hrs(r['forecast_hours'])}</td>
            <td style="text-align:right"><strong>{_fmt_pct(r['forecast_utilization'])}</strong></td>
            <td style="font-size:11px;color:#666">{notes}</td>
          </tr>""")

    rows_html = "".join(rows)

    if rollup["techs_above_target"]:
        congrats_line = (
            f"<p>Congrats to <strong>{_join_no_oxford(rollup['techs_above_target'])}</strong> "
            f"for being above our {_fmt_pct(COMPANY_UTILIZATION_TARGET)} utilization target.</p>"
        )
    else:
        congrats_line = (
            f"<p>No technician landed above the {_fmt_pct(COMPANY_UTILIZATION_TARGET)} target this week.</p>"
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Utilization Forecast for {week_label}</title>
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
<h2>Utilization Forecast for {week_label}</h2>
<p>Forecasting <strong>{_fmt_hrs(rollup['total_billable'])}</strong> billable hours across <strong>{rollup['tech_count']}</strong> technicians, averaging <strong>{_fmt_hrs(rollup['avg_billable_per_tech'])}</strong> billable hours per tech for a company forecast utilization of <strong>{_fmt_pct(rollup['company_utilization'])}</strong>.</p>
{congrats_line}
<table>
  <thead>
    <tr>
      <th>Technician</th>
      <th style="text-align:right">Billable Hrs Sched</th>
      <th style="text-align:right">Hours Scheduled</th>
      <th style="text-align:right">Forecast OT</th>
      <th style="text-align:right">Forecast Hours</th>
      <th style="text-align:right">Forecast Utilization</th>
      <th>Notes</th>
    </tr>
  </thead>
  <tbody>{rows_html}
  </tbody>
  <tfoot>
    <tr>
      <td>Total</td>
      <td style="text-align:right">{_fmt_hrs(rollup['total_billable'])}</td>
      <td style="text-align:right">{_fmt_hrs(rollup['total_scheduled'])}</td>
      <td style="text-align:right">{_fmt_hrs(rollup['total_ot'])}</td>
      <td style="text-align:right">{_fmt_hrs(rollup['total_forecast_hours'])}</td>
      <td style="text-align:right">{_fmt_pct(rollup['company_utilization'])}</td>
      <td></td>
    </tr>
  </tfoot>
</table>
</body>
</html>"""
