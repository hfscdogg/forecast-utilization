"""Tests for the Nailed It / Failed It verdict block (nailed_it.py)."""

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nailed_it import (  # noqa: E402
    is_candidate,
    parse_photo_description,
    render_nailed_block,
    select_candidates,
)

# Verbatim descriptions from the asset-library Drive folder (2026-11-04).
BLOCK_PARTY_DESC = (
    "Job: Block Party\nDate: 2026-09-21\nSent by: brianredden@getlivewire.com\n"
    "Residential or commercial? Commercial\nWhat did we install? Event\n"
    "Where is the job at? Finished\nIs the customer OK with us sharing these? Yes, they said OK"
)
CLIFFORD_DESC = (
    "Job: job\nDate: 2026-10-26\nSent by: henry@getlivewire.com\nJob or event name Clifford\n"
    "Residential or commercial? Residential\nWhat did we install? Lighting control (Lutron and similar)\n"
    "Where in the building? Office or conference room\nWhere is the job at? Work in progress\n"
    "Brands in the photos DMF\nTell us about it Upgrade lighting \n"
    "Is the customer OK with us sharing these? Yes, they said OK"
)

NOW = datetime(2026, 10, 1, 20, 0, tzinfo=timezone.utc)


def photo(pid, desc, created="2026-09-21T21:31:59Z", mime="image/jpeg"):
    return {"id": pid, "description": desc, "createdTime": created, "mimeType": mime}


def finished_desc(consent="Yes, they said OK", stage="Finished"):
    return (
        f"Job: Test Job\nSent by: tech@getlivewire.com\nWhere is the job at? {stage}\n"
        f"Is the customer OK with us sharing these? {consent}"
    )


# --- description parsing ---------------------------------------------------

def test_parse_block_party_fields():
    f = parse_photo_description(BLOCK_PARTY_DESC)
    assert f["job_name"] == "Block Party"
    assert f["sent_by"] == "brianredden@getlivewire.com"
    assert f["stage"] == "Finished"
    assert f["consent"].startswith("Yes")
    assert f["installed"] == "Event"


def test_parse_prefers_event_name_over_generic_job():
    f = parse_photo_description(CLIFFORD_DESC)
    assert f["job_name"] == "Clifford"
    assert f["stage"] == "Work in progress"
    assert f["brands"] == "DMF"


def test_parse_empty_description():
    assert parse_photo_description(None)["job_name"] == ""


# --- candidate filter ------------------------------------------------------

def test_finished_with_consent_is_candidate():
    assert is_candidate(photo("a", BLOCK_PARTY_DESC), NOW)


def test_work_in_progress_is_not_candidate():
    assert not is_candidate(photo("b", CLIFFORD_DESC, created="2026-09-30T00:00:00Z"), NOW)


def test_missing_or_negative_consent_is_not_candidate():
    assert not is_candidate(photo("c", "Job: X\nWhere is the job at? Finished"), NOW)
    assert not is_candidate(photo("d", finished_desc(consent="No")), NOW)


def test_old_used_or_non_image_is_not_candidate():
    assert not is_candidate(photo("e", finished_desc(), created="2026-08-01T00:00:00Z"), NOW)
    assert not is_candidate(photo("f", finished_desc()), NOW, used_ids={"f"})
    assert not is_candidate(photo("g", finished_desc(), mime="video/mp4"), NOW)


def test_select_candidates_newest_first_and_limited():
    photos = [
        photo("old", finished_desc(), created="2026-09-10T00:00:00Z"),
        photo("new", finished_desc(), created="2026-09-28T00:00:00Z"),
        photo("mid", finished_desc(), created="2026-09-20T00:00:00Z"),
        photo("wip", finished_desc(stage="Work in progress"), created="2026-09-29T00:00:00Z"),
    ]
    picked = select_candidates(photos, NOW, limit=2)
    assert [p["id"] for p in picked] == ["new", "mid"]
    assert picked[0]["fields"]["job_name"] == "Test Job"


