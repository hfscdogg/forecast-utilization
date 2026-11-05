# Cowork prompt: Zoho Creator setup for Nailed It / Failed It

Paste the block below into Claude Cowork on a computer where you're logged in to
Zoho Creator, Google, and GitHub. It follows `docs/nailed_it_photos_form_schema.md`.
Its guardrails stop it from emailing all@getlivewire.com, editing existing
schedules, or handling secrets. Bring its report back to Claude Code to deal with
any failures.

```
You're setting up a feature in my Zoho Creator app. Work in my browser, where I'm already logged in to Zoho and Google. Go step by step and confirm each step before moving on.

GOAL
The weekly "Utilization Actuals" email gets a picture card:
- "Nailed it": a photo of finished work, when team utilization is 75% or higher.
- "Failed it": a staged gag image, when it's below 75%.

The code is already written and merged. Your job is the Creator setup only.

SOURCE OF TRUTH
GitHub repo hfscdogg/forecast-utilization, branch main. I'm logged in to GitHub.
- Read docs/nailed_it_photos_form_schema.md first. It has the form fields and the setup steps.
- The Deluge code is in deluge/. Paste each file's full contents exactly. Do not edit the code.

GUARDRAILS (do not break these)
- Never trigger an email to all@getlivewire.com.
  - Do not run send_actuals_email or scheduled_actuals.
  - Do not change the existing Monday actuals schedule or the Thursday forecast schedule.
- Stop and ask me before any Google or Zoho OAuth consent screen. I'll click Allow myself.
- Never type, copy, or show API keys or secrets in chat.
  - ANTHROPIC_API_KEY already exists as an App Variable. Leave it alone.
- Don't delete or rename anything that already exists in the app. The only exception is replacing the code of the send_actuals_email function in step 5.
- If a function won't save, stop. Show me the exact error text. Don't "fix" the code yourself.

STEPS
1. Find the app. Open Zoho Creator and find the app that already contains the function send_actuals_email and the form Utilization_Actuals_History. Tell me its name before going further.
   Note the time zone of the existing Monday 4:00 PM actuals schedule. You'll need it in step 7.

2. Create the form "Nailed It Photos", link name Nailed_It_Photos. Use exactly these fields and link names:
   - File ID: File_ID, Single Line, required
   - Public File ID: Public_File_ID, Single Line, NOT required
   - Job Name: Job_Name, Single Line
   - Sent By: Sent_By, Single Line
   - Installed: Installed, Single Line
   - Send Date: Send_Date, Date, required
   - Status: Status, Dropdown with exactly Suggested, Picked, Used; required
   - Picked By: Picked_By, Single Line
   - Company Utilization: Company_Utilization, Decimal
   - Score: Score, Number
   - Score Reason: Score_Reason, Single Line

3. Create the Google Drive connection.
   - Setup > Connections > add the built-in Google Drive service.
   - The link name must be exactly google_drive.
   - Include the scope https://www.googleapis.com/auth/drive.
   - Stop at the consent screen so I can approve it as henry@getlivewire.com.

4. Add App Variables. Leave existing variables untouched.
   - NAILED_IT_PICK_API_URL: set it to the placeholder "pending" for now.
   - NAILED_IT_EMAIL_ASSETS_FOLDER_ID: leave it empty.
   Confirm that ANTHROPIC_API_KEY exists, without opening its value.

5. Add the functions under Workflow > Functions. Paste them in this order, each one's full file contents from deluge/:
   1. nailed_it_share.dg
   2. nailed_it_candidates.dg
   3. nailed_it_score.dg
   4. pick_nailed_photo.dg
   5. scheduled_photo_picker.dg

   Then replace the code of the existing send_actuals_email function with deluge/send_actuals_email.dg.
   Save each one. All must save with no errors.

6. Create the Custom API (Microservices > Custom API).
   - Method: GET
   - Function: pick_nailed_photo
   - Parameter: file_id
   - Authentication: public key, so a link clicked from email works without logging in.
   Copy the full URL, key included, into the NAILED_IT_PICK_API_URL App Variable. Don't paste the URL in chat.

7. Create the schedule (Workflow > Schedules).
   - Run scheduled_photo_picker weekly, Sunday at 4:00 PM.
   - Use the same time zone as the Monday actuals schedule from step 1.

8. Test. This is safe because it only emails henry@getlivewire.com.
   1. Run scheduled_photo_picker once by hand.
   2. Check Gmail for "Pick tomorrow's Nailed It photo". Tell me:
      - how many photos it shows;
      - whether they have scores and reasons, or the note "Photo scoring was unavailable".
   3. Check the Nailed It Photos report for a Suggested record.
   4. Click "Use this one" on the top photo. Tell me what the page says.
   5. Confirm a Picked record now exists.

9. Check link sharing in Google Drive.
   - Open the shared-drive folder https://drive.google.com/drive/folders/17vdHcT-3YYMsQ7o0zH0OGf_uht5XsgtJ.
   - Open the file failed_it_01_rats_nest.jpg and click Share.
   - Tell me whether "Anyone with the link" is selectable under General access, or greyed out.
   - Don't change anything there.

REPORT BACK
- Pass or fail for each step, with exact error text for any failure.
- The app name.
- The schedule time zone.
- The step 8 results.
- The step 9 result.
```
