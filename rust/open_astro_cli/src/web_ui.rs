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
    :root { --bg:#0c0e12; --panel:#14171e; --tree:#101319; --border:#2a3140; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; --green:#3fb950; --yellow:#d29922; --red:#f85149; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Segoe UI",-apple-system,sans-serif; background:var(--bg); color:var(--text); height:100vh; display:flex; flex-direction:column; }
    header { padding:10px 18px; background:var(--panel); border-bottom:1px solid var(--border); display:flex; justify-content:space-between; align-items:center; gap:12px; }
    .pill { padding:2px 8px; border-radius:999px; font-size:11px; font-weight:700; background:rgba(248,81,73,0.18); color:var(--red); }
    .okpill { background:rgba(63,185,80,0.18); color:var(--green); }
    .main { display:flex; flex:1; overflow:hidden; }
    aside { width:260px; background:var(--tree); border-right:1px solid var(--border); padding:12px; overflow-y:auto; }
    .tree-grp { font-size:11px; text-transform:uppercase; color:var(--muted); margin:12px 0 6px; letter-spacing:0.6px; }
    .tree-item { padding:7px 10px; border-radius:6px; cursor:pointer; font-size:13px; margin-bottom:2px; }
    .tree-item:hover { background:#1b202b; }
    .tree-item.active { background:#1f6feb; color:#fff; font-weight:600; }
    section { flex:1; padding:20px; overflow-y:auto; }
    .card { background:var(--panel); border:1px solid var(--border); border-radius:8px; padding:16px; margin-bottom:16px; }
    h2 { margin:0 0 12px; font-size:15px; color:var(--accent); text-transform:uppercase; }
    table { width:100%; border-collapse:collapse; font-size:13px; }
    th, td { text-align:left; padding:7px; border-bottom:1px solid #222733; }
    th { color:var(--muted); }
    input, select, button { background:#0b0d11; color:var(--text); border:1px solid var(--border); border-radius:6px; padding:6px 9px; font-size:13px; }
    button { background:#1f6feb; border-color:#388bfd; font-weight:600; cursor:pointer; }
    pre { background:#090b0f; border:1px solid var(--border); border-radius:6px; padding:10px; font-size:12px; overflow:auto; }
    .stash { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
    .slot { border-radius:6px; padding:10px; border:1px solid rgba(255,255,255,0.14); font-size:12px; }
    .c80 { background:#162b44; border-color:#2f6aa8; }
    .c81 { background:#3a2b12; border-color:#9e7423; }
    .c82 { background:#3a1619; border-color:#9e3138; }
    .hidden { display:none; }
  </style>
</head>
<body>
  <header>
    <div><strong>OpenAstro CPS</strong> <span class="pill okpill" id="healthBadge">Rust Engine</span></div>
    <div style="display:flex;align-items:center;gap:8px;">
      <select id="cpSelect" style="min-width:240px;"></select>
      <button onclick="loadCodeplug()">Load Codeplug</button>
      <span class="pill">Partition 0x82 Firewall: ACTIVE</span>
    </div>
  </header>
  <div class="main">
    <aside>
      <div class="tree-grp">Radio Configuration</div>
      <div class="tree-item active" onclick="showPane('info', this)">📁 Radio Info &amp; FLASHcode</div>
      <div class="tree-item" onclick="showPane('zones', this)">📁 Zones &amp; Channels</div>
      <div class="tree-item" onclick="showPane('pers', this)">📁 Conv &amp; Trunk Personalities</div>
      <div class="tree-item" onclick="showPane('buttons', this)">📁 Buttons &amp; Scan Lists</div>
      <div class="tree-item" onclick="showPane('adp', this)">📁 Secure / ADP Keys</div>
      <div class="tree-grp">Hardware &amp; Custom Tools</div>
      <div class="tree-item" onclick="showPane('stash', this)">🧱 Flash / EEPROM Map</div>
      <div class="tree-item" onclick="showPane('mobile', this)">🚗 Mobile XTL / PM (G-Opts)</div>
      <div class="tree-item" onclick="showPane('custom', this)">🚀 Custom (NAS / SDR / Relay)</div>
    </aside>
    <section>
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
        <div class="card"><h2>Conventional &amp; Trunking Personalities (0x0FFB / 0x0FD0 / 0x0FF8)</h2><p style="color:var(--muted);">Phase 5 target: per-personality TX power, TOT, squelch, and talkgroup lists.</p></div>
      </div>

      <div id="pane-buttons" class="pane hidden">
        <div class="card"><h2>Buttons, Switches &amp; Scan Lists (0x0020 / 0x003C / 0x0FF1)</h2><p style="color:var(--muted);">CLI active: <code>open-astro buttons backups/205CFR2930.cpg</code></p></div>
      </div>

      <div id="pane-adp" class="pane hidden">
        <div class="card"><h2>Secure / ADP 40-bit RC4 Keys (0x80:0x005D)</h2><p style="color:var(--muted);">Verified persistent on simulated XTS 2500 &amp; XTS 5000 (`0x0034`, `0x0037`, `0x0038`, `0x005D`).</p></div>
      </div>

      <div id="pane-stash" class="pane hidden">
        <div class="card">
          <h2>Radio Flash &amp; EEPROM Partitions (Tarkov Map)</h2>
          <div class="stash">
            <div class="slot c80" style="grid-column:span 2;"><strong>0x80 Codeplug (384 KB)</strong><br/>164 ISH types · RW<br/><small>Channels, Zones, ADP 0x005D</small></div>
            <div class="slot c81" style="grid-column:span 2;"><strong>0x81 EEPROM (16 KB)</strong><br/>3 types · RW-Locked (0x0107)<br/><small>0x1004 Serial, 0x1005/06 FLASHcode</small></div>
            <div class="slot c81" style="grid-column:span 2;"><strong>0x85 System</strong><br/>2 types · RW-Locked<br/><small>0x12BE, 0x12BF</small></div>
            <div class="slot c82" style="grid-column:span 2;"><strong>0x82 RF Soft-Pots (512 KB)</strong><br/>ReadOnly · BLOCKED<br/><small>Never written by OpenAstro</small></div>
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
  <script>
    let activeFile = '';
    function showPane(name, el) {
      document.querySelectorAll('.pane').forEach(p => p.classList.add('hidden'));
      document.getElementById('pane-' + name).classList.remove('hidden');
      document.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
      if (el) el.classList.add('active');
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
      document.getElementById('radioMeta').textContent = JSON.stringify({
        file: activeFile,
        radio_model: cp.radio_model,
        serial_number: cp.serial_number,
        bandsplit: cp.bandsplit,
        flashcode: cp.flashcode,
        zone_count: (cp.zones || []).length
      }, null, 2);
      if (cp.flashcode) {
        document.getElementById('fcStart').value = cp.flashcode.replaceAll('-', '').slice(0, 12);
        calcFc();
      }
      const b = document.getElementById('chanBody');
      b.innerHTML = '';
      (cp.zones || []).forEach((z, zi) => {
        (z.channels || []).forEach((c, ci) => {
          const tr = document.createElement('tr');
          const mode = `${c.voice_type || ''} ${c.rx_nac || ''} ${c.rx_pl_tone ? 'PL ' + c.rx_pl_tone : ''} ${c.rx_only ? '[RX-ONLY]' : ''}`;
          tr.innerHTML = `<td>${z.name || z.zone_number}</td>
            <td><input id="n_${zi}_${ci}" value="${c.name || ''}" style="width:130px"/></td>
            <td><input id="rx_${zi}_${ci}" value="${c.rx_frequency ?? ''}" style="width:95px"/></td>
            <td><input id="tx_${zi}_${ci}" value="${c.tx_frequency ?? ''}" style="width:95px"/></td>
            <td>${mode}</td>
            <td><button onclick="saveChan(${zi},${ci})">Save</button></td>`;
          b.appendChild(tr);
        });
      });
    }
    async function saveChan(zi, ci) {
      const body = {
        file: activeFile,
        zone_index: zi,
        channel_index: ci,
        name: document.getElementById(`n_${zi}_${ci}`).value,
        rx_frequency: parseFloat(document.getElementById(`rx_${zi}_${ci}`).value),
        tx_frequency: parseFloat(document.getElementById(`tx_${zi}_${ci}`).value)
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
        assert!(String::from_utf8_lossy(&response).contains("Partition 0x82 Firewall: ACTIVE"));
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
    fn test_handle_http_request_missing() {
        let request = "GET /missing HTTP/1.1\r\nHost: localhost\r\n\r\n";
        let response = handle_http_request(request);
        assert!(response.starts_with(b"HTTP/1.1 404 Not Found"));
    }
}
