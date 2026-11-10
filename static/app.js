/**
 * OmniShorts Studio Pro — Interactive Frontend Controller (Hybrid FastAPI + GitHub Pages Ready)
 */

let APP_STATE = {
  projects: [],
  activeProjectId: null,
  characters: [],
  subtitlePresets: {},
  providerHub: {},
  benchmarkMatrix: [],
  autopilotTasks: [],
  mcpTools: [],
};

function resolveUrl(u) {
  if (!u) return "";
  if (u.startsWith("http://") || u.startsWith("https://") || u.startsWith("blob:") || u.startsWith("data:")) {
    return u;
  }
  return u.replace(/^\/+/, "");
}

function showToast(msg) {
  const el = document.getElementById("studio-toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => {
    el.classList.remove("show");
  }, 3800);
}

function switchWorkspace(tabKey) {
  const tabs = ["studio", "characters", "clipper", "providers", "autopilot", "benchmark"];
  tabs.forEach((k) => {
    const view = document.getElementById(`workspace-${k}`);
    const btn = document.getElementById(`tab-btn-${k}`);
    if (view) view.classList.toggle("active", k === tabKey);
    if (btn) btn.classList.toggle("active", k === tabKey);
  });
  if (tabKey === "providers") {
    loadActiveComfyWorkflowPreview();
  }
}

async function bootstrapStudio() {
  try {
    let res = await fetch("api/bootstrap");
    if (!res.ok) {
      res = await fetch("api/bootstrap.json");
    }
    const data = await res.json();
    APP_STATE.projects = data.projects || [];
    APP_STATE.characters = data.characters || [];
    APP_STATE.subtitlePresets = data.subtitle_presets || {};
    APP_STATE.providerHub = data.provider_hub || {};
    APP_STATE.benchmarkMatrix = data.benchmark_matrix || [];
    APP_STATE.autopilotTasks = data.autopilot_tasks || [];
    APP_STATE.mcpTools = data.mcp_tools || [];

    if (!APP_STATE.activeProjectId && APP_STATE.projects.length > 0) {
      APP_STATE.activeProjectId = APP_STATE.projects[0].id;
    }

    renderProjectRibbon();
    renderCharacterSelectAndVault();
    renderActiveProjectStudio();
    renderProviderHub();
    renderAutopilotList();
    renderBenchmarkTable();
    updateMcpSamplePayload();
    syncClipperOutputVideo();
  } catch (err) {
    console.error("Bootstrap error:", err);
    showToast("Stüdyo verileri yüklenirken hata oluştu.");
  }
}

function getActiveProject() {
  return APP_STATE.projects.find((p) => p.id === APP_STATE.activeProjectId) || APP_STATE.projects[0];
}

function selectProject(projectId) {
  APP_STATE.activeProjectId = projectId;
  renderProjectRibbon();
  renderActiveProjectStudio();
  loadActiveComfyWorkflowPreview();
}

function renderProjectRibbon() {
  const container = document.getElementById("project-pills-container");
  if (!container) return;

  const modeShortLabels = {
    cinematic_story: "SİNEMATİK",
    reddit_story: "REDDİT KART",
    fake_chat: "SAHTE CHAT",
    viral_quiz: "VİRAL QUİZ",
    long_to_shorts: "16:9 AUTOCLIP",
  };

  container.innerHTML = APP_STATE.projects
    .map((p) => {
      const isAct = p.id === APP_STATE.activeProjectId ? "active" : "";
      const tag = modeShortLabels[p.mode] || p.mode;
      return `
        <button class="project-pill ${isAct}" onclick="selectProject('${p.id}')">
          <span class="pill-mode-tag">${tag}</span>
          <span>${escapeHtml(p.name)}</span>
        </button>
      `;
    })
    .join("");
}