# --- rendering -------------------------------------------------------------

PHOTO = {"id": "abc123", "job_name": "Block Party", "installed": "Event",
         "sent_by": "brianredden@getlivewire.com"}


def test_nailed_block_shows_photo_and_credit():
    html = render_nailed_block(PHOTO)
    assert "Nailed it." in html
    assert "thumbnail?id=abc123" in html
    assert "Block Party" in html and "photo by brianredden@getlivewire.com" in html
    # Henry 2026-11-06: no utilization verdict on the card
    assert "utilization" not in html and "target" not in html
    assert "alt='Nailed it: photo of recent finished Livewire work.'" in html


def test_no_block_without_a_photo():
    assert render_nailed_block(None) == ""
    assert render_nailed_block({}) == ""
    assert render_nailed_block({"id": ""}) == ""


def test_caption_escapes_html():
    html = render_nailed_block({"id": "x", "job_name": "Smith's <Den>"})
    assert "Smith&#x27;s &lt;Den&gt;" in html


# --- vision scoring ----------------------------------------------------------

import json  # noqa: E402

from nailed_it import (  # noqa: E402
    SCORING_MODEL,
    apply_scores,
    build_scoring_request,
    suggested_pick,
)

CANDS = [
    {"id": "a", "thumb_url": "https://lh3.example/a=s220", "fields": {"job_name": "Rack", "installed": "Network"}},
    {"id": "b", "thumb_url": "https://lh3.example/b=s220", "fields": {"job_name": "Theater"}},
    {"id": "c", "thumb_url": "https://lh3.example/c=s220", "fields": {}},
]


def api_response(photos, stop_reason="end_turn"):
    return {"stop_reason": stop_reason,
            "content": [{"type": "text", "text": json.dumps({"photos": photos})}]}


def entry(i, score, dq=False):
    return {"index": i, "score": score, "nailed_it": score >= 7 and not dq,
            "disqualified": dq, "reason": f"r{i}"}


def test_scoring_request_shape():
    req = build_scoring_request(CANDS)
    assert req["model"] == SCORING_MODEL
    assert req["output_config"]["format"]["type"] == "json_schema"
    blocks = req["messages"][0]["content"]
    images = [b for b in blocks if b["type"] == "image"]
    assert [b["source"]["url"] for b in images] == [
        "https://lh3.example/a=s1600", "https://lh3.example/b=s1600", "https://lh3.example/c=s1600"]
    assert blocks[0]["text"] == "Photo 1: Rack · Network"
    assert blocks[4]["text"] == "Photo 3"
    assert blocks[-1]["type"] == "text" and "Nailed it" in blocks[-1]["text"]


def test_apply_scores_ranks_and_drops_disqualified():
    ranked, scored = apply_scores(CANDS, api_response([entry(1, 6), entry(2, 9), entry(3, 10, dq=True)]))
    assert scored
    assert [c["id"] for c in ranked] == ["b", "a"]
    assert ranked[0]["above_bar"] and not ranked[1]["above_bar"]
    assert ranked[0]["reason"] == "r2"
    assert suggested_pick(ranked, scored)["id"] == "b"


def test_no_suggestion_when_nothing_clears_the_bar():
    ranked, scored = apply_scores(CANDS, api_response([entry(1, 5), entry(2, 6), entry(3, 3)]))
    assert scored and len(ranked) == 3
    assert suggested_pick(ranked, scored) is None


def test_unusable_response_falls_back_to_unscored_newest():
    for bad in (api_response([entry(1, 9)], stop_reason="refusal"),
                api_response([entry(1, 9)], stop_reason="max_tokens"),
                {"stop_reason": "end_turn", "content": [{"type": "text", "text": "not json"}]},
                None):
        ranked, scored = apply_scores(CANDS, bad)
        assert not scored
        assert [c["id"] for c in ranked] == ["a", "b", "c"]
        assert ranked[0]["score"] is None
        assert suggested_pick(ranked, scored)["id"] == "a"


