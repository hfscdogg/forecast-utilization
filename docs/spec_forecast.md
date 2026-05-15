# Utilization Forecast Automation — Spec

**Owner:** Henry Clifford
**Build target:** Claude Code
**Status:** Ready for Phase 1 build. All field names resolved.
**Last updated:** 2026-05-13 (v1.4 — corrected schedule to Thursday 4 PM ET; flagged lagging actuals report as Phase 2)

---

## 1. Purpose

Replace the manual weekly Utilization Forecast process (currently run by Dustin on the service desk) with a scheduled Zoho Creator + Deluge automation that pulls job data from Zoho CRM, applies Livewire's forecasting math, emails formatted output to Leadership/PM/Logistics, and stores historical forecast data for accuracy measurement.

**Time saved:** ~30 min/week for Dustin.
**Strategic upside:** Historical forecast vs actuals dataset enables forecast accuracy tracking.

---

## 2. Current State (for context)

Every week, Dustin manually:

1. Opens three Zoho Desk Knowledgebase-linked reports:
   - `PROD_BILLABLE FORECAST RPT`
   - `PROD_NON-BILLABLE RPT (LW)` (filtered to next week)
   - `PROD_FORECAST PLACEHOLDER RPT (NW)`
2. Opens the `Billable Hours Reporting (Utilization)` Google Sheet
3. Duplicates the most recent tab, renames to next week's date range (both top-left header and tab name)
4. For each technician, enters:
   - Billable Hours Scheduled
   - Hours Scheduled
   - Forecast OT
   - Forecast Hours
5. Capped at 40 hours per tech on Hours Scheduled, overflow into Forecast OT
6. Screenshots the result and emails Leadership, PM, and Logistics for review
7. Reviews Placeholder report and confirms/removes events before sending

---

## 3. Target Architecture

```
┌──────────────────┐
│  Zoho Creator    │
│  (scheduled fn)  │  ← cron: Every Thursday 4:00 PM ET
└────────┬─────────┘
         │
         │ 1. Query CRM via COQL
         ▼
┌──────────────────┐
│  Zoho CRM        │
│  - Events        │  ← scheduled jobs (billable, non-billable, placeholders)
│  - Users (techs) │
└────────┬─────────┘
         │
         │ 2. Apply forecast math
         ▼
┌──────────────────┐
│  Deluge logic    │
│  - Trip charges  │
│  - 30-min adders │
│  - 40-hr cap     │
│  - OT overflow   │
└────────┬─────────┘
         │
         │ 3. Write history + email
         ├──────────────────┐
         ▼                  ▼
┌──────────────────┐   ┌──────────────────┐
│ Creator Form     │   │ Send Email (HTML)│
│ (history)        │   │ to distribution  │
└──────────────────┘   └──────────────────┘
```

**Tech stack:**
- Zoho Creator (host)
- Deluge (scripting)
- Zoho CRM (data source via COQL)
- Zoho Mail / `sendmail` Deluge task (delivery)

**Why CRM API direct, not running existing reports:** Reports are fragile (column rename = silent break). Direct COQL queries give a stable contract. Replicate filter logic in Deluge once; never touch it again.

---

## 4. Data Model

### 4.1 CRM Source Tables

Need to confirm exact module names during build, but expected:

- **Events** module (or equivalent scheduling object) — fields needed:
  - `Owner` / `Technician_1` (primary tech)
  - `Technician_2` (paired tech, if populated) — **confirmed by Stacy 2026-05-13**
  - `Duration_Man_Hrs` (display name: "Duration (Man Hrs)") — **confirmed by Stacy 2026-05-13 as a computed field**, queryable via COQL like any standard field. Pre-split per technician, handles trip charge math upstream.
  - `Start_DateTime`, `End_DateTime`
  - `Event_Type` (Billable / Non-Billable / Placeholder / Online-Booking-Block / PTO)
  - `Status` (to filter out cancelled)

> ⚠️ **Phase 1 verification task (not a blocker):** Confirm the exact API field name for `Duration (Man Hrs)` via a one-off `getRecords` call. Zoho typically converts display labels to underscored API names (e.g., `Duration_Man_Hrs`). Stored or computed field both work for COQL.

- **Users** / **Technicians** — fields needed:
  - `Active` flag (boolean) — **critical: terminated techs linger a few days; filter on active status, not presence**
  - `Display_Name`
  - `Role` (technician vs PM vs sales — only forecast on techs)

