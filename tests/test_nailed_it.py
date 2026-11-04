"""Tests for the Nailed It / Failed It verdict block (nailed_it.py)."""

import sys
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nailed_it import (  # noqa: E402
    TEAM_VERDICT_TARGET,
    is_candidate,
    parse_photo_description,
    pick_failed_image,
    render_verdict_block,
    select_candidates,
    team_verdict,
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


# --- verdict ---------------------------------------------------------------

def test_verdict_at_target_counts_as_nailed():
    assert team_verdict(TEAM_VERDICT_TARGET) == "nailed"
    assert team_verdict(TEAM_VERDICT_TARGET + 0.01) == "nailed"
    assert team_verdict(TEAM_VERDICT_TARGET - 0.0001) == "failed"
    assert team_verdict(None) is None


def test_failed_image_rotates_by_week():
    ids = ["f0", "f1", "f2"]
    # 2026-09-20 is ISO week 38 -> 38 % 3 = 2
    assert pick_failed_image(ids, date(2026, 9, 20)) == "f2"
    assert pick_failed_image([], date(2026, 9, 20)) is None


# --- rendering -------------------------------------------------------------

PHOTO = {"id": "abc123", "job_name": "Block Party", "installed": "Event",
         "sent_by": "brianredden@getlivewire.com"}


def test_nailed_block_shows_photo_and_credit():
    html = render_verdict_block(0.84, photo=PHOTO, failed_image_id="fail1")
    assert "Nailed it." in html
    assert "thumbnail?id=abc123" in html
    assert "fail1" not in html
    assert "Block Party" in html and "photo by brianredden@getlivewire.com" in html
    assert "84.00% team utilization vs our 80.00% target" in html
    # Alt text carries the verdict when images are blocked
    assert "alt='Nailed it: 84.00%" in html


def test_failed_block_uses_staged_image_and_no_names():
    html = render_verdict_block(0.66, photo=PHOTO, failed_image_id="fail1")
    assert "Failed it... this week." in html
    assert "thumbnail?id=fail1" in html
    assert "abc123" not in html
    assert "Block Party" not in html


def test_no_block_when_utilization_unknown_or_image_missing():
    assert render_verdict_block(None, photo=PHOTO, failed_image_id="fail1") == ""
    assert render_verdict_block(0.9, photo=None) == ""
    assert render_verdict_block(0.5, failed_image_id=None) == ""


def test_caption_escapes_html():
    html = render_verdict_block(0.9, photo={"id": "x", "job_name": "Smith's <Den>"})
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
