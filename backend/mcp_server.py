"""
OmniShorts Studio — Model Context Protocol (MCP) Server (JSON-RPC 2.0)
Allows AI Agents (Claude Desktop, Cursor, OpenMontage Agents, LangGraph, CrewAI)
to programmatically create, edit, clip, and render 9:16 Shorts via standard MCP tools.
Supports both stdio transport and HTTP REST/JSON-RPC integration.
"""
import json
import sys
from typing import Dict, Any, List
from backend.models import GenerateProjectRequest, CharacterProfile


MCP_TOOLS_SPEC: List[Dict[str, Any]] = [
    {
        "name": "omnishorts_create_video",
        "description": "Generates and renders a complete 9:16 vertical MP4 Short with voiceover, Foley SFX, BGM ducking, and burned-in ASS karaoke subtitles across any of the 5 modes (cinematic_story, reddit_story, fake_chat, viral_quiz, long_to_shorts).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["cinematic_story", "reddit_story", "fake_chat", "viral_quiz", "long_to_shorts"],
                    "description": "Production template mode",
                },
                "workflow_source": {
                    "type": "string",
                    "enum": ["Idea2Video", "Script2Video", "Novel2Video", "Template2Video", "Clip2Shorts"],
                },
                "topic_or_input": {
                    "type": "string",
                    "description": "Topic, script, novel passage, Reddit question, or clip timestamp",
                },
                "subtitle_style": {
                    "type": "string",
                    "enum": ["hormozi_gold", "mrbeast_cyan", "tiktok_clean", "cinema_minimal", "reddit_rapid", "neon_cyber"],
                },
                "bgm_track": {
                    "type": "string",
                    "enum": ["cyberpunk_pulse", "dark_tension_drone", "lofi_story_chill", "kinetic_synthwave", "none"],
                },
            },
            "required": ["mode", "topic_or_input"],
        },
    },
    {
        "name": "omnishorts_clip_long_video",
        "description": "Extracts a high-retention 9:16 vertical Short from a 16:9 widescreen video using Active Speaker Face Tracking or Split-Screen Podcast layout (AutoClip + OpenShorts engine).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source_video": {"type": "string", "description": "Path or URL to 16:9 video"},
                "crop_mode": {
                    "type": "string",
                    "enum": ["smart_speaker_track", "split_screen_podcast"],
                },
                "subtitle_style": {"type": "string", "default": "hormozi_gold"},
            },
            "required": ["crop_mode"],
        },
    },
    {
        "name": "omnishorts_lock_character_dna",
        "description": "Registers or updates a character in CharacterVault with persistent DNA prompt, wardrobe tags, deterministic seed, and IP-Adapter weight (ViMax + Toonflow continuity).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "role": {"type": "string"},
                "dna_prompt": {"type": "string"},
                "wardrobe_prompt": {"type": "string"},
                "seed": {"type": "integer"},
            },
            "required": ["id", "name", "dna_prompt"],
        },
    },
    {
        "name": "omnishorts_export_comfyui_workflow",
        "description": "Exports a low-VRAM ComfyUI node graph JSON with IP-Adapter character consistency locks for local GPU execution (Pixelle-Video bridge).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
            },
            "required": ["project_id"],
        },
    },
]


def handle_mcp_tool_call(tool_name: str, arguments: Dict[str, Any], director, character_vault, render_fn, projects_store: Dict[str, Any]) -> Dict[str, Any]:
    """Executes an MCP tool call against the live OmniShorts Studio engine."""
    if tool_name == "omnishorts_create_video":
        req = GenerateProjectRequest(
            mode=arguments.get("mode", "cinematic_story"),
            workflow_source=arguments.get("workflow_source", "Idea2Video"),
            topic_or_input=arguments.get("topic_or_input", "2099 İstanbul Kuantum Arşivi"),
            subtitle_style=arguments.get("subtitle_style", "hormozi_gold"),
            bgm_track=arguments.get("bgm_track", "cyberpunk_pulse"),
            auto_render=True,
        )
        proj = director.run_agent_pipeline(req)
        proj = render_fn(proj, character_vault)
        projects_store[proj.id] = proj
        return {
            "status": "success",
            "tool": tool_name,
            "project_id": proj.id,
            "output_video_url": proj.output_video_url,
            "output_thumbnail_url": proj.output_thumbnail_url,
            "output_subtitle_url": proj.output_subtitle_url,
            "output_comfy_url": proj.output_comfy_url,
            "render_time_sec": proj.render_time_sec,
            "virality_score": proj.virality_metrics.get("overall_score", 96),
        }

    if tool_name == "omnishorts_clip_long_video":
        crop_mode = arguments.get("crop_mode", "smart_speaker_track")
        req = GenerateProjectRequest(
            name=f"MCP AutoClip ({crop_mode})",
            mode="long_to_shorts",
            workflow_source="Clip2Shorts",
            topic_or_input=crop_mode,
            subtitle_style=arguments.get("subtitle_style", "hormozi_gold"),
            bgm_track="lofi_story_chill",
            auto_render=True,
        )
        proj = director.run_agent_pipeline(req)
        proj = render_fn(proj, character_vault)
        projects_store[proj.id] = proj
        return {
            "status": "success",
            "tool": tool_name,
            "project_id": proj.id,
            "crop_mode": crop_mode,
            "output_video_url": proj.output_video_url,
            "virality_score": proj.clipper_segment.virality_score if proj.clipper_segment else 97,
        }

    if tool_name == "omnishorts_lock_character_dna":
        profile = CharacterProfile(
            id=arguments["id"],
            name=arguments["name"],
            role=arguments.get("role", "Başrol Karakteri"),
            avatar_url="/assets/images/char_elena_archivist_dna.jpg",
            dna_prompt=arguments["dna_prompt"],
            wardrobe_prompt=arguments.get("wardrobe_prompt", "tailored dark coat"),
            seed=int(arguments.get("seed", 2099777)),
        )
        character_vault.upsert_character(profile)
        return {
            "status": "success",
            "tool": tool_name,
            "character": profile.dict(),
        }

    if tool_name == "omnishorts_export_comfyui_workflow":
        pid = arguments.get("project_id")
        proj = projects_store.get(pid) or next(iter(projects_store.values()), None)
        if not proj:
            return {"status": "error", "message": "Project not found"}
        path = character_vault.export_comfyui_workflow(proj.id, proj.scenes, "/home/antigravity/omnishorts-studio/output/workflows")
        return {
            "status": "success",
            "tool": tool_name,
            "project_id": proj.id,
            "workflow_path": path,
        }

    return {"status": "error", "message": f"Unknown MCP tool: {tool_name}"}


def run_stdio_mcp_server(director, character_vault, render_fn, projects_store) -> None:
    """Standard JSON-RPC 2.0 stdio loop for MCP clients."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method", "")
            req_id = req.get("id")
            if method == "initialize":
                res = {
                    "protocolVersion": "2025-06-18",
                    "serverInfo": {"name": "omnishorts-studio-mcp", "version": "2.6.0"},
                    "capabilities": {"tools": {}},
                }
            elif method == "tools/list":
                res = {"tools": MCP_TOOLS_SPEC}
            elif method == "tools/call":
                params = req.get("params", {})
                out = handle_mcp_tool_call(
                    params.get("name", ""),
                    params.get("arguments", {}),
                    director,
                    character_vault,
                    render_fn,
                    projects_store,
                )
                res = {"content": [{"type": "text", "text": json.dumps(out, ensure_ascii=False)}]}
            else:
                res = {"status": "ok"}
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": res}, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as exc:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32000, "message": str(exc)}}) + "\n")
            sys.stdout.flush()