> ⚠️ **TODO during build:** Inspect actual `PROD_BILLABLE FORECAST RPT`, `PROD_NON-BILLABLE RPT (LW)`, and `PROD_FORECAST PLACEHOLDER RPT (NW)` report definitions in Zoho Desk to confirm exact field names, module, and filter criteria. Replicate as COQL.

### 4.2 Creator Form (history)

**Form name:** `Utilization_Forecast_History`

Fields (one record per tech per week):

| Field Name | Type | Notes |
|---|---|---|
| `Week_Of` | Date | Monday of forecasted week |
| `Forecast_Generated_At` | DateTime | When the script ran |
| `Technician_Name` | String | |
| `Technician_ID` | Lookup → Users | |
| `Billable_Hours_Scheduled` | Decimal | Sum after trip charge math |
| `Hours_Scheduled` | Decimal | Billable + 30 min/non-trip job, capped at 40 |
| `Forecast_OT` | Decimal | Overflow above 40 |
| `Forecast_Hours` | Decimal | Hours_Scheduled + Forecast_OT |
| `Forecast_Utilization` | Decimal | Hours_Scheduled / 40 |
| `Placeholder_Flags` | Multi-line | Any placeholder events flagged for review |
| `Run_ID` | String | UUID grouping all records from one weekly run |

---

## 5. Forecast Math (the rules)

### 5.1 Billable Hours Scheduled

**Simplified per Stacy's 2026-05-13 confirmation:** The CRM `Duration (Man Hrs)` field is computed and pre-split per technician. The SOP's "trip charge × 2 for solo / × 1 per tech for paired" rule is handled upstream by that computation — we don't reconstruct it.

For each technician:

```
billable_hours_scheduled = SUM(Duration_Man_Hrs) across all billable events
  WHERE (Technician_1 = this_tech OR Technician_2 = this_tech)
    AND Event_Type = Billable
    AND Status != Cancelled
    AND Start_DateTime is in forecast week
```

**Why this is simpler than the SOP's worded description:**

The SOP walks through Jim Zimmerman's example using trip charge multiplication ("2 hours each for May 12 and 15, and 1 hour for May 14 shared with Jordan = 5 hours total"). That's exactly what `Duration (Man Hrs)` produces — the report just shows the worked-out result. We sum that field directly.

### 5.2 Hours Scheduled

```
non_billable_event_count = count of non-billable scheduled events where this tech is Technician_1 or Technician_2
hours_scheduled = billable_hours_scheduled + SUM(Duration_Man_Hrs for non-billable events) + (0.5 × count of events without trip charge)
```

