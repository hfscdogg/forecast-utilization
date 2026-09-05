# Field Mapping — confirmed from CRM inspector (2026-05-18)

Live state of the Livewire CRM as observed by the inspector script. All field
API names and picklist values below are confirmed by direct CRM read.

## Events module

API module name: `Events` (display label "Meetings"). Built-in default module.

### Confirmed field API names

| Display label | API name | Type | Notes |
|---|---|---|---|
| Meeting Owner | `Owner` | ownerlookup | Primary technician (has id/name/email) |
| Technician 2 | `Helper1` | picklist | Paired tech name (NOT a lookup — free picklist of name strings) |
| Duration (Hrs) | `Duration_Hrs` | formula | Total event hours (for sanity check) |
| Duration (Man Hrs) | `Duration_Man_Hrs` | formula | Per-tech hours after the multi-tech split — sum this |
| Start DateTime | `Start_DateTime` | datetime | ISO 8601 with timezone offset |
| End DateTime | `End_DateTime` | datetime | |
| Event Type | `Event_Type` | picklist | See picklist values below |
| Event Status | `Event_Status` | picklist | NOT "Status"; see picklist values below |
| Trip Charge? | `Trip_Charge` | picklist | Numeric picklist (count of charges), null = no charge |
| Billed | `Billed` | boolean | |
| Placeholder | `Placeholder` | boolean | Boolean for placeholder events (in addition to "Place Holder" Event_Type) |
| Hours Logged | `Hours_Logged` | double | Actual hours logged on the event |
| Service Rate | `Service_Rate` | currency | |
| Service Plan | `Service_Plan` | picklist | Customer's plan tier |
| Total Hours Sold | `Total_Hours_Sold` | integer | |

### Event_Type picklist values (TODO: Dustin to categorize)

**Currently in use ("type":"used") — 22 values including `-None-`:**

| Value | Likely category | Confirmation needed |
|---|---|---|
| `Trim-Out ($$$)` | Billable | ✓ ($$$) suffix |
| `Rough-In ($$$)` | Billable | ✓ ($$$) |
| `Finish-Out ($$$)` | Billable | ✓ ($$$) |
| `Sub Contractor Finish-Out ($$$)` | Billable | ✓ ($$$) |
| `Retrofit ($$$)` | Billable | ✓ ($$$) |
| `Discovery - Payment Required ($$$)` | Billable | ✓ ($$$) |
| `Discovery - Prepaid` | Billable | Prepaid means the customer already paid via package |
| `Service - Payment Required ($$$)` | Billable | ✓ ($$$) |
| `Remote Assistance (Payment Required)` | Billable | "Payment Required" |
| `Remote Support (Parasol)` | ? | Ask Dustin — counts as billable? |
| `In-House Electrical` | ? | Ask Dustin |
| `Service - Warranty / Punchout` | Non-Billable | "Warranty" implies no charge |
| `Install - Warranty / Punchout` | Non-Billable | "Warranty" |
| `Package Overage - Non Billable` | Non-Billable | Explicit "Non Billable" |
| `Meeting -Non Billable` | Non-Billable | Explicit |
| `Project Management` | Non-Billable | Internal work |
| `Undersold - Not Billable` | Non-Billable | Explicit |
| `Training` | Training | Counts as worked per spec, flag if drives OT |
| `Scheduled Off` | Excluded | PTO equivalent? Confirm |
| `Place Holder` | Excluded | Maps to spec's placeholder-routing flow |
| `Service Location` | ? | Ask Dustin |
| `-None-` | Excluded | Default empty value |

**Currently unused ("type":"unused"), historical values:** `Called Out`,
`Development (office only)`, `Monitoring Activation`, `N.O.C.`, `Rack Build`.
Should be excluded from the forecast — but if they show up in a week (rare),
flag rather than silently drop.

### Event_Status picklist values

`-None-`, `Complete`, `Incomplete`, `Incomplete - Job Not Ready`, `Ready to Bill`.

