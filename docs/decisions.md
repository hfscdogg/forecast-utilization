# Decisions Log

A running record of decisions made during the build, with attribution and date.
Future-Claude and future-Henry should read this before changing anything in `deluge/config.dg`.

---

## 2026-05-15 — Dustin (Service Desk)

### Forecast vs Actuals must stay on separate systems

> "When calculating the forecast, you would use Forecast Scheduled, which is not hard data. It is an estimation of how long they SHOULD be clocked in based on what they've been scheduled for at that time. The Lagging Utilization report uses actual hard data from the time card. They are two different systems, and should remain that way for accurate data."

**Implication:** Forecast pulls scheduled hours from Zoho CRM Events. Actuals pull clocked hours from iSolved. No shared "hours" source. Encoded as a code-level separation in `config.dg` — distinct FORECAST and ACTUALS sections.

### iSolved is the timecard source

> "It is done in the same way as the forecast, with minor exceptions: we filter the dates differently because it's reading from different weeks. iSolved provides hours worked, and we don't estimate drive times."

**Implication:** iSolved API is the Hours Worked source for the lagging report. Three deltas vs the forecast:
1. Date window: 2 weeks back, not 1 week forward
2. Hours Worked source: iSolved API, not CRM-derived scheduled hours
3. No 30-min drive-time adder (forecast estimates, actuals doesn't)

Dominion Payroll has no known public API per Dustin; McKenzie is investigating broader timecard automation but it's not required — iSolved (the HCM behind Dominion's Manager View) has its own API.

### Actual Utilization formula

> "That formula is this `=SUM(Hours Billed/Hours Paid)`. It's essentially taking the value of hours billed and dividing by hours paid. So in the spreadsheet it may look like `=SUM(H6/K6)` for example."

**Implication:** `actual_utilization = hours_billed / actual_hours_paid`.

### OT paid at time-and-a-half — verified from spreadsheet

Read of the live spreadsheet on 2026-05-15 confirmed: `actual_hours_paid = hours_worked + (ot * 1.5)`.

Verified examples:
- Grant: Hours Worked 40, OT 2.88, Actual Hours Paid 44.32 → 40 + 2.88 × 1.5 = 44.32 ✓
- Stephen: Hours Worked 40, OT 3.92, Actual Hours Paid 45.88 → 40 + 3.92 × 1.5 = 45.88 ✓
- Josh (no OT): Hours Worked 35.57, OT blank, Actual Hours Paid 35.57 ✓

Earlier draft used `actual_hours_paid = hours_worked + ot` (no multiplier), which would have under-stated paid hours and over-stated utilization for any tech with OT. Corrected before any code was written. Encoded as `OT_PAY_MULTIPLIER = 1.5` in config so a future change (e.g., double-time on holidays) is a one-file edit.

### Company utilization target = 62.5%

From Dustin's spreadsheet email lead-in: "Congrats to ... for hitting our 62.5% utilization goal." Encoded as `COMPANY_UTILIZATION_TARGET = 0.625` and used to drive the congrats-list in the email template.

### Per-tech sort order = descending by Actual Utilization

Matches Dustin's spreadsheet convention. Encoded as the default sort in both forecast and actuals email templates.

---

## 2026-05-13 — Stacy (COO) and Dustin

### Trip-charge math handled upstream by `Duration_Hours_per_tech`

`Duration (Man Hrs)` is a computed CRM field that pre-splits hours per technician on multi-tech jobs. The SOP's "trip charge × 2 for solo / × 1 per tech for paired" rule is irrelevant — we sum the field directly. Field display name confirmed as "Duration (Man Hrs)"; API name likely `Duration_Man_Hrs` (TODO verify with inspector script).

### `Technician_2` field exists for paired-tech jobs

Use `Technician_1` (= Owner) OR `Technician_2` as the filter when summing per-tech hours. No reconstruction of pairings needed.

### Active technician filtering required

Terminated techs linger in Zoho for ~a few days post-termination so their future events can be rescheduled. Filter on an explicit `Active` flag, not roster presence. If the field doesn't exist yet, Stacy will add it before go-live.

### PTO is fully excluded from forecast

> "Time off (PTO and otherwise) is not factored into the forecast at all. The forecast is based purely on scheduled jobs and clocked time."

Training counts as worked hours. Training-driven OT gets flagged in the email.

---

