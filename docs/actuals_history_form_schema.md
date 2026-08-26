# Actuals History Form — Creator schema

One Creator form, one record per technician per scheduled actuals run. All
records from a single run share a `Run_ID` (matches the convention of
`Utilization_Forecast_History`).

**Form name:** `Utilization_Actuals_History`
**Link name (auto):** `Utilization_Actuals_History`
**Display name:** `Utilization Actuals History`

## Fields

| Field name | Link name | Type | Required | Notes |
|---|---|---|---|---|
| Run ID | `Run_ID` | Single Line | Yes | UUID-ish string grouping rows from one actuals run. |
| Actuals Generated At | `Actuals_Generated_At` | Date-Time | Yes | When the run executed. America/New_York. |
| Lag Week Start | `Lag_Week_Start` | Date | Yes | Monday of the lag week (8-14 days before run). |
| Lag Week End | `Lag_Week_End` | Date | Yes | Sunday of the lag week. |
| Technician | `Technician` | Single Line | Yes | Full name matching Zoho CRM users module. |
| Hours Billed | `Hours_Billed` | Decimal | Yes | Sum of billable Event durations for the lag week. No cap. |
| Non Billable Hours | `Non_Billable_Hours` | Decimal | Yes | Sum of non-billable Event durations for the lag week. |
| Hours Worked | `Hours_Worked` | Decimal | No | From iSolved time-cards, capped at 40. Null until iSolved access lands. |
| OT | `OT` | Decimal | No | iSolved time-card overflow above 40. Null pending iSolved. |
| Actual Hours Paid | `Actual_Hours_Paid` | Decimal | No | Hours Worked + (OT × 1.5). Null pending iSolved. |
| Actual Utilization | `Actual_Utilization` | Decimal | No | Hours Billed / Actual Hours Paid, fraction. Null pending iSolved. |
| Worked Utilization | `Worked_Utilization` | Decimal | No | Hours Worked / 40, fraction. Forecast-comparable. Null pending iSolved. |
| iSolved Pending | `iSolved_Pending` | Boolean | Yes | True when this row's time-card data is not yet wired. Flips to false once iSolved is integrated. Link name confirmed against the live form 2026-08-26 (lowercase leading i; Creator link names are case-insensitive-unique, so a case-only rename is impossible). |
| Notes | `Notes` | Multi Line | No | Auto-derived: non-billable totals, OT amount, "iSolved pending" marker. |
| Source Events Count | `Source_Events_Count` | Number | No | Total events the run scanned for this tech in the lag week. |

## Indexes

- `Run_ID` — exact lookup for "show me all rows from this run".
- `Technician` + `Lag_Week_Start` — composite for tech-history queries.
- `Lag_Week_Start` alone — for "all techs for this week" queries.

## Pairing with the forecast for accuracy tracking

The strategic prize: pair Thursday's forecast for a given week with the
matching Monday actuals for that same week, once it lands two weeks later.
That's what enables forecast-accuracy tracking.

Join key: match `Utilization_Forecast_History.Forecast_Week_Start` to
`Utilization_Actuals_History.Lag_Week_Start`. One forecast row and one
actuals row per (tech, week) makes diffing straightforward in a Creator
report or external dashboard later.

## How records are written

`write_actuals_history.dg` is called once per scheduled run with the full
actuals result Map plus the run's ID. It iterates the per-tech list and
uses Deluge's native `insert into Utilization_Actuals_History [ ... ]`
syntax (same reason as the forecast history form: `zoho.creator.createRecord`
on this tenant requires the 6-arg signature, while `insert into` runs
without a connection in the function's own auth context).
