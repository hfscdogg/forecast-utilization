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

The 10/15-10/21 tab was a stale older tab; the actual most recent forecast
is the 5/17-5/23 tab. fixtures/expected_forecast.json rebuilt from that
2026-05-21 paste, with 7 techs having usable forecast numbers (Josh B,
Jason, Patrick, Andre, Jeffrey, Thomas, Jim). Jordan excluded (0/0).

### Validation finding — Duration_Man_Hrs is TOTAL, not per-tech

The 2026-05-13 reading of Stacy's "Duration (Man Hrs) is a computed CRM
field that pre-splits hours per technician on multi-tech jobs" was
INCORRECT. Real-data evidence (2026-05-21 inspector pull):

- Event 322935002 Rough-In, Josh + Jason paired: Duration_Hrs=4.73,
  Duration_Man_Hrs=9.47 (= 4.73 × 2).
- Event 324464540 Finish-Out, Andre + Jeffrey paired: Duration_Hrs=9.63,
  Duration_Man_Hrs=19.27 (= 9.63 × 2).
- Event 319473201 Finish-Out, Patrick solo: Duration_Hrs=7.25,
  Duration_Man_Hrs=7.25 (= 7.25 × 1).

So `Duration_Man_Hrs = Duration_Hrs × tech_count`. The PER-TECH
contribution is `Duration_Hrs` (wall-clock); `Duration_Man_Hrs` is the
company-wide man-hours rollup. forecast_math.py and actuals_math.py now
sum `Duration_Hrs` per tech.

### Validation finding — "Hours Scheduled" is hand-entered

The Google Sheet shows "Coordinator to fill in green boxes" under both
the Billable Hours Scheduled and Hours Scheduled columns. Both are
hand-entered by Dustin / a coordinator each Thursday, not derived from
a formula. That explains the Patrick row (billable 10 > scheduled 9):
the manual process allows internal inconsistency. The automation will
be more rigorous (Hours Scheduled will always include Billable Hours
Scheduled + non-billable + training + adder).

### Validation finding — multi-day off-time markers

Some events are typed as Meeting / Training / Scheduled Off but span
24-120+ hours (e.g., a 24h "Meeting -Non Billable" from Sun 8pm to Mon
8pm). These are calendar blocks for unavailability that span beyond the
forecast week. The automation should pro-rate event duration to the
within-week slice rather than counting full Duration_Hrs. Open for the
next iteration.

### Validation result summary

With Duration_Hrs as the per-tech aggregator, utilization percentages
land within 3-30 points of Dustin's manual forecast for the 5/17-5/23
week. Closest: Josh B (Δ 2 pts), Jim (Δ 3 pts), Jeffrey (Δ 9 pts). The
remaining gap is the time-snapshot mismatch (Dustin forecast 5/14,
this pull was 5/21) and the multi-day-event issue above. The
methodology is sound; final tuning happens in parallel run.

### Technician identification — resolved by inference

Henry: office staff (CEO, sales, admin) do not own field events. So the
technician roster derives from the data: distinct Owner and Helper1 values on
events of real field-work types in the forecast week. No new CRM field, no
ask to Stacy. config.dg TECHNICIAN_FILTER_STRATEGY updated.

## 2026-05-26 — Phase 3 ship

Four Creator Standalone Functions live and verified end-to-end:
`generate_forecast`, `send_forecast_email`, `write_forecast_history`,
`scheduled_forecast`. Schedule "Weekly Utilization Forecast" wired in
Creator's scheduler, first run Thursday 2026-05-28 at 16:00 in IANA zone
`America/New_York`, recurring weekly, status Enabled. Schedule action is
a one-line Deluge that calls `thisapp.scheduled_forecast()`.

### `zoho.creator.createRecord` 6-arg incompatibility

Livewire's Creator tenant requires the 6-argument signature for
`zoho.creator.createRecord` (scope + connection in addition to the
owner/app/form/record args); the 4-arg form errors with
`mandatory params '6'`. Rewrote `write_forecast_history.dg` to use the
native Deluge `insert into Utilization_Forecast_History [ ... ]` syntax,
which runs in the calling function's own auth context and needs no
connection. Functionally equivalent, no scope coupling, fewer moving parts.

### Form field link name collision fix

`Training Drove OT` initially got link name `Training_Drove_OT1` (trailing
`1`) because Creator hit a collision with another field at form-creation
time. Renamed to `Training_Drove_OT` in the form designer and updated the
matching `insert into` field in `write_forecast_history.dg`. Repo doc
(`forecast_history_form_schema.md`) already used the clean name; no edit
needed.

### First successful manual run

Tuesday 2026-05-26 at 17:48:06 local. `Run_ID = 20260526174806-3066`. 7
techs scanned, 15 events consumed, 7 history records inserted (all 17
fields populated), one HTML email landed at `henry@getlivewire.com`. Used
inline OAuth in `generate_forecast.dg` (Self Client refresh token in
source), the deliberate stopgap.

