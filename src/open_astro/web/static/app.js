"use strict";

// Thin client for the OpenAstro read-only web API. Every call hits an /api/*
// endpoint that wraps the existing OpenAstro library. Nothing here writes a radio.

async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  let data;
  try { data = await res.json(); } catch (e) { data = { error: `HTTP ${res.status}` }; }
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

function esc(s) {
  return String(s === null || s === undefined ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function selectedCpg() {
  const typed = document.getElementById("cpgPath").value.trim();
  return typed || document.getElementById("cpgPicker").value;
}

// --- Health ---------------------------------------------------------------
async function checkHealth() {
  const el = document.getElementById("health");
  try {
    const h = await api("GET", "/api/health");
    el.textContent = `backend ok · v${h.version} · writes ${h.write_enabled ? "ON" : "disabled"}`;
    el.className = "pill pill-ok";
  } catch (e) {
    el.textContent = "backend unreachable";
    el.className = "pill pill-bad";
  }
}

// --- Decode ---------------------------------------------------------------
async function decode() {
  const btn = document.getElementById("decodeBtn");
  const summary = document.getElementById("decodeSummary");
  const zonesEl = document.getElementById("zones");
  btn.disabled = true;
  summary.className = "summary"; summary.innerHTML = "decoding…";
  zonesEl.innerHTML = "";
  try {
    const d = await api("POST", "/api/decode-cpg", { path: selectedCpg() });
    summary.innerHTML = `
      <div class="stat"><b>${d.zone_count}</b><span>zones</span></div>
      <div class="stat"><b>${d.channel_count}</b><span>channels</span></div>
      <div class="stat"><b>${d.personality_count}</b><span>personalities</span></div>
      <div class="stat"><b>${d.talkgroup_count}</b><span>talkgroups</span></div>
      <div class="stat"><b>${d.scan_list_count}</b><span>scan lists</span></div>`;
    const title = document.createElement("p");
    title.className = "hint";
    title.innerHTML = `<b>${esc(d.radio_model)}</b> · ${esc(d.bandsplit)} · S/N ${esc(d.serial_number)}`;
    zonesEl.appendChild(title);
    for (const z of d.codeplug.zones) {
      const div = document.createElement("div");
      div.className = "zone";
      let rows = z.channels.map(c => `<tr>
        <td>${c.channel_number}</td><td>${esc(c.name)}</td>
        <td>${c.rx_frequency}</td><td>${c.tx_frequency}</td>
        <td>${esc(c.voice_type)}</td><td>${esc(c.rx_nac)}</td>
        <td>${c.rx_pl_tone ? c.rx_pl_tone + " Hz" : (c.rx_dpl_code ? "DPL " + c.rx_dpl_code : "CSQ")}</td>
      </tr>`).join("");
      div.innerHTML = `<h3>${esc(z.name)} (${z.channels.length} ch)</h3>
        <table><thead><tr><th>#</th><th>Name</th><th>RX</th><th>TX</th>
        <th>Voice</th><th>NAC</th><th>Tone</th></tr></thead><tbody>${rows}</tbody></table>`;
      zonesEl.appendChild(div);
    }
  } catch (e) {
    summary.innerHTML = `<div class="box result-bad">${esc(e.message)}</div>`;
  } finally {
    btn.disabled = false;
  }
}

// --- Personalities --------------------------------------------------------
async function listPersonalities() {
  const out = document.getElementById("persResult");
  out.innerHTML = "loading…";
  try {
    const d = await api("GET", "/api/personalities?path=" + encodeURIComponent(selectedCpg()));
    if (!d.personality_count) { out.innerHTML = `<div class="box">No personalities decoded.</div>`; return; }
    const rows = d.personalities.map(p => `<tr>
      <td>${p.index}</td><td>${p.rx_frequency}</td><td>${p.tx_frequency}</td>
      <td>${esc(p.rx_nac)}</td><td>${p.simplex ? "simplex" : "duplex"}</td>
      <td>${esc(p.voice_type)}</td>
      <td>${p.rx_pl_tone ? p.rx_pl_tone + " Hz" : (p.rx_dpl_code ? "DPL " + p.rx_dpl_code : "CSQ")}</td>
    </tr>`).join("");
    out.innerHTML = `<div class="box" style="padding:0;background:none">
      <table><thead><tr><th>#</th><th>RX</th><th>TX</th><th>NAC</th>
      <th>Flag</th><th>Voice</th><th>Tone</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  } catch (e) {
    out.innerHTML = `<div class="box result-bad">${esc(e.message)}</div>`;
  }
}

// --- Flashcode ------------------------------------------------------------
async function loadFeatures() {
  const grid = document.getElementById("featureGrid");
  try {
    const d = await api("GET", "/api/flashcode/features");
    grid.innerHTML = "";
    for (const f of d.features) {
      const wrap = document.createElement("div");
      wrap.className = "feature" + (f.hardware_gated ? " gated" : "");
      wrap.innerHTML = `<input type="checkbox" value="${f.slug}" data-gated="${f.hardware_gated}" />
        <label title="${esc(f.label)}">${f.slug}${f.hardware_gated ? ' <span class="gated-badge">UCM</span>' : ""}</label>`;
      grid.appendChild(wrap);
    }
  } catch (e) {
    grid.innerHTML = `<div class="box result-bad">${esc(e.message)}</div>`;
  }
}

async function upgradeFlashcode() {
  const out = document.getElementById("fcResult");
  const add = Array.from(document.querySelectorAll("#featureGrid input:checked")).map(i => i.value);
  const allowUcm = document.getElementById("allowUcm").checked;
  out.innerHTML = "computing…";
  try {
    const d = await api("POST", "/api/flashcode/upgrade", {
      flashcode: document.getElementById("fcInput").value.trim(),
      add, allow_ucm: allowUcm,
    });
    const enabled = d.features_enabled.map(f => `  + ${esc(f.label)}${f.hardware_gated ? "  [UCM]" : ""}`).join("\n") || "  (none)";
    const gated = d.hardware_gated.length
      ? `\n\n[!] Hardware-gated in final code (bit alone won't activate):\n` +
        d.hardware_gated.map(g => `  - ${esc(g.label)}: ${esc(g.gate_note)}`).join("\n")
      : "";
    out.innerHTML = `<div class="box result-ok">From: ${esc(d.old)}
To  : <span class="fc-big">${esc(d.new)}</span>
check digit ${esc(d.check_digit)} · Luhn ${d.valid ? "OK" : "FAIL"} · transmitted: ${d.transmitted}

Enabled:
${enabled}${gated}</div>`;
  } catch (e) {
    out.innerHTML = `<div class="box result-bad">Refused / error: ${esc(e.message)}</div>`;
  }
}

// --- Export ---------------------------------------------------------------
async function exportSdr() {
  const out = document.getElementById("exportResult");
  out.innerHTML = "exporting…";
  try {
    const d = await api("POST", "/api/export-sdr", {
      codeplug_json_path: document.getElementById("exportPath").value.trim(),
      format: document.getElementById("exportFormat").value,
    });
    const files = Object.entries(d.files_relative).map(([k, v]) => `  ${k}: ${esc(v)}`).join("\n");
    out.innerHTML = `<div class="box result-ok">format: ${esc(d.format)}
output dir: ${esc(d.output_dir)}

generated:
${files}</div>`;
  } catch (e) {
    out.innerHTML = `<div class="box result-bad">${esc(e.message)}</div>`;
  }
}

// --- Wire up --------------------------------------------------------------
document.getElementById("decodeBtn").addEventListener("click", decode);
document.getElementById("persBtn").addEventListener("click", listPersonalities);
document.getElementById("fcBtn").addEventListener("click", upgradeFlashcode);
document.getElementById("exportBtn").addEventListener("click", exportSdr);
checkHealth();
loadFeatures();
