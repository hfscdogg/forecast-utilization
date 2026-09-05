# Parallel Run Log

Weekly comparison of the automated forecast against Dustin's manual numbers
for the same report week (Sun-Sat as of 2026-09-05, matching Dustin's manual
week; Mon-Sun before that). The point is the same-moment apples-to-apples diff:
both runs read CRM as it stands Thursday afternoon and produce numbers for
the upcoming week. The 5/14 manual vs 5/21 automated mismatch we did during
Phase 1 validation is *not* a parallel run; it was a snapshot mismatch.

## Cutover criteria

Per the spec acceptance check (and Henry's standing rule): the automated
forecast must match Dustin's manual within **±0.5 hours per technician** on
both Billable Hours Scheduled and Hours Scheduled, for **2 consecutive
weeks**, before the email distribution widens beyond `henry@getlivewire.com`.

Failures should be diagnosed and either:
- Fixed in code (math bug, taxonomy gap, sort order, etc.) — clock resets
- Documented as a known manual-process quirk we accept (e.g., hand-entered
  inconsistency like Patrick's billable 10 / scheduled 9) — clock continues

## Status tracker

| Week of (Mon-Sun) | Run ID | Within ±0.5? | Consecutive count | Notes |
|---|---|---|---|---|
| 2026-06-01 to 2026-06-07 | _pending_ | _pending_ | 0 | First scheduled run, fires Thu 5/28 16:00 ET |
| 2026-06-08 to 2026-06-14 | _pending_ | _pending_ | 0 | |

Cutover unlocks when the consecutive count hits 2.

---

## Week of 2026-06-01 to 2026-06-07

**Automated run:** scheduled Thursday 2026-05-28 16:00 ET. Fill in once it
fires.

| Field | Value |
|---|---|
| Run ID | _pending_ |
| Forecast Generated At | _pending_ |
| Tech count | _pending_ |
| Events scanned | _pending_ |
| Email delivered? | _pending_ |
| History rows written? | _pending_ |

### Per-tech comparison

| Technician | Mine: Billable | Dustin: Billable | Δ Billable | Mine: Hrs Sched | Dustin: Hrs Sched | Δ Hrs Sched | Within ±0.5? |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |

### Company rollup

| Metric | Mine | Dustin | Δ |
|---|---|---|---|
| Total Billable | | | |
| Total Hours Scheduled | | | |
| Total Forecast OT | | | |
| Company Utilization (%) | | | |
| Techs above 62.5% | | | |

### Reconciliation notes

_Any per-tech divergences, suspected causes (snapshot timing, multi-day
event over-count, taxonomy edge case, hand-entered quirk), and follow-ups._

---

## Week of 2026-06-08 to 2026-06-14

**Automated run:** scheduled Thursday 2026-06-04 16:00 ET.

| Field | Value |
|---|---|
| Run ID | _pending_ |
| Forecast Generated At | _pending_ |
| Tech count | _pending_ |
| Events scanned | _pending_ |
| Email delivered? | _pending_ |
| History rows written? | _pending_ |

### Per-tech comparison

| Technician | Mine: Billable | Dustin: Billable | Δ Billable | Mine: Hrs Sched | Dustin: Hrs Sched | Δ Hrs Sched | Within ±0.5? |
|---|---|---|---|---|---|---|---|
| | | | | | | | |
| | | | | | | | |

### Company rollup

| Metric | Mine | Dustin | Δ |
|---|---|---|---|
| Total Billable | | | |
| Total Hours Scheduled | | | |
| Total Forecast OT | | | |
| Company Utilization (%) | | | |
| Techs above 62.5% | | | |

### Reconciliation notes

_TBD_

---

## How to fill this in each week

After Thursday's scheduled run fires:

1. Open the Utilization Forecast History form in Creator and filter on the
   newest Run_ID. Each row is one tech.
2. Open Dustin's Google Sheet (Billable Hours Reporting / Utilization tab
   for the same Mon-Sun) and grab his Billable Hours Scheduled and Hours
   Scheduled columns.
3. Fill the per-tech table above. Compute Δ = mine minus Dustin's. Mark
   each row green (|Δ| ≤ 0.5 on both columns), yellow (one of the two
   over), or red (both over or large gap).
4. If any row is yellow/red, write a one-line note explaining the suspected
   cause and whether it needs a code fix.
5. Update the status tracker at the top: increment the consecutive-pass
   counter if all techs were green this week, reset to 0 otherwise.

When the consecutive counter hits 2, widen `EMAIL_FULL_DISTRIBUTION` in
`config.dg` to include leadership / PM / logistics, swap the automation's
TO list to that, and announce the cutover.
