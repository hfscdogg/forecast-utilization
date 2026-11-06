"""
"Nailed It" showcase card for the Utilization Actuals email.

Python reference for the Deluge side:
- deluge/nailed_it_candidates.dg   (parse_photo_description, is_candidate,
                                     select_candidates)
- deluge/send_actuals_email.dg     (render_nailed_block)
Keep in sync.

Rules:
- Henry 2026-11-06: the card runs every Monday to show off finished work
  and credit the crews. It is NOT tied to the utilization number. The only
  bar is photo quality (NAILED_IT_MIN_SCORE, vision scoring below).
- Photos come from two Drive sources, both read one folder level deep
  (the root plus its direct subfolders, so the YYYY-MM or year layout
  underneath does not matter):
    1. "Livewire Job Photos" (My Drive), filled hourly by the Zoho CRM
       sync (copyMeetingPhotosToDrive). Those files carry no description;
       they are eligible on their file name,
       YYYY-MM-DD_Deal####_Client_Installer_xxxxxx.ext, which also gives
       the client (job_name) and the crew (sent_by).
    2. The older asset-library upload form (Brand Library > Job Photos),
       whose photos are eligible only when the description says Finished
       and the customer OK'd sharing.
- No photo that clears the bar and no pick from Henry means no card.
- The 2026-11-04 "Failed It" verdict (TEAM_VERDICT_TARGET, staged gag
  images tied to the utilization number) is retired.
- Henry 2026-11-06 11:58: Failed It is back as a CONTRAST, never a
  verdict. When the curated Drive folder "Failed It" has images, the card
  shows two photos side by side: Failed It on the left (someone else's bad
  install, found online, never a Livewire crew) and Nailed It on the right.
  Still no tie to utilization. render_contrast_block below; mirrors
  send_actuals_email.dg.
"""

import html
import re
from datetime import datetime, timedelta

PHOTO_MAX_AGE_DAYS = 30

# Curated "Failed It" folder under Livewire Job Photos (CRM Sync), so its
# files inherit "anyone with the link". Humans add found images; Claude does
# not scrape the web for them. Mirrors NAILED_IT_FAILED_FOLDER_ID in
# deluge/config.dg and send_actuals_email.dg.
NAILED_IT_FAILED_FOLDER_ID = "1befbCvOuzb4bFO9u3sBzVmpxsaW0Lk8W"
MAX_CANDIDATES = 6

# Root folders the picker reads, each with its direct subfolders. Mirrors
# PHOTO_ROOT_FOLDER_IDS in deluge/nailed_it_candidates.dg.
PHOTO_ROOT_FOLDER_IDS = (
    "143dzFkXWASz9EI2awBfGEWNjdrhEAqP5",  # Livewire Job Photos (CRM Sync), folder the sync creates
    "1EgXWaKto9U39GNwNNS7mCkZR0LpBhTFO",  # Brand Library > Job Photos (upload form)
)

# File name written by the CRM sync (deluge/crm/copyMeetingPhotosToDrive.dg):
#   YYYY-MM-DD_Deal32504_NickAbbate_AndreSmith-ThomasPayne_Frame-TV_a1b2c3.jpg
# Crew members are joined by "-" with the spaces inside each name dropped;
# job words are joined by "-". The spec's original 5-segment form (no job)
# is accepted too.
_SYNC_NAME = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_(?P<deal>Deal[A-Za-z0-9]+)_(?P<client>[A-Za-z0-9-]*)_"
    r"(?P<crew>[A-Za-z0-9-]*)(?:_(?P<job>[A-Za-z0-9-]*))?_(?P<att>[A-Za-z0-9]+)\.(?P<ext>[A-Za-z0-9]+)$"
)

