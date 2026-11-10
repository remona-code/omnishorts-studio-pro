"""
OmniShorts Studio — Multi-Mode 9:16 Video & Viral Template Render Engine
Supports:
1. Cinematic Story / Idea2Video / Novel2Video (ViMax + OpenMontage + Pixelle-Video + MoneyPrinterTurbo)
2. Viral Reddit Story Card + Rapid Karaoke (PurffleShorts)
3. Fake Chat / iMessage Dark Animated Conversation (PurffleShorts)
4. Viral Quiz / Trivia Countdown & Reveal
5. Long-to-Shorts 16:9 -> 9:16 Smart Speaker Tracking & Split-Screen Podcast Clipper (AutoClip + OpenShorts)
"""
import math
import os
import subprocess
import time
import textwrap
from typing import Dict, List, Tuple, Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

from backend.models import (
    ProjectConfig,
    SceneItem,
    RedditCardConfig,
    ChatConfig,
    QuizConfig,
    ClipperSegment,
)
from backend.audio_engine import (
    build_project_master_audio,
    compute_word_timings,
    synthesize_speech_prosody,
    synthesize_sfx,
    synthesize_bgm,
    write_wav_file,
    SAMPLE_RATE,
)
from backend.subtitle_engine import generate_ass_subtitles


BASE_DIR = "/home/antigravity/omnishorts-studio"
ASSETS_IMG_DIR = os.path.join(BASE_DIR, "assets/images")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

FONT_BOLD_PATH = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Bold.ttf"
FONT_REG_PATH = "/usr/share/fonts/truetype/roboto/unhinted/RobotoTTF/Roboto-Regular.ttf"
FONT_FALLBACK_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [FONT_BOLD_PATH, FONT_FALLBACK_BOLD] if bold else [FONT_REG_PATH, FONT_BOLD_PATH, FONT_FALLBACK_BOLD]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def resolve_local_image(url_or_path: str) -> str:
    if not url_or_path:
        return os.path.join(ASSETS_IMG_DIR, "scene_cyber_istanbul_2099.jpg")
    if os.path.exists(url_or_path):
        return url_or_path
    if url_or_path.startswith("/assets/images/"):
        candidate = os.path.join(BASE_DIR, url_or_path.lstrip("/"))
        if os.path.exists(candidate):
            return candidate
    basename = os.path.basename(url_or_path)
    candidate = os.path.join(ASSETS_IMG_DIR, basename)
    if os.path.exists(candidate):
        return candidate
    return os.path.join(ASSETS_IMG_DIR, "scene_cyber_istanbul_2099.jpg")


def load_and_cover_image(img_path: str, target_w: int, target_h: int) -> Image.Image:
    """Loads an image and center-crops it to cover (target_w, target_h) with high quality."""
    try:
        im = Image.open(img_path).convert("RGB")
    except Exception:
        im = Image.new("RGB", (target_w, target_h), (14, 16, 22))
    src_w, src_h = im.size
    scale = max(target_w / max(1, src_w), target_h / max(1, src_h))
    new_w = int(src_w * scale)
    new_h = int(src_h * scale)
    im = im.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return im.crop((left, top, left + target_w, top + target_h))


def apply_camera_motion(base_oversized: Image.Image, target_w: int, target_h: int, progress: float, motion: str) -> Image.Image:
    """
    Applies smooth Ken Burns camera motion from a pre-scaled oversized canvas (1.22x).
    """
    ow, oh = base_oversized.size
    p = max(0.0, min(1.0, progress))
    # Smooth ease-in-out
    ease = 0.5 - 0.5 * math.cos(math.pi * p)

    if motion == "zoom_out":
        scale = 0.84 + 0.16 * ease
        cw, ch = int(target_w * scale / 0.84), int(target_h * scale / 0.84)
        cw, ch = min(ow, cw), min(oh, ch)
        x0 = (ow - cw) // 2
        y0 = (oh - ch) // 2
        return base_oversized.crop((x0, y0, x0 + cw, y0 + ch)).resize((target_w, target_h), Image.Resampling.BILINEAR)

    if motion == "pan_right":
        max_dx = ow - target_w
        x0 = int(max_dx * ease)
        y0 = (oh - target_h) // 2
        return base_oversized.crop((x0, y0, x0 + target_w, y0 + target_h))

    if motion == "pan_left":
        max_dx = ow - target_w
        x0 = int(max_dx * (1.0 - ease))
        y0 = (oh - target_h) // 2
        return base_oversized.crop((x0, y0, x0 + target_w, y0 + target_h))

    # Default: zoom_in_slow
    zoom = 1.0 - 0.14 * ease
    cw = max(target_w, min(ow, int(ow * zoom)))
    ch = max(target_h, min(oh, int(oh * zoom)))
    x0 = (ow - cw) // 2
    y0 = (oh - ch) // 2
    return base_oversized.crop((x0, y0, x0 + cw, y0 + ch)).resize((target_w, target_h), Image.Resampling.BILINEAR)


