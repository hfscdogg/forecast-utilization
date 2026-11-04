# Nailed It Photos form: Creator schema and setup

Tracks which asset-library photo goes into the **Nailed It** card of the
Monday Utilization Actuals email, and which photos have already been used.
One record per pick.

**Form name:** `Nailed_It_Photos`
**Display name:** `Nailed It Photos`

## Fields

| Field name | Link name | Type | Required | Notes |
|---|---|---|---|---|
| File ID | `File_ID` | Single Line | Yes | Drive file id in the asset library. Used to keep a photo from repeating. |
| Public File ID | `Public_File_ID` | Single Line | Yes | Id the email loads. Same as File ID under Plan A (link share), or the copy's id under Plan B. |
| Job Name | `Job_Name` | Single Line | No | From the upload form ("Job or event name", else "Job:"). |
| Sent By | `Sent_By` | Single Line | No | Uploader email, shown as the photo credit. |
| Installed | `Installed` | Single Line | No | "What did we install?" answer. |
| Send Date | `Send_Date` | Date | Yes | The Monday the photo is meant for. |
| Status | `Status` | Dropdown: `Suggested`, `Picked`, `Used` | Yes | `Suggested` = Sunday's top-scored photo (no-pick fallback). `Picked` = Henry's choice. Whichever goes out becomes `Used`. |
| Picked By | `Picked_By` | Single Line | No | "Henry (picker email)" or "Auto (top score)". |
| Company Utilization | `Company_Utilization` | Decimal | No | Filled when the photo is used. |
| Score | `Score` | Number | No | Vision score 1-10 (Suggested records). Blank when scoring was unavailable. |
| Score Reason | `Score_Reason` | Single Line | No | Claude's one-line reason for the score. |

## One-time setup in Creator

1. Create the form above.
2. **Connection:** add a Google Drive connection with link name
   `google_drive` and scope `https://www.googleapis.com/auth/drive`. Authorize
   it with a Google account that can read the asset-library shared drive.
   It must also be able to share files there, or to write into the Plan B
   folder.
3. **Functions:** paste in `nailed_it_candidates`, `nailed_it_share`, `nailed_it_score`,
   `pick_nailed_photo` and `scheduled_photo_picker` from `deluge/`, plus the
   updated `send_actuals_email`.
4. **Custom API:** publish `pick_nailed_photo` as a GET Custom API with
   API-key auth and a `file_id` parameter. Store the full URL, including the
   key, in the App Variable `NAILED_IT_PICK_API_URL`.
5. **Claude API key:** put an Anthropic API key in the App Variable
   `ANTHROPIC_API_KEY`. Without it the picker still works, unscored and
   newest first. One call a week, about $0.10.
6. **Schedule:** run `scheduled_photo_picker` every Sunday at 16:00
   America/New_York.
7. **Plan B (only if link sharing is blocked on the shared drive):** create
   a My Drive folder, share it "anyone with the link: viewer", and put its
   id in the App Variable `NAILED_IT_EMAIL_ASSETS_FOLDER_ID`.
8. **Failed It images:** done 2026-11-04. The six `assets/failed_it/`
   illustrations are in the asset library and their ids are in
   `FAILED_IT_IMAGE_IDS`. On a missed week the email shares that week's
   image at send time through `nailed_it_share`, which needs the
   `google_drive` connection from step 2.

## Weekly flow

- **Sunday 4pm:** Claude scores up to 15 eligible photos on how well they
  show off the work. Henry gets "Pick tomorrow's Nailed It photo" with the
  best 6, each with a score and a one-line reason, and photos under the bar
  listed separately. The top photo is saved as `Suggested` if it scores 7
  or higher. Clicking **Use this one** creates or replaces the `Picked`
  record for Monday.
- **Monday 4pm:** if company utilization is at or above `TEAM_VERDICT_TARGET`,
  the email shows the picked photo, else this week's `Suggested` photo,
  else no photo. After the send, the record flips to `Used`.
- **Missed week:** the email shows a staged Failed It image. Any pick stays
  `Picked` and the photo comes back as a candidate next Sunday.
