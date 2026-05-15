# Utilization Reporting (Lagging Actuals) — SOP

**Source:** Zoho Desk Knowledgebase → Utilization Reporting
**Captured:** 2026-05-15 (from PDF export)

---

Utilization reporting is similar to Forecasting with a few differences: We are going to be working on a tab two weeks prior to current date. So from the Forecasting example of 5/17-5/23 we would instead be looking at the week of 5/3-5/9. We stagger this by two weeks to allow PM's and Accounting to get all of the hours situated on jobs from that week so our data can be as accurate as possible.

## Reports used

- `PROD_BILLABLE RPT(LW)_1` — filtered for the date range of your spreadsheet tab
- `PROD_NON-BILLABLE RPT(LW)` — filtered for the date range on your spreadsheet tab
- Dominion Payroll (Manager View) — to view technician time cards

> **Automation note (2026-05-15):** Per Dustin, the Hours Worked source for the automated version is the **iSolved API**, not Dominion's Manager View. iSolved is the HCM platform that powers Dominion Payroll's Manager View. Reports listed above stay in the manual process for parallel-run comparison only.

## Spreadsheet columns (second half of each weekly tab)

| H | I | J | K | L | M |
|---|---|---|---|---|---|
| HOURS BILLED | HOURS WORKED | OT | ACTUAL HOURS PAID | ACTUAL UTILIZATION | Non-Billable Hours |

Plus a Notes column (free text).

## Process per technician

1. Fill **Hours Billed** from the Billable Report (including trip charges) — can exceed 40
2. Fill **Hours Worked** from Dominion Payroll (iSolved in automation) — time on the clock only
3. Cap **Hours Worked** at 40; overflow into **OT**
4. **Actual Hours Paid** = `Hours Worked + (OT × 1.5)` — OT paid at time-and-a-half (verified from live spreadsheet 2026-05-15)
5. **Actual Utilization** = `Hours Billed / Actual Hours Paid` (Dustin's formula: `=SUM(H/K)`)
6. **Non-Billable Hours** column gets per-tech non-billable totals, which roll up into the bottom Non-Billable Hours box for the company-wide Delta

## Critical exclusions

> "Please keep in mind that you will not count PTO, Holidays, Sick Days, or absences as part of Hours Worked. This is only time on the clock. We do NOT add the 30 minute drive times per job on this side of the spreadsheet. Forecasting is estimating, while this is actual data."

- Exclude from Hours Worked: PTO, Holidays, Sick Days, Absences
- Do NOT add 30-minute drive-time adders (forecast does, actuals doesn't)
- Hours Worked capped at 40; overflow → OT (Hours Billed has no cap)

## Company-wide rollup (bottom of each weekly tab)

- **Billable Hours Report** — sum of per-tech Hours Billed
- **Non-Billable Hours** — sum of per-tech Non-Billable Hours
- **Total Hours** — sum of the two
- **Delta** — Billable minus Non-Billable (sometimes shown as a percentage)

## Email lead-in format (sample from 12/12/16 tab)

> "Below are the results from last week's. Last week we produced 278 billable hours resulting in an average of 23.28 billable hours per tech resulting in 69.6% utilization. Congrats to Jason, Jeff, Drake, Tommy, Todd, Robert, Ben and Mark for hitting our 62.5% utilization goal."

Auto-version template:
> "Last week we produced {total_billable} billable hours resulting in an average of {avg_billable_per_tech} billable hours per tech resulting in {company_utilization}% utilization. Congrats to {techs_above_target} for hitting our 62.5% utilization goal."

## Reference spreadsheet

[Billable Hours Reporting (Utilization)](https://docs.google.com/spreadsheets/d/1hFyR7iyTPhpu14J1GZo-QN4OuAwMcj_oi7KzDStyB2U/edit?gid=2012046356#gid=2012046356)
