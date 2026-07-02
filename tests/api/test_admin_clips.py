"""Admin clip center API."""

from pathlib import Path

from utils.allure_helper import assert_status


def test_non_admin_cannot_access_clip_jobs(player_client):
    status, body = player_client.admin_list_clips()
    assert status == 403, f"Expected 403, got {status}: {body}"


def test_upload_rejects_non_video_file(admin_client, tmp_path: Path):
    bad_file = tmp_path / "clip.txt"
    bad_file.write_text("not a video", encoding="utf-8")

    status, body = admin_client.admin_upload_clip_source(str(bad_file), "text/plain")

    assert status == 400, body


def test_create_clip_validates_segment_range(admin_client, tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake mp4 payload")
    status, uploaded = admin_client.admin_upload_clip_source(str(source), "video/mp4")
    assert_status(status, 200)

    payload = {
        "title": "Invalid clip",
        "lineup_id": None,
        "source_url": uploaded["url"],
        "source_filename": uploaded["filename"],
        "segments": [
            {
                "title": "bad range",
                "note": "",
                "start_seconds": 12,
                "end_seconds": 10,
            }
        ],
        "template_type": "lineup_tutorial",
    }
    status, body = admin_client.admin_create_clip(payload)

    assert status == 400, body


def test_create_clip_accepts_focus_zoom_settings(admin_client, tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake mp4 payload")
    status, uploaded = admin_client.admin_upload_clip_source(str(source), "video/mp4")
    assert_status(status, 200)

    payload = {
        "title": "Zoom clip",
        "lineup_id": None,
        "source_url": uploaded["url"],
        "source_filename": uploaded["filename"],
        "segments": [
            {
                "title": "aim point",
                "note": "",
                "start_seconds": 10,
                "end_seconds": 20,
                "focus_mode": "auto_center",
                "focus_point_seconds": 2,
                "focus_pause_seconds": 1.5,
                "focus_x": 0.2,
                "focus_y": 0.18,
                "focus_width": 0.34,
                "focus_height": 0.34,
                "focus_scale": 1.2,
                "focus_position": "top_left",
            }
        ],
        "template_type": "lineup_tutorial",
    }

    status, body = admin_client.admin_create_clip(payload)

    assert_status(status, 200)
    segment = body["segments"][0]
    assert segment["focus_point_seconds"] == 2
    assert segment["focus_pause_seconds"] == 1.5
    assert segment["focus_position"] == "top_left"


def test_create_clip_rejects_focus_region_outside_frame(admin_client, tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake mp4 payload")
    status, uploaded = admin_client.admin_upload_clip_source(str(source), "video/mp4")
    assert_status(status, 200)

    payload = {
        "title": "Bad zoom clip",
        "lineup_id": None,
        "source_url": uploaded["url"],
        "source_filename": uploaded["filename"],
        "segments": [
            {
                "title": "bad focus",
                "note": "",
                "start_seconds": 0,
                "end_seconds": 8,
                "focus_x": 0.8,
                "focus_y": 0.2,
                "focus_width": 0.4,
                "focus_height": 0.4,
            }
        ],
        "template_type": "lineup_tutorial",
    }

    status, body = admin_client.admin_create_clip(payload)

    assert status == 400, body


def test_render_missing_clip_returns_404(admin_client):
    status, body = admin_client.admin_render_clip(999999)
    assert status == 404, body