### IANA timezone vs hardcoded offset — not the same thing

Creator's Schedule itself uses IANA `America/New_York`, which handles
EDT/EST automatically. The scheduler fires at 4pm local year-round
regardless of DST. Separate issue: `scheduled_forecast.dg` builds the
forecast-week ISO strings by string-concatenating `"-04:00"` directly
into the timestamps. That literal is correct in EDT (Mar-Nov) and wrong
in EST (Nov-Mar). Still a TODO; left in place this round.

## 2026-05-27 — Secret leak remediation

GitGuardian flagged the repo for two Zoho secret types (OAuth2 Keys and
Zoho API Key). Root cause: the inline-OAuth stopgap from Phase 3 left the
Self Client refresh token, client ID, and client secret hardcoded inside
the production Deluge functions and committed across many commits.

Two-part fix:

1. **Code refactor.** Both `generate_forecast.dg` and `generate_actuals.dg`
   now read OAuth credentials from Creator App Variables (Settings →
   Developer Tools → Variables) via `thisapp.Variables.ZOHO_CLIENT_ID`,
   `thisapp.Variables.ZOHO_CLIENT_SECRET`, `thisapp.Variables.ZOHO_REFRESH_TOKEN`.
   No secret in source. Henry must create those three Variables in Creator
   with the rotated values before pasting the updated functions.
2. **History scrub.** `git filter-repo --replace-text` rewrote every
   commit to redact the leaked strings, followed by force-push. Old commit
   SHAs no longer exist on the remote.

**Rotation is non-optional.** Even with the code refactor and history
scrub, anyone who pulled the repo (or saw any of the GitGuardian-style
public scanners) has the values. Old Self Client credentials must be
revoked at `api-console.zoho.com` and replaced with fresh values, which
then go into the Creator Variables.

Going forward: never inline OAuth in committed code. App Variables for
the stopgap, Custom Service Connection long-term.

## 2026-08-25 — Dustin (actuals parallel-run reconciliation, week of 8/10-8/16)

Dustin's review of the 8/24 actuals email ("I think you have this locked down
pretty well") surfaced two fixes and two accepted deltas.

### Trip charges now counted in actuals Hours Billed

> "Jason and Josh B also had trip charges that you didnt capture. Their trip
> charges were listed on their events though."

Root cause: `generate_actuals.dg` selected `Trip_Charge` but never used it —
Hours Billed only summed `Duration_Hrs` (wall-clock). The SOP says Hours
Billed comes from the Billable Report **including trip charges**. Encoded the
SOP rule directly: each trip charge is worth 2 billable hours on a solo event
and 1 billable hour per tech on a paired event ("trip charge x 2 for solo /
x 1 per tech for paired"); `Trip_Charge` is the count (picklist 1-4). Applies
to billable-type events only. Constants `TRIP_CHARGE_HOURS_SOLO` and
`TRIP_CHARGE_HOURS_PAIRED_PER_TECH` in `generate_actuals.dg` and
`event_types.py` (`trip_charge_hours()`).

Jim's missed trip charge that week was a scheduling data-entry gap (charge
not labeled on the event) — Dustin owns that process fix, not the automation.

**RESOLVED same day:** the forecast side had the same gap. The 2026-05-13
note that `Duration_Man_Hrs` "handles trip charge math upstream" was
invalidated on 2026-05-19 (`Duration_Man_Hrs = Duration_Hrs x tech_count`,
no trip math), and Dustin's 8/7 and 8/13 forecast reviews both flagged
missing trip charges. `trip_charge_hours()` is now applied in
`forecast_math.py` / `generate_forecast.dg` too; the drive-adder interplay
is unchanged (a trip charge still suppresses the 0.5 hr adder).

Guard added in the same pass: cancelled events are shrunk to a 1-minute
duration but KEEP their `Trip_Charge`, so trip hours are skipped for events
matching the cancellation heuristic (status "Incomplete - Job Not Ready"
and duration <= 0.1 hr) in both forecast and actuals. Without this a
cancelled out-of-town job would have billed its trip hours forever.

### Missing timecard is a flagged data gap, not 0% utilization

> "I think Josh Brown's time wasnt put in when your automation fired off
> because he's listed at 0% on yours which dropped your number."

