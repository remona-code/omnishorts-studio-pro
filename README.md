# OmniShorts Studio Pro (v2.6 Hybrid NLE + MCP)

**OmniShorts Studio Pro**, GitHub'daki en popüler 18 açık kaynak AI Shorts ve video üretim projesinin (*MoneyPrinterTurbo, OpenMontage, Pixelle-Video, ViMax, Toonflow, MoneyPrinter, NarratoAI, MoneyPrinterV2, PurffleShorts, short-video-maker, ShortGPT, Video Autopilot, AutoClip, OpenShorts, AI YouTube Shorts Generator, FunClip, Huobao Drama, waoowaoo*) tüm güçlü yönlerini tek bir profesyonel mimaride birleştiren ve her birinin eksiklerini gideren uçtan uca AI video prodüksiyon sistemidir.

---

## Temel Yetenekler ve 18 Projeye Göre Üstünlükleri

1. **5-Ajanlı Otonom Yönetmen İş Akışı (`OpenMontage` + `MoneyPrinterTurbo`++)**:
   - **1. Research Agent**: Konu, merak boşluğu (curiosity gap) ve trend analizi.
   - **2. Viral Hook & Script Agent**: İlk 3 saniye kancası, `Idea2Video`, `Script2Video`, `Novel2Video` senaryo bölümleme.
   - **3. Character & Storyboard Agent**: `CharacterVault` üzerinden sahneler arası %100 yüz, kıyafet ve seed sürekliliği.
   - **4. Audio, Prosody & Foley Agent**: Milisaniyelik kelime zamanlamaları (`WordTiming`), geçiş ses efektleri (`whoosh`, `sub_bass_impact`, `imessage_pop`, `quiz_chime`) ve konuşma sırasında müziği otomatik kısan **-14dB Sidechain Ducking**.
   - **5. Virality Critic Agent**: Kanca gücü, kelime hızı (WPM) ve tutundurma (retention) puanlaması.

2. **Karakter Kasası & Sahne Sürekliliği (`ViMax` + `Toonflow` + `Huobao Drama`++)**:
   - Her karakter için sabit `dna_prompt`, `wardrobe_prompt`, deterministik `seed`, `ip_adapter_weight` ve `lora_model` kilidi.
   - *Huobao Drama* (`CC BY-NC-SA 4.0`) ve *waoowaoo* (`Elastic 2.0`) projelerindeki ticari kısıtlamalar yerine **%100 MIT Lisansı** ile engelsiz ticari kullanım.

3. **5 Farklı Üretim ve Viral Şablon Motoru (`PurffleShorts` + `NarratoAI`++)**:
   - `cinematic_story`: Ken Burns (`zoom_in_slow`, `pan_right`, `zoom_out`, `pan_left`) kamera hareketleri, ARRI renk katmanı, yayın HUD telemetrisi ve ASS Karaoke altyazı.
   - `reddit_story`: Gerçekçi **Reddit Gönderi Kartı** (Subreddit rozeti, ödüller, beğeni/yorum sayaçları) + yüksek hızlı kinetik arka plan ve hızlı kelime-kelime altyazı.
   - `fake_chat`: **iMessage / WhatsApp Koyu Tema** animasyonlu sohbet balonları, "yazıyor..." (`• • •`) göstergesi, iki ayrı konuşmacı sesi ve bildirim ses efektleri.
   - `viral_quiz`: **Bilim/Genel Kültür Testi** kartı, 3 şık (`A`, `B`, `C`), animasyonlu geri sayım çubuğu, saat tıkırtısı ve doğru cevap açıklaması.
   - `long_to_shorts`: **16:9 → 9:16 Akıllı Konuşmacı Yüz Takibi (`smart_speaker_track`)** ve **İkili Bölünmüş Podcast Ekranı (`split_screen_podcast`)** (`AutoClip` + `OpenShorts` + `FunClip`).

4. **Kelime Düzeyinde Dinamik ASS Karaoke Altyazı Motoru (`short-video-maker` + `ShortGPT`++)**:
   - FFmpeg `libass` üzerinden milisaniye hassasiyetinde aktif kelime renk değişimi ve `%112` ölçek büyütme (pop) animasyonu.
   - 6 hazır viral stil: `hormozi_gold`, `mrbeast_cyan`, `tiktok_clean`, `cinema_minimal`, `reddit_rapid`, `neon_cyber`.

5. **Hibrit AI & Yerel ComfyUI Düğüm Grafiği (`Pixelle-Video` + `MoneyPrinter`++)**:
   - Sıfır API maliyetiyle yerel çalışma + her proje için otomatik `_comfyui_workflow.json` (IP-Adapter + KSampler + Tiled VAE düşük VRAM) dışa aktarımı.

6. **Kanal Autopilot, CLI ve MCP Ajan Sunucusu (`MoneyPrinterV2` + `Video Autopilot` + `short-video-maker`)**:
   - Standart JSON-RPC 2.0 **MCP Sunucusu** (`stdio` ve `/api/mcp/call`), **FastAPI REST API**, **CLI (`cli.py`)** ve **Docker** kurulumu.

---

## Hızlı Başlangıç

### 1. Web Stüdyosunu Başlatma
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8080
```

### 2. Komut Satırı (CLI) Kullanımı
```bash
# Sıfırdan Sinematik AI Short üretimi
python3 cli.py render --mode cinematic_story --workflow Idea2Video --topic "2099 İstanbul Kuantum Arşivi"

# Reddit Viral Hikâye Kartı üretimi
python3 cli.py render --mode reddit_story --topic "Boğaz'ın altında bulunan 2099 tarihli kara kutu"

# Sahte Mesajlaşma (Fake Chat) videosu üretimi
python3 cli.py render --mode fake_chat --topic "03:14 Boğaz Ekspresi şifreli uyarı"

# 18 Açık Kaynak Proje Karşılaştırma Matrisi
python3 cli.py benchmark

# MCP (Model Context Protocol) Stdio Sunucusu
python3 cli.py mcp-stdio
```