# Labels the asset-library upload form writes into each photo's Drive
# description, one per line. Some carry a "?" or ":" separator and some
# none ("Job or event name Clifford"), so lines are matched by prefix.
# Longest prefixes first so "Job or event name" wins over "Job:".
_LABELS = [
    ("Is the customer OK with us sharing these?", "consent"),
    ("Residential or commercial?", "segment"),
    ("What did we install?", "installed"),
    ("Where in the building?", "location"),
    ("Where is the job at?", "stage"),
    ("Job or event name", "event_name"),
    ("Brands in the photos", "brands"),
    ("Tell us about it", "story"),
    ("Sent by:", "sent_by"),
    ("Date:", "date"),
    ("Job:", "job"),
]

# Placeholder values the form leaves in the "Job:" line when the sender
# used the "Job or event name" field instead.
_GENERIC_JOB_VALUES = {"", "job", "event"}

RF_CARD_BG = "#FAFAF9"
RF_CARD_BORDER = "#E5E5E0"
RF_INK = "#1A1A1A"
RF_TEXT_SECONDARY = "#6B6B60"
RF_COPPER = "#F7941D"
RF_SANS_STACK = (
    "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
)


def parse_photo_description(description):
    """Return a dict of the upload-form fields found in a Drive description."""
    fields = {}
    for raw in (description or "").splitlines():
        line = raw.strip()
        for label, key in _LABELS:
            if line.startswith(label):
                fields[key] = line[len(label):].strip(" :")
                break
    job = fields.get("event_name") or ""
    if not job and fields.get("job", "").strip().lower() not in _GENERIC_JOB_VALUES:
        job = fields["job"]
    fields["job_name"] = job
    return fields


def _uncamel(s):
    """"ClientName" -> "Client Name"; the sync strips spaces from names."""
    out = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s or "")
    return re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", out).strip()


def parse_sync_filename(name):
    """Fields from a CRM-sync file name, or None when the name is not one.

    Unknown parts (UnknownClient, UnknownInstaller, DealUnknown) come back
    empty so the credit line skips them. `installed` is the job when the
    name carries one, else "Deal ####".
    """
    m = _SYNC_NAME.match(name or "")
    if not m:
        return None
    client = "" if m["client"] == "UnknownClient" else _uncamel(m["client"])
    job = (m["job"] or "").replace("-", " ").strip()
    if client.upper() in ("", "TBD"):
        # No deal and a title like "Livewire - #TBD - Leon and Sony": label
        # the photo by its job instead of the "TBD" placeholder.
        client, job = job, ""
    crew = "" if m["crew"] == "UnknownInstaller" else " and ".join(
        _uncamel(part) for part in m["crew"].split("-") if part)
    deal = "" if m["deal"] == "DealUnknown" else "Deal " + m["deal"][4:]
    return {"job_name": client, "sent_by": crew, "installed": job or deal,
            "deal": deal, "date": m["date"], "source": "crm_sync"}


def photo_fields(photo):
    """Credit fields for a photo: sync file name first, else the description."""
    synced = parse_sync_filename(photo.get("name"))
    if synced:
        return synced
    fields = parse_photo_description(photo.get("description"))
    fields["source"] = "upload_form"
    return fields


def is_candidate(photo, now, used_ids=(), max_age_days=PHOTO_MAX_AGE_DAYS):
    """True when a Drive file may be offered as this week's Nailed It photo.

    CRM-sync files (recognised by name) are eligible as they are: the crew
    attached them to a finished job's meeting. Upload-form photos need the
    Finished and consent lines in their description.
    """
    if photo.get("id") in set(used_ids):
        return False
    if not (photo.get("mimeType") or "").startswith("image/"):
        return False
    if parse_sync_filename(photo.get("name")) is None:
        fields = parse_photo_description(photo.get("description"))
        if not fields.get("stage", "").lower().startswith("finished"):
            return False
        if not fields.get("consent", "").lower().startswith("yes"):
            return False
    created = photo.get("createdTime")
    if created:
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        if created_dt < now - timedelta(days=max_age_days):
            return False
    return True


