# Forecast History Form — Creator schema

One Creator form, one record per technician per forecast run. All records
from a single run share a `Run_ID` (UUID) for easy grouping later.

**Form name:** `Utilization_Forecast_History`
**Link name (auto):** `Utilization_Forecast_History`
**Display name:** `Utilization Forecast History`

## Fields

| Field name | Link name | Type | Required | Notes |
|---|---|---|---|---|
| Run ID | `Run_ID` | Single Line | Yes | UUID grouping all rows from one forecast run. Index this field for fast lookup. |
| Forecast Generated At | `Forecast_Generated_At` | Date-Time | Yes | When the run executed. America/New_York. |
| Forecast Week Start | `Forecast_Week_Start` | Date | Yes | Monday of the forecast week. |
| Forecast Week End | `Forecast_Week_End` | Date | Yes | Sunday of the forecast week. |
| Technician | `Technician` | Single Line | Yes | Full name as it appears in the CRM users module. Plain text, not a lookup, since the manual sheet uses display names. |
| Billable Hours Scheduled | `Billable_Hours_Scheduled` | Decimal | Yes | 2 decimal places. |
| Hours Scheduled | `Hours_Scheduled` | Decimal | Yes | Uncapped per-tech total of all counted event hours plus drive-time adder. |
| Non Billable Hours | `Non_Billable_Hours` | Decimal | Yes | Excludes training. |
| Training Hours | `Training_Hours` | Decimal | Yes | Tracked separately; counts toward Hours Scheduled but flagged in Notes. |
| Drive Time Adder | `Drive_Time_Adder` | Decimal | Yes | 0.5 hr per on-site event without a trip charge. |
| Forecast OT | `Forecast_OT` | Decimal | Yes | max(0, Hours Scheduled minus 40). |
| Forecast Hours | `Forecast_Hours` | Decimal | Yes | Hours Scheduled minus Forecast OT (the within-40 portion). |
| Forecast Utilization | `Forecast_Utilization` | Decimal | Yes | Billable Hours Scheduled divided by Forecast Hours, stored as a fraction (e.g., 0.875 for 87.5%). |
| Training Drove OT | `Training_Drove_OT` | Boolean | No | True when forecast_ot greater than 0 and training_hours greater than 0. |
| Notes | `Notes` | Multi Line | No | Auto-derived facts (training hours, non-billable hours, unknown event types). |
| Unknown Event Types | `Unknown_Event_Types` | Multi Line | No | Comma-separated list. Non-empty means a data-entry mistake worth flagging. |
| Source Events Count | `Source_Events_Count` | Number | No | Total events the run scanned for this tech in the forecast week. Useful for spotting "tech has 0 events" weeks. |

## Indexes

- `Run_ID` — exact lookup for "show me all rows from this run".
- `Technician` + `Forecast_Week_Start` — composite index for "show me Joshua Brown's forecast history week by week".

## How records are written

`write_forecast_history.dg` is called once per scheduled run with the full
forecast result Map plus the run's UUID. It iterates the per-tech list and
calls `zoho.creator.createRecord` for each row, all sharing the same
`Run_ID` and `Forecast_Generated_At`.

## Lagging actuals counterpart

A parallel `Utilization_Actuals_History` form will be created in Phase 4
with the same shape plus the actuals columns (Hours Billed, Hours Worked,
OT, Actual Hours Paid, Actual Utilization, Worked Utilization). Sharing
the Run_ID concept lets us join forecast and actuals later for accuracy
tracking.
