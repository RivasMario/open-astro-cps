use tokio::net::TcpListener;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use serde_json::{json, Value};
use std::path::{Path, PathBuf};

pub fn render_http_response(status: &str, content_type: &str, body: &str) -> Vec<u8> {
    format!(
        "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        status,
        content_type,
        body.len(),
        body
    )
    .into_bytes()
}

fn find_backups_dir() -> Option<PathBuf> {
    for cand in ["backups", "../backups", "../../backups"] {
        let p = Path::new(cand);
        if p.is_dir() {
            return Some(p.to_path_buf());
        }
    }
    None
}

fn safe_backup_path(filename: &str) -> Option<PathBuf> {
    if filename.contains('/') || filename.contains('\\') || filename.contains("..") || !filename.ends_with(".json") {
        return None;
    }
    let dir = find_backups_dir()?;
    let full = dir.join(filename);
    if full.is_file() { Some(full) } else { None }
}

fn url_decode(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let bytes = s.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' && i + 2 < bytes.len() {
            if let Ok(hex_str) = std::str::from_utf8(&bytes[i + 1..i + 3]) {
                if let Ok(val) = u8::from_str_radix(hex_str, 16) {
                    out.push(val as char);
                    i += 3;
                    continue;
                }
            }
        } else if bytes[i] == b'+' {
            out.push(' ');
            i += 1;
            continue;
        }
        out.push(bytes[i] as char);
        i += 1;
    }
    out
}