def create_cinematic_gradient_overlay(w: int, h: int) -> Image.Image:
    """Creates a reusable RGBA dark gradient overlay at top (HUD) and bottom (Subtitle readability)."""
    arr = np.zeros((h, w, 4), dtype=np.uint8)
    y = np.linspace(0.0, 1.0, h)
    alpha = np.zeros(h, dtype=np.float32)
    # Top 18% subtle shade for broadcast header
    top_mask = y < 0.18
    alpha[top_mask] = 135.0 * (1.0 - y[top_mask] / 0.18) ** 1.6
    # Bottom 42% rich cinematic gradient for karaoke subtitles
    bot_mask = y > 0.58
    alpha[bot_mask] = 215.0 * ((y[bot_mask] - 0.58) / 0.42) ** 1.5
    arr[:, :, 0] = 6
    arr[:, :, 1] = 8
    arr[:, :, 2] = 12
    arr[:, :, 3] = np.clip(alpha, 0, 240).astype(np.uint8)[:, None]
    return Image.fromarray(arr, mode="RGBA")


def draw_broadcast_hud(draw: ImageDraw.ImageDraw, w: int, h: int, project_name: str, scene_idx: int, total_scenes: int, timecode_sec: float, mode_badge: str) -> None:
    """Draws subtle ARRI/Broadcast telemetry bar at the top of the 9:16 frame."""
    f_small = get_font(18, bold=True)
    f_mono = get_font(17, bold=False)

    # Top-left mode & continuity badge
    badge_x, badge_y = 32, 34
    draw.rounded_rectangle((badge_x, badge_y, badge_x + 235, badge_y + 34), radius=6, fill=(14, 16, 22, 205), outline=(245, 158, 11, 180), width=1)
    # Recording amber dot
    draw.ellipse((badge_x + 12, badge_y + 11, badge_x + 24, badge_y + 23), fill=(245, 158, 11, 255))
    draw.text((badge_x + 32, badge_y + 7), mode_badge[:22].upper(), font=f_small, fill=(244, 244, 246, 255))

    # Top-right timecode & scene counter
    mins = int(timecode_sec) // 60
    secs = int(timecode_sec) % 60
    frames = int((timecode_sec - int(timecode_sec)) * 24)
    tc_str = f"TC 00:{mins:02d}:{secs:02d}:{frames:02d}  •  S{scene_idx}/{total_scenes}"
    draw.rounded_rectangle((w - 285, badge_y, w - 32, badge_y + 34), radius=6, fill=(14, 16, 22, 205), outline=(63, 68, 82, 160), width=1)
    draw.text((w - 270, badge_y + 7), tc_str, font=f_mono, fill=(161, 168, 184, 255))