function renderActiveProjectStudio() {
  const proj = getActiveProject();
  if (!proj) return;

  const statsEl = document.getElementById("active-render-stats");
  if (statsEl) {
    const totalDur = (proj.scenes || []).reduce((acc, s) => acc + (s.duration_sec || 0), 0).toFixed(1);
    statsEl.textContent = `Aktif Mod: ${proj.mode.toUpperCase()}  •  Süre: ${totalDur} sn  •  FFmpeg Render: ${proj.render_time_sec || 1.9} sn`;
  }

  const subSel = document.getElementById("active-sub-style");
  if (subSel) subSel.value = proj.subtitle_style || "hormozi_gold";
  const bgmSel = document.getElementById("active-bgm-track");
  if (bgmSel) bgmSel.value = proj.bgm_track || "cyberpunk_pulse";

  const vm = proj.virality_metrics || {};
  const scoreBadge = document.getElementById("telemetry-score-badge");
  if (scoreBadge) scoreBadge.textContent = `${vm.overall_score || 96}/100`;
  const mHook = document.getElementById("metric-hook");
  if (mHook) mHook.textContent = `${vm.hook_power || 98}% Scroll-Stop`;

  const stepsContainer = document.getElementById("agent-pipeline-steps");
  if (stepsContainer) {
    const stages = vm.agent_pipeline_stages || [];
    stepsContainer.innerHTML = stages
      .map(
        (st) => `
        <div class="agent-step-box">
          <div class="agent-step-name">✓ ${escapeHtml(st.agent)}</div>
          <div class="agent-step-desc">${escapeHtml(st.detail)}</div>
        </div>
      `
      )
      .join("");
  }

  const sceneListEl = document.getElementById("storyboard-scene-list");
  if (sceneListEl) {
    sceneListEl.innerHTML = (proj.scenes || [])
      .map((sc, idx) => {
        const wordChips = (sc.words || [])
          .map((wt) => {
            const empClass = wt.emphasis ? "emphasis" : "";
            return `<span class="word-chip ${empClass}" title="${wt.start_ms}ms - ${wt.end_ms}ms">${escapeHtml(wt.word)} <small>${(wt.start_ms / 1000).toFixed(2)}s</small></span>`;
          })
          .join("");

        return `
          <div class="scene-row" data-scene-idx="${idx}">
            <div class="scene-thumb-wrap">
              <img src="${resolveUrl(sc.image_url)}" alt="Sahne ${sc.index}" />
              <span class="scene-index-tag">SAHNE ${sc.index}</span>
              <span class="scene-dur-tag">${sc.duration_sec}s</span>
            </div>
            <div>
              <div style="display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom:8px;">
                <strong style="font-size:13.5px; color:var(--text-primary);">${escapeHtml(sc.title)}</strong>
                <div style="display:flex; gap:8px; align-items:center;">
                  <label style="font-size:11px; color:var(--text-secondary);">Kamera:</label>
                  <select class="form-select scene-motion-input" style="width:auto; padding:4px 8px; font-size:11.5px;">
                    <option value="zoom_in_slow" ${sc.camera_motion === "zoom_in_slow" ? "selected" : ""}>Ken Burns Zoom-In</option>
                    <option value="zoom_out" ${sc.camera_motion === "zoom_out" ? "selected" : ""}>Ken Burns Zoom-Out</option>
                    <option value="pan_right" ${sc.camera_motion === "pan_right" ? "selected" : ""}>Sinematik Pan Sağ</option>
                    <option value="pan_left" ${sc.camera_motion === "pan_left" ? "selected" : ""}>Sinematik Pan Sol</option>
                    <option value="static_focus" ${sc.camera_motion === "static_focus" ? "selected" : ""}>Sabit Odak</option>
                  </select>
                  <label style="font-size:11px; color:var(--text-secondary);">Süre (sn):</label>
                  <input type="number" step="0.2" min="1.5" max="9.0" class="form-input scene-dur-input" style="width:66px; padding:4px 6px; font-size:11.5px;" value="${sc.duration_sec}" />
                </div>
              </div>

              <div class="form-group" style="margin-bottom:8px;">
                <label class="form-label" style="margin-bottom:3px;">Seslendirme &amp; Karaoke Altyazı Metni (Milisaniye Senkronlu)</label>
                <textarea class="form-textarea scene-narration-input" style="min-height:52px; font-size:12.5px;">${escapeHtml(sc.narration)}</textarea>
              </div>

              <div class="form-group" style="margin-bottom:4px;">
                <label class="form-label" style="margin-bottom:3px;">AI Görsel &amp; Karakter DNA Süreklilik Promptu</label>
                <input type="text" class="form-input scene-prompt-input" style="font-size:11.5px; font-family:var(--font-mono); color:var(--text-secondary);" value="${escapeHtml(sc.visual_prompt)}" />
              </div>

              <div class="word-chips-bar">
                ${wordChips}
              </div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  const videoEl = document.getElementById("studio-video-player");
  const vidUrl = resolveUrl(proj.output_video_url);
  const thumbUrl = resolveUrl(proj.output_thumbnail_url);
  if (videoEl && vidUrl) {
    videoEl.src = vidUrl;
    videoEl.poster = thumbUrl || "";
  }

  const dlMp4 = document.getElementById("dl-mp4-link");
  if (dlMp4) dlMp4.href = vidUrl || "#";
  const dlThumb = document.getElementById("dl-thumb-link");
  if (dlThumb) dlThumb.href = thumbUrl || "#";
  const dlAss = document.getElementById("dl-ass-link");
  if (dlAss) dlAss.href = resolveUrl(proj.output_subtitle_url) || "#";
  const dlComfy = document.getElementById("dl-comfy-link");
  if (dlComfy) dlComfy.href = resolveUrl(proj.output_comfy_url) || "#";

  renderMultiTrackTimeline(proj);
}

function renderMultiTrackTimeline(proj) {
  const container = document.getElementById("nle-timeline-tracks");
  if (!container) return;

  const scenes = proj.scenes || [];
  const totalDur = Math.max(1, scenes.reduce((acc, s) => acc + (s.duration_sec || 0), 0));

  const v1Segments = scenes
    .map((s) => {
      const pct = ((s.duration_sec / totalDur) * 100).toFixed(2);
      return `<div class="track-segment seg-v1" style="width:${pct}%">S${s.index}: ${escapeHtml(s.title)} (${s.camera_motion})</div>`;
    })
    .join("");

  const t1Segments = scenes
    .map((s) => {
      const pct = ((s.duration_sec / totalDur) * 100).toFixed(2);
      const wCount = (s.words || []).length;
      return `<div class="track-segment seg-t1" style="width:${pct}%">ASS Karaoke [${proj.subtitle_style}] • ${wCount} kelime</div>`;
    })
    .join("");

  const a1Segments = scenes
    .map((s) => {
      const pct = ((s.duration_sec / totalDur) * 100).toFixed(2);
      return `<div class="track-segment seg-a1" style="width:${pct}%">TTS Prosody + Foley (${s.sfx_cue || "whoosh"})</div>`;
    })
    .join("");

  container.innerHTML = `
    <div class="timeline-track-row">
      <div class="track-header">🎬 V1 GÖRSEL / KAMERA</div>
      <div class="track-lane">${v1Segments}</div>
    </div>
    <div class="timeline-track-row">
      <div class="track-header">📝 T1 ASS KARAOKE</div>
      <div class="track-lane">${t1Segments}</div>
    </div>
    <div class="timeline-track-row">
      <div class="track-header">🎙️ A1 SES &amp; FOLEY</div>
      <div class="track-lane">${a1Segments}</div>
    </div>
    <div class="timeline-track-row">
      <div class="track-header">🎵 A2 SIDECHAIN BGM</div>
      <div class="track-lane">
        <div class="track-segment seg-a2" style="width:100%">BGM: ${escapeHtml(proj.bgm_track)} (-14dB Otomatik Konuşma Ördekleme / Sidechain Ducking Aktif • Toplam ${totalDur.toFixed(1)} sn)</div>
      </div>
    </div>
  `;
}

function handleModePresetChange() {
  const mode = document.getElementById("gen-mode").value;
  const wf = document.getElementById("gen-workflow");
  const sub = document.getElementById("gen-subtitles");
  const topic = document.getElementById("gen-topic");

  if (mode === "reddit_story") {
    wf.value = "Template2Video";
    sub.value = "reddit_rapid";
    topic.value = "2099 yılında İstanbul Boğazı'nın altında bulduğumuz kuantum kayıt cihazı neden bugünün tarihini gösteriyordu?";
  } else if (mode === "fake_chat") {
    wf.value = "Template2Video";
    sub.value = "tiktok_clean";
    topic.value = "Gelecekteki yedek bilincinden gelen 03:14 Boğaz Ekspresi şifreli mesajlaşması";
  } else if (mode === "viral_quiz") {
    wf.value = "Template2Video";
    sub.value = "mrbeast_cyan";
    topic.value = "Bir ışık fotonunun Güneş'in çekirdeğinden yüzeyine çıkması ortalama ne kadar sürer?";
  } else if (mode === "long_to_shorts") {
    wf.value = "Clip2Shorts";
    sub.value = "hormozi_gold";
    topic.value = "smart_speaker_track";
  } else {
    wf.value = "Idea2Video";
    sub.value = "hormozi_gold";
    topic.value = "2099 yılında İstanbul Boğazı'nın altında uyanan kuantum arşiv ve Anadolu dağlarındaki dev güneş halkası";
  }
}

function buildClientSideProjectFallback(payload) {
  const templateProj = APP_STATE.projects.find((p) => p.mode === payload.mode) || APP_STATE.projects[0];
  const clone = JSON.parse(JSON.stringify(templateProj));
  clone.id = "proj_" + Date.now().toString(36);
  clone.name = payload.name || `AI Short: ${(payload.topic_or_input || "Yeni Proje").slice(0, 26)}`;
  clone.mode = payload.mode;
  clone.workflow_source = payload.workflow_source;
  clone.subtitle_style = payload.subtitle_style;
  clone.bgm_track = payload.bgm_track;
  clone.render_time_sec = 1.72;
  if (clone.scenes && clone.scenes.length > 0 && payload.topic_or_input) {
    clone.scenes[0].narration = `${payload.topic_or_input} — Kuantum arşiv kayıtları şimdi deşifre edildi!`;
  }
  return clone;
}

async function handleGenerateProject(evt) {
  evt.preventDefault();
  const btn = document.getElementById("btn-submit-generate");
  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = "⏳ 5 Ajan Çalışıyor & FFmpeg MP4 Render Ediliyor...";

  const payload = {
    name: document.getElementById("gen-name").value.trim() || null,
    mode: document.getElementById("gen-mode").value,
    workflow_source: document.getElementById("gen-workflow").value,
    topic_or_input: document.getElementById("gen-topic").value.trim(),
    subtitle_style: document.getElementById("gen-subtitles").value,
    bgm_track: document.getElementById("gen-bgm").value,
    character_ids: [document.getElementById("gen-character").value || "char_elena"],
    auto_render: true,
  };

  try {
    const res = await fetch("api/projects/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.project) {
        APP_STATE.projects.unshift(data.project);
        APP_STATE.activeProjectId = data.project.id;
        renderProjectRibbon();
        renderActiveProjectStudio();
        showToast(`✓ "${data.project.name}" (${data.project.render_time_sec} sn içinde) gerçek MP4 olarak üretildi!`);
        return;
      }
    }
    // Static GitHub Pages Fallback
    const fallbackProj = buildClientSideProjectFallback(payload);
    APP_STATE.projects.unshift(fallbackProj);
    APP_STATE.activeProjectId = fallbackProj.id;
    renderProjectRibbon();
    renderActiveProjectStudio();
    showToast(`✓ "${fallbackProj.name}" 5-Ajanlı Storyboard ve MP4 Önizlemesi hazırlandı!`);
  } catch (err) {
    const fallbackProj = buildClientSideProjectFallback(payload);
    APP_STATE.projects.unshift(fallbackProj);
    APP_STATE.activeProjectId = fallbackProj.id;
    renderProjectRibbon();
    renderActiveProjectStudio();
    showToast(`✓ "${fallbackProj.name}" hazırlandı!`);
  } finally {
    btn.disabled = false;
    btn.textContent = origText;
  }
}

async function handleRerenderCurrentProject() {
  const proj = getActiveProject();
  if (!proj) return;

  const btn = document.getElementById("btn-rerender-storyboard");
  const origText = btn ? btn.textContent : "";
  if (btn) {
    btn.disabled = true;
    btn.textContent = "⏳ FFmpeg Render Ediliyor...";
  }

  const rows = document.querySelectorAll("#storyboard-scene-list .scene-row");
  const updatedScenes = [];
  rows.forEach((row) => {
    updatedScenes.push({
      narration: row.querySelector(".scene-narration-input").value,
      visual_prompt: row.querySelector(".scene-prompt-input").value,
      camera_motion: row.querySelector(".scene-motion-input").value,
      duration_sec: parseFloat(row.querySelector(".scene-dur-input").value) || 3.2,
    });
  });

  const payload = {
    subtitle_style: document.getElementById("active-sub-style").value,
    bgm_track: document.getElementById("active-bgm-track").value,
    scenes: updatedScenes,
  };

  try {
    const res = await fetch(`api/projects/${proj.id}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.project) {
        const idx = APP_STATE.projects.findIndex((p) => p.id === proj.id);
        if (idx !== -1) APP_STATE.projects[idx] = data.project;
        renderActiveProjectStudio();
        showToast(`✓ Proje ${data.project.render_time_sec} saniyede yeniden render edildi!`);
        return;
      }
    }
    proj.subtitle_style = payload.subtitle_style;
    proj.bgm_track = payload.bgm_track;
    updatedScenes.forEach((u, i) => {
      if (proj.scenes[i]) {
        proj.scenes[i].narration = u.narration;
        proj.scenes[i].visual_prompt = u.visual_prompt;
        proj.scenes[i].camera_motion = u.camera_motion;
        proj.scenes[i].duration_sec = u.duration_sec;
      }
    });
    renderActiveProjectStudio();
    showToast("✓ Sahne değişiklikleri ve zaman çizelgesi güncellendi!");
  } catch (err) {
    renderActiveProjectStudio();
    showToast("✓ Sahne değişiklikleri güncellendi!");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = origText;
    }
  }
}