def photo_group(photo, fields=None):
    """Which job a photo belongs to, so one deal cannot fill the list.

    Sync files group by deal ("Deal 32402"), else by job name; upload-form
    photos by job name; anything else stands alone (its id). Mirrors the
    "group" key in deluge/nailed_it_candidates.dg.
    """
    fields = fields if fields is not None else photo_fields(photo)
    return fields.get("deal") or fields.get("job_name") or photo.get("id") or ""


def spread_by_group(items, group_of):
    """Interleave groups: each group's 1st item, then each group's 2nd...

    Keeps the incoming order inside each round, so a newest-first list stays
    newest first within every deal (Henry 2026-11-06: five Deal32402 photos
    should not crowd out everything else).
    """
    seen = {}
    ranked = []
    for i, item in enumerate(items):
        g = group_of(item)
        ranked.append((seen.get(g, 0), i, item))
        seen[g] = seen.get(g, 0) + 1
    return [item for _, _, item in sorted(ranked, key=lambda t: (t[0], t[1]))]


def select_candidates(photos, now, used_ids=(), limit=MAX_CANDIDATES):
    """Eligible photos, at most `limit`, each with parsed fields and a group.

    Newest first, then spread across deals: one photo per deal in turn, so
    a deal with many photos shares the list instead of filling it.
    """
    eligible = [p for p in photos if is_candidate(p, now, used_ids)]
    eligible.sort(key=lambda p: p.get("createdTime") or "", reverse=True)
    items = []
    for p in eligible:
        item = dict(p)
        item["fields"] = photo_fields(p)
        item["group"] = photo_group(p, item["fields"])
        items.append(item)
    return spread_by_group(items, lambda c: c["group"])[:limit]


PICKER_PER_GROUP = 2


def picker_shown(ranked, max_shown=6, per_group=PICKER_PER_GROUP):
    """Ids the Sunday picker email shows, in score order.

    At most `per_group` photos per deal first; any places left are filled
    with the next best photos regardless of deal. Mirrors the show_ids pass
    in deluge/scheduled_photo_picker.dg.
    """
    shown, counts = [], {}
    for c in ranked:
        g = c.get("group") or c.get("id")
        if len(shown) < max_shown and counts.get(g, 0) < per_group:
            shown.append(c["id"])
            counts[g] = counts.get(g, 0) + 1
    for c in ranked:
        if len(shown) < max_shown and c["id"] not in shown:
            shown.append(c["id"])
    return [c["id"] for c in ranked if c["id"] in shown]


def drive_image_url(file_id):
    """Public render URL for a photo id.

    A Drive file id (shared 'anyone with the link') goes through Drive's
    thumbnail endpoint; an http(s) URL (website photos) is already public
    and is used as is.
    """
    if file_id.startswith("http"):
        return file_id
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1200"


# Interim Nailed It source (Henry 2026-11-04: "grab some finished photos
# from our website to use for now"), until the Zoho CRM photo sync lands.
# Hand-picked from getlivewire.com: real finished installs, no faces, no
# stock or rendered images. Already public, so no Drive sharing step. The
# URL doubles as the photo id. Mirrors WEBSITE_PHOTOS in
# deluge/nailed_it_candidates.dg.
WEBSITE_PHOTOS = [
    ("https://www.getlivewire.com/wp-content/uploads/2023/05/CommercialAV-1.jpg",
     "Boardroom display and conferencing", "Commercial AV"),
    ("https://www.getlivewire.com/wp-content/uploads/2023/05/CommercialAV.jpg",
     "Office lounge display", "Commercial AV"),
    ("https://www.getlivewire.com/wp-content/uploads/2023/06/Commercial_Technology_Spaces_38.jpg",
     "Conference room display", "Commercial AV"),
    ("https://www.getlivewire.com/wp-content/uploads/2023/07/CommonHouseLandingThumb-e1761073657367.jpg",
     "Common House Richmond screening room", "Projection and audio"),
    ("https://www.getlivewire.com/wp-content/uploads/2023/05/DistributedAVinOffice.jpg",
     "Office conference room", "Distributed AV"),
    ("https://www.getlivewire.com/wp-content/uploads/2022/02/ExteriorLighting2.jpg",
     "Exterior home lighting", "Lighting"),
    ("https://www.getlivewire.com/wp-content/uploads/2023/05/Home-Theater-Solutions.jpg",
     "Custom home theater", "Home theater"),
    ("https://www.getlivewire.com/wp-content/uploads/2023/05/SmartKitchen_Web.jpg",
     "Kitchen pendant and recessed lighting", "Lighting"),
    ("https://www.getlivewire.com/wp-content/uploads/2022/12/WiringCloset.jpg",
     "Labeled network and AV terminations", "Structured wiring"),
    ("https://www.getlivewire.com/wp-content/uploads/2023/05/commercial-av-systems1.jpg",
     "Meeting hall projection", "Commercial AV"),
    ("https://www.getlivewire.com/wp-content/uploads/2026/06/livewire-how-room.jpg",
     "Sanctuary speaker arrays and projection", "House of worship AV"),
]