**TODO during Phase 1:** Verify whether the 30-min adder applies to *all* non-trip-charge events (the SOP's wording) or only non-billable ones. The SOP is ambiguous — re-read with Dustin if results diverge during parallel run.

```
IF hours_scheduled > 40:
  forecast_ot = hours_scheduled − 40
  hours_scheduled = 40
ELSE:
  forecast_ot = 0
```

### 5.3 Forecast Hours

```
forecast_hours = hours_scheduled + forecast_ot
```

### 5.4 Forecast Utilization

```
forecast_utilization = hours_scheduled / 40
```

### 5.5 Confirmed business rules (from Stacy & Dustin, 2026-05-12 / 2026-05-13)

- ✅ **Helper/Participant field is reliable** — safe to depend on for solo/paired determination (field name TBD during build, see 4.1)
- ✅ **40-hour cap is hard** for OT approval purposes
- ✅ **PTO does NOT count toward the 40** — tech must have 40 worked hours before OT
- ⚠️ **Training counts as worked hours** — could push into OT, avoided where possible
- ✅ **Time off (PTO and otherwise) is not factored into the forecast at all** (Dustin) — the forecast is based purely on scheduled jobs and clocked time. No half-day PTO math, no PTO subtraction from the 40-hour baseline. PTO appears in actuals, not forecast.

> Implication: When pulling jobs, exclude `Job_Type = PTO` from `hours_scheduled` totals. Include training. Flag training-related OT in the email so PMs can review.

---

## 6. Placeholder Review Logic

**Important clarification from Dustin (2026-05-13):** Only PMs create Placeholder events, and Placeholders are always tied to jobs. Dustin's online-booking time blocks are a **different event type entirely** and should be excluded from this logic.

Placeholder events need human confirmation/removal before the work week starts. Ownership routing is based on job type:

| Job Type | Owner |
|---|---|
| Builder Standards (RI & TO only) | Ben |
| A/V and electrical | Main PM (currently Brian Mosier) |

> Note: Dustin does NOT own placeholder review — earlier draft incorrectly assumed service techs had placeholder events. Service tech jobs do not generate placeholders.

**Implementation:** The weekly email includes a "⚠️ Placeholder Events Needing Review" section. Each row is tagged with the responsible PM based on the scheduler/creator of the placeholder event in CRM. v1 stays unified — single email with sub-sections per PM. **Filter out non-Placeholder event types** (Dustin's online-booking blocks) when scanning for review items.

---

## 7. Technician Roster — Active Status Handling

**Problem:** Terminated techs are left in Zoho for a few days post-termination (with password changed) to allow rescheduling of their future events. If the automation pulls all roster entries, it will produce ghost forecast rows for terminated techs.

**Solution:** Filter on an explicit "Active" status field, not roster presence. If no Active field exists today, add one to the Users/Technicians module before go-live.

> ⚠️ **TODO during build:** Confirm with Stacy whether an Active field exists. If not, add it and backfill.

---

## 8. Email Output

**Format:** HTML table in email body (no attachments, no screenshot).

**Distribution list:** Leadership, PM team, Logistics (confirm exact addresses during build — likely `leadership@getlivewire.com` plus individual PM aliases)

**Subject:** `Weekly Utilization Forecast: {WEEK_START} – {WEEK_END}`

**Body structure:**

```
Weekly Utilization Forecast
Week of {WEEK_START}–{WEEK_END}
Generated {TIMESTAMP}

[Forecast Table]
Technician | Billable Hrs | Hours Scheduled | Forecast OT | Forecast Hrs | Utilization
Josh B     | 32.5         | 35.0            | 0.0         | 35.0         | 87.5%
...
TOTALS     | 280.0        | 320.0           | 12.5        | 332.5        | —

⚠️ Placeholder Events Needing Review

Boulder Standards (Ben):
  • [Job 12345] May 14 — Jordan T at 11938 Red Cross Way

Service (Dustin):
  • [Job 12350] May 13 — Jeffrey at 8797 Pocahontas Trail

A/V & Electrical (Brian Mosier):
  • (none this week)

— Auto-generated by Utilization Forecast bot
  Source: Zoho CRM | History: [link to Creator report]
```

**Styling:** Match Livewire brand standards. Use Unicode bold for emphasis (not Markdown asterisks) in case any client strips HTML. No em dashes. No Oxford commas.

---

## 9. Open Questions — RESOLVED

Dustin's answers (2026-05-13) and Stacy's field-name follow-up (2026-05-13) closed out the open list:

| Question | Answer | Implementation impact |
|---|---|---|
| **Field names for paired tech and per-tech hours** | `Technician_2` and `Duration_Hours_per_tech` (Stacy) | Use these directly. Trip charge multiplication rule from SOP becomes irrelevant — handled upstream. |
| **Overlapping jobs** | Shouldn't happen. When they do, the scheduler (Dustin or PM) fixes them. | No special-case logic. Treat as data quality issue, not forecast logic. |
| **Multi-day jobs** | (Not explicitly raised.) Treat each scheduled event as discrete. | Apply 30-min adder per scheduled event, not per parent job. |
| **Mid-week reschedules** | Don't matter. Forecast is an estimate. Only Utilization (actuals) report is affected, and that only breaks if an event isn't updated within 2 weeks — which "should never happen." | No mid-week regen. Weekly run only. |
| **Half-day PTO / time off** | Not factored into forecast at all. Forecast is jobs + clocked time only. | Exclude all PTO/time-off event types from the query. |
| **On-call rotations** | Not explicitly addressed. Default: include only if scheduled as a job event in CRM. | Verify during Phase 1 sample data review. |
| **Non-standard job categories** | Online-booking blocks are a separate event type and should be excluded. Placeholders are PM-only and tied to jobs. | Filter event types explicitly — whitelist, not blacklist. |
| **Trip charges with helpers** | Handled upstream by `Duration_Hours_per_tech` field. | No reconstruction needed. |

**Remaining Phase 1 verification tasks (not blockers):**
1. Confirm the exact API field name for `Duration (Man Hrs)` via a one-off `getRecords` call (likely `Duration_Man_Hrs`).
2. Confirm whether the 30-min adder applies to all non-trip-charge events or only non-billable ones (Section 5.2).
3. Confirm whether an `Active` flag exists on the Users module, or add one.

---

## 10. Build Sequence (for Claude Code)

### Phase 1: Foundation (no scheduling yet)

1. Create new Zoho Creator app: `Utilization Forecast`
2. Create `Utilization_Forecast_History` form per Section 4.2
3. Build Deluge function `generate_forecast(week_start_date)`:
   - Accept a Monday date as input
   - Query CRM Events for that week
   - Apply Section 5 math
   - Return a structured object (don't email yet)
4. Test against a known historical week — compare to Dustin's actual output

### Phase 2: Output

5. Build HTML email template per Section 8
6. Build `send_forecast_email(forecast_object)` function
7. Write history records to `Utilization_Forecast_History` form

### Phase 3: Scheduling + parallel run

8. Wire up scheduled trigger: every Thursday 4:00 PM ET (forecasts the week starting the following Sunday/Monday)
9. **Run in parallel with Dustin's manual process for 2 weeks**
10. Compare automated output to Dustin's manual output every Monday
11. Reconcile any deltas — capture in a discrepancy log

### Phase 4: Cutover

12. Stop manual process
13. Retire the Google Sheet (or freeze read-only as archive)
14. Add a monthly check-in for the first 2 months to catch drift

---

## 11. Out of Scope (v1) — Planned for Future Phases

### Phase 2 (planned): Lagging Actuals Report

A companion automation that emails **actual** utilization for the *prior* week, every Monday at 4:00 PM ET. Pairs with the Thursday forecast to create a leading + lagging system.

**Open spec questions (to resolve before Phase 2):**
- Data source for clocked time (Zoho time logs, Zoho meeting reports, or both combined) — Stacy hinted "data from zoho meeting reports and time clocked in"
- Field set for the email (likely mirrors forecast format, may add "variance vs forecast" column)
- Distribution list (default: same as forecast — Leadership/PM/Logistics)

**Strategic upside:** Pairing leading + lagging unlocks forecast accuracy measurement (Thursday's forecast vs Monday's actuals for the same week). This is the real prize — knowing how reliable the forecast actually is over time.

### Other v2+ items

- Forecast accuracy dashboard (forecast vs actuals trended over time)
- Per-owner placeholder email routing (one email per PM instead of unified)
- Mid-week forecast regeneration on demand
- Mobile/Slack notifications
- Predictive forecasting (ML-based) — not planned

---

## 12. Acceptance Criteria

- [ ] Runs every Thursday at 4:00 PM ET without manual trigger
- [ ] Produces forecast numbers that match Dustin's manual output within ±0.5 hours per tech for 2 consecutive weeks
- [ ] Email lands in Leadership/PM/Logistics inboxes by 4:05 PM ET Thursday
- [ ] Placeholder events correctly tagged to Ben/Dustin/PM owner based on job type
- [ ] Only active technicians appear in the forecast
- [ ] Historical records written to Creator for every weekly run
- [ ] If the scheduled job fails, Henry gets an alert email

---

## 13. Risks

| Risk | Mitigation |
|---|---|
| CRM field/module names different than expected | Phase 1 starts with field inspection; spec gets updated before coding |
| Active tech field doesn't exist | Add it before build, backfill |
| Dustin's edge case answers reveal a rule the math doesn't handle | Block on Section 9 answers before Phase 1 completion |
| Email blast feels spammy week over week | v1 is opt-in via existing distribution list; revisit if recipients complain |
| Forecast diverges from manual during parallel run | 2-week parallel run is the catch; reconcile and patch before cutover |

---

## 14. Reference Files

- SOP location: Zoho Desk Knowledgebase → Utilization Forecasting (Version 2.0)
- Current spreadsheet: `Billable Hours Reporting (Utilization)` (Google Sheets)
- Source reports: `PROD_BILLABLE FORECAST RPT`, `PROD_NON-BILLABLE RPT (LW)`, `PROD_FORECAST PLACEHOLDER RPT (NW)`

---

## 15. Stakeholders

| Role | Person |
|---|---|
| Sponsor | Henry Clifford (CEO) |
| Operations owner | Stacy Hicks (COO) |
| Current process owner | Dustin (Service Desk) |
| Builder | Claude Code |
| Email recipients | Leadership, PM team, Logistics |
| Placeholder owners | Ben (Builder Standards), Brian Mosier (A/V & Electrical, main PM) |