## 2026-05-15 — Henry (Sponsor)

### Build approach

- **Repo role:** Deluge source mirror + Python test harness + fixtures + docs (this repo).
- **Verification gaps:** Build with assumed field names behind `config.dg` constants; swap at deploy.
- **Zoho access:** Production read-only credentials coming separately from Henry.
- **Session scope:** Forecast Phases 1–3 (math → output → scheduled parallel run), then lagging Phase 4 (iSolved-integrated).
- **Parallel-run TO list:** `henry@getlivewire.com` only, until math matches Dustin's for 2 consecutive weeks.
- **Failure alert TO:** `henry@getlivewire.com`.
- **Sender:** `henry@getlivewire.com` (placeholder — swap to dedicated bot address at cutover).
- **Brand styling:** brand guide URL at `claude.ai/design/p/9c200e29-8f70-4513-82bc-21936e70fd35`; restyle email template before Phase 2 ships.
- **Test harness:** Python 3 + pytest, stdlib only.

### Email and prose conventions

- No em dashes.
- No Oxford commas.
- Unicode bold for emphasis in email body (not Markdown asterisks).
- Whitelist event types — never blacklist.

---

## 2026-05-18 — CRM Inspector Run

First successful read of live CRM. Confirmed field shape; documented in
`docs/field_mapping.md`. Highlights of what changed vs. assumption:

### Confirmed
- `Duration_Man_Hrs` API name ✓ (matches assumption)
- Active flag exists ✓ (`users.status == "active"`)
- No custom Technicians module — built-in users endpoint is the only roster source

### Changed from spec assumptions
- **Technician 2 field's API name is `Helper1`**, not `Technician_2`. It's a free
  picklist of name strings, not a user lookup — paired-tech filtering compares
  by name, not ID.
- **Event_Status, not Status.** And the picklist has no "Cancelled" value —
  spec's `Status != Cancelled` rule has no direct map. See open items below.
- **Event_Type has 22 used values, not 3.** "Billable / Non-Billable / Training"
  was a simplification. Real categorization tracked in `config.dg` EVENT_TYPES_*
  lists, with TODOs for Dustin to confirm the ambiguous ones.
- **Trip_Charge is a numeric picklist** (`1`/`2`/`3`/`4`), not boolean. `null` or
  `"-None-"` means no trip charge.

### Open items surfaced by the inspector
1. **Event_Type categorization** — RESOLVED, see Dustin 2026-05-18 below.
2. **Cancellation tracking** — RESOLVED, see Dustin 2026-05-18 below.
3. **Technician identification** — still open, pending Stacy.

## 2026-05-18 — Dustin (Event_Type categorization + rules)

### Cancellation tracking — no status filter needed

> "Cancelled events are usually just set to 'incomplete - Job not ready' and we
> change the time to be 1 minute. We can't just delete them because zoho starts
> being weird on reporting so we leave them there, adjust their times, and mark
> them incomplete - job not ready, then put in the 'ActionTaken (office only)'
> field that the job was cancelled or rescheduled."

**Implication:** the math needs NO status filter. A cancelled event has a
1-minute duration (~0.017 hr), so it self-neutralizes when Duration_Man_Hrs is
summed. "Incomplete - Job Not Ready" is also a valid status for genuinely-not-
ready jobs, so it must never be blanket-filtered. The auto-Notes feature can
detect cancellations heuristically: status "Incomplete - Job Not Ready" + a
duration under CANCELLED_EVENT_MAX_HOURS (0.1 hr).

### 30-minute drive-time adder — on-site, no trip charge

> "It applies to all events without trip charges, but is only counted when a
> technician goes to an actual customer site. If they have a meeting/training
> at the shop it isn't counted, so location matters."

**Implication:** the 0.5 hr adder applies per event where the event has no trip
charge AND its Event_Type is on-site (customer location). config.dg
EVENT_TYPES_ONSITE = billable jobs + warranty/punchout. Shop-based types
(Training, Meeting, Project Management) get no adder.

### Scheduled Off — excluded

> "Scheduled off just means the tech isn't working that day ... it probably
> doesn't need to consider it."

**Implication:** "Scheduled Off" is in EVENT_TYPES_EXCLUDED — contributes no
hours.

### Event types confirmed NOT in use

Dustin: Remote Support (Parasol), Sub Contractor Finish-Out, Discovery -
Prepaid, Remote Assistance — all unused. Removed from the billable whitelist.
If one appears it falls through to "unknown" and the email flags it.