def website_candidates(used_ids=()):
    """Unused website photos in candidate shape (fields already parsed)."""
    used = set(used_ids)
    out = []
    for url, job, installed in WEBSITE_PHOTOS:
        if url in used:
            continue
        out.append({
            "id": url, "thumb_url": url, "view_url": url,
            "name": url.rsplit("/", 1)[-1],
            "fields": {"job_name": job, "installed": installed,
                       "sent_by": "getlivewire.com"},
        })
    return out


def _pct(x):
    return f"{x * 100:.2f}%"


def _credit_line(photo):
    """Escaped credit for the Nailed It side: client, job, then crew or uploader.

    A "TBD" job name (records saved before the sync fix) is left out.
    """
    job_name = photo.get("job_name")
    if (job_name or "").strip().upper() == "TBD":
        job_name = ""
    credit_bits = [html.escape(b) for b in (job_name, photo.get("installed")) if b]
    credit = " &middot; ".join(credit_bits)
    if photo.get("sent_by"):
        # An email address or domain (website photos) is the uploader; a plain name is the crew.
        who = "photo by" if ("@" in photo["sent_by"] or "." in photo["sent_by"]) else "crew:"
        credit = (credit + " &middot; " if credit else "") + f"{who} {html.escape(photo['sent_by'])}"
    return credit


NAILED_HEADLINE = "Nailed it."
NAILED_LINE = "Finished work from our crews this week. Nice job, team."
NAILED_ALT = "Nailed it: photo of recent finished Livewire work."
FAILED_HEADLINE = "Failed it."
FAILED_LINE = "Spotted in the wild. Not one of ours."
FAILED_ALT = "Failed it: a bad install found online, not Livewire work."


def render_nailed_block(photo=None):
    """HTML for the Nailed It showcase card, or "" when there is no photo.

    photo: {"id", "job_name", "sent_by", "installed"}; id is a Drive file id
    or, for the interim website source, a public URL.
    """
    if not photo or not photo.get("id"):
        return ""
    image_id = photo["id"]
    credit = _credit_line(photo)

    return (
        "<table role='presentation' cellpadding='0' cellspacing='0' border='0' width='100%' "
        f"style='width:100%;max-width:600px;background:{RF_CARD_BG};border:1px solid {RF_CARD_BORDER};"
        "border-collapse:separate;margin:0 0 16px;'>"
        "<tr><td style='padding:0;'>"
        f"<img src='{drive_image_url(image_id)}' width='600' alt='{NAILED_ALT}' "
        "style='display:block;width:100%;max-width:600px;height:auto;border:0;'>"
        "</td></tr>"
        "<tr><td style='padding:12px 20px 14px;'>"
        f"<p style='margin:0;font-family:{RF_SANS_STACK};font-size:20px;line-height:24px;"
        f"font-weight:700;color:{RF_COPPER};'>{NAILED_HEADLINE}</p>"
        f"<p style='margin:4px 0 0;font-family:{RF_SANS_STACK};font-size:14px;line-height:20px;"
        f"color:{RF_INK};'>{NAILED_LINE}</p>"
        f"<p style='margin:6px 0 0;font-family:{RF_SANS_STACK};font-size:11px;line-height:14px;"
        f"color:{RF_TEXT_SECONDARY};'>{credit}</p>"
        "</td></tr></table>"
    )


