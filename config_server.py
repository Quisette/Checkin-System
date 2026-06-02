"""
Config GUI server — run with: python config_server.py
Then open: http://localhost:8765
"""

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
PORT = 8765

# Shared test-run state
_test_lock   = threading.Lock()
_test_result = {}   # { key: { running, success, log } }

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Checkin Config</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         background: #f5f5f7; color: #1d1d1f; min-height: 100vh; padding: 32px 16px; }
  h1 { font-size: 24px; font-weight: 700; }
  .projects { display: flex; flex-direction: column; gap: 20px; max-width: 780px; margin: 0 auto; }

  .card { background: #fff; border-radius: 14px; padding: 24px;
          box-shadow: 0 2px 8px rgba(0,0,0,.08); }
  .card-header { display: flex; justify-content: space-between; align-items: center;
                 margin-bottom: 20px; }
  .card-title { font-size: 16px; font-weight: 600; }

  .field { margin-bottom: 14px; }
  .field label { display: block; font-size: 12px; font-weight: 500; color: #6e6e73;
                 margin-bottom: 4px; text-transform: uppercase; letter-spacing: .4px; }
  .field input { width: 100%; padding: 9px 12px; border: 1px solid #d2d2d7;
                 border-radius: 8px; font-size: 14px; font-family: inherit;
                 background: #fafafa; transition: border .15s; }
  .field input:focus { outline: none; border-color: #0071e3; background: #fff; }
  .row { display: flex; gap: 12px; }
  .row .field { flex: 1; }

  .ranges-label { font-size: 12px; font-weight: 500; color: #6e6e73;
                  text-transform: uppercase; letter-spacing: .4px; margin-bottom: 8px; }
  .range-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
  .range-row input { flex: 1; padding: 8px 10px; border: 1px solid #d2d2d7;
                     border-radius: 8px; font-size: 13px; background: #fafafa; }
  .range-row input:focus { outline: none; border-color: #0071e3; background: #fff; }
  .range-sep { font-size: 13px; color: #6e6e73; flex-shrink: 0; }

  .btn { border: none; border-radius: 8px; font-size: 13px; font-weight: 500;
         cursor: pointer; padding: 7px 14px; transition: opacity .15s; }
  .btn:hover:not(:disabled) { opacity: .82; }
  .btn:disabled { opacity: .45; cursor: default; }
  .btn-primary { background: #0071e3; color: #fff; }
  .btn-danger  { background: #ff3b30; color: #fff; }
  .btn-ghost   { background: #e8e8ed; color: #1d1d1f; }
  .btn-test    { background: #ff9f0a; color: #fff; }
  .btn-sm      { padding: 5px 10px; font-size: 12px; }

  .card-actions { display: flex; gap: 8px; margin-top: 18px; flex-wrap: wrap; }

  /* Test result panel */
  .test-panel { margin-top: 16px; border-radius: 10px; overflow: hidden;
                border: 1px solid #d2d2d7; display: none; }
  .test-panel.visible { display: block; }
  .test-panel-header { padding: 8px 14px; font-size: 13px; font-weight: 600;
                       display: flex; align-items: center; gap: 8px; }
  .test-panel-header.running  { background: #fff3cd; color: #856404; }
  .test-panel-header.success  { background: #d1e7dd; color: #0f5132; }
  .test-panel-header.fail     { background: #f8d7da; color: #842029; }
  .test-log { background: #1c1c1e; color: #e5e5ea; font-family: monospace;
              font-size: 12px; padding: 12px 14px; max-height: 220px;
              overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
  .spinner { display: inline-block; width: 12px; height: 12px;
             border: 2px solid currentColor; border-top-color: transparent;
             border-radius: 50%; animation: spin .7s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }

  #toast { position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
           background: #1d1d1f; color: #fff; padding: 10px 20px; border-radius: 20px;
           font-size: 14px; opacity: 0; transition: opacity .25s; pointer-events: none; z-index: 99; }
  #toast.show { opacity: 1; }

  .add-project-btn { max-width: 780px; margin: 0 auto; display: block; width: 100%;
                     padding: 14px; border: 2px dashed #d2d2d7; border-radius: 14px;
                     background: transparent; color: #6e6e73; font-size: 15px;
                     cursor: pointer; transition: border-color .15s, color .15s; }
  .add-project-btn:hover { border-color: #0071e3; color: #0071e3; }
  .checked-badge { font-size: 11px; background: #e8f4fd; color: #0071e3;
                   padding: 2px 8px; border-radius: 10px; margin-left: 8px; }
</style>
</head>
<body>
<div style="max-width:780px;margin:0 auto">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
    <h1>Checkin Config</h1>
    <button class="btn btn-primary" onclick="saveAll()">Save</button>
  </div>
  <div class="projects" id="projects"></div>
  <br>
  <button class="add-project-btn" onclick="addProject()">+ Add Project</button>
</div>
<div id="toast"></div>

<script>
let config = {};

async function load() {
  const res = await fetch('/config');
  config = await res.json();
  render();
}

function render() {
  const container = document.getElementById('projects');
  container.innerHTML = '';
  for (const [key, proj] of Object.entries(config)) {
    container.appendChild(makeCard(key, proj));
  }
}

function makeCard(key, proj) {
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.key = key;
  const checkedCount = (proj.checked_in_date || []).length;

  card.innerHTML = `
    <div class="card-header">
      <span class="card-title">
        ${key}
        ${checkedCount ? `<span class="checked-badge">${checkedCount} checked in</span>` : ''}
      </span>
      <button class="btn btn-danger btn-sm" onclick="removeProject('${key}')">Remove</button>
    </div>

    <div class="field">
      <label>Project Name</label>
      <input data-field="projectName" value="${esc(proj.projectName || '')}" placeholder="計畫名稱">
    </div>
    <div class="field">
      <label>Project Time (Taiwan format)</label>
      <input data-field="projectTime" value="${esc(proj.projectTime || '')}" placeholder="1140922 ~ 1150327">
    </div>
    <div class="field">
      <label>Sign-out Message</label>
      <input data-field="message" value="${esc(proj.message || '')}" placeholder="協助計畫執行">
    </div>
    <div class="row">
      <div class="field">
        <label>Check-in Time</label>
        <input type="time" data-field="start_hour" value="${(proj.start_hour||'10:00:00').slice(0,5)}" step="1">
      </div>
      <div class="field">
        <label>Check-out Time</label>
        <input type="time" data-field="end_hour" value="${(proj.end_hour||'18:30:00').slice(0,5)}" step="1">
      </div>
    </div>

    <div class="ranges-label" style="margin-top:4px">Date Ranges</div>
    <div class="range-list" id="ranges-${key}">
      ${(proj.date_ranges || []).map((r, i) => rangeRow(key, i, r)).join('')}
    </div>
    <button class="btn btn-ghost btn-sm" style="margin-top:4px" onclick="addRange('${key}')">+ Add Range</button>

    <div class="card-actions">
      <button class="btn btn-test btn-sm" id="test-btn-${key}" onclick="runTest('${key}')">▶ Test Check-in/out</button>
      <button class="btn btn-ghost btn-sm" onclick="clearCheckins('${key}')">Clear History</button>
    </div>

    <div class="test-panel" id="test-panel-${key}">
      <div class="test-panel-header" id="test-header-${key}"></div>
      <div class="test-log" id="test-log-${key}"></div>
    </div>
  `;
  return card;
}

function rangeRow(key, i, r) {
  return `
    <div class="range-row" id="range-${key}-${i}">
      <input type="date" data-range-start value="${r.start_date || ''}">
      <span class="range-sep">→</span>
      <input type="date" data-range-end value="${r.end_date || ''}">
      <button class="btn btn-danger btn-sm" onclick="removeRange('${key}',${i})">✕</button>
    </div>`;
}

function addRange(key) {
  const list = document.getElementById(`ranges-${key}`);
  const i = list.children.length;
  list.insertAdjacentHTML('beforeend', rangeRow(key, i, { start_date: '', end_date: '' }));
}

function removeRange(key, i) {
  document.getElementById(`range-${key}-${i}`)?.remove();
  const list = document.getElementById(`ranges-${key}`);
  [...list.children].forEach((row, idx) => {
    row.id = `range-${key}-${idx}`;
    row.querySelector('button').setAttribute('onclick', `removeRange('${key}',${idx})`);
  });
}

function addProject() {
  const key = 'project' + (Object.keys(config).length + 1);
  config[key] = { projectName:'', projectTime:'', message:'',
                  start_hour:'10:00:00', end_hour:'18:30:00',
                  date_ranges:[], checked_in_date:[] };
  render();
  setTimeout(() => document.querySelector(`[data-key="${key}"]`)
    ?.scrollIntoView({ behavior:'smooth' }), 50);
}

function removeProject(key) {
  if (!confirm(`Remove "${key}"?`)) return;
  delete config[key];
  render();
}

function clearCheckins(key) {
  if (!confirm('Clear all check-in history for this project?')) return;
  config[key].checked_in_date = [];
  toast('Check-in history cleared');
}

// ── Test check-in/out ────────────────────────────────────────────────────────

async function runTest(key) {
  const btn    = document.getElementById(`test-btn-${key}`);
  const panel  = document.getElementById(`test-panel-${key}`);
  const header = document.getElementById(`test-header-${key}`);
  const logEl  = document.getElementById(`test-log-${key}`);

  btn.disabled = true;
  panel.classList.add('visible');
  header.className = 'test-panel-header running';
  header.innerHTML = '<span class="spinner"></span> Running check-in/out…';
  logEl.textContent = '';

  // Collect current card data for this project
  const card = document.querySelector(`[data-key="${key}"]`);
  const get  = f => card.querySelector(`[data-field="${f}"]`)?.value ?? '';
  const startHour = get('start_hour');
  const endHour   = get('end_hour');
  const proj = {
    projectName: get('projectName'),
    projectTime: get('projectTime'),
    message:     get('message'),
    start_hour:  startHour.length === 5 ? startHour + ':00' : startHour,
    end_hour:    endHour.length   === 5 ? endHour   + ':00' : endHour,
  };

  // Poll for log lines while running
  let polling = true;
  let lastLen = 0;
  const poller = setInterval(async () => {
    if (!polling) { clearInterval(poller); return; }
    try {
      const r = await fetch(`/test-log?key=${encodeURIComponent(key)}`);
      const d = await r.json();
      if (d.log && d.log.length > lastLen) {
        logEl.textContent = d.log.join('\n');
        logEl.scrollTop = logEl.scrollHeight;
        lastLen = d.log.length;
      }
    } catch {}
  }, 800);

  try {
    const res = await fetch('/test-checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key, proj }),
    });
    const data = await res.json();
    polling = false;
    clearInterval(poller);

    logEl.textContent = (data.log || []).join('\n');
    logEl.scrollTop = logEl.scrollHeight;

    if (data.success) {
      header.className = 'test-panel-header success';
      header.innerHTML = '✓ Success';
    } else {
      header.className = 'test-panel-header fail';
      header.innerHTML = '✗ Failed';
    }
  } catch (e) {
    polling = false;
    clearInterval(poller);
    header.className = 'test-panel-header fail';
    header.innerHTML = '✗ Request error';
    logEl.textContent = String(e);
  }

  btn.disabled = false;
}

// ── Save ─────────────────────────────────────────────────────────────────────

function collectConfig() {
  const out = {};
  document.querySelectorAll('.card').forEach(card => {
    const key = card.dataset.key;
    const get = f => card.querySelector(`[data-field="${f}"]`)?.value ?? '';
    const ranges = [...card.querySelectorAll('.range-row')].map(row => ({
      start_date: row.querySelector('[data-range-start]').value,
      end_date:   row.querySelector('[data-range-end]').value,
    })).filter(r => r.start_date && r.end_date);
    const startHour = get('start_hour');
    const endHour   = get('end_hour');
    out[key] = {
      projectName:     get('projectName'),
      projectTime:     get('projectTime'),
      message:         get('message'),
      start_hour:      startHour.length === 5 ? startHour + ':00' : startHour,
      end_hour:        endHour.length   === 5 ? endHour   + ':00' : endHour,
      date_ranges:     ranges,
      checked_in_date: config[key]?.checked_in_date || [],
    };
  });
  return out;
}

async function saveAll() {
  const data = collectConfig();
  const res = await fetch('/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data, null, 2),
  });
  if (res.ok) { config = data; toast('Saved ✓'); }
  else        { toast('Save failed ✗'); }
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;');
}
function toast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2200);
}

load();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._respond(200, "text/html", HTML.encode())
        elif path == "/config":
            with open(CONFIG_FILE, "rb") as f:
                self._respond(200, "application/json", f.read())
        elif path == "/test-log":
            qs  = parse_qs(urlparse(self.path).query)
            key = qs.get("key", [""])[0]
            with _test_lock:
                entry = _test_result.get(key, {})
            self._json(200, {"log": entry.get("log", [])})
        else:
            self._respond(404, "text/plain", b"Not found")

    def do_POST(self):
        path   = urlparse(self.path).path
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)

        if path == "/config":
            try:
                data = json.loads(body)
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self._json(200, {"ok": True})
            except Exception as e:
                self._respond(500, "text/plain", str(e).encode())

        elif path == "/test-checkin":
            try:
                payload = json.loads(body)
                key     = payload["key"]
                proj    = payload["proj"]
                with _test_lock:
                    _test_result[key] = {"running": True, "log": []}
                result = self._run_checkin(key, proj)
                self._json(200, result)
            except Exception as e:
                self._json(500, {"success": False, "log": [str(e)]})
        else:
            self._respond(404, "text/plain", b"Not found")

    def _run_checkin(self, key: str, proj: dict) -> dict:
        import sys, os
        sys.path.insert(0, os.path.dirname(CONFIG_FILE))

        log_lines = []

        def capture(msg):
            log_lines.append(str(msg))
            with _test_lock:
                if key in _test_result:
                    _test_result[key]["log"] = list(log_lines)

        # Patch log.CheckinLog temporarily
        import log as log_mod
        original_log = log_mod.CheckinLog
        log_mod.CheckinLog = capture

        try:
            import importlib
            import selenium_checkin as sc
            importlib.reload(sc)  # re-run credential load with fresh env

            success = sc.SeleniumCheckin(
                proj["projectName"],
                proj["projectTime"],
                proj["message"],
            )
        except Exception as e:
            success = False
            capture(f"Exception: {e}")
        finally:
            log_mod.CheckinLog = original_log
            with _test_lock:
                _test_result[key] = {"running": False, "success": success, "log": log_lines}

        return {"success": success, "log": log_lines}

    def _respond(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self._respond(code, "application/json", body)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"Config GUI → {url}")
    print("Press Ctrl+C to stop.")
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
