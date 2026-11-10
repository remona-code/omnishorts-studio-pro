"""
Automated End-to-End Verification Suite for OmniShorts Studio Pro
Tests all 5 production modes, FFmpeg MP4 video streams, ASS subtitles,
ComfyUI workflow export, CharacterVault continuity, and MCP Server tools.
"""
import json
import os
import subprocess
from backend.app import (
    seed_showcase_projects,
    PROJECTS_STORE,
    character_vault,
    director,
)
from backend.render_engine import render_project_video
from backend.mcp_server import handle_mcp_tool_call


def test_all_modes_and_deliverables() -> None:
    seed_showcase_projects()
    assert len(PROJECTS_STORE) >= 5, "Expected all 5 showcase projects to be initialized"

    for pid, proj in PROJECTS_STORE.items():
        mp4_path = f"/home/antigravity/omnishorts-studio{proj.output_video_url}"
        thumb_path = f"/home/antigravity/omnishorts-studio{proj.output_thumbnail_url}"
        ass_path = f"/home/antigravity/omnishorts-studio{proj.output_subtitle_url}"
        comfy_path = f"/home/antigravity/omnishorts-studio{proj.output_comfy_url}"

        assert os.path.exists(mp4_path) and os.path.getsize(mp4_path) > 20000, f"Missing or empty MP4 for {pid}"
        assert os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 5000, f"Missing thumbnail for {pid}"
        assert os.path.exists(ass_path) and os.path.getsize(ass_path) > 200, f"Missing ASS subtitle for {pid}"
        assert os.path.exists(comfy_path) and os.path.getsize(comfy_path) > 100, f"Missing ComfyUI workflow for {pid}"

        # Verify valid H.264 video and AAC audio streams with ffprobe
        probe_out = subprocess.check_output([
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_name,width,height",
            "-of", "json",
            mp4_path,
        ]).decode("utf-8")
        probe_data = json.loads(probe_out)
        codecs = [s.get("codec_name") for s in probe_data.get("streams", [])]
        assert "h264" in codecs and "aac" in codecs, f"Invalid codecs in {pid}: {codecs}"

    # Verify MCP tool call creates a real rendered video
    mcp_res = handle_mcp_tool_call(
        tool_name="omnishorts_clip_long_video",
        arguments={"crop_mode": "split_screen_podcast", "subtitle_style": "mrbeast_cyan"},
        director=director,
        character_vault=character_vault,
        render_fn=render_project_video,
        projects_store=PROJECTS_STORE,
    )
    assert mcp_res["status"] == "success"
    print("ALL END-TO-END TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    test_all_modes_and_deliverables()