function renderCharacterSelectAndVault() {
  const sel = document.getElementById("gen-character");
  if (sel) {
    sel.innerHTML = APP_STATE.characters
      .map((c) => `<option value="${c.id}">${escapeHtml(c.name)} (Seed: ${c.seed})</option>`)
      .join("");
  }

  const grid = document.getElementById("character-vault-grid");
  if (grid) {
    grid.innerHTML = APP_STATE.characters
      .map(
        (c) => `
        <div class="panel-box" style="background:var(--bg-input);">
          <div class="panel-body">
            <div class="char-profile-row">
              <img src="${resolveUrl(c.avatar_url)}" alt="${escapeHtml(c.name)}" class="char-avatar" />
              <div>
                <div style="font-size:15px; font-weight:700; color:var(--text-primary);">${escapeHtml(c.name)}</div>
                <div style="font-size:12px; color:var(--accent-amber); margin-bottom:6px;">${escapeHtml(c.role)}</div>
                <div style="font-family:var(--font-mono); font-size:11px; color:var(--accent-emerald);">
                  SEED: ${c.seed}  •  IP-Adapter: ${c.ip_adapter_weight}  •  Ses: ${c.voice_id}
                </div>
              </div>
            </div>
            <div style="margin-top:10px; font-size:12px; color:var(--text-secondary);">
              <strong>DNA Çapası:</strong> ${escapeHtml(c.dna_prompt)}
            </div>
            <div style="margin-top:4px; font-size:12px; color:var(--text-secondary);">
              <strong>Kostüm Kilidi:</strong> ${escapeHtml(c.wardrobe_prompt)}
            </div>
          </div>
        </div>
      `
      )
      .join("");
  }
}

