"""
Validate forecast_math.py against Dustin's manual 5/17-5/23 forecast tab.

Loads:
  fixtures/events_sample_week.json   (CRM events for 5/16-5/25)
  fixtures/users_sample.json         (id -> name)
  fixtures/expected_forecast.json    (Dustin's manual numbers, 7 techs)

Enriches each event with Owner = users[Owner.id], filters by Start_DateTime
to two candidate forecast-week bins, runs forecast_for_technician for each
of the 7 techs, and prints the comparison.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from email_template import render_forecast_email  # noqa: E402
from forecast_math import forecast_for_technician  # noqa: E402


def load_fixture(name):
    with open(ROOT / "fixtures" / name) as f:
        return json.load(f)


def enrich_events(events, users_by_id):
    """Replace Owner dict with the owner's full name string so forecast_math
    can compare Owner against tech names."""
    out = []
    for e in events:
        owner_id = e["Owner"]["id"]
        e_copy = dict(e)
        e_copy["Owner"] = users_by_id.get(owner_id, f"UNKNOWN({owner_id})")
        out.append(e_copy)
    return out


def filter_week(events, start_iso, end_iso):
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return [
        e for e in events
        if start <= datetime.fromisoformat(e["Start_DateTime"]) <= end
    ]


def fmt_row(name, r, exp):
    return (
        f"{name:<10} "
        f"{r['billable_hours_scheduled']:>7.2f} {r['hours_scheduled']:>7.2f} "
        f"{r['forecast_utilization'] * 100:>7.2f}%  "
        f"|  {exp['billable_hours_scheduled']:>5} {exp['hours_scheduled']:>5} "
        f"{exp['forecast_utilization'] * 100:>6.2f}%"
    )


def run(events, expected, label, window_start, window_end):
    print(f"\n{'=' * 78}")
    print(f"BIN: {label}  ({len(events)} events in window, with pro-rating)")
    print(f"{'=' * 78}")
    print(
        f"{'Tech':<10} "
        f"{'mine_B':>7} {'mine_S':>7} {'mine_U':>8}   "
        f"|  Dustin (sheet)"
    )
    print("-" * 78)
    for sheet_name, exp in expected["technicians"].items():
        if exp["hours_scheduled"] == 0:
            continue
        full_name = expected["_name_map"][sheet_name]
        r = forecast_for_technician(full_name, events, window_start, window_end)
        print(fmt_row(sheet_name, r, exp))


def main():
    events_data = load_fixture("events_sample_week.json")
    users_data = load_fixture("users_sample.json")
    expected = load_fixture("expected_forecast.json")

    all_events = enrich_events(events_data["events"], users_data["users_by_id"])

    bins = [
        ("Mon 5/18 00:00 - Sun 5/24 23:59 EDT",
         "2026-05-18T00:00:00-04:00", "2026-05-24T23:59:59-04:00"),
        ("Sun 5/17 - Sat 5/23 (literal tab label)",
         "2026-05-17T00:00:00-04:00", "2026-05-23T23:59:59-04:00"),
    ]
    for label, s, e in bins:
        ws = datetime.fromisoformat(s)
        we = datetime.fromisoformat(e)
        events = filter_week(all_events, s, e)
        run(events, expected, label, ws, we)

    # Render a sample email from the Mon-Sun bin for visual inspection.
    ws = datetime.fromisoformat("2026-05-18T00:00:00-04:00")
    we = datetime.fromisoformat("2026-05-24T23:59:59-04:00")
    events = filter_week(all_events, "2026-05-18T00:00:00-04:00", "2026-05-24T23:59:59-04:00")
    per_tech = []
    for sheet_name, exp in expected["technicians"].items():
        if exp["hours_scheduled"] == 0:
            continue
        full_name = expected["_name_map"][sheet_name]
        per_tech.append(forecast_for_technician(full_name, events, ws, we))
    html = render_forecast_email(per_tech, ws, we)
    out_path = ROOT / "fixtures" / "sample_email.html"
    out_path.write_text(html)
    print(f"\nSample email rendered to: {out_path}")
    print(f"Open in a browser to preview, or send to yourself for an email-client check.")


if __name__ == "__main__":
    main()