def build_reddit_card_overlay(w: int, h: int, cfg: RedditCardConfig) -> Image.Image:
    """Renders a crisp transparent RGBA overlay containing an authentic Reddit Story Card."""
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    card_x0, card_y0 = 42, 310
    card_x1, card_y1 = w - 42, 790

    # Drop shadow
    draw.rounded_rectangle((card_x0 + 6, card_y0 + 10, card_x1 + 6, card_y1 + 10), radius=24, fill=(0, 0, 0, 165))
    # Main dark slate card with subtle warm orange/amber accent border
    draw.rounded_rectangle((card_x0, card_y0, card_x1, card_y1), radius=24, fill=(18, 20, 26, 248), outline=(255, 87, 34, 220), width=3)

    # Subreddit avatar circle
    av_x, av_y = card_x0 + 28, card_y0 + 28
    draw.ellipse((av_x, av_y, av_x + 56, av_y + 56), fill=(255, 87, 34, 255))
    f_av = get_font(26, bold=True)
    draw.text((av_x + 15, av_y + 12), "r/", font=f_av, fill=(255, 255, 255, 255))

    # Subreddit name & author
    f_sub = get_font(23, bold=True)
    f_auth = get_font(18, bold=False)
    draw.text((av_x + 72, av_y + 4), cfg.subreddit, font=f_sub, fill=(248, 250, 252, 255))
    draw.text((av_x + 72, av_y + 33), f"{cfg.author}  •  Doğrulanmış Arşiv", font=f_auth, fill=(148, 163, 184, 255))

    # Award badges on top right of card
    badge_x = card_x1 - 135
    draw.rounded_rectangle((badge_x, av_y + 8, card_x1 - 28, av_y + 44), radius=18, fill=(245, 158, 11, 40), outline=(245, 158, 11, 210), width=2)
    draw.text((badge_x + 16, av_y + 15), f"★ {cfg.awards_count} ÖDÜL", font=get_font(17, bold=True), fill=(245, 158, 11, 255))

    # Divider line
    draw.line((card_x0 + 28, av_y + 74, card_x1 - 28, av_y + 74), fill=(45, 50, 65, 220), width=2)

    # Wrapped Post Title
    f_title = get_font(29, bold=True)
    wrapped_lines = textwrap.wrap(cfg.title, width=32)[:6]
    ty = av_y + 96
    for line in wrapped_lines:
        draw.text((card_x0 + 30, ty), line, font=f_title, fill=(248, 250, 252, 255))
        ty += 42

    # Bottom engagement pills (Upvotes & Comments)
    pill_y = card_y1 - 68
    draw.rounded_rectangle((card_x0 + 28, pill_y, card_x0 + 195, pill_y + 44), radius=22, fill=(30, 34, 45, 255), outline=(255, 87, 34, 180), width=2)
    draw.text((card_x0 + 48, pill_y + 10), f"▲ {cfg.upvotes}", font=get_font(20, bold=True), fill=(255, 87, 34, 255))

    draw.rounded_rectangle((card_x0 + 212, pill_y, card_x0 + 390, pill_y + 44), radius=22, fill=(30, 34, 45, 255), outline=(71, 85, 105, 180), width=1)
    draw.text((card_x0 + 232, pill_y + 10), f"💬 {cfg.comments} yorum", font=get_font(19, bold=True), fill=(226, 232, 240, 255))

    return overlay


def render_chat_frame(
    bg_img: Image.Image,
    cfg: ChatConfig,
    visible_messages: List[Tuple[int, float]],
    show_typing: bool,
    timecode_sec: float,
) -> Image.Image:
    """
    Renders a single 9:16 frame for Fake Chat / Messaging Story mode (PurffleShorts).
    visible_messages is a list of (msg_index, pop_progress_0_to_1).
    """
    w, h = bg_img.size
    frame = bg_img.copy()
    # Darken background so chat UI pops with cinema clarity
    enhancer = ImageEnhance.Brightness(frame)
    frame = enhancer.enhance(0.32).convert("RGBA")

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Top glass contact header
    draw.rounded_rectangle((28, 42, w - 28, 152), radius=22, fill=(18, 21, 28, 240), outline=(55, 65, 81, 200), width=2)
    # Contact Avatar
    draw.ellipse((50, 62, 118, 130), fill=(245, 158, 11, 255))
    draw.text((73, 76), "29", font=get_font(28, bold=True), fill=(10, 12, 16, 255))
    # Contact Name & Online Status
    draw.text((138, 66), cfg.contact_name, font=get_font(25, bold=True), fill=(248, 250, 252, 255))
    draw.ellipse((140, 106, 152, 118), fill=(16, 185, 129, 255))
    draw.text((160, 100), cfg.contact_status, font=get_font(18, bold=False), fill=(16, 185, 129, 255))

    # Draw visible message bubbles
    cursor_y = 190
    f_msg = get_font(24, bold=False)
    f_meta = get_font(15, bold=False)

    for msg_idx, pop_p in visible_messages:
        msg = cfg.messages[msg_idx]
        lines = textwrap.wrap(msg.text, width=28)[:4]
        box_h = 36 + len(lines) * 32 + 24
        box_w = min(w - 130, max(240, max(len(ln) for ln in lines) * 15 + 52))

        # Slide-up micro-animation on entrance
        y_offset = int((1.0 - min(1.0, pop_p * 3.0)) * 18)
        by0 = cursor_y + y_offset
        by1 = by0 + box_h

        if msg.sender == "me":
            bx1 = w - 36
            bx0 = bx1 - box_w
            bubble_fill = (16, 124, 92, 245)
            border_col = (16, 185, 129, 220)
            text_col = (248, 250, 252, 255)
        else:
            bx0 = 36
            bx1 = bx0 + box_w
            bubble_fill = (28, 32, 42, 245)
            border_col = (71, 85, 105, 200)
            text_col = (241, 245, 249, 255)

        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=22, fill=bubble_fill, outline=border_col, width=2)
        ty = by0 + 18
        for ln in lines:
            draw.text((bx0 + 22, ty), ln, font=f_msg, fill=text_col)
            ty += 32

        meta_txt = f"{msg.sender_name} • {msg.timestamp_label}" + (" ✓✓" if msg.sender == "me" else "")
        draw.text((bx0 + 22, by1 - 24), meta_txt, font=f_meta, fill=(165, 180, 198, 220))
        cursor_y += box_h + 20

    if show_typing and cursor_y < h - 220:
        draw.rounded_rectangle((36, cursor_y, 160, cursor_y + 52), radius=22, fill=(28, 32, 42, 230), outline=(245, 158, 11, 180), width=2)
        dots = "•  •  •" if int(timecode_sec * 4) % 2 == 0 else "◦  •  ◦"
        draw.text((66, cursor_y + 12), dots, font=get_font(24, bold=True), fill=(245, 158, 11, 255))

    return Image.alpha_composite(frame, overlay).convert("RGB")