**Retrofit** — Dustin says it "shouldn't be used" (work is really a Finish-Out
or Service) but Brian M used it this week. Kept billable so the hours are not
lost; the email flags it so Dustin can correct the source record.

**Service Location** — Dustin: an event type he uses to block online booking
and keep it off reports. "Not billable and shouldn't be considered in the
calculations at all." Added to EVENT_TYPES_EXCLUDED.

### In-House Electrical — RESOLVED 2026-05-19

Dustin: "In House Electrical works the same way as service payment required.
It is billable time." Added to EVENT_TYPES_BILLABLE and EVENT_TYPES_ONSITE.
All 22 used Event_Type values are now categorized.

## 2026-05-19 — Sheet-derived corrections

Read the live "Billable Hours Reporting (Utilization)" Google Sheet directly
(Henry has editor access, the Drive tools can read it). Two findings.

### Forecast utilization formula — spec was wrong

The spec (Section 5) said `forecast_utilization = hours_scheduled / 40`. The
sheet instead divides billable scheduled hours by a denominator. Dustin
confirmed 2026-05-19 the exact denominator:

    forecast_utilization = billable_hours_scheduled / forecast_hours

where `forecast_hours` is the within-40 portion of scheduled time
(hours_scheduled minus the OT overflow). For a tech under 40 hours,
forecast_hours equals hours_scheduled, so the under-40 sheet rows still check
out: David 17.5 / 20 = 87.50%, Grant 22.5 / 27.5 = 81.82%, Bill 30 / 32 =
93.75%, Jim 20 / 26.5 = 75.47%.

OPEN (non-blocking): no over-40 row in the new sheet format was captured
before Drive access dropped, so the exact definition of Forecast Hours when a
tech exceeds 40 is an assumption. Current code: forecast_hours =
min(hours_scheduled, 40). An alternative (forecast_hours = 40 + OT * 1.5,
mirroring Actual Hours Paid) is possible but less likely for a utilization
metric. The reference validation week has every tech under 40, so this does
not block Phase 1. Confirm with Dustin if a parallel-run week drifts.

Consequence: forecast utilization and actual utilization are BOTH billable-
fraction metrics, so they are directly comparable. The earlier worry about
non-comparability (capacity vs billing efficiency) was based on the spec's
wrong /40 formula. The derived worked_utilization column in actuals_math.py
is now redundant — left in place for now, candidate for removal.

### hours_scheduled is uncapped

Old tabs show "Hours Scheduled" values above 40 (45 is common), and the
utilization denominator uses that uncapped figure. So hours_scheduled is NOT
capped at 40. The 40-hour threshold only feeds forecast_ot (the overflow).
The spec's "cap hours_scheduled at 40" instruction was also wrong.

### Reference week for validation

Saved fixtures/expected_forecast.json from the most recent tab (labelled
"10/15-10/21", year unconfirmed). 7 techs have usable forecast numbers
(David, Andre, Anthony, Grant, Bill, Stephen, Jim). Josh and Patrick have
blank forecast cells. TODO Henry: confirm the year so the matching CRM
events can be pulled for a tech-by-tech diff.

### Technician identification — resolved by inference

Henry: office staff (CEO, sales, admin) do not own field events. So the
technician roster derives from the data: distinct Owner and Helper1 values on
events of real field-work types in the forecast week. No new CRM field, no
ask to Stacy. config.dg TECHNICIAN_FILTER_STRATEGY updated.

## Open verification items (not blocking, surface during build)

1. **30-min adder scope** — spec Section 5.2 is ambiguous whether it applies to all non-trip events or only non-billable. Ask Dustin during parallel-run reconciliation.
2. **iSolved tenant API access** — confirm Livewire's iSolved tenant has the REST API enabled. Dustin or McKenzie can verify.
3. **iSolved → Zoho employee mapping** — populate `iSolved_Employee_ID` on each Zoho User. One-time backfill, Stacy or Dustin.
4. **iSolved exclusion categories** — exact names for PTO / Holiday / Sick / Absence in iSolved's response payload.
5. **Event_Type categorization** (NEW) — see CRM Inspector Run above.
6. **Cancellation tracking** (NEW) — see CRM Inspector Run above.
7. **Technician identification** (NEW) — see CRM Inspector Run above.