**No "Cancelled" value.** Spec's `Status != Cancelled` rule has no direct map.
TODO Dustin: how are cancellations tracked? Possibilities:
1. Hard delete (event removed from CRM)
2. `Record_Status__s` (Zoho's built-in deleted flag) — need to inspect
3. A different field entirely

### Trip_Charge picklist values

`-None-`, `0` (unused), `1`, `2`, `3`, `4`. Numeric count of trip charges.
Sample event observed: `"Trip_Charge": null` — so the absence of a trip charge
shows as `null`, not `"0"` or `"-None-"`. Filter for "no trip charge" =
`Trip_Charge == null OR Trip_Charge == "-None-"`.

### Related potential (Deals) — second trip-charge field

Dustin 2026-08-31: the billable report carries a SECOND trip-charge field on
the related service potential, and the two drift (potentials auto-created
from meetings never populate theirs; finish-out meetings created from a
potential can carry a blank event-side value). Assumed mapping — **verify
with `deluge/inspectors/inspect_deal_trip_charge.dg` before deploy**:

| Display label | API name | Type | Notes |
|---|---|---|---|
| Related To | `What_Id` | lookup | Built-in on Events; `id` matches `Deals.id` for potentials. TODO confirm it is populated on service/finish-out meetings |
| Trip Charge? (on Deals) | `Trip_Charge` | picklist? | TODO confirm API name and picklist values via inspector |

The generators take the MAX of the event-side and deal-side counts (equal →
one; different → the positive one; never a sum). The Python mirror sees the
deal-side value merged onto the event as `Potential_Trip_Charge`.

### Helper1 picklist values (paired tech names)

Free picklist of name strings, not a user lookup. Currently "used" values
(active paired-tech options):

`No Helper`, `Andre Smith`, `David Hicks`, `Dustin Roskam`, `Jason Good`,
`Jeffrey Walburn`, `Jim Zimmerman`, `Jordan Toppin`, `Joshua Brown`,
`Joshua McDonough`, `Patrick Jones`, `Thomas Payne`.

Implication: paired-tech filter compares `Helper1 == tech.full_name` as a
string match, not an ID join.

### Sample event JSON shape

```json
{
  "Owner": {"name": "Patrick Jones", "id": "...", "email": "pjones@getlivewire.com"},
  "Helper1": "No Helper",
  "Event_Type": "Finish-Out ($$$)",
  "Event_Status": null,
  "Trip_Charge": null,
  "Duration_Hrs": 8,
  "Duration_Man_Hrs": 8,
  "Start_DateTime": "2026-05-19T09:00:00-04:00",
  "End_DateTime": "2026-05-19T17:00:00-04:00",
  "Billed": false,
  "Placeholder": <not returned because not requested>
}
```

For multi-tech jobs, `Duration_Hrs` would be the wall-clock duration and
`Duration_Man_Hrs` the per-tech allocation (e.g., 4 each for an 8-hour
2-tech job).

## Users (built-in CRM users endpoint)

API endpoint: `/crm/v6/users?type=ActiveUsers`. No custom Technicians module
exists.

### Confirmed user fields

| Path | Type | Notes |
|---|---|---|
| `id` | string | Zoho user ID — matches the `Owner.id` on Events |
| `full_name` | string | "First Last" — matches `Helper1` picklist display values |
| `email` | string | |
| `status` | string | `"active"` for active users (this is our Active flag) |
| `role.name` | string | Hierarchy role (CEO, etc.). NOT a tech-vs-non-tech distinguisher |
| `profile.name` | string | Permission profile (Administrator, Sales, etc.) |
| `category` | string | "regular_user" for the sampled users |

### TODO: Technician identification

Neither `role.name` nor `profile.name` cleanly identifies a tech. The two
sampled users (Henry and Marshall) are both CEO/role with different
profiles. Options:

1. **Filter via Helper1 picklist names** — the "used" Helper1 values are
   exactly the active techs. Cross-reference against `users.full_name`.
2. **Custom user field** — Stacy adds a boolean like `Is_Active_Technician`
   and backfills.
3. **Profile filter** — if there's a "Technician" profile, filter on that.

Option 2 is the cleanest long-term. Ask Stacy.

## Modules inventory

No custom `Technicians` module exists. The only custom modules of note:
- `Service_Tickets` (CustomModule1)
- `Project_Management` (CustomModule2)
- `Package_Feedback` (CustomModule8)
- `Virtual_Sales_Whiteboard` (CustomModule9)
- `Sales_Rep_Goals` (CustomModule18)

None of these are relevant to the forecast. Use the built-in `users`
endpoint for the tech roster.