def render_quiz_frame(
    bg_img: Image.Image,
    cfg: QuizConfig,
    elapsed_sec: float,
    total_sec: float,
) -> Image.Image:
    """
    Renders a single 9:16 frame for Viral Quiz / Trivia Countdown & Reveal mode.
    """
    w, h = bg_img.size
    frame = ImageEnhance.Brightness(bg_img.copy()).enhance(0.38).convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    is_reveal = elapsed_sec >= cfg.think_duration_sec

    # Top category header
    draw.rounded_rectangle((42, 60, w - 42, 122), radius=16, fill=(245, 158, 11, 240))
    draw.text((68, 76), f"⚡ {cfg.category}", font=get_font(24, bold=True), fill=(10, 12, 16, 255))

    # Question Card
    draw.rounded_rectangle((42, 148, w - 42, 410), radius=24, fill=(18, 21, 28, 245), outline=(71, 85, 105, 220), width=2)
    q_lines = textwrap.wrap(cfg.question, width=28)[:5]
    qy = 178
    for ln in q_lines:
        draw.text((68, qy), ln, font=get_font(28, bold=True), fill=(248, 250, 252, 255))
        qy += 42

    # Countdown Progress Bar
    bar_y = 436
    draw.rounded_rectangle((42, bar_y, w - 42, bar_y + 28), radius=14, fill=(30, 35, 46, 240))
    if not is_reveal:
        rem_ratio = max(0.0, min(1.0, 1.0 - (elapsed_sec / max(0.1, cfg.think_duration_sec))))
        fill_w = int((w - 84) * rem_ratio)
        if fill_w > 12:
            draw.rounded_rectangle((42, bar_y, 42 + fill_w, bar_y + 28), radius=14, fill=(245, 158, 11, 255))
    else:
        draw.rounded_rectangle((42, bar_y, w - 42, bar_y + 28), radius=14, fill=(16, 185, 129, 255))

    # Options A, B, C
    opt_y = 495
    for opt in cfg.options:
        if is_reveal and opt.is_correct:
            bg_c = (16, 124, 92, 248)
            out_c = (16, 185, 129, 255)
            badge_c = (16, 185, 129, 255)
            suffix = "  ✓ DOĞRU CEVAP"
        elif is_reveal:
            bg_c = (22, 25, 34, 180)
            out_c = (51, 65, 85, 140)
            badge_c = (71, 85, 105, 200)
            suffix = ""
        else:
            bg_c = (24, 28, 38, 242)
            out_c = (100, 116, 139, 210)
            badge_c = (245, 158, 11, 255)
            suffix = ""

        draw.rounded_rectangle((42, opt_y, w - 42, opt_y + 92), radius=20, fill=bg_c, outline=out_c, width=3)
        draw.ellipse((64, opt_y + 18, 120, opt_y + 74), fill=badge_c)
        draw.text((82, opt_y + 28), opt.label, font=get_font(28, bold=True), fill=(10, 12, 16, 255))
        draw.text((142, opt_y + 28), f"{opt.text}{suffix}", font=get_font(25, bold=True), fill=(248, 250, 252, 255))
        opt_y += 114

    # Explanation Card during Reveal
    if is_reveal:
        draw.rounded_rectangle((42, 855, w - 42, 1020), radius=20, fill=(14, 38, 32, 245), outline=(16, 185, 129, 220), width=2)
        exp_lines = textwrap.wrap(cfg.explanation, width=34)[:3]
        ey = 878
        for ln in exp_lines:
            draw.text((66, ey), ln, font=get_font(22, bold=False), fill=(236, 253, 245, 255))
            ey += 34

    return Image.alpha_composite(frame, overlay).convert("RGB")


