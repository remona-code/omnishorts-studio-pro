"""
OmniShorts Studio — FastAPI Production Backend & REST / MCP API Server
"""
import os
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.models import (
    ProjectConfig,
    GenerateProjectRequest,
    CharacterProfile,
    AutopilotTask,
)
from backend.character_vault import CharacterVault
from backend.agents_engine import (
    MultiAgentDirector,
    PROVIDER_HUB_REGISTRY,
    PROJECT_BENCHMARK_MATRIX,
    get_default_autopilot_tasks,
)
from backend.subtitle_engine import SUBTITLE_PRESETS
from backend.render_engine import render_project_video, ensure_source_longform_video
from backend.mcp_server import MCP_TOOLS_SPEC, handle_mcp_tool_call


BASE_DIR = "/home/antigravity/omnishorts-studio"
STATIC_DIR = os.path.join(BASE_DIR, "static")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

app = FastAPI(
    title="OmniShorts Studio Pro API",
    description="Unified Multi-Agent AI Shorts, Storyboard Continuity, Viral Templates & Long-to-Shorts Production Engine",
    version="2.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

character_vault = CharacterVault()
director = MultiAgentDirector(character_vault)
PROJECTS_STORE: Dict[str, ProjectConfig] = {}
AUTOPILOT_STORE: List[AutopilotTask] = get_default_autopilot_tasks()


def seed_showcase_projects() -> None:
    """
    Pre-generates and renders all 5 flagship production modes on startup if not already cached,
    so the Studio has real, playable 9:16 H.264+AAC MP4 videos ready immediately.
    """
    if PROJECTS_STORE:
        return

    ensure_source_longform_video()

    showcase_specs = [
        GenerateProjectRequest(
            name="2099 İstanbul: Kuantum Arşivi & Monolit",
            mode="cinematic_story",
            workflow_source="Idea2Video",
            topic_or_input="2099 yılında İstanbul Boğazı'nın altında uyanan kuantum arşiv ve Anadolu dağlarındaki dev güneş halkası",
            subtitle_style="hormozi_gold",
            bgm_track="cyberpunk_pulse",
            character_ids=["char_elena", "char_kael"],
        ),
        GenerateProjectRequest(
            name="Reddit Viral: Boğaz'daki 2099 Zaman Kapsülü",
            mode="reddit_story",
            workflow_source="Template2Video",
            topic_or_input="2099 yılında İstanbul Boğazı'nın dibinde bulduğumuz kuantum kayıt cihazı neden tam bugünün tarihini gösteriyordu?",
            subtitle_style="reddit_rapid",
            bgm_track="kinetic_synthwave",
        ),
        GenerateProjectRequest(
            name="Şifreli Mesaj: 03:14 Boğaz Ekspresi",
            mode="fake_chat",
            workflow_source="Template2Video",
            topic_or_input="Gelecekteki kuantum yedek bilincinden gelen 03:14 Boğaz Ekspresi uyarısı",
            subtitle_style="tiktok_clean",
            bgm_track="dark_tension_drone",
        ),
        GenerateProjectRequest(
            name="Bilim Testi: Güneş Fotonu Kaç Yılda Çıkar?",
            mode="viral_quiz",
            workflow_source="Template2Video",
            topic_or_input="Bir ışık fotonunun Güneş'in çekirdeğinden yüzeyine çıkması ortalama ne kadar sürer?",
            subtitle_style="mrbeast_cyan",
            bgm_track="cyberpunk_pulse",
        ),
        GenerateProjectRequest(
            name="AutoClip 9:16: AI Ajanları ve Hibrit Sinema",
            mode="long_to_shorts",
            workflow_source="Clip2Shorts",
            topic_or_input="smart_speaker_track",
            subtitle_style="hormozi_gold",
            bgm_track="lofi_story_chill",
        ),
    ]

    fixed_ids = [
        "proj_cinematic_2099",
        "proj_reddit_kapsul",
        "proj_chat_0314",
        "proj_quiz_foton",
        "proj_autoclip_podcast",
    ]

    for fixed_id, req in zip(fixed_ids, showcase_specs):
        proj = director.run_agent_pipeline(req)
        proj.id = fixed_id
        mp4_file = os.path.join(OUTPUT_DIR, "videos", f"{fixed_id}.mp4")
        thumb_file = os.path.join(OUTPUT_DIR, "thumbnails", f"{fixed_id}_thumb.jpg")
        if os.path.exists(mp4_file) and os.path.getsize(mp4_file) > 15000 and os.path.exists(thumb_file):
            proj.output_video_url = f"/output/videos/{fixed_id}.mp4"
            proj.output_thumbnail_url = f"/output/thumbnails/{fixed_id}_thumb.jpg"
            proj.output_subtitle_url = f"/output/subtitles/{fixed_id}.ass"
            proj.output_comfy_url = f"/output/workflows/{fixed_id}_comfyui_workflow.json"
            proj.render_time_sec = 1.85
            proj.status = "completed"
        else:
            proj = render_project_video(proj, character_vault)
        PROJECTS_STORE[proj.id] = proj


@app.on_event("startup")
def on_startup() -> None:
    seed_showcase_projects()


@app.get("/api/bootstrap")
def get_bootstrap() -> Dict[str, Any]:
    seed_showcase_projects()
    return {
        "projects": [p.dict() for p in PROJECTS_STORE.values()],
        "characters": [c.dict() for c in character_vault.list_characters()],
        "subtitle_presets": SUBTITLE_PRESETS,
        "provider_hub": PROVIDER_HUB_REGISTRY,
        "benchmark_matrix": PROJECT_BENCHMARK_MATRIX,
        "autopilot_tasks": [t.dict() for t in AUTOPILOT_STORE],
        "mcp_tools": MCP_TOOLS_SPEC,
        "source_longform_video_url": "/output/videos/source_podcast_16_9.mp4",
    }


@app.post("/api/projects/generate")
def api_generate_project(req: GenerateProjectRequest) -> Dict[str, Any]:
    proj = director.run_agent_pipeline(req)
    if req.auto_render:
        proj = render_project_video(proj, character_vault)
    PROJECTS_STORE[proj.id] = proj
    return {"status": "ok", "project": proj.dict()}


@app.put("/api/projects/{project_id}")
def api_update_project(project_id: str, updated: ProjectConfig) -> Dict[str, Any]:
    if project_id not in PROJECTS_STORE:
        raise HTTPException(status_code=404, detail="Project not found")
    updated.id = project_id
    updated = render_project_video(updated, character_vault)
    PROJECTS_STORE[project_id] = updated
    return {"status": "ok", "project": updated.dict()}


@app.post("/api/projects/{project_id}/render")
def api_rerender_project(project_id: str, payload: Dict[str, Any] = None) -> Dict[str, Any]:
    proj = PROJECTS_STORE.get(project_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if payload:
        if "subtitle_style" in payload:
            proj.subtitle_style = payload["subtitle_style"]
        if "bgm_track" in payload:
            proj.bgm_track = payload["bgm_track"]
        if "bgm_volume" in payload:
            proj.bgm_volume = float(payload["bgm_volume"])
        if "workflow_source" in payload:
            proj.workflow_source = payload["workflow_source"]
        if "crop_mode" in payload and proj.clipper_segment:
            proj.clipper_segment.crop_mode = payload["crop_mode"]
        if "scenes" in payload and isinstance(payload["scenes"], list):
            for idx, sc_data in enumerate(payload["scenes"]):
                if idx < len(proj.scenes):
                    proj.scenes[idx].narration = sc_data.get("narration", proj.scenes[idx].narration)
                    proj.scenes[idx].visual_prompt = sc_data.get("visual_prompt", proj.scenes[idx].visual_prompt)
                    proj.scenes[idx].camera_motion = sc_data.get("camera_motion", proj.scenes[idx].camera_motion)
                    proj.scenes[idx].duration_sec = float(sc_data.get("duration_sec", proj.scenes[idx].duration_sec))
                    proj.scenes[idx].words = []  # Recompute word timings on render

    proj = render_project_video(proj, character_vault)
    PROJECTS_STORE[project_id] = proj
    return {"status": "ok", "project": proj.dict()}


@app.post("/api/characters")
def api_upsert_character(profile: CharacterProfile) -> Dict[str, Any]:
    saved = character_vault.upsert_character(profile)
    return {"status": "ok", "character": saved.dict(), "characters": [c.dict() for c in character_vault.list_characters()]}


@app.post("/api/autopilot")
def api_create_autopilot(task: AutopilotTask) -> Dict[str, Any]:
    AUTOPILOT_STORE.insert(0, task)
    return {"status": "ok", "autopilot_tasks": [t.dict() for t in AUTOPILOT_STORE]}


@app.post("/api/mcp/call")
def api_mcp_call(payload: Dict[str, Any]) -> Dict[str, Any]:
    tool_name = payload.get("name", "")
    arguments = payload.get("arguments", {})
    result = handle_mcp_tool_call(
        tool_name=tool_name,
        arguments=arguments,
        director=director,
        character_vault=character_vault,
        render_fn=render_project_video,
        projects_store=PROJECTS_STORE,
    )
    return {"status": "ok", "result": result, "projects": [p.dict() for p in PROJECTS_STORE.values()]}


app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