def test_scores_are_clamped_and_missing_entries_dropped():
    ranked, _ = apply_scores(CANDS, api_response([entry(1, 14)]))
    assert [(c["id"], c["score"]) for c in ranked] == [("a", 10)]


# --- website photos (interim source) ----------------------------------------

from nailed_it import WEBSITE_PHOTOS, drive_image_url, website_candidates  # noqa: E402


def test_website_photo_urls_pass_through_and_drive_ids_use_thumbnail():
    url = WEBSITE_PHOTOS[0][0]
    assert drive_image_url(url) == url
    assert drive_image_url("abc") == "https://drive.google.com/thumbnail?id=abc&sz=w1200"


def test_website_candidates_skip_used_and_feed_scoring():
    first, second = WEBSITE_PHOTOS[0][0], WEBSITE_PHOTOS[1][0]
    cands = website_candidates(used_ids={first})
    assert len(cands) == len(WEBSITE_PHOTOS) - 1
    assert cands[0]["id"] == second and cands[0]["fields"]["sent_by"] == "getlivewire.com"
    req = build_scoring_request(cands[:2])
    assert [b["source"]["url"] for b in req["messages"][0]["content"] if b["type"] == "image"] == [
        second, WEBSITE_PHOTOS[2][0]]


def test_website_photo_renders_directly_in_nailed_card():
    url = WEBSITE_PHOTOS[0][0]
    html = render_nailed_block({"id": url, "job_name": "Boardroom"})
    assert f"src='{url}'" in html


# --- CRM sync file names (Livewire Job Photos) ------------------------------

from nailed_it import parse_sync_filename, photo_fields, PHOTO_ROOT_FOLDER_IDS  # noqa: E402


def test_sync_filename_gives_client_crew_job_and_deal():
    f = parse_sync_filename("2026-11-06_Deal32504_NickAbbate_AndreSmith-ThomasPayne_Frame-TV_a1b2c3.jpg")
    assert f == {"job_name": "Nick Abbate", "sent_by": "Andre Smith and Thomas Payne",
                 "installed": "Frame TV", "deal": "Deal 32504", "date": "2026-11-06",
                 "source": "crm_sync"}
    five = parse_sync_filename("2026-11-05_Deal31234_SmithResidence_BrianRedden_a1b2c3.jpg")
    assert five["sent_by"] == "Brian Redden" and five["installed"] == "Deal 31234"
    unknown = parse_sync_filename("2026-11-05_DealUnknown_UnknownClient_UnknownInstaller__zz9.heic")
    assert unknown["job_name"] == "" and unknown["sent_by"] == "" and unknown["installed"] == ""
    va = parse_sync_filename("2026-10-28_Deal32344_VAMedicalCenterRichmond_PatrickJones-ThomasPayne_Brandy-Williams-Upgrades-2026_865039.jpg")
    assert va["job_name"] == "VA Medical Center Richmond" and va["sent_by"] == "Patrick Jones and Thomas Payne"
    assert parse_sync_filename("IMG_4412.jpg") is None
    assert parse_sync_filename(None) is None


def test_synced_photo_is_eligible_without_description_and_credits_the_crew():
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    synced = {"id": "s1", "name": "2026-11-05_Deal31234_SmithResidence_BrianRedden_a1b2c3.jpg",
              "mimeType": "image/jpeg", "createdTime": "2026-11-05T20:00:00Z"}
    plain = {"id": "p1", "name": "IMG_4412.jpg", "mimeType": "image/jpeg",
             "createdTime": "2026-11-05T20:00:00Z"}
    assert is_candidate(synced, now)
    assert not is_candidate(plain, now)
    cands = select_candidates([synced, plain], now)
    assert [c["id"] for c in cands] == ["s1"]
    assert cands[0]["fields"]["sent_by"] == "Brian Redden"
    assert photo_fields({"description": "Sent by: x@getlivewire.com"})["source"] == "upload_form"
    html = render_nailed_block({"id": "s1", "job_name": "Smith Residence",
                               "installed": "Deal 31234", "sent_by": "Brian Redden"})
    assert "crew: Brian Redden" in html and "photo by" not in html
    site = render_nailed_block({"id": "https://x/y.jpg", "job_name": "Lobby", "sent_by": "getlivewire.com"})
    assert "photo by getlivewire.com" in site and "crew:" not in site