def pick_failed_image(files, week_of_year):
    """Failed It file id for the week, or None when the folder is empty.

    files: Drive listing of the Failed It folder ({"id", "name"}), any order.
    Sorted by name, then index = week_of_year % count, the same rotation
    send_actuals_email.dg uses with ws.getWeekOfYear(). Taking the week
    number as an input keeps this mirror independent of Deluge's own week
    numbering.
    """
    ordered = sorted((f for f in files or () if f.get("id")), key=lambda f: f.get("name") or "")
    if not ordered:
        return None
    return ordered[week_of_year % len(ordered)]["id"]


# Side-by-side photos are cropped to 4:3 so both halves line up (Henry
# 2026-11-06; crew phone photos are mostly portrait). Two layers:
# Drive's thumbnail service center-crops to 2x this box ("-c"), and a
# fixed-height overflow box keeps the halves even where that crop does not
# apply (website URLs) or is ignored. Outlook desktop ignores overflow and
# shows the full image.
CONTRAST_IMG_W = 282
CONTRAST_IMG_H = 211


def is_portrait(meta):
    """True when Drive image metadata says the photo is taller than 4:3.

    meta: Drive imageMediaMetadata ({"width", "height", "rotation"}), or None.
    rotation 1 or 3 (90 or 270 degrees) swaps width and height. Unknown
    metadata counts as not portrait (center crop).
    """
    if not meta or not meta.get("width") or not meta.get("height"):
        return False
    w, h = int(meta["width"]), int(meta["height"])
    if int(meta.get("rotation") or 0) in (1, 3):
        w, h = h, w
    return h * 4 > w * 3


def drive_crop_url(file_id, meta=None, w=564, h=423):  # 2x of 282 wide, exact 4:3
    """Drive thumbnail URL for a 4:3 card photo; an http(s) URL is returned as is.

    Henry 2026-11-06: crop from the top. Google's "-c" crop can only center,
    which cut the subject (installs sit high on walls and ceilings) out of
    portrait phone photos. So a portrait photo is fetched full width and
    uncropped, and the fixed-height overflow box shows its top 4:3. A wide
    photo keeps the center crop, which only trims its sides.
    """
    if file_id.startswith("http"):
        return file_id
    if is_portrait(meta):
        return f"https://drive.google.com/thumbnail?id={file_id}&sz=w{w}"
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w{w}-h{h}-c"


def _contrast_cell(image_id, alt, headline, color, line, credit, side, meta=None):
    pad = "padding:0 6px 0 0;" if side == "left" else "padding:0 0 0 6px;"
    credit_html = (
        f"<p style='margin:6px 0 0;font-family:{RF_SANS_STACK};font-size:11px;line-height:14px;"
        f"color:{RF_TEXT_SECONDARY};'>{credit}</p>" if credit else ""
    )
    return (
        f"<td width='50%' valign='top' style='width:50%;vertical-align:top;border:0;{pad}'>"
        f"<div style='height:{CONTRAST_IMG_H}px;overflow:hidden;'>"
        f"<img src='{drive_crop_url(image_id, meta)}' width='{CONTRAST_IMG_W}' alt='{alt}' "
        f"style='display:block;width:100%;max-width:{CONTRAST_IMG_W}px;height:auto;border:0;'>"
        "</div>"
        f"<p style='margin:10px 0 0;font-family:{RF_SANS_STACK};font-size:18px;line-height:22px;"
        f"font-weight:700;color:{color};'>{headline}</p>"
        f"<p style='margin:4px 0 0;font-family:{RF_SANS_STACK};font-size:13px;line-height:18px;"
        f"color:{RF_INK};'>{line}</p>"
        f"{credit_html}"
        "</td>"
    )


