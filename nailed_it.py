"""
"Nailed It / Failed It" verdict block for the Utilization Actuals email.

Python reference for the Deluge side:
- deluge/nailed_it_candidates.dg   (parse_photo_description, is_candidate,
                                     select_candidates)
- deluge/send_actuals_email.dg     (team_verdict, pick_failed_image,
                                     render_verdict_block)
Keep in sync.

Rules (Henry 2026-11-04):
- The verdict is for the TEAM number only (company utilization vs
  TEAM_VERDICT_TARGET). No per-tech "failed it" call-outs.
- "Nailed It" shows a real job photo from the Livewire asset library, but
  only one marked Finished whose customer said OK to sharing.
- "Failed It" shows a staged gag image, never a real customer job.
- No verdict block when utilization is unknown (iSolved pending).
"""

import html
from datetime import datetime, timedelta

# Company utilization at or above this is "Nailed it". Mirrors
# TEAM_VERDICT_TARGET in deluge/config.dg and send_actuals_email.dg.
TEAM_VERDICT_TARGET = 0.75  # Henry 2026-11-04

PHOTO_MAX_AGE_DAYS = 30
MAX_CANDIDATES = 6

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


def is_candidate(photo, now, used_ids=(), max_age_days=PHOTO_MAX_AGE_DAYS):
    """True when a Drive file may be offered as this week's Nailed It photo."""
    if photo.get("id") in set(used_ids):
        return False
    if not (photo.get("mimeType") or "").startswith("image/"):
        return False
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


def select_candidates(photos, now, used_ids=(), limit=MAX_CANDIDATES):
    """Newest-first eligible photos, at most `limit`, each with parsed fields."""
    eligible = [p for p in photos if is_candidate(p, now, used_ids)]
    eligible.sort(key=lambda p: p.get("createdTime") or "", reverse=True)
    out = []
    for p in eligible[:limit]:
        item = dict(p)
        item["fields"] = parse_photo_description(p.get("description"))
        out.append(item)
    return out


def team_verdict(company_utilization, target=TEAM_VERDICT_TARGET):
    """'nailed', 'failed', or None when the number isn't known."""
    if company_utilization is None:
        return None
    return "nailed" if company_utilization >= target else "failed"


def pick_failed_image(failed_image_ids, week_start):
    """Rotate the staged Failed It images by ISO week of the lag week."""
    if not failed_image_ids:
        return None
    week = week_start.isocalendar()[1]
    return failed_image_ids[week % len(failed_image_ids)]


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


def render_verdict_block(company_utilization, photo=None, failed_image_id=None,
                         target=TEAM_VERDICT_TARGET):
    """HTML for the verdict card, or "" when there is nothing to show.

    photo: {"id", "job_name", "sent_by", "installed"} for a nailed week.
    failed_image_id: Drive id of the staged image for a failed week.
    """
    verdict = team_verdict(company_utilization, target)
    if verdict is None:
        return ""
    util = _pct(company_utilization)
    tgt = _pct(target)
    if verdict == "nailed":
        if not photo:
            return ""
        image_id = photo["id"]
        headline = "Nailed it."
        line = f"{util} team utilization vs our {tgt} target."
        credit_bits = [html.escape(b) for b in (photo.get("job_name"), photo.get("installed")) if b]
        credit = " &middot; ".join(credit_bits)
        if photo.get("sent_by"):
            credit = (credit + " &middot; " if credit else "") + f"photo by {html.escape(photo['sent_by'])}"
        alt = f"Nailed it: {util} team utilization vs {tgt} target. Photo of recent Livewire work."
        accent = RF_COPPER
    else:
        if not failed_image_id:
            return ""
        image_id = failed_image_id
        headline = "Failed it... this week."
        line = f"{util} team utilization vs our {tgt} target. Next week we nail it."
        credit = "Staged photo. No customer jobs were harmed."
        alt = f"Failed it this week: {util} team utilization vs {tgt} target."
        accent = RF_INK

    return (
        "<table role='presentation' cellpadding='0' cellspacing='0' border='0' width='100%' "
        f"style='width:100%;max-width:600px;background:{RF_CARD_BG};border:1px solid {RF_CARD_BORDER};"
        "border-collapse:separate;margin:0 0 16px;'>"
        "<tr><td style='padding:0;'>"
        f"<img src='{drive_image_url(image_id)}' width='600' alt='{alt}' "
        "style='display:block;width:100%;max-width:600px;height:auto;border:0;'>"
        "</td></tr>"
        "<tr><td style='padding:12px 20px 14px;'>"
        f"<p style='margin:0;font-family:{RF_SANS_STACK};font-size:20px;line-height:24px;"
        f"font-weight:700;color:{accent};'>{headline}</p>"
        f"<p style='margin:4px 0 0;font-family:{RF_SANS_STACK};font-size:14px;line-height:20px;"
        f"color:{RF_INK};'>{line}</p>"
        f"<p style='margin:6px 0 0;font-family:{RF_SANS_STACK};font-size:11px;line-height:14px;"
        f"color:{RF_TEXT_SECONDARY};'>{credit}</p>"
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
