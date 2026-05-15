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

## Open verification items (not blocking, surface during build)

1. **30-min adder scope** — spec Section 5.2 is ambiguous whether it applies to all non-trip events or only non-billable. Ask Dustin during parallel-run reconciliation.
2. **iSolved tenant API access** — confirm Livewire's iSolved tenant has the REST API enabled. Dustin or McKenzie can verify.
3. **iSolved → Zoho employee mapping** — populate `iSolved_Employee_ID` on each Zoho User. One-time backfill, Stacy or Dustin.
4. **Exact `Duration (Man Hrs)` API name** — likely `Duration_Man_Hrs`, confirm via inspector script.
5. **Active flag on Users module** — confirm exists; if not, request Stacy add and backfill.
6. **iSolved exclusion categories** — exact names for PTO / Holiday / Sick / Absence in iSolved's response payload.