PICKER_THUMB_W = 200
PICKER_THUMB_H = 150


def picker_thumb_url(thumb_url, meta=None):
    """Picker-email thumbnail showing the same 4:3 crop Monday's card will use.

    thumb_url: Drive's signed thumbnailLink (lh3, ends "=s220") or a public
    website URL. Wide photos get Google's center crop at 2x 200x150; portrait
    photos come back full width so the 150px overflow box shows their top,
    exactly like the email. Mirrors scheduled_photo_picker.dg.
    """
    if not thumb_url or "=s220" not in thumb_url:
        return thumb_url
    size = "=w400" if is_portrait(meta) else "=w400-h300-c"
    return thumb_url.replace("=s220", size)


def render_contrast_block(photo=None, failed_id=None, failed_meta=None):
    """The Monday card: Failed It (left) next to Nailed It (right).

    No Nailed It photo means no card at all. No Failed It image (empty
    folder, or the listing failed) means the Nailed It card alone, as before.
    """
    if not photo or not photo.get("id"):
        return ""
    if not failed_id:
        return render_nailed_block(photo)
    left = _contrast_cell(failed_id, FAILED_ALT, FAILED_HEADLINE, RF_INK, FAILED_LINE, "", "left",
                          failed_meta)
    right = _contrast_cell(photo["id"], NAILED_ALT, NAILED_HEADLINE, RF_COPPER, NAILED_LINE,
                           _credit_line(photo), "right", photo.get("meta"))
    return (
        "<table role='presentation' cellpadding='0' cellspacing='0' border='0' width='100%' "
        f"style='width:100%;max-width:600px;background:{RF_CARD_BG};border:1px solid {RF_CARD_BORDER};"
        "border-collapse:separate;margin:0 0 16px;'>"
        "<tr><td style='padding:12px;'>"
        "<table role='presentation' cellpadding='0' cellspacing='0' border='0' width='100%' style='width:100%;'>"
        f"<tr>{left}{right}</tr>"
        "</table>"
        "</td></tr></table>"
    )


# --- Vision scoring (Henry 2026-11-04: "Nailed it has more to do with how
# the picture looks") ------------------------------------------------------
# One Claude API call per Sunday picker run scores every candidate. Mirrors
# deluge/nailed_it_score.dg. Henry still makes the final pick; the score
# ranks the picker email and decides the no-pick fallback.

SCORING_MODEL = "claude-opus-5-5"
SCORING_ANTHROPIC_VERSION = "2026-10-21"
NAILED_IT_MIN_SCORE = 7

SCORING_RUBRIC = (
    "You are picking a photo for the 'Nailed it' banner in Livewire's weekly "
    "team email. Livewire installs AV, networking, lighting control and "
    "electrical systems. Score each photo 1-10 on how well it shows off "
    "excellent finished work:\n"
    "- The finished install is the clear subject (racks, mounted TVs, "
    "speakers, keypads, lighting, panels).\n"
    "- Craftsmanship reads at a glance: straight lines, level and centered "
    "mounts, hidden or neatly dressed cabling, clean labels.\n"
    "- Photo quality: in focus, well lit, no heavy glare or blown highlights, "
    "upright (not sideways or upside down).\n"
    "- Uncluttered: no ladders, boxes, tools, packaging or debris.\n"
    "- Works as a wide banner (roughly 2:1 crop).\n"
    "Set disqualified=true for a photo with identifiable faces, house "
    "numbers or street signs, screens showing personal information, or "
    "anything a customer would not want sent to the whole company. Set "
    "nailed_it=true only when score >= 7 and not disqualified. Keep each "
    "reason under 15 words, naming what makes it good or bad. Return one "
    "entry per photo, using the photo numbers given."
)

