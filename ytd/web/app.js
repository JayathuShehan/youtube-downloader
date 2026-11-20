(() => {
  const $ = (id) => document.getElementById(id);
  const el = {
    url: $("url"), fetch: $("fetch"), msg: $("msg"), preview: $("preview"), thumb: $("thumb"),
    title: $("title"), uploader: $("uploader"), duration: $("duration"), quality: $("quality"),
    folder: $("folder"), browse: $("browse"), connections: $("connections"),
    start: $("start"), pause: $("pause"), resume: $("resume"),
    pCard: $("progressCard"), pTitle: $("pTitle"), pState: $("pState"), pFill: $("pFill"),
    pPercent: $("pPercent"), pStage: $("pStage"), sDone: $("sDone"), sTotal: $("sTotal"),
    sSpeed: $("sSpeed"), sEta: $("sEta"), sConn: $("sConn"), sQuality: $("sQuality"),
    streams: $("streams"), pError: $("pError"), doneRow: $("doneRow"), pOutput: $("pOutput"),
    openFolder: $("openFolder"), hCard: $("historyCard"), history: $("history"), version: $("version"),
  };

  let options = null;      // result of /api/info
  let optionsUrl = "";
  let type = "video";
  let currentJob = null;   // job id shown in the progress card
  let lastSnap = null;

  // ---------------------------------------------------------------- helpers
  async function api(path, body) {
    const res = await fetch(path, body === undefined ? {} : {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }

  function bytes(n) {
    if (n == null || isNaN(n)) return "–";
    const u = ["B", "KB", "MB", "GB", "TB"];
    let i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return i === 0 ? `${Math.round(n)} B` : `${n.toFixed(1)} ${u[i]}`;
  }

  function time(s) {
    if (s == null || !isFinite(s) || s < 0) return "–";
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    const mm = String(m).padStart(2, "0"), ss = String(sec).padStart(2, "0");
    return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
  }

  function setMsg(text, isError = false) {
    el.msg.textContent = text || "";
    el.msg.classList.toggle("error", isError);
  }

  function savePref(key, value) { try { localStorage.setItem("ytd." + key, value); } catch (_) {} }
  function loadPref(key) { try { return localStorage.getItem("ytd." + key); } catch (_) { return null; } }

  // ------------------------------------------------------------------ fetch
  async function fetchInfo() {
    const url = el.url.value.trim();
    if (!url) { setMsg("Paste a video link first.", true); el.url.focus(); return; }
    el.fetch.disabled = true;
    el.start.disabled = true;
    setMsg("Getting video info…");
    try {
      options = await api("/api/info", { url });
      optionsUrl = url;
      el.thumb.src = options.thumbnail || "";
      el.title.textContent = options.title;
      el.uploader.textContent = options.uploader || "";
      el.duration.textContent = options.duration ? `Length ${time(options.duration)}` : "";
      el.preview.hidden = false;
      setMsg("");
      if (type === "video" && !options.video.length) setType("audio"); else fillQualities();
    } catch (e) {
      options = null;
      el.preview.hidden = true;
      fillQualities();
      setMsg(e.message, true);
    } finally {
      el.fetch.disabled = false;
    }
  }

  function fillQualities() {
    el.quality.innerHTML = "";
    const list = options ? options[type] : [];
    if (!list || !list.length) {
      el.quality.add(new Option(options ? "Not available" : "Fetch a link first", ""));
      el.quality.disabled = true;
      el.start.disabled = true;
      return;
    }
    for (const q of list) el.quality.add(new Option(q.label, q.id));
    el.quality.disabled = false;
    el.start.disabled = false;
  }

  function setType(t) {
    type = t;
    document.querySelectorAll(".seg-btn").forEach((b) => {
      const on = b.dataset.type === t;
      b.classList.toggle("active", on);
      b.setAttribute("aria-checked", on);
    });
    fillQualities();
  }

  // --------------------------------------------------------------- actions
  async function start() {
    const url = el.url.value.trim();
    if (!options || url !== optionsUrl) { await fetchInfo(); if (!options) return; }
    const folder = el.folder.value.trim();
    savePref("folder", folder);
    savePref("connections", el.connections.value);
    el.start.disabled = true;
    try {
      const r = await api("/api/start", {
        url, type, quality: el.quality.value, folder, connections: Number(el.connections.value),
      });
      currentJob = r.job_id;
      poll();
      refreshHistory();
    } catch (e) {
      setMsg(e.message, true);
    } finally {
      el.start.disabled = !options;
    }
  }

  async function control(action) {
    if (!currentJob) return;
    el.pause.disabled = el.resume.disabled = true;
    try { await api(`/api/${action}`, { job_id: currentJob }); } catch (e) { setMsg(e.message, true); }
    poll();
  }

  async function browse() {
    el.browse.disabled = true;
    try {
      const r = await api("/api/browse", { folder: el.folder.value.trim() });
      if (r.folder) { el.folder.value = r.folder; savePref("folder", r.folder); }
    } catch (e) {
      setMsg(e.message, true);
    } finally {
      el.browse.disabled = false;
    }
  }

  // --------------------------------------------------------------- progress
  async function poll() {
    if (!currentJob) return;
    try {
      render(await api(`/api/status?job_id=${encodeURIComponent(currentJob)}`));
    } catch (_) { /* server busy or gone; try again next tick */ }
  }

  function render(s) {
    lastSnap = s;
    el.pCard.hidden = false;
    el.pTitle.textContent = s.title;
    el.pTitle.title = s.title;
    el.pState.textContent = s.state;
    el.pState.className = `badge ${s.state}`;

    const processing = s.state === "processing";
    const pct = processing ? s.process_progress : s.percent;
    el.pFill.style.width = `${pct}%`;
    el.pFill.className = "fill" + (s.state === "done" ? " done" : s.state === "paused" ? " paused" : "");
    el.pPercent.textContent = processing ? `${pct.toFixed(1)}% processed` : `${s.percent.toFixed(1)}%`;
    el.pStage.textContent = s.stage;

    el.sDone.textContent = bytes(s.downloaded);
    el.sTotal.textContent = s.total ? bytes(s.total) : "–";
    el.sSpeed.textContent = s.state === "downloading" ? `${bytes(s.speed)}/s` : "–";
    el.sEta.textContent = s.state === "downloading" ? time(s.eta) : "–";
    el.sConn.textContent = `${s.connections} / ${s.max_connections * Math.max(1, s.streams.length)}`;
    el.sQuality.textContent = s.quality || "–";

    el.streams.innerHTML = s.streams.map((st) => {
      const size = st.size || 1;
      const segs = st.segments.map(([a, b, p]) => {
        const left = (a / size) * 100, width = ((p - a) / size) * 100;
        const live = p <= b ? " live" : "";
        return `<div class="s${live}" style="left:${left}%;width:${width}%"></div>`;
      }).join("");
      const pc = st.size ? ((st.downloaded / st.size) * 100).toFixed(1) : "0.0";
      return `<div class="stream">
        <div class="stream-head"><span><b>${st.role}</b> · ${st.segments.length} segments · ${st.active} connections</span>
        <span>${bytes(st.downloaded)} / ${bytes(st.size)} · ${pc}%${st.speed ? " · " + bytes(st.speed) + "/s" : ""}</span></div>
        <div class="segbar">${segs}</div></div>`;
    }).join("");

    el.pError.hidden = !s.error;
    el.pError.textContent = s.error || "";
    el.doneRow.hidden = s.state !== "done";
    el.pOutput.textContent = s.output || "";

    el.pause.disabled = !["queued", "fetching", "downloading"].includes(s.state);
    el.resume.disabled = !["paused", "error"].includes(s.state);
    el.resume.textContent = s.state === "error" ? "Retry" : "Resume";
  }

  async function refreshHistory() {
    try {
      const { jobs } = await api("/api/jobs");
      el.hCard.hidden = jobs.length < 2;
      el.history.innerHTML = "";
      for (const j of jobs) {
        const li = document.createElement("li");
        li.className = j.id === currentJob ? "sel" : "";
        const t = document.createElement("span");
        t.className = "t";
        t.textContent = `${j.title} · ${j.quality || ""}`;
        const b = document.createElement("span");
        b.className = `badge ${j.state}`;
        b.textContent = j.state === "downloading" ? `${j.percent.toFixed(0)}%` : j.state;
        li.append(t, b);
        li.onclick = () => { currentJob = j.id; poll(); refreshHistory(); };
        el.history.append(li);
      }
    } catch (_) { /* ignore */ }
  }

  // ------------------------------------------------------------------- init
  el.fetch.onclick = fetchInfo;
  el.url.addEventListener("keydown", (e) => { if (e.key === "Enter") fetchInfo(); });
  el.url.addEventListener("paste", () => setTimeout(fetchInfo, 50));
  document.querySelectorAll(".seg-btn").forEach((b) => (b.onclick = () => setType(b.dataset.type)));
  el.start.onclick = start;
  el.pause.onclick = () => control("pause");
  el.resume.onclick = () => control("resume");
  el.browse.onclick = browse;
  el.openFolder.onclick = () => currentJob && api("/api/open", { job_id: currentJob }).catch((e) => setMsg(e.message, true));

  api("/api/config").then((c) => {
    el.folder.value = loadPref("folder") || c.folder;
    el.connections.value = loadPref("connections") || String(c.connections);
    el.version.textContent = `v${c.version}`;
  }).catch(() => {});

  setInterval(() => {
    if (currentJob && (!lastSnap || !["done", "error"].includes(lastSnap.state) || lastSnap.id !== currentJob)) poll();
  }, 500);
  setInterval(refreshHistory, 2000);
})();