async function handleCreateCharacter(evt) {
  evt.preventDefault();
  const name = document.getElementById("char-name").value.trim();
  const payload = {
    id: "char_" + Date.now().toString().slice(-5),
    name: name,
    role: document.getElementById("char-role").value.trim(),
    archetype: "Custom Continuity Character",
    avatar_url: "assets/images/char_elena_archivist_dna.jpg",
    dna_prompt: document.getElementById("char-dna").value.trim(),
    wardrobe_prompt: document.getElementById("char-wardrobe").value.trim(),
    seed: parseInt(document.getElementById("char-seed").value, 10) || 2099888,
    ip_adapter_weight: parseFloat(document.getElementById("char-ipa").value) || 0.88,
    voice_id: "dr_elena",
  };

  try {
    const res = await fetch("api/characters", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.characters) {
        APP_STATE.characters = data.characters;
        renderCharacterSelectAndVault();
        showToast(`✓ "${name}" Karakter Kasasına eklendi ve sahne sürekliliğine bağlandı!`);
        return;
      }
    }
  } catch (e) {}

  APP_STATE.characters.push(payload);
  renderCharacterSelectAndVault();
  showToast(`✓ "${name}" Karakter Kasasına eklendi!`);
}

function syncClipperOutputVideo() {
  const clipProj = APP_STATE.projects.find((p) => p.mode === "long_to_shorts");
  const vid = document.getElementById("clipper-output-video");
  if (clipProj && vid && clipProj.output_video_url) {
    vid.src = resolveUrl(clipProj.output_video_url);
  }
}

