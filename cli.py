#!/usr/bin/env python3
"""
OmniShorts Studio Pro — Command Line Interface (CLI)
Supports headless video generation, Long-to-Shorts smart clipping, Character Vault inspection,
and Model Context Protocol (MCP) stdio server mode.
"""
import argparse
import json
import sys

from backend.models import GenerateProjectRequest
from backend.character_vault import CharacterVault
from backend.agents_engine import MultiAgentDirector, PROJECT_BENCHMARK_MATRIX
from backend.render_engine import render_project_video
from backend.mcp_server import run_stdio_mcp_server, MCP_TOOLS_SPEC


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="omnishorts",
        description="OmniShorts Studio Pro — Unified AI Shorts, Storyboard Continuity & AutoClip Engine",
    )
    sub = parser.add_subparsers(dest="command")

    # 1. render command
    p_render = sub.add_parser("render", help="Generate and render a 9:16 vertical MP4 Short from topic, script, novel, or template")
    p_render.add_argument("--mode", default="cinematic_story", choices=["cinematic_story", "reddit_story", "fake_chat", "viral_quiz", "long_to_shorts"])
    p_render.add_argument("--workflow", default="Idea2Video", choices=["Idea2Video", "Script2Video", "Novel2Video", "Template2Video", "Clip2Shorts"])
    p_render.add_argument("--topic", required=True, help="Topic, script text, novel passage, or question")
    p_render.add_argument("--name", default=None, help="Project title")
    p_render.add_argument("--subtitles", default="hormozi_gold", choices=["hormozi_gold", "mrbeast_cyan", "tiktok_clean", "cinema_minimal", "reddit_rapid", "neon_cyber"])
    p_render.add_argument("--bgm", default="cyberpunk_pulse", choices=["cyberpunk_pulse", "dark_tension_drone", "lofi_story_chill", "kinetic_synthwave", "none"])

    # 2. characters command
    sub.add_parser("characters", help="List CharacterVault profiles and DNA locks")

    # 3. benchmark command
    sub.add_parser("benchmark", help="Show comparison matrix against all 18 open-source AI video projects")

    # 4. mcp-tools command
    sub.add_parser("mcp-tools", help="Print MCP Server JSON tool definitions")

    # 5. mcp-stdio command
    sub.add_parser("mcp-stdio", help="Start standard JSON-RPC 2.0 MCP Server over stdio")

    args = parser.parse_args()
    vault = CharacterVault()
    director = MultiAgentDirector(vault)
    store = {}

    if args.command == "render":
        req = GenerateProjectRequest(
            name=args.name,
            mode=args.mode,
            workflow_source=args.workflow,
            topic_or_input=args.topic,
            subtitle_style=args.subtitles,
            bgm_track=args.bgm,
            auto_render=True,
        )
        proj = director.run_agent_pipeline(req)
        proj = render_project_video(proj, vault)
        print(json.dumps({
            "status": "completed",
            "project_id": proj.id,
            "name": proj.name,
            "mode": proj.mode,
            "output_video": f"/home/antigravity/omnishorts-studio{proj.output_video_url}",
            "output_thumbnail": f"/home/antigravity/omnishorts-studio{proj.output_thumbnail_url}",
            "output_subtitles": f"/home/antigravity/omnishorts-studio{proj.output_subtitle_url}",
            "output_comfyui_workflow": f"/home/antigravity/omnishorts-studio{proj.output_comfy_url}",
            "render_time_sec": proj.render_time_sec,
            "virality_metrics": proj.virality_metrics,
        }, ensure_ascii=False, indent=2))
        return

    if args.command == "characters":
        print(json.dumps([c.dict() for c in vault.list_characters()], ensure_ascii=False, indent=2))
        return

    if args.command == "benchmark":
        print(json.dumps(PROJECT_BENCHMARK_MATRIX, ensure_ascii=False, indent=2))
        return

    if args.command == "mcp-tools":
        print(json.dumps(MCP_TOOLS_SPEC, ensure_ascii=False, indent=2))
        return

    if args.command == "mcp-stdio":
        run_stdio_mcp_server(director, vault, render_project_video, store)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
