"""
OmniShorts Studio — Core Data Models & Schemas
Combines the best capabilities of all 18 open-source AI video projects:
MoneyPrinterTurbo, OpenMontage, Pixelle-Video, ViMax, Toonflow, MoneyPrinter,
NarratoAI, MoneyPrinterV2, PurffleShorts, short-video-maker, ShortGPT,
Video Autopilot, AutoClip, OpenShorts, AI YouTube Shorts Generator, FunClip,
Huobao Drama, and waoowaoo (under a clean commercial-friendly MIT architecture).
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class WordTiming(BaseModel):
    word: str
    start_ms: int
    end_ms: int
    emphasis: bool = False


class CharacterProfile(BaseModel):
    id: str
    name: str
    role: str
    archetype: str = "Protagonist"
    avatar_url: str
    dna_prompt: str = Field(..., description="Immutable visual identity descriptor injected into every scene")
    wardrobe_prompt: str = Field(default="", description="Consistent outfit and styling tags")
    negative_prompt: str = Field(default="deformed, blurry, inconsistent face, extra limbs, watermark, bad anatomy")
    seed: int = 4202026
    ip_adapter_weight: float = 0.85
    lora_model: str = "omnishorts-char-consistency-v2.safetensors"
    voice_id: str = "dr_elena"
    voice_pitch: float = 1.0
    voice_speed: float = 1.0


class ChatMessageItem(BaseModel):
    sender: str  # "me" or "them"
    sender_name: str
    text: str
    timestamp_label: str = "03:14"
    duration_sec: float = 2.4


class QuizOptionItem(BaseModel):
    label: str  # "A", "B", "C"
    text: str
    is_correct: bool = False


class SceneItem(BaseModel):
    id: str
    index: int
    title: str
    narration: str
    visual_prompt: str
    image_url: str
    duration_sec: float = 3.5
    camera_motion: str = "zoom_in_slow"  # zoom_in_slow, zoom_out, pan_right, pan_left, static_focus
    transition: str = "crossfade"
    character_ids: List[str] = []
    sfx_cue: str = "whoosh_transition"  # whoosh_transition, cinematic_riser, sub_bass_impact, none
    words: List[WordTiming] = []


class RedditCardConfig(BaseModel):
    subreddit: str = "r/GelecekArsivi"
    author: str = "u/KuantumGozlemcisi"
    title: str = "2099 yılında İstanbul Boğazı'nın altında bulduğumuz kuantum kayıt cihazı neden bugünün tarihini gösteriyordu?"
    upvotes: str = "42.8k"
    comments: str = "3.9k"
    awards_count: int = 5
    intro_duration_sec: float = 3.2


class ChatConfig(BaseModel):
    contact_name: str = "Bilinmeyen Numara (2099)"
    contact_status: str = "çevrimiçi • şifreli kanal"
    platform_style: str = "imessage_dark"  # imessage_dark, whatsapp_dark
    messages: List[ChatMessageItem] = []


class QuizConfig(BaseModel):
    category: str = "YAPAY ZEKA & BİLİM TESTİ"
    question: str = "Bir ışık fotonunun Güneş'in çekirdeğinden yüzeyine çıkması ortalama ne kadar sürer?"
    options: List[QuizOptionItem] = []
    think_duration_sec: float = 3.2
    reveal_duration_sec: float = 2.4
    explanation: str = "Fotonlar yoğun plazmada milyarlarca kez saçıldığı için yüzeye ulaşması 100.000 yılı bulur!"


class ClipperSegment(BaseModel):
    id: str
    title: str
    start_sec: float
    end_sec: float
    transcript: str
    virality_score: int = 96
    hook_strength: int = 98
    retention_score: int = 94
    crop_mode: str = "smart_speaker_track"  # smart_speaker_track, split_screen_podcast, center_crop
    active_speaker_track_points: List[Dict[str, Any]] = []
    dub_language: str = "tr"


class ProjectConfig(BaseModel):
    id: str
    name: str
    mode: str = "cinematic_story"  # cinematic_story, reddit_story, fake_chat, viral_quiz, long_to_shorts
    workflow_source: str = "Idea2Video"  # Idea2Video, Script2Video, Novel2Video, Template2Video, Clip2Shorts
    topic_or_input: str
    language: str = "tr"
    aspect_ratio: str = "9:16"
    resolution: str = "720x1280"
    fps: int = 24
    subtitle_style: str = "hormozi_gold"  # hormozi_gold, mrbeast_cyan, tiktok_clean, cinema_minimal, reddit_rapid, neon_cyber
    bgm_track: str = "cyberpunk_pulse"  # cyberpunk_pulse, dark_tension_drone, lofi_story_chill, kinetic_synthwave, none
    bgm_volume: float = 0.22
    voice_provider: str = "local_neural_hybrid"  # local_neural_hybrid, edge_tts, elevenlabs, openai_tts
    llm_provider: str = "hybrid_router"  # hybrid_router, ollama_local, gemini_pro, openai_gpt4o
    visual_provider: str = "hybrid_comfy_flux"  # hybrid_comfy_flux, comfyui_local, flux_pro, kling_video, pexels_smart
    scenes: List[SceneItem] = []
    character_ids: List[str] = []
    reddit_config: Optional[RedditCardConfig] = None
    chat_config: Optional[ChatConfig] = None
    quiz_config: Optional[QuizConfig] = None
    clipper_segment: Optional[ClipperSegment] = None
    virality_metrics: Dict[str, Any] = {}
    output_video_url: Optional[str] = None
    output_thumbnail_url: Optional[str] = None
    output_subtitle_url: Optional[str] = None
    output_comfy_url: Optional[str] = None
    render_time_sec: Optional[float] = None
    status: str = "ready"


class GenerateProjectRequest(BaseModel):
    name: Optional[str] = None
    mode: str = "cinematic_story"
    workflow_source: str = "Idea2Video"
    topic_or_input: str
    language: str = "tr"
    subtitle_style: str = "hormozi_gold"
    bgm_track: str = "cyberpunk_pulse"
    character_ids: List[str] = ["char_elena"]
    auto_render: bool = True


class AutopilotTask(BaseModel):
    id: str
    channel_name: str
    platform: str  # YouTube Shorts, TikTok, Instagram Reels
    niche: str
    mode: str
    cron_schedule: str
    next_run: str
    auto_publish: bool = True
    status: str = "active"
    last_video_id: Optional[str] = None
    seo_title: str = ""
    seo_hashtags: List[str] = []