def ensure_source_longform_video() -> str:
    """
    Generates a genuine 16:9 widescreen (1280x720) broadcast podcast source video
    from source_longform_podcast_studio.jpg if it doesn't already exist, so that
    Long-to-Shorts Smart Clipper (AutoClip / OpenShorts) can inspect and crop a real 16:9 MP4.
    """
    out_path = os.path.join(OUTPUT_DIR, "videos", "source_podcast_16_9.mp4")
    if os.path.exists(out_path) and os.path.getsize(out_path) > 20000:
        return out_path

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    src_img_path = resolve_local_image("source_longform_podcast_studio.jpg")
    base_16_9 = load_and_cover_image(src_img_path, 1280, 720)

    duration_sec = 8.0
    fps = 24
    total_frames = int(duration_sec * fps)

    # Create podcast speech audio
    podcast_text = (
        "Yapay zeka ajanları artık sadece metin yazmıyor, "
        "karakter sürekliliğini koruyarak uçtan uca sinematik kurgu ve ses tasarımı yapıyor! "
        "Geleceğin medya stüdyosu tam olarak bu hibrit mimaridir."
    )
    words = compute_word_timings(podcast_text, start_offset_ms=150, target_duration_sec=duration_sec)
    voice_sig, _ = synthesize_speech_prosody(words, duration_sec, voice_id="narrator_deep")
    bgm_sig = synthesize_bgm("cyberpunk_pulse", duration_sec) * 0.14
    wav_path = os.path.join(OUTPUT_DIR, "videos", "temp_podcast_16_9.wav")
    write_wav_file(wav_path, voice_sig + bgm_sig)

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", "1280x720", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-i", wav_path,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest",
        out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    f_hud = get_font(20, bold=True)
    for f_idx in range(total_frames):
        t_sec = f_idx / fps
        frame = base_16_9.copy()
        draw = ImageDraw.Draw(frame)
        # Active speaker indicator (Left speaker 0-4.2s, Right speaker 4.2-8.0s)
        is_left = t_sec < 4.2
        box_x = 180 if is_left else 780
        speaker_label = "KONUŞMACI 1: Dr. Kaelen (Sol Kamera)" if is_left else "KONUŞMACI 2: Dr. Elena (Sağ Kamera)"
        draw.rounded_rectangle((36, 636, 620, 686), radius=10, fill=(12, 14, 18))
        draw.text((54, 650), f"CANLI YAYIN 16:9  •  {speaker_label}", font=f_hud, fill=(245, 158, 11))
        # Subtle face/speaker tracker target box preview
        draw.rounded_rectangle((box_x, 120, box_x + 310, 520), radius=12, outline=(16, 185, 129), width=2)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    return out_path