pub fn handle_http_request(req: &str) -> Vec<u8> {
    let (head, body) = if let Some((h, b)) = req.split_once("\r\n\r\n") {
        (h, b)
    } else if let Some((h, b)) = req.split_once("\n\n") {
        (h, b)
    } else {
        (req, "")
    };

    let lines: Vec<&str> = head.lines().collect();
    if lines.is_empty() {
        return render_http_response("400 Bad Request", "text/plain", "Invalid request");
    }

    let parts: Vec<&str> = lines[0].split_whitespace().collect();
    if parts.len() != 3 {
        return render_http_response("400 Bad Request", "text/plain", "Invalid request line");
    }
    let method = parts[0];
    let uri = parts[1];

    if method == "POST" && uri == "/api/save-channel" {
        let Ok(payload) = serde_json::from_str::<Value>(body.trim()) else {
            return render_http_response("400 Bad Request", "application/json", r#"{"error":"Invalid JSON body"}"#);
        };
        let Some(file) = payload.get("file").and_then(|v| v.as_str()) else {
            return render_http_response("400 Bad Request", "application/json", r#"{"error":"Missing file"}"#);
        };
        let Some(path) = safe_backup_path(file) else {
            return render_http_response("404 Not Found", "application/json", r#"{"error":"Backup file not found"}"#);
        };
        let Ok(raw) = std::fs::read_to_string(&path) else {
            return render_http_response("500 Internal Server Error", "application/json", r#"{"error":"Failed to read file"}"#);
        };
        let Ok(mut doc) = serde_json::from_str::<Value>(&raw) else {
            return render_http_response("500 Internal Server Error", "application/json", r#"{"error":"Invalid codeplug JSON"}"#);
        };
        let zi = payload.get("zone_index").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
        let ci = payload.get("channel_index").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
        let Some(ch) = doc.get_mut("zones")
            .and_then(|z| z.get_mut(zi))
            .and_then(|z| z.get_mut("channels"))
            .and_then(|c| c.get_mut(ci))
            .and_then(|c| c.as_object_mut()) else {
            return render_http_response("404 Not Found", "application/json", r#"{"error":"Zone/channel index not found"}"#);
        };

        let old_name = ch.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string();
        if let Some(n) = payload.get("name").and_then(|v| v.as_str()) {
            ch.insert("name".into(), json!(n));
        }
        if let Some(rx) = payload.get("rx_frequency").and_then(|v| v.as_f64()) {
            ch.insert("rx_frequency".into(), json!(rx));
        }
        if let Some(tx) = payload.get("tx_frequency").and_then(|v| v.as_f64()) {
            ch.insert("tx_frequency".into(), json!(tx));
        }
        if let Some(rx_only) = payload.get("rx_only").and_then(|v| v.as_bool()) {
            ch.insert("rx_only".into(), json!(rx_only));
        }
        let new_name = ch.get("name").and_then(|v| v.as_str()).unwrap_or("").to_string();

        let Ok(pretty) = serde_json::to_string_pretty(&doc) else {
            return render_http_response("500 Internal Server Error", "application/json", r#"{"error":"Serialize failed"}"#);
        };
        if std::fs::write(&path, pretty).is_err() {
            return render_http_response("500 Internal Server Error", "application/json", r#"{"error":"Write failed"}"#);
        }
        let resp = json!({
            "status": "saved",
            "file": file,
            "diff": format!("zone[{}].ch[{}]: '{}' -> '{}'", zi, ci, old_name, new_name)
        }).to_string();
        return render_http_response("200 OK", "application/json", &resp);
    }

    if method != "GET" {
        return render_http_response("405 Method Not Allowed", "text/plain", "Method not allowed");
    }

    match uri {
        "/" => {
            let html_content = r#"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OpenAstro CPS (Pure Rust)</title>
  <style>
    :root { --bg:#181a1f; --panel:#20232a; --well:#121418; --tree:#17191e; --hi:#3d4452; --lo:#0a0b0e; --text:#e2e6ed; --muted:#9aa3b2; --sel:#0b4f8c; --green:#3fb950; --red:#f85149; }
    * { box-sizing:border-box; border-radius:0 !important; }
    body { margin:0; font-family:Tahoma,"MS Sans Serif","Segoe UI",sans-serif; font-size:12px; background:var(--bg); color:var(--text); height:100vh; display:flex; flex-direction:column; }
    .titlebar { padding:4px 8px; background:linear-gradient(90deg,#0a246a,#1f4e8c); color:#fff; font-weight:700; font-size:12px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--lo); }
    .menubar { padding:2px 6px; background:var(--panel); border-bottom:1px solid var(--lo); display:flex; gap:14px; font-size:11px; color:var(--text); }
    .menubar span { padding:2px 5px; cursor:default; }
    .menubar span:hover { background:var(--sel); color:#fff; }
    header { padding:5px 8px; background:var(--panel); border-top:1px solid var(--hi); border-bottom:1px solid var(--lo); display:flex; justify-content:space-between; align-items:center; gap:8px; }
    .pill { padding:2px 6px; font-size:11px; font-weight:700; background:#2b1416; color:var(--red); border:1px inset var(--lo); }
    .okpill { background:#13291b; color:var(--green); }
    .main { display:flex; flex:1; overflow:hidden; }
    aside { width:245px; background:var(--tree); border-right:2px groove var(--hi); padding:6px; overflow-y:auto; }
    .tree-grp { font-size:11px; font-weight:700; color:var(--muted); margin:8px 0 3px; padding:2px 4px; border-bottom:1px solid #2a2e38; }
    .tree-item { padding:4px 8px; cursor:pointer; font-size:12px; margin-bottom:1px; border:1px solid transparent; display:flex; align-items:center; gap:5px; user-select:none; }
    .tree-item:hover { background:#242934; border-color:#343b49; }
    .tree-item.active { background:var(--sel); color:#fff; border:1px dotted #8ec3f6; }
    .tree-sub { margin-left:16px; border-left:1px dotted #4a5262; padding-left:6px; margin-bottom:3px; }
    .tree-leaf { padding:3px 6px; font-size:11px; color:var(--muted); cursor:pointer; }
    .tree-leaf:hover { background:#242934; color:var(--text); }
    .tbtn { font-family:Consolas,monospace; font-size:11px; color:#9aa3b2; }
    section { flex:1; padding:10px; overflow-y:auto; background:var(--bg); }
    .card { background:var(--panel); border-top:1px solid var(--hi); border-left:1px solid var(--hi); border-right:1px solid var(--lo); border-bottom:1px solid var(--lo); padding:10px; margin-bottom:10px; }
    h2 { margin:0 0 8px; font-size:12px; color:#c8d6eb; background:#282d37; padding:4px 8px; border-left:3px solid #3a7bd5; text-transform:none; }
    table { width:100%; border-collapse:collapse; font-size:12px; background:var(--well); }
    th, td { text-align:left; padding:4px 6px; border:1px solid #2b303c; }
    th { background:#252933; color:#cbd3e0; font-weight:700; }
    input, select { background:var(--well); color:var(--text); border-top:1px solid var(--lo); border-left:1px solid var(--lo); border-right:1px solid var(--hi); border-bottom:1px solid var(--hi); padding:3px 6px; font-size:12px; font-family:Tahoma,sans-serif; }
    button { background:#2b303b; color:var(--text); border-top:1px solid #4e5668; border-left:1px solid #4e5668; border-right:1px solid #0b0c0f; border-bottom:1px solid #0b0c0f; padding:3px 10px; font-size:12px; font-family:Tahoma,sans-serif; cursor:pointer; }
    button:active { border-top:1px solid #0b0c0f; border-left:1px solid #0b0c0f; border-right:1px solid #4e5668; border-bottom:1px solid #4e5668; }
    pre { background:var(--well); border:1px inset var(--lo); padding:8px; font-family:Consolas,monospace; font-size:12px; overflow:auto; margin:0; }
    .stash { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; }
    .slot { padding:8px; border:1px solid var(--hi); font-size:12px; }
    .c80 { background:#162b44; border-color:#2f6aa8; }
    .c81 { background:#3a2b12; border-color:#9e7423; }
    .c82 { background:#3a1619; border-color:#9e3138; }
    .statusbar { padding:3px 8px; background:var(--panel); border-top:1px solid var(--hi); display:flex; justify-content:space-between; font-size:11px; color:var(--muted); }
    .fam-bar { padding:6px 10px; margin-bottom:10px; border:1px solid var(--hi); display:flex; justify-content:space-between; align-items:center; font-weight:700; }
    .fam-port { background:#10253a; border-left:4px solid #388bfd; color:#a5d6ff; }
    .fam-mob { background:#2d210e; border-left:4px solid #d29922; color:#f2cc60; }
    .fam-err { background:#3a1619; border-left:4px solid #f85149; color:#ffa198; }
    .hidden { display:none; }
  </style>
</head>
<body>
  <div class="titlebar">
    <span>OpenAstro CPS R20 — ASTRO 25 Portable &amp; Mobile</span>
    <span title="Blocks writes to factory RF tuning memory (Partition 0x82)">[RF Tuning Write-Protect: ON]</span>
  </div>
  <div class="menubar">
    <span>File</span><span>Edit</span><span>View</span><span>Device</span><span>Tools</span><span>Help</span>
  </div>
  <header>
    <div><span class="pill okpill" id="healthBadge">Rust Engine</span></div>
    <div style="display:flex;align-items:center;gap:6px;">
      <span>Archive:</span>
      <select id="cpSelect" style="min-width:260px;"></select>
      <button onclick="loadCodeplug()">Open / Load</button>
      <span class="pill" title="Factory RF tuning / soft-pots (Partition 0x82) are hard-locked Read-Only in code so flashing a codeplug can never wipe your radio's frequency or TX power calibration.">RF Tuning Write-Protect: 0x82 Read-Only</span>
    </div>
  </header>
  <div class="main">
    <aside>
      <div class="tree-grp">Radio Configuration</div>
      <div class="tree-item active" onclick="toggleNode('sub-info','info',this)"><span class="tbtn" id="btn-sub-info">[-]</span> Radio Info &amp; FLASHcode</div>
      <div class="tree-sub" id="sub-info">
        <div class="tree-leaf" onclick="showPane('info')">Radio Identity (Model / Serial)</div>
        <div class="tree-leaf" onclick="showPane('info')">FLASHcode Feature Decoder</div>
      </div>

      <div class="tree-item" onclick="toggleNode('sub-zones','zones',this)"><span class="tbtn" id="btn-sub-zones">[+]</span> Zones &amp; Channels</div>
      <div class="tree-sub hidden" id="sub-zones">
        <div class="tree-leaf" onclick="filterZone(null)">All Zones &amp; Channels</div>
      </div>

      <div class="tree-item" onclick="toggleNode('sub-pers','pers',this)"><span class="tbtn" id="btn-sub-pers">[+]</span> Conv &amp; Trunk Personalities</div>
      <div class="tree-sub hidden" id="sub-pers">
        <div class="tree-leaf" onclick="showPane('pers')">Talkgroups (0x0FD0)</div>
        <div class="tree-leaf" onclick="showPane('pers')">Trunking Sites / Systems</div>
      </div>

      <div class="tree-item" onclick="toggleNode('sub-buttons','buttons',this)"><span class="tbtn" id="btn-sub-buttons">[+]</span> Buttons &amp; Scan Lists</div>
      <div class="tree-sub hidden" id="sub-buttons">
        <div class="tree-leaf" onclick="showPane('buttons')">Scan Lists (0x0FF1)</div>
        <div class="tree-leaf" onclick="showPane('buttons')">Controls &amp; Switches (0x0020)</div>
      </div>

      <div class="tree-item" onclick="toggleNode('sub-adp','adp',this)"><span class="tbtn" id="btn-sub-adp">[+]</span> Secure / ADP Keys</div>
      <div class="tree-sub hidden" id="sub-adp">
        <div class="tree-leaf" onclick="showPane('adp')">40-bit RC4 ADP Slots (0x005D)</div>
      </div>

      <div class="tree-grp">Hardware &amp; Custom Tools</div>
      <div class="tree-item" onclick="showPane('stash', this)"><span class="tbtn">[MEM]</span> Flash / EEPROM Map</div>
      <div class="tree-item" onclick="showPane('mobile', this)"><span class="tbtn">[XTL]</span> Mobile XTL / PM (G-Opts)</div>
      <div class="tree-item" onclick="showPane('custom', this)"><span class="tbtn">[EXT]</span> Custom (NAS / SDR / Relay)</div>
    </aside>
    <section>
      <div id="famBanner" class="fam-bar fam-port">
        <span id="famTitle">[PORTABLE] XTS / PRC-153 · Q/H Options · USB 0cad:1001/1002</span>
        <span id="famGuard">[GUARD] Cross-Flash Lock: PORTABLE ONLY (Mobile M*/XTL blocked)</span>
      </div>
      <div id="pane-info" class="pane">
        <div class="card">
          <h2>Loaded Radio Identity</h2>
          <pre id="radioMeta">Select a codeplug JSON from the header dropdown...</pre>
        </div>
        <div class="card">
          <h2>FLASHcode Decoder (0x81:1006)</h2>
          <div style="margin-bottom:10px;">
            <input id="fcStart" value="000008002410" style="width:160px;font-family:Consolas,monospace;" />
            <button onclick="calcFc()">Decode / Check</button>
            <button onclick="document.getElementById('fcStart').value='FBFFFFB7F3FF';calcFc();">Max Non-UCM</button>
          </div>
          <pre id="fcOut">Loading...</pre>
        </div>
      </div>

      <div id="pane-zones" class="pane hidden">
        <div class="card">
          <h2>Zones &amp; Channels (Live JSON Inspector / Inline Editor)</h2>
          <pre id="editStatus" style="margin-bottom:10px;">Edit any channel name/RX/TX and click Save to update the codeplug JSON.</pre>
          <table><thead><tr><th>Zone</th><th>Channel</th><th>RX (MHz)</th><th>TX (MHz)</th><th>Mode / NAC / PL</th><th>Action</th></tr></thead><tbody id="chanBody"></tbody></table>
        </div>
      </div>

      <div id="pane-pers" class="pane hidden">
        <div class="card">
          <h2>Trunking Talkgroups &amp; Sites (0x0FFB / 0x0FD0 / 0x0FF8)</h2>
          <pre id="persOut">Load a codeplug JSON to inspect talkgroups, sites, and trunking systems...</pre>
        </div>
      </div>

      <div id="pane-buttons" class="pane hidden">
        <div class="card">
          <h2>Buttons, Switches &amp; Scan Lists (0x0020 / 0x003C / 0x0FF1)</h2>
          <pre id="scanOut">Load a codeplug JSON to inspect scan lists...</pre>
        </div>
      </div>

      <div id="pane-adp" class="pane hidden">
        <div class="card">
          <h2>Secure / ADP 40-bit RC4 Keys (0x80:0x005D)</h2>
          <pre id="adpOut">Load a codeplug JSON to inspect encryption key slots...</pre>
        </div>
      </div>

      <div id="pane-stash" class="pane hidden">
        <div class="card">
          <h2>Radio Memory Map &amp; What OpenAstro Protects</h2>
          <p style="margin:0 0 10px;color:var(--muted);">Motorola stores channels, identity, and factory RF calibration in separate memory partitions. OpenAstro enforces hard write-protections so normal programming cannot damage your radio:</p>
          <div class="stash">
            <div class="slot c80" style="grid-column:span 2;"><strong>Codeplug (0x80 · 384 KB)</strong><br/>Read / Write (Normal Programming)<br/><small>Channels, zones, scan lists, personalities, ADP keys. Safe to edit and flash.</small></div>
            <div class="slot c81" style="grid-column:span 2;"><strong>Identity / EEPROM (0x81 · 16 KB)</strong><br/>Write-Protected (Needs 0x0107 Unlock)<br/><small>Serial number &amp; FLASHcode feature bits. Blocked unless explicitly unlocked.</small></div>
            <div class="slot c81" style="grid-column:span 2;"><strong>System Area (0x85)</strong><br/>Write-Protected<br/><small>Internal system blocks; untouched during normal codeplug writes.</small></div>
            <div class="slot c82" style="grid-column:span 2;"><strong>Factory RF Tuning (0x82 · 512 KB)</strong><br/>HARD-LOCKED READ-ONLY<br/><small>Oscillator warp, TX power, squelch soft-pots. OpenAstro blocks all writes here so you never lose RF alignment.</small></div>
          </div>
        </div>
      </div>

      <div id="pane-mobile" class="pane hidden">
        <div class="card">
          <h2>Mobile ASTRO 25 (XTL 1500 / 2500 / 5000 / PM 1500) — G-Options</h2>
          <pre id="mobOpts">Loading mobile schema...</pre>
        </div>
      </div>

      <div id="pane-custom" class="pane hidden">
        <div class="card">
          <h2>Custom OpenAstro Features (Not in Original CPS)</h2>
          <pre>open-astro make-nas --tgid 1188 --tg-name "SEATTLE DISP" -o seattle_nas.json
open-astro export-sdr backups/Radio4_RedmondPD_721CLZ0655_codeplug.json -o backups/sdr_exports
open_astro_cli.exe relay --listen 127.0.0.1:8002 --target 192.168.128.1:8002</pre>
        </div>
      </div>
    </section>
  </div>
  <div class="statusbar">
    <span>Ready · ASTRO 25 Portable (XTS/PRC-153) &amp; Mobile (XTL/PM)</span>
    <span>192.168.128.1:8002 · RF Tuning (0x82) Write-Protected</span>
  </div>
  <script>
    let activeFile = '';
    let activeCp = null;
    function showPane(name, el) {
      document.querySelectorAll('.pane').forEach(p => p.classList.add('hidden'));
      document.getElementById('pane-' + name).classList.remove('hidden');
      if (el) {
        document.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
        el.classList.add('active');
      }
    }
    function toggleNode(subId, paneName, el) {
      showPane(paneName, el);
      const sub = document.getElementById(subId);
      const btn = document.getElementById('btn-' + subId);
      if (sub) {
        const opening = sub.classList.contains('hidden');
        sub.classList.toggle('hidden');
        if (btn) btn.textContent = opening ? '[-]' : '[+]';
      }
    }
    function filterZone(zoneIdx) {
      showPane('zones');
      if (!activeCp) return;
      renderChannels(activeCp, zoneIdx);
    }
    function renderChannels(cp, onlyZoneIdx) {
      const b = document.getElementById('chanBody');
      b.innerHTML = '';
      (cp.zones || []).forEach((z, zi) => {
        if (onlyZoneIdx !== null && onlyZoneIdx !== undefined && zi !== onlyZoneIdx) return;
        (z.channels || []).forEach((c, ci) => {
          const tr = document.createElement('tr');
          const mode = `${c.voice_type || ''} ${c.rx_nac || ''} ${c.rx_pl_tone ? 'PL ' + c.rx_pl_tone : ''} ${c.rx_only ? '[RX-ONLY]' : ''}`;
          tr.innerHTML = `<td>${z.name || z.zone_number}</td>
            <td><input id="n_${zi}_${ci}" value="${c.name || ''}" style="width:130px"/></td>
            <td><input id="rx_${zi}_${ci}" value="${c.rx_frequency ?? ''}" style="width:95px"/></td>
            <td><input id="tx_${zi}_${ci}" value="${c.tx_frequency ?? ''}" style="width:95px"/></td>
            <td>${mode} <label style="margin-left:6px;"><input type="checkbox" id="rxo_${zi}_${ci}" ${c.rx_only ? 'checked' : ''}/> RX-Only</label></td>
            <td><button onclick="saveChan(${zi},${ci})">Save</button></td>`;
          b.appendChild(tr);
        });
      });
    }
    fetch('/api/health').then(r=>r.json()).then(d=>{
      document.getElementById('healthBadge').textContent = `Rust Engine (${d.status})`;
    });
    async function calcFc() {
      const s = document.getElementById('fcStart').value;
      const r = await fetch('/api/flashcode?start=' + encodeURIComponent(s));
      document.getElementById('fcOut').textContent = await r.text();
    }
    async function initBackups() {
      const r = await fetch('/api/backups');
      const files = await r.json();
      const sel = document.getElementById('cpSelect');
      files.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f; opt.textContent = f;
        if (f.includes('721CLZ0655_codeplug.json')) opt.selected = true;
        sel.appendChild(opt);
      });
      if (files.length > 0) loadCodeplug();
    }
    async function loadCodeplug() {
      activeFile = document.getElementById('cpSelect').value;
      if (!activeFile) return;
      const r = await fetch('/api/codeplug?file=' + encodeURIComponent(activeFile));
      const cp = await r.json();
      activeCp = cp;
      const mdl = (cp.radio_model || cp.model || '').toUpperCase().trim();
      const isPort = mdl.includes('XTS') || mdl.includes('PRC') || mdl.includes('MT 1500') || mdl.includes('PR 1500') || /^H\d{2}/.test(mdl);
      const isMob = !isPort && (mdl.includes('XTL') || mdl.includes('PM 1500') || /^M\d{2}/.test(mdl));
      const banner = document.getElementById('famBanner');
      banner.className = 'fam-bar ' + (isMob ? 'fam-mob' : 'fam-port');
      document.getElementById('famTitle').textContent = isMob
        ? `[MOBILE] ${cp.radio_model || cp.model || 'XTL / PM'} · G* Options · USB 0cad:1003/1010-1015`
        : `[PORTABLE] ${cp.radio_model || cp.model || 'XTS / PRC-153'} · Q/H Options · USB 0cad:1001/1002`;
      document.getElementById('famGuard').textContent = isMob
        ? '[GUARD] Cross-Flash Lock: MOBILE ONLY (Portable H*/XTS writes blocked)'
        : '[GUARD] Cross-Flash Lock: PORTABLE ONLY (Mobile M*/XTL writes blocked)';
      document.getElementById('radioMeta').textContent = JSON.stringify({
        file: activeFile,
        detected_family: isMob ? 'MOBILE (XTL/PM - G* Options)' : 'PORTABLE (XTS/PRC-153 - Q/H Options)',
        radio_model: cp.radio_model || cp.model,
        serial_number: cp.serial_number || cp.serial,
        bandsplit: cp.bandsplit,
        flashcode: cp.flashcode,
        zone_count: (cp.zones || []).length
      }, null, 2);
      if (cp.flashcode) {
        document.getElementById('fcStart').value = cp.flashcode.replaceAll('-', '').slice(0, 12);
        calcFc();
      }
      const zSub = document.getElementById('sub-zones');
      zSub.innerHTML = '<div class="tree-leaf" onclick="filterZone(null)">All Zones (' + (cp.zones || []).length + ')</div>';
      (cp.zones || []).forEach((z, zi) => {
        const d = document.createElement('div');
        d.className = 'tree-leaf';
        d.textContent = (z.name || ('Zone ' + (z.zone_number || zi + 1))) + ' (' + (z.channels || []).length + ')';
        d.onclick = () => filterZone(zi);
        zSub.appendChild(d);
      });
      renderChannels(cp, null);
      document.getElementById('persOut').textContent = JSON.stringify({
        talkgroups: cp.talkgroups || [],
        sites: cp.sites || [],
        systems: cp.systems || []
      }, null, 2);
      document.getElementById('scanOut').textContent = JSON.stringify(cp.scan_lists || [], null, 2);
      document.getElementById('adpOut').textContent = JSON.stringify(cp.encryption_keys || [], null, 2);
    }
    async function saveChan(zi, ci) {
      const body = {
        file: activeFile,
        zone_index: zi,
        channel_index: ci,
        name: document.getElementById(`n_${zi}_${ci}`).value,
        rx_frequency: parseFloat(document.getElementById(`rx_${zi}_${ci}`).value),
        tx_frequency: parseFloat(document.getElementById(`tx_${zi}_${ci}`).value),
        rx_only: document.getElementById(`rxo_${zi}_${ci}`).checked
      };
      const r = await fetch('/api/save-channel', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body) });
      document.getElementById('editStatus').textContent = await r.text();
    }
    initBackups();
    fetch('/api/mobile-options').then(r=>r.text()).then(t=>{
      document.getElementById('mobOpts').textContent = t;
    });
    calcFc();
  </script>
</body>
</html>"#;
            render_http_response("200 OK", "text/html; charset=utf-8", html_content)
        }
        "/api/backups" => {
            let mut files = Vec::new();
            if let Some(dir) = find_backups_dir() {
                if let Ok(entries) = std::fs::read_dir(dir) {
                    for e in entries.flatten() {
                        let name = e.file_name().to_string_lossy().to_string();
                        if name.ends_with(".json") {
                            files.push(name);
                        }
                    }
                }
            }
            files.sort();
            render_http_response("200 OK", "application/json", &json!(files).to_string())
        }
        _ if uri.starts_with("/api/codeplug") => {
            let file = uri
                .splitn(2, '?')
                .nth(1)
                .and_then(|q| q.split('&').find_map(|p| p.strip_prefix("file=")))
                .map(url_decode)
                .unwrap_or_default();
            match safe_backup_path(&file).and_then(|p| std::fs::read_to_string(p).ok()) {
                Some(raw) => render_http_response("200 OK", "application/json", &raw),
                None => render_http_response("404 Not Found", "application/json", r#"{"error":"Codeplug not found"}"#),
            }
        }
        "/api/sample-channels" => {
            let sample = json!([
                {"zone":"TEAM SECURE","name":"TEAM CLEAR","rx":"851.51250","tx":"851.51250","mode":"P25 NAC:$293"},
                {"zone":"TEAM SECURE","name":"TEAM ENCRYPT","rx":"852.01250","tx":"852.01250","mode":"P25 NAC:$293 [ADP]"},
                {"zone":"800 INTEROP","name":"8CALL90","rx":"851.01250","tx":"806.01250","mode":"Analog PL 156.7"},
                {"zone":"PS MONITOR","name":"PSERN CTRL 1","rx":"851.88750","tx":"0.00000","mode":"P25 [RX-ONLY LOCK]"}
            ]).to_string();
            render_http_response("200 OK", "application/json", &sample)
        }
        "/api/mobile-options" => {
            const MOBILE_OPTS: &str = include_str!("../../../schema/mobile_flashcode_options.json");
            render_http_response("200 OK", "application/json", MOBILE_OPTS)
        }
        _ if uri.starts_with("/api/check-family") => {
            let query = uri.splitn(2, '?').nth(1).unwrap_or("");
            let radio_model = query.split('&').find_map(|p| p.strip_prefix("radio_model=")).map(url_decode).unwrap_or_default();
            let cp_model = query.split('&').find_map(|p| p.strip_prefix("codeplug_model=")).map(url_decode).unwrap_or_default();
            match crate::flashcode::guard_family_match(&radio_model, &cp_model) {
                Ok(fam) => render_http_response("200 OK", "application/json", &json!({"ok": true, "family": fam.to_string()}).to_string()),
                Err(e) => render_http_response("409 Conflict", "application/json", &json!({"ok": false, "error": e.to_string()}).to_string()),
            }
        }
        "/api/health" => {
            let json_content = json!({
                "status": "ok",
                "engine": "rust"
            }).to_string();
            render_http_response("200 OK", "application/json", &json_content)
        }
        _ if uri.starts_with("/api/flashcode") => {
            let start = uri
                .splitn(2, '?')
                .nth(1)
                .and_then(|q| q.split('&').find_map(|p| p.strip_prefix("start=")))
                .filter(|s| !s.is_empty())
                .unwrap_or("000008002410")
                .to_string();

            match crate::flashcode::format_flashcode(&start) {
                Ok(flashcode) => {
                    let json_content = json!({
                        "flashcode": flashcode
                    }).to_string();
                    render_http_response("200 OK", "application/json", &json_content)
                }
                Err(_) => render_http_response("400 Bad Request", "text/plain", "Error formatting flashcode"),
            }
        }
        _ => render_http_response("404 Not Found", "text/plain", "Not Found"),
    }
}

pub async fn run_web_server(port: u16) -> anyhow::Result<()> {
    let listener = TcpListener::bind(format!("127.0.0.1:{}", port)).await?;
    println!("Listening on 127.0.0.1:{}", port);

    loop {
        let (mut socket, _) = listener.accept().await?;
        tokio::spawn(async move {
            let mut buffer = [0; 8192];
            if let Ok(Ok(n)) = tokio::time::timeout(
                std::time::Duration::from_secs(5),
                socket.read(&mut buffer),
            )
            .await
            {
                if n > 0 {
                    let request = String::from_utf8_lossy(&buffer[..n]);
                    let response = handle_http_request(&request);
                    let _ = socket.write_all(&response).await;
                }
            }
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_handle_http_request_root() {
        let request = "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let response = handle_http_request(request);
        assert!(response.starts_with(b"HTTP/1.1 200 OK"));
        assert!(String::from_utf8_lossy(&response).contains("RF Tuning Write-Protect: 0x82 Read-Only"));
    }

    #[test]
    fn test_handle_http_request_health() {
        let request = "GET /api/health HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let response = handle_http_request(request);
        assert!(response.starts_with(b"HTTP/1.1 200 OK"));
        assert!(String::from_utf8_lossy(&response).contains("\"status\":\"ok\""));
    }

    #[test]
    fn test_handle_http_request_flashcode() {
        let request = "GET /api/flashcode?start=000008002410 HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let response = handle_http_request(request);
        assert!(response.starts_with(b"HTTP/1.1 200 OK"));
        assert!(String::from_utf8_lossy(&response).contains("\"flashcode\":\"000008-002410-2\""));
    }

    #[test]
    fn test_handle_http_request_backups_and_traversal() {
        let req_list = "GET /api/backups HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let resp_list = handle_http_request(req_list);
        assert!(resp_list.starts_with(b"HTTP/1.1 200 OK"));

        let req_trav = "GET /api/codeplug?file=../../Cargo.toml HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let resp_trav = handle_http_request(req_trav);
        assert!(resp_trav.starts_with(b"HTTP/1.1 404 Not Found"));
    }

    #[test]
    fn test_handle_http_request_mobile_options() {
        let request = "GET /api/mobile-options HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let response = handle_http_request(request);
        assert!(response.starts_with(b"HTTP/1.1 200 OK"));
        let body = String::from_utf8_lossy(&response);
        assert!(body.contains("\"g_option_count\": 73"));
        assert!(body.contains("PatMobDepot.exe"));
        assert!(body.contains("G51"));
    }

    #[test]
    fn test_handle_http_request_missing() {
        let request = "GET /missing HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let response = handle_http_request(request);
        assert!(response.starts_with(b"HTTP/1.1 404 Not Found"));
    }
}