def test_picker_reads_sync_folder_first():
    assert PHOTO_ROOT_FOLDER_IDS[0] == "143dzFkXWASz9EI2awBfGEWNjdrhEAqP5"


# --- Failed It / Nailed It contrast (Henry 2026-11-06 11:58) ----------------

from nailed_it import (  # noqa: E402
    NAILED_IT_FAILED_FOLDER_ID,
    pick_failed_image,
    render_contrast_block,
)

SYNCED = {"id": "nail1", "job_name": "Nick Abbate", "installed": "Frame TV",
          "sent_by": "Andre Smith and Thomas Payne"}
FAILED_FILES = [{"id": "f-c", "name": "c.jpg"}, {"id": "f-a", "name": "a.jpg"},
                {"id": "f-b", "name": "b.jpg"}]


def test_failed_image_rotates_by_week_over_name_order():
    assert [pick_failed_image(FAILED_FILES, w) for w in (0, 1, 2, 3)] == ["f-a", "f-b", "f-c", "f-a"]
    assert pick_failed_image([], 10) is None
    assert pick_failed_image(None, 10) is None


def test_contrast_card_puts_failed_left_and_nailed_right_with_crew_credit():
    html = render_contrast_block(SYNCED, "f-b")
    assert html.index("Failed it.") < html.index("Nailed it.")
    assert html.index("thumbnail?id=f-b") < html.index("thumbnail?id=nail1")
    assert "Not one of ours." in html
    assert "crew: Andre Smith and Thomas Payne" in html
    # The credit belongs to the Nailed It side only.
    assert html.index("crew:") > html.index("Nailed it.")
    assert html.count("width='50%'") == 2
    assert "max-width:600px" in html


def test_contrast_falls_back_to_nailed_alone_and_needs_a_nailed_photo():
    assert render_contrast_block(SYNCED, None) == render_nailed_block(SYNCED)
    assert render_contrast_block(SYNCED, "") == render_nailed_block(SYNCED)
    assert render_contrast_block(None, "f-a") == ""
    assert render_contrast_block({"id": ""}, "f-a") == ""


def test_failed_it_folder_files_are_never_nailed_it_candidates():
    # The Failed It folder sits under the CRM Sync root, so the picker lists
    # its files; they carry no sync-style name and no description.
    now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
    for name in ("failed_it_01_rats_nest.jpg", "found-online-rack-mess.png", "IMG_2041.JPG"):
        f = {"id": "x", "name": name, "mimeType": "image/jpeg",
             "createdTime": "2026-11-06T10:00:00Z", "parents": [NAILED_IT_FAILED_FOLDER_ID]}
        assert not is_candidate(f, now)


def test_tbd_client_falls_back_to_the_job_label():
    f = parse_sync_filename("2026-11-05_DealUnknown_TBD_AndreSmith_Leon-and-Sony_a1b2c3.jpg")
    assert f["job_name"] == "Leon and Sony"
    assert f["installed"] == ""
    f = parse_sync_filename("2026-11-05_Deal32504_UnknownClient_AndreSmith_Frame-TV_a1b2c3.jpg")
    assert f["job_name"] == "Frame TV" and f["installed"] == "Deal 32504"
    # A real client is untouched.
    f = parse_sync_filename("2026-11-05_Deal32504_NickAbbate_AndreSmith_Frame-TV_a1b2c3.jpg")
    assert f["job_name"] == "Nick Abbate" and f["installed"] == "Frame TV"