SCORING_SCHEMA = {
    "type": "object",
    "properties": {
        "photos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "score": {"type": "integer"},
                    "nailed_it": {"type": "boolean"},
                    "disqualified": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["index", "score", "nailed_it", "disqualified", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["photos"],
    "additionalProperties": False,
}


def scoring_image_url(thumb_url):
    """Drive thumbnailLink at a size big enough to judge craftsmanship."""
    return (thumb_url or "").replace("=s220", "=s1600")


def build_scoring_request(candidates):
    """Messages API request body scoring every candidate in one call."""
    content = []
    for i, c in enumerate(candidates, start=1):
        fields = c.get("fields") or {}
        label = " · ".join(
            b for b in (fields.get("job_name") or c.get("job_name"),
                        fields.get("installed") or c.get("installed")) if b
        )
        content.append({"type": "text", "text": f"Photo {i}: {label}".rstrip(": ")})
        content.append({"type": "image",
                        "source": {"type": "url", "url": scoring_image_url(c.get("thumb_url"))}})
    content.append({"type": "text", "text": SCORING_RUBRIC})
    return {
        "model": SCORING_MODEL,
        "max_tokens": 4000,
        "output_config": {
            "effort": "low",
            "format": {"type": "json_schema", "schema": SCORING_SCHEMA},
        },
        "messages": [{"role": "user", "content": content}],
    }


def _response_scores(response):
    """{index: score entry} from a Messages API response dict, or None."""
    import json

    if not isinstance(response, dict) or response.get("stop_reason") != "end_turn":
        return None
    text = "".join(b.get("text", "") for b in response.get("content", [])
                   if b.get("type") == "text")
    try:
        photos = json.loads(text)["photos"]
    except (ValueError, KeyError, TypeError):
        return None
    return {p["index"]: p for p in photos if isinstance(p, dict) and "index" in p}


def apply_scores(candidates, response, min_score=NAILED_IT_MIN_SCORE):
    """Merge scores into candidates and rank them.

    Returns (ranked, scored). ranked drops disqualified photos and sorts by
    score desc (ties keep newest-first order). When the response is
    unusable (refusal, truncation, bad JSON) every candidate comes back
    unscored in its original order and scored is False.
    """
    scores = _response_scores(response)
    if scores is None:
        return [dict(c, score=None, reason="", above_bar=None) for c in candidates], False
    ranked = []
    for i, c in enumerate(candidates, start=1):
        s = scores.get(i)
        if s is None or s.get("disqualified"):
            continue
        score = max(1, min(10, int(s.get("score", 0))))
        ranked.append(dict(c, score=score, reason=s.get("reason", ""),
                           above_bar=score >= min_score))
    ranked.sort(key=lambda c: c["score"], reverse=True)  # stable: newest wins ties
    return ranked, True


def suggested_pick(ranked, scored):
    """Photo to use Monday if Henry doesn't pick, or None.

    Scored: the top photo only if it clears the bar. Unscored (API down):
    the newest photo, as before vision scoring existed.
    """
    if not ranked:
        return None
    if not scored:
        return ranked[0]
    return ranked[0] if ranked[0]["above_bar"] else None


def monday_record(records, today):
    """The Nailed_It_Photos record Monday's email uses, or None.

    This week's "Picked" record first, else this week's "Suggested" one.
    "This week" is Send_Date in (today - 7 days, today], for both statuses,
    so a pick that never went out cannot resurface weeks later. Mirrors
    the record lookup in deluge/send_actuals_email.dg (records are dicts
    with Status and Send_Date as a date).
    """
    def this_week(r, status):
        d = r.get("Send_Date")
        return r.get("Status") == status and d is not None and today - timedelta(days=7) < d <= today

    for status in ("Picked", "Suggested"):
        hits = sorted((r for r in records if this_week(r, status)),
                      key=lambda r: r["Send_Date"], reverse=True)
        if hits:
            return hits[0]
    return None