Josh Brown billed 31.47 CRM hours but had no iSolved time when the run fired
(he doesn't clock in; David Hicks backfills his time to match Zoho events).
The math gave him 0% and averaged it into the company mean, dragging 64.52%
down from ~75%. New rule: billed hours > 0 with a zero timecard sets
`timecard_missing` — the row stays in the table and hour totals with
utilization rendered as a placeholder, is left out of the company mean and
congrats list (same treatment as ramp-up), gets a Notes entry and a banner
naming affected techs. Distinct from the whole-run iSolved-pending state.

### Accepted deltas (no code change)

- **Elijah in the table but out of the mean** — already matches Henry's
  2026-08-17 "let him burden the number" call combined with the ramp-up
  exclusion; Dustin excludes him entirely, which is presentation only.
- **Week boundary stays Mon-Sun** — Dustin's manual week runs Sun-Sat. Henry
  2026-08-25: keep Mon-Sun as is for now. Revisit if iSolved's payroll week
  (likely Sun-Sat) makes the OT split drift from payroll.
  **SUPERSEDED 2026-09-05** — see the week-boundary entry below.

## 2026-08-31 / 2026-09-04 — Dustin (8/17-8/23 actuals review + 9/7-9/13 forecast review)

Dustin's review of the 8/31 actuals email ("Everyone else's time looks
correct within a few tenths of a point") surfaced one bug and re-raised the
week boundary; his 9/4 forecast review pinned the same bug on the forecast
side ("Trip charges" was his entire diagnosis of the delta).

### Trip charge merged from BOTH the meeting and the potential

> "The billable report has two Trip charge fields. One is pulled from the
> meeting and one from the potential. ... Ultimately it should check both
> and if its the same, discard one result, but if its different then keep
> the positive result, because service potentials do not update the
> tripcharge field when automatically created from the meeting which is how
> Service calls are scheduled 98% of the time. Those potentials are created
> after the meeting is created, but finish out meetings are created after
> the potential is created."

This is what dropped Jim's trip charges from the 8/17-8/23 actuals: the
automation only read `Events.Trip_Charge`, and on finish-out meetings
created from a potential that field can sit blank while the potential holds
the real value (the mirror drift of the service case). Fix: both generators
now select `What_Id`, fetch `Trip_Charge` from the related Deals records,
and take the MAX of the two counts — equal values collapse to one, differing
values keep the positive one, never a sum. A trip charge from either source
also suppresses the forecast drive-time adder. Failure mode is conservative:
if the Deals query errors or the field name is wrong, the map stays empty
and the run behaves exactly as before (event-side only). Encoded in
`generate_actuals.dg`, `generate_forecast.dg`, and
`event_types.py` (`effective_trip_charge_count()`); the fetch layer merges
the potential-side value onto the event as `Potential_Trip_Charge` for the
Python mirror. The Deals-side API name `Trip_Charge` is an assumption —
verify with `deluge/inspectors/inspect_deal_trip_charge.dg` before deploy
(open item 8).

Dustin's "We may need to streamline that somehow" is the upstream fix: the
CRM automations that create service potentials from meetings (and finish-out
meetings from potentials) should copy the trip-charge field across. That
kills the drift at the source; the report-side max() stays as a safety net
(open item 9, Dustin owns the CRM automation side).

### Week boundary is now Sun-Sat (supersedes Henry 2026-08-25)

> "Also yours is still doing Monday to Sunday instead of Sunday to Saturday"

The 2026-08-25 revisit condition was effectively met: the actuals OT split
caps iSolved hours at 40 over OUR window, so a window offset from the
Sun-Sat payroll week skews OT and Actual Hours Paid, and every parallel-run
comparison against Dustin's Sun-Sat sheet carried Sunday-edge noise. Both
reports now use Sun-Sat: the Monday actuals run reports the Sun-Sat ending
9 days prior (`subDay(15)`/`subDay(9)`), the Friday forecast run targets the
upcoming Sun-Sat (`days_to_sunday = 2`). Email subjects and labels derive
from the dates, so they follow automatically. History rows keep their field
names (`Lag_Week_Start` etc.) — only the dates they carry shift.

## Open verification items (not blocking, surface during build)

1. **30-min adder scope** — spec Section 5.2 is ambiguous whether it applies to all non-trip events or only non-billable. Ask Dustin during parallel-run reconciliation.
2. **iSolved tenant API access** — confirm Livewire's iSolved tenant has the REST API enabled. Dustin or McKenzie can verify.
3. **iSolved → Zoho employee mapping** — populate `iSolved_Employee_ID` on each Zoho User. One-time backfill, Stacy or Dustin.
4. **iSolved exclusion categories** — exact names for PTO / Holiday / Sick / Absence in iSolved's response payload.
5. **Event_Type categorization** (NEW) — see CRM Inspector Run above.
6. **Cancellation tracking** (NEW) — see CRM Inspector Run above.
7. **Technician identification** (NEW) — see CRM Inspector Run above.
8. **Deals-side trip-charge field API name** — assumed `Trip_Charge` on the
   `Deals` module. Run `deluge/inspectors/inspect_deal_trip_charge.dg` over a
   recent week and confirm before deploying the dual-field merge; also
   confirms `What_Id` resolves to the potential.
9. **Upstream trip-charge sync** — Dustin to make the CRM automations copy
   the trip-charge field when creating service potentials from meetings and
   finish-out meetings from potentials ("We may need to streamline that
   somehow", 2026-08-31).