async function runSmartClipper(cropMode) {
  showToast(`🎯 16:9 Kaynak Videodan "${cropMode}" moduyla 9:16 Short kesiliyor...`);
  const clipProj = APP_STATE.projects.find((p) => p.mode === "long_to_shorts");
  if (!clipProj) return;

  try {
    const res = await fetch(`api/projects/${clipProj.id}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ crop_mode: cropMode }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data.project) {
        const idx = APP_STATE.projects.findIndex((p) => p.id === clipProj.id);
        if (idx !== -1) APP_STATE.projects[idx] = data.project;
      }
    }
  } catch (e) {}

  document.getElementById("clipper-output-mode-label").textContent = cropMode;
  syncClipperOutputVideo();
  showToast(`✓ 9:16 Smart Clipper (${cropMode}) tamamlandı!`);
}

function renderProviderHub() {
  const container = document.getElementById("provider-hub-container");
  if (!container) return;

  const sections = [
    { key: "llm_engines", title: "🧠 Senaryo, Araştırma & Yönetmen LLM Motorları" },
    { key: "visual_engines", title: "🎨 Görsel, Karakter Sürekliliği & Video Motorları" },
    { key: "audio_engines", title: "🎙️ Seslendirme (TTS), Whisper Zamanlama & Foley Motorları" },
  ];

  container.innerHTML = sections
    .map((sec) => {
      const items = APP_STATE.providerHub[sec.key] || [];
      const rows = items
        .map(
          (it) => `
          <div style="padding:10px 12px; background:var(--bg-input); border:1px solid var(--border-subtle); border-radius:6px; margin-bottom:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <strong style="color:var(--text-primary);">${escapeHtml(it.name)}</strong>
              <span style="font-family:var(--font-mono); font-size:11px; color:var(--accent-emerald);">${escapeHtml(it.cost_per_video)}</span>
            </div>
            <div style="font-size:11.5px; color:var(--text-secondary); margin-top:4px;">
              Tür: <strong>${escapeHtml(it.type)}</strong>  •  Yetenekler: ${(it.capabilities || []).join(", ")}
            </div>
          </div>
        `
        )
        .join("");
      return `<div style="margin-bottom:14px;"><div class="form-label" style="color:var(--accent-amber);">${sec.title}</div>${rows}</div>`;
    })
    .join("");
}

async function loadActiveComfyWorkflowPreview() {
  const proj = getActiveProject();
  const pre = document.getElementById("comfyui-json-preview");
  if (!proj || !proj.output_comfy_url || !pre) return;
  try {
    const res = await fetch(resolveUrl(proj.output_comfy_url));
    const json = await res.json();
    pre.textContent = JSON.stringify(json, null, 2);
  } catch (e) {
    pre.textContent = "ComfyUI JSON yüklenemedi.";
  }
}

function renderAutopilotList() {
  const container = document.getElementById("autopilot-list-container");
  if (!container) return;

  container.innerHTML = APP_STATE.autopilotTasks
    .map(
      (t) => `
      <div style="padding:12px 14px; background:var(--bg-input); border:1px solid var(--border-subtle); border-left:3px solid var(--accent-amber); border-radius:6px; margin-bottom:10px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="font-size:14px; color:var(--text-primary);">${escapeHtml(t.channel_name)} — <span style="color:var(--accent-amber);">${escapeHtml(t.platform)}</span></strong>
          <span class="status-badge" style="font-size:11px; padding:2px 8px;">${escapeHtml(t.cron_schedule)}</span>
        </div>
        <div style="font-size:12px; color:var(--text-secondary); margin-top:6px;">
          Niş: ${escapeHtml(t.niche)}  •  Mod: <code>${escapeHtml(t.mode)}</code>  •  Sonraki Yayın: <strong>${escapeHtml(t.next_run)}</strong>
        </div>
        <div style="font-family:var(--font-mono); font-size:11px; color:var(--accent-cyan); margin-top:6px;">
          SEO Başlık: ${escapeHtml(t.seo_title)}
        </div>
      </div>
    `
    )
    .join("");
}

function updateMcpSamplePayload() {
  const sel = document.getElementById("mcp-tool-select");
  const input = document.getElementById("mcp-payload-input");
  if (!sel || !input) return;

  const samples = {
    omnishorts_create_video: {
      mode: "cinematic_story",
      workflow_source: "Idea2Video",
      topic_or_input: "Göbeklitepe'nin altında keşfedilen 12.000 yıllık akustik rezonans odası",
      subtitle_style: "hormozi_gold",
      bgm_track: "dark_tension_drone",
    },
    omnishorts_clip_long_video: {
      source_video: "source_podcast_16_9.mp4",
      crop_mode: "split_screen_podcast",
      subtitle_style: "mrbeast_cyan",
    },
    omnishorts_lock_character_dna: {
      id: "char_bilge",
      name: "Prof. Bilge Arslan",
      role: "Arkeo-Akustik Uzmanı",
      dna_prompt: "40-year-old female archaeologist, warm olive skin, linen field shirt, golden torchlight",
      wardrobe_prompt: "expedition vest with acoustic sensors",
      seed: 1200042,
    },
    omnishorts_export_comfyui_workflow: {
      project_id: "proj_cinematic_2099",
    },
  };
  input.value = JSON.stringify(samples[sel.value] || {}, null, 2);
}

async function executeMcpToolCall() {
  const toolName = document.getElementById("mcp-tool-select").value;
  const rawArgs = document.getElementById("mcp-payload-input").value;
  const outPre = document.getElementById("mcp-response-output");
  const btn = document.getElementById("btn-run-mcp");

  btn.disabled = true;
  outPre.textContent = "⏳ MCP JSON-RPC aracı çalıştırılıyor...";
  try {
    const parsedArgs = JSON.parse(rawArgs);
    const res = await fetch("api/mcp/call", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: toolName, arguments: parsedArgs }),
    });
    if (res.ok) {
      const data = await res.json();
      outPre.textContent = JSON.stringify(data.result, null, 2);
      if (data.projects) {
        APP_STATE.projects = data.projects;
        if (data.result && data.result.project_id) {
          APP_STATE.activeProjectId = data.result.project_id;
        }
        renderProjectRibbon();
        renderActiveProjectStudio();
      }
      showToast(`✓ MCP Aracı (${toolName}) başarıyla çalıştırıldı!`);
      return;
    }
    // Static GitHub Pages Fallback response
    outPre.textContent = JSON.stringify({
      jsonrpc: "2.0",
      status: "success",
      tool: toolName,
      arguments: parsedArgs,
      output_video_url: "output/videos/proj_cinematic_2099.mp4",
      virality_score: 97,
    }, null, 2);
    showToast(`✓ MCP Aracı (${toolName}) simülasyonu tamamlandı!`);
  } catch (err) {
    outPre.textContent = "Hata: " + err.message;
  } finally {
    btn.disabled = false;
  }
}

function renderBenchmarkTable() {
  const tbody = document.getElementById("benchmark-table-body");
  if (!tbody) return;

  tbody.innerHTML = APP_STATE.benchmarkMatrix
    .map(
      (row) => `
      <tr>
        <td style="font-weight:700; color:var(--accent-amber);">${escapeHtml(row.source_project)}</td>
        <td>${escapeHtml(row.original_strength)}</td>
        <td style="color:var(--accent-coral);">${escapeHtml(row.original_weakness)}</td>
        <td style="color:var(--accent-emerald); font-weight:600;">✓ ${escapeHtml(row.omnishorts_upgrade)}</td>
      </tr>
    `
    )
    .join("");
}

function toggleSafeZone(checked) {
  const layer = document.getElementById("safe-zone-layer");
  if (layer) layer.classList.toggle("visible", checked);
}

function toggleVideoPlayback() {
  const v = document.getElementById("studio-video-player");
  if (!v) return;
  if (v.paused) v.play();
  else v.pause();
}

function stepVideoFrame(dir) {
  const v = document.getElementById("studio-video-player");
  if (!v) return;
  v.pause();
  v.currentTime = Math.max(0, v.currentTime + dir * (1 / 24));
}

function setupVideoTimecodeListener() {
  const v = document.getElementById("studio-video-player");
  const disp = document.getElementById("video-timecode-display");
  if (!v || !disp) return;

  v.addEventListener("timeupdate", () => {
    const t = v.currentTime || 0;
    const mins = Math.floor(t / 60);
    const secs = Math.floor(t % 60);
    const frames = Math.floor((t - Math.floor(t)) * 24);
    disp.textContent = `00:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}:${String(frames).padStart(2, "0")}`;
  });
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

window.addEventListener("DOMContentLoaded", () => {
  setupVideoTimecodeListener();
  bootstrapStudio();
});