def render_clipper_frame(
    src_16_9: Image.Image,
    target_w: int,
    target_h: int,
    t_sec: float,
    total_sec: float,
    crop_mode: str,
    virality_score: int,
) -> Image.Image:
    """
    Implements OpenShorts / AutoClip 9:16 Smart Face/Speaker Tracking Crop & Split-Screen Podcast Layout!
    """
    sw, sh = src_16_9.size  # e.g., 1280x720

    if crop_mode == "split_screen_podcast":
        # Top half: Left Speaker close-up; Bottom half: Right Speaker close-up + Middle telemetry waveform bar
        half_h = target_h // 2
        left_crop = src_16_9.crop((80, 40, 620, 680)).resize((target_w, half_h), Image.Resampling.BILINEAR)
        right_crop = src_16_9.crop((640, 40, 1180, 680)).resize((target_w, half_h), Image.Resampling.BILINEAR)
        canvas = Image.new("RGB", (target_w, target_h))
        canvas.paste(left_crop, (0, 0))
        canvas.paste(right_crop, (0, half_h))
        draw = ImageDraw.Draw(canvas)
        # Center divider with animated audio equalizer bars
        draw.rectangle((0, half_h - 18, target_w, half_h + 18), fill=(12, 14, 20))
        draw.line((0, half_h - 18, target_w, half_h - 18), fill=(245, 158, 11), width=2)
        draw.line((0, half_h + 18, target_w, half_h + 18), fill=(16, 185, 129), width=2)
        draw.text((28, half_h - 11), f"OPENSHORTS AI SPLIT-CROP  •  VİRAL SKOR: {virality_score}/100", font=get_font(16, bold=True), fill=(245, 158, 11))
        return canvas

    # Default: smart_speaker_track (Smoothly pans 9:16 crop window from Speaker 1 on left to Speaker 2 on right)
    crop_h = sh
    crop_w = int(crop_h * (target_w / target_h))  # 720 * 9 / 16 = 405
    # Speaker 1 center is around x=340; Speaker 2 center is around x=940
    # Smooth transition between t=3.6s and t=4.4s
    if t_sec < 3.6:
        cx = 340.0 + 18.0 * math.sin(t_sec * 1.5)
        active_tag = "YÜZ TAKİBİ: KONUŞMACI 1 [SOL]"
    elif t_sec > 4.4:
        cx = 930.0 + 18.0 * math.sin(t_sec * 1.5)
        active_tag = "YÜZ TAKİBİ: KONUŞMACI 2 [SAĞ]"
    else:
        p = (t_sec - 3.6) / 0.8
        ease = 0.5 - 0.5 * math.cos(math.pi * p)
        cx = 340.0 + (930.0 - 340.0) * ease
        active_tag = "AI KAMERA GEÇİŞİ (SMART PAN)"

    x0 = max(0, min(sw - crop_w, int(cx - crop_w / 2)))
    cropped = src_16_9.crop((x0, 0, x0 + crop_w, crop_h)).resize((target_w, target_h), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(cropped)
    draw.rounded_rectangle((32, 84, 420, 120), radius=8, fill=(12, 16, 22))
    draw.text((46, 93), f"🎯 {active_tag} • SKOR {virality_score}%", font=get_font(16, bold=True), fill=(16, 185, 129))
    return cropped


def generate_project_thumbnail(project: ProjectConfig, base_img: Image.Image, out_thumb_path: str) -> str:
    """
    Generates a high-click-through-rate (CTR) 9:16 viral cover thumbnail with bold hook typography.
    """
    os.makedirs(os.path.dirname(out_thumb_path), exist_ok=True)
    w, h = base_img.size
    thumb = base_img.copy().convert("RGBA")
    grad = create_cinematic_gradient_overlay(w, h)
    thumb = Image.alpha_composite(thumb, grad)
    draw = ImageDraw.Draw(thumb)

    # Top viral badge
    mode_labels = {
        "cinematic_story": "SİNEMATİK AI HİKÂYE • 2099",
        "reddit_story": "REDDİT GİZEM ARŞİVİ",
        "fake_chat": "ŞİFRELİ MESAJ KAYDI",
        "viral_quiz": "YAPAY ZEKA BİLİM TESTİ",
        "long_to_shorts": "PODCAST VİRAL KESİT",
    }
    badge_txt = mode_labels.get(project.mode, "OMNISHORTS STUDIO PRO")
    draw.rounded_rectangle((42, 64, 440, 114), radius=12, fill=(245, 158, 11, 245))
    draw.text((62, 77), badge_txt, font=get_font(22, bold=True), fill=(10, 12, 16, 255))

    # Hook Headline near bottom
    hook_title = project.name.upper()
    lines = textwrap.wrap(hook_title, width=18)[:3]
    ty = h - 340
    f_hook = get_font(48, bold=True)
    for ln in lines:
        # Black stroke outline
        for dx, dy in [(-3, -3), (3, -3), (-3, 3), (3, 3), (0, 4)]:
            draw.text((46 + dx, ty + dy), ln, font=f_hook, fill=(0, 0, 0, 255))
        draw.text((46, ty), ln, font=f_hook, fill=(255, 255, 255, 255))
        ty += 58

    thumb.convert("RGB").save(out_thumb_path, quality=92)
    return out_thumb_path


def render_project_video(project: ProjectConfig, character_vault=None) -> ProjectConfig:
    """
    Executes the full end-to-end production pipeline for a ProjectConfig:
    1. Synthesizes voiceover, word-level timestamps, Foley SFX, and sidechain-ducked BGM
    2. Generates word-level karaoke .ass subtitles
    3. Exports ComfyUI continuity workflow JSON
    4. Renders 9:16 H.264 + AAC .mp4 video via FFmpeg + libass
    5. Generates viral 9:16 cover thumbnail
    """
    t0 = time.time()
    w, h = 720, 1280
    fps = project.fps or 24

    os.makedirs(os.path.join(OUTPUT_DIR, "videos"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "thumbnails"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "subtitles"), exist_ok=True)
    os.makedirs(os.path.join(OUTPUT_DIR, "workflows"), exist_ok=True)

    wav_path = os.path.join(OUTPUT_DIR, "videos", f"{project.id}_master.wav")
    ass_path = os.path.join(OUTPUT_DIR, "subtitles", f"{project.id}.ass")
    mp4_path = os.path.join(OUTPUT_DIR, "videos", f"{project.id}.mp4")
    thumb_path = os.path.join(OUTPUT_DIR, "thumbnails", f"{project.id}_thumb.jpg")

    # Configure extra SFX events for interactive modes (Fake Chat pops, Quiz ticks & chime)
    extra_sfx: List[Tuple[float, str]] = []
    if project.mode == "fake_chat" and project.chat_config:
        t_cur = 0.25
        for msg in project.chat_config.messages:
            sfx_name = "imessage_send_pop" if msg.sender == "me" else "imessage_recv_pop"
            extra_sfx.append((t_cur, sfx_name))
            t_cur += msg.duration_sec
    elif project.mode == "viral_quiz" and project.quiz_config:
        think_s = project.quiz_config.think_duration_sec
        t_tick = 0.4
        while t_tick < think_s:
            extra_sfx.append((t_tick, "quiz_clock_tick"))
            t_tick += 0.8
        extra_sfx.append((think_s, "quiz_correct_chime"))

    voice_id = "dr_elena"
    if project.mode == "reddit_story":
        voice_id = "reddit_host"
    elif project.mode == "viral_quiz":
        voice_id = "quiz_master"
    elif project.mode == "long_to_shorts":
        voice_id = "narrator_deep"

    # Step 1: Build Master Audio & Word Timings
    build_project_master_audio(
        scenes=project.scenes,
        bgm_track=project.bgm_track,
        bgm_volume=project.bgm_volume,
        output_wav_path=wav_path,
        default_voice_id=voice_id,
        extra_sfx_events=extra_sfx,
    )

    # Step 2: Generate Word-Level Karaoke ASS Subtitles
    skip_first_sub = project.mode == "reddit_story"
    generate_ass_subtitles(
        scenes=project.scenes,
        style_key=project.subtitle_style,
        output_ass_path=ass_path,
        play_res_x=w,
        play_res_y=h,
        skip_first_scene_subtitles=skip_first_sub,
    )

    # Step 3: Export ComfyUI Continuity Workflow JSON
    if character_vault is not None:
        comfy_file = character_vault.export_comfyui_workflow(
            project.id, project.scenes, os.path.join(OUTPUT_DIR, "workflows")
        )
        project.output_comfy_url = f"/output/workflows/{os.path.basename(comfy_file)}"

    # Preload oversized scene images (1.22x for smooth Ken Burns motion)
    oversized_w, oversized_h = int(w * 1.22), int(h * 1.22)
    scene_canvases: List[Image.Image] = []
    for sc in project.scenes:
        img_p = resolve_local_image(sc.image_url)
        scene_canvases.append(load_and_cover_image(img_p, oversized_w, oversized_h))

    grad_overlay = create_cinematic_gradient_overlay(w, h)
    reddit_overlay = build_reddit_card_overlay(w, h, project.reddit_config) if (project.mode == "reddit_story" and project.reddit_config) else None

    # If long_to_shorts mode, ensure 16:9 source video exists and load 16:9 studio image
    src_16_9_img = None
    if project.mode == "long_to_shorts":
        ensure_source_longform_video()
        src_16_9_img = load_and_cover_image(resolve_local_image("source_longform_podcast_studio.jpg"), 1280, 720)

    # Step 4: Stream rendered frames into FFmpeg + burn ASS subtitles (unless fake_chat/viral_quiz where custom UI fills center)
    vf_filters = []
    if project.mode not in ("fake_chat",):
        vf_filters.append(f"ass={ass_path}")

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-i", wav_path,
    ]
    if vf_filters:
        cmd.extend(["-vf", ",".join(vf_filters)])
    cmd.extend([
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        mp4_path,
    ])

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    total_scenes = len(project.scenes)
    total_duration = sum(max(1.2, sc.duration_sec) for sc in project.scenes)
    global_time_sec = 0.0
    first_frame_saved: Optional[Image.Image] = None

    for s_idx, sc in enumerate(project.scenes):
        dur = max(1.2, sc.duration_sec)
        n_frames = max(1, int(round(dur * fps)))
        base_canvas = scene_canvases[s_idx]

        for f_i in range(n_frames):
            local_p = f_i / max(1, n_frames - 1)

            if project.mode == "long_to_shorts" and src_16_9_img is not None:
                crop_mode = project.clipper_segment.crop_mode if project.clipper_segment else "smart_speaker_track"
                v_score = project.clipper_segment.virality_score if project.clipper_segment else 96
                frame_rgb = render_clipper_frame(src_16_9_img, w, h, global_time_sec, total_duration, crop_mode, v_score)
                frame_rgba = Image.alpha_composite(frame_rgb.convert("RGBA"), grad_overlay)
                draw = ImageDraw.Draw(frame_rgba)
                draw_broadcast_hud(draw, w, h, project.name, s_idx + 1, total_scenes, global_time_sec, "AUTOCLIP 9:16 AI")
                final_frame = frame_rgba.convert("RGB")

            elif project.mode == "fake_chat" and project.chat_config is not None:
                bg_frame = apply_camera_motion(base_canvas, w, h, local_p, "zoom_in_slow")
                # Determine which messages are visible at global_time_sec
                vis_msgs = []
                msg_cursor = 0.20
                show_typing = False
                for m_idx, m_item in enumerate(project.chat_config.messages):
                    if global_time_sec >= msg_cursor:
                        pop_p = (global_time_sec - msg_cursor) / max(0.2, m_item.duration_sec)
                        vis_msgs.append((m_idx, pop_p))
                    elif global_time_sec >= msg_cursor - 0.35:
                        show_typing = True
                    msg_cursor += m_item.duration_sec
                final_frame = render_chat_frame(bg_frame, project.chat_config, vis_msgs, show_typing, global_time_sec)

            elif project.mode == "viral_quiz" and project.quiz_config is not None:
                bg_frame = apply_camera_motion(base_canvas, w, h, local_p, sc.camera_motion)
                final_frame = render_quiz_frame(bg_frame, project.quiz_config, global_time_sec, total_duration)

            else:
                # Cinematic Story or Reddit Story
                moved = apply_camera_motion(base_canvas, w, h, local_p, sc.camera_motion)
                # Smooth crossfade during last 0.25s of scene into next scene
                if s_idx + 1 < total_scenes and (dur - f_i / fps) < 0.25:
                    fade_alpha = 1.0 - max(0.0, (dur - f_i / fps) / 0.25)
                    next_moved = apply_camera_motion(scene_canvases[s_idx + 1], w, h, 0.0, project.scenes[s_idx + 1].camera_motion)
                    moved = Image.blend(moved, next_moved, fade_alpha)

                frame_rgba = Image.alpha_composite(moved.convert("RGBA"), grad_overlay)
                if project.mode == "reddit_story" and s_idx == 0 and reddit_overlay is not None:
                    frame_rgba = Image.alpha_composite(frame_rgba, reddit_overlay)

                draw = ImageDraw.Draw(frame_rgba)
                badge_label = "REDDIT VIRAL STORY" if project.mode == "reddit_story" else f"{project.workflow_source} • DNA LOCK"
                draw_broadcast_hud(draw, w, h, project.name, s_idx + 1, total_scenes, global_time_sec, badge_label)
                final_frame = frame_rgba.convert("RGB")

            if first_frame_saved is None and f_i == min(5, n_frames - 1):
                first_frame_saved = final_frame.copy()

            proc.stdin.write(final_frame.tobytes())
            global_time_sec += 1.0 / fps

    proc.stdin.close()
    stderr_bytes = proc.stderr.read() if proc.stderr else b""
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg render failed: {stderr_bytes.decode('utf-8', errors='ignore')[-500:]}")

    # Step 5: Generate Viral Cover Thumbnail
    thumb_source = first_frame_saved if first_frame_saved is not None else load_and_cover_image(resolve_local_image(project.scenes[0].image_url), w, h)
    generate_project_thumbnail(project, thumb_source, thumb_path)

    project.output_video_url = f"/output/videos/{os.path.basename(mp4_path)}"
    project.output_thumbnail_url = f"/output/thumbnails/{os.path.basename(thumb_path)}"
    project.output_subtitle_url = f"/output/subtitles/{os.path.basename(ass_path)}"
    project.render_time_sec = round(time.time() - t0, 2)
    project.status = "completed"
    return project
