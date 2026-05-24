import atexit
import json
import os
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, render_template_string, request, stream_with_context
from dotenv import load_dotenv

from audio import AudioManager
from speechtt import SpeechToText
from llm import LLM, HELIX_SYSTEM
from tts import TTS


load_dotenv()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

_stt: SpeechToText = None
_llm: LLM = None
_audio: AudioManager = None
_tts: TTS = None

_history: list = []
_history_lock = threading.Lock()
_MAX_HISTORY = 30

_settings = {
    "temperature": 0.72,
    "max_tokens": 512,
    "top_p": 0.9,
    "tts_enabled": False,
    "system_prompt": HELIX_SYSTEM,
}


# ─────────────────────────────────────────────
#   HTML / CSS / JS  (Premium Bright Interface)
# ─────────────────────────────────────────────
PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>HELIX ALPHA — Local AI Assistant</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;700;900&family=JetBrains+Mono:wght@400;600&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked@15.0.7/marked.min.js"></script>
<style>
:root {
  --accent: #006aff;
  --accent-glow: rgba(0, 106, 255, 0.15);
  --accent-soft: rgba(0, 106, 255, 0.05);
  --bg: #f5f8ff;
  --surface: #ffffff;
  --surface-alt: #f0f4ff;
  --text: #051630;
  --text-dim: #5c6c8c;
  --border: rgba(0, 106, 255, 0.1);
  --border-strong: rgba(0, 106, 255, 0.25);
  --red: #ff3b30;
  --green: #34c759;
  --radius: 12px;
  --shadow: 0 10px 40px rgba(0, 50, 150, 0.06);
  --font-display: 'Orbitron', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; overflow: hidden; font-family: var(--font-body); background: var(--bg); color: var(--text); }

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes floatIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* Grid Background */
.bg-layer { position: absolute; inset: 0; z-index: 0; pointer-events: none; opacity: 0.4; }
.bg-layer::before { content: ''; position: absolute; inset: 0; background-image: linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px); background-size: 50px 50px; }

/* Splash Screen */
.splash { position: fixed; inset: 0; z-index: 9999; background: #fff; display: flex; flex-direction: column; align-items: center; justify-content: center; transition: 0.8s ease; }
.splash.gone { opacity: 0; pointer-events: none; }
.orbit { position: relative; width: 140px; height: 140px; margin-bottom: 30px; }
.orbit-ring { position: absolute; inset: 0; border: 2px solid var(--border); border-radius: 50%; border-top-color: var(--accent); animation: spin 2s linear infinite; }
.orbit-inner { position: absolute; inset: 15px; border: 1px solid var(--border-strong); border-radius: 50%; border-bottom-color: var(--accent); animation: spin 1s linear reverse infinite; }
.orbit-core { position: absolute; inset: 40px; background: var(--accent); border-radius: 50%; box-shadow: 0 0 20px var(--accent-glow); animation: pulse 2s infinite; }

/* Main Layout */
header { height: 60px; background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; padding: 0 24px; z-index: 100; box-shadow: var(--shadow); }
.logo { font-family: var(--font-display); font-weight: 800; font-size: 18px; letter-spacing: 4px; }
.logo em { color: var(--accent); font-style: normal; }

main { flex: 1; overflow-y: auto; display: flex; flex-direction: column; padding: 24px; gap: 16px; position: relative; z-index: 10; scroll-behavior: smooth; }
main::-webkit-scrollbar { width: 5px; }
main::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 10px; }

.msg { max-width: 80%; animation: floatIn 0.4s ease; display: flex; flex-direction: column; gap: 2px; }
.msg.user { align-self: flex-end; }
.msg.helix { align-self: flex-start; }
.msg-meta { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); text-transform: uppercase; font-weight: 600; padding: 0 4px; }
.msg.user .msg-meta { text-align: right; color: var(--accent); }

.bubble { padding: 14px 20px; line-height: 1.6; font-size: 15px; border-radius: var(--radius); background: var(--surface); border: 1px solid var(--border); box-shadow: var(--shadow); }
.msg.user .bubble { background: var(--accent); color: #fff; border-bottom-right-radius: 2px; border: none; }
.msg.helix .bubble { border-bottom-left-radius: 2px; }

footer { background: var(--surface); border-top: 1px solid var(--border); padding: 16px 24px; position: relative; z-index: 100; }
.input-row { display: flex; align-items: flex-end; gap: 12px; }
.input-wrap { flex: 1; min-height: 48px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 14px; display: flex; transition: 0.2s; }
.input-wrap:focus-within { border-color: var(--accent); background: #fff; box-shadow: 0 0 0 4px var(--accent-glow); }
textarea { width: 100%; border: none; outline: none; background: transparent; padding: 12px 16px; font-family: var(--font-body); font-size: 15px; line-height: 1.5; resize: none; max-height: 150px; color: var(--text); }

.btn-send { width: 48px; height: 48px; border: none; border-radius: 14px; background: var(--accent); color: #fff; cursor: pointer; transition: 0.2s; display: flex; align-items: center; justify-content: center; }
.btn-send:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 12px var(--accent-glow); }
.btn-send:disabled { opacity: 0.3; cursor: not-allowed; }

.controls { display: flex; align-items: center; gap: 16px; margin-top: 12px; }
.btn-mic { width: 40px; height: 40px; border-radius: 50%; border: 1px solid var(--border-strong); background: #fff; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 18px; transition: 0.2s; }
.btn-mic:hover { background: var(--surface-alt); color: var(--accent); }
.btn-mic.rec { background: var(--red); color: #fff; border-color: var(--red); box-shadow: 0 0 15px rgba(255,0,0,0.3); animation: pulse 1s infinite; }

.status-pill { font-family: var(--font-mono); font-size: 10px; color: var(--text-dim); padding: 4px 12px; border: 1px solid var(--border); border-radius: 20px; text-transform: uppercase; letter-spacing: 1px; }

.branding { position: fixed; bottom: 30px; width: 100%; text-align: center; font-family: var(--font-display); font-size: 32px; letter-spacing: 16px; opacity: 0.05; color: var(--accent); pointer-events: none; z-index: 1; text-transform: uppercase; }

/* Settings Sidebar */
.settings-panel { position: fixed; top: 0; right: -400px; width: 380px; height: 100%; background: #fff; z-index: 1000; transition: right 0.4s cubic-bezier(0.2, 1, 0.3, 1); border-left: 1px solid var(--border); box-shadow: -10px 0 50px rgba(0,0,0,0.05); padding: 24px; display: flex; flex-direction: column; }
.settings-panel.open { right: 0; }
.s-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
.s-head h2 { font-family: var(--font-display); font-size: 14px; color: var(--text); }
.s-row { margin-bottom: 20px; }
.s-row label { display: block; font-size: 11px; font-weight: 700; color: var(--text-dim); margin-bottom: 6px; text-transform: uppercase; }
.s-row input, .s-row textarea { width: 100%; padding: 10px; border: 1px solid var(--border); border-radius: 8px; font-family: var(--font-body); font-size: 14px; background: var(--surface-alt); outline: none; }
.cursor { display: inline-block; width: 2px; height: 1.1em; background: var(--accent); margin-left: 2px; vertical-align: middle; }
</style>
</head>
<body style="display:flex; flex-direction:column;">

<div class="bg-layer"></div>
<div class="branding">ALPHA HELIX</div>

<!-- Splash -->
<div class="splash" id="splash">
  <div class="orbit">
    <div class="orbit-ring"></div>
    <div class="orbit-inner"></div>
    <div class="orbit-core"></div>
  </div>
  <div class="logo">HELIX&nbsp;<em>ALPHA</em></div>
  <div id="bootMsg" style="font-family:var(--font-mono); font-size:11px; color:#5c6c8c; margin-top:16px;">Initializing...</div>
</div>

<header>
  <div class="logo">HELIX&nbsp;<em>ALPHA</em></div>
  <div style="display:flex; align-items:center; gap:12px;">
    <div class="status-pill" id="status">OFFLINE</div>
    <button id="setBtn" style="border:none;background:none;cursor:pointer;font-size:20px;">⚙️</button>
  </div>
</header>

<main id="chat"></main>

<div class="settings-panel" id="setPan">
  <div class="s-head"><h2>CONTROL PANEL</h2><button id="setCls" style="border:none;background:none;cursor:pointer;font-size:18px;">✕</button></div>
  <div class="s-row"><label>Temperature</label><input type="range" id="sTemp" min="0" max="1" step="0.1" value="0.7"><div id="sTempVal" style="text-align:right;font-size:10px;font-family:var(--font-mono)">0.7</div></div>
  <div class="s-row"><label>Max Tokens</label><input type="number" id="sMax" value="512"></div>
  <div class="s-row" style="display:flex; align-items:center; justify-content:space-between;"><label style="margin:0">Voice Mode</label><input type="checkbox" id="sTTS" style="width:20px;height:20px;"></div>
  <div class="s-row"><label>Personality</label><textarea id="sPrompt" rows="5">You are Helix Alpha, a sophisticated, helpful, and direct AI assistant.</textarea></div>
</div>

<footer>
  <div class="input-row">
    <div class="input-wrap"><textarea id="msgIn" rows="1" placeholder="Enter command or message..."></textarea></div>
    <button class="btn-send" id="sendBtn" disabled>➤</button>
  </div>
  <div class="controls">
    <button class="btn-mic" id="micBtn">🎤</button>
    <div id="modelInfo" style="font-family:var(--font-mono); font-size:10px; color:var(--text-dim)">Checking AI engine...</div>
  </div>
</footer>

<script>
/** Helix Client Logic */
const chat = document.getElementById('chat');
const msgIn = document.getElementById('msgIn');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const status = document.getElementById('status');
const setBtn = document.getElementById('setBtn');
const setPan = document.getElementById('setPan');
const setCls = document.getElementById('setCls');
const modelInfo = document.getElementById('modelInfo');

let busy = false;
let cfg = {temperature:0.7, max_tokens:512, tts_enabled:false, system_prompt:''};

function addBubble(text, role){
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + (role==='user'?'user':'helix');
  const meta = document.createElement('div');
  meta.className = 'msg-meta';
  meta.textContent = role==='user' ? 'YOU' : 'HELIX';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  if(role==='assistant'){
    bubble.innerHTML = marked.parse(text);
  } else {
    bubble.textContent = text;
  }
  wrap.appendChild(meta);
  wrap.appendChild(bubble);
  chat.appendChild(wrap);
  chat.scrollTop = chat.scrollHeight;
  return bubble;
}

async function sendChat(){
  const text = msgIn.value.trim();
  if(!text || busy) return;
  busy = true; msgIn.value = ''; sendBtn.disabled = true; msgIn.style.height = 'auto';
  
  addBubble(text, 'user');
  status.textContent = 'BUSY';
  status.style.color = '#ff9500';
  
  const bubble = addBubble('', 'assistant');
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  bubble.appendChild(cursor);
  
  let fullText = '';
  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text, ...cfg, system_prompt: document.getElementById('sPrompt').value})
    });
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while(true){
      const {done, value} = await reader.read();
      if(done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      for(const line of lines){
        if(line.startsWith('data: ')){
          const payload = line.slice(6);
          if(payload === '[DONE]') continue;
          try {
            const data = JSON.parse(payload);
            if(data.token){
              fullText += data.token;
              bubble.innerHTML = marked.parse(fullText) + '<span class="cursor"></span>';
              chat.scrollTop = chat.scrollHeight;
            } else if(data.error){
              bubble.textContent = 'Error: ' + data.error;
            }
          } catch(e) {}
        }
      }
    }
  } catch(err) {
    bubble.textContent = 'Connection Error: ' + err.message;
  } finally {
    const cursors = bubble.querySelectorAll('.cursor');
    cursors.forEach(c => c.remove());
    busy = false;
    sendBtn.disabled = false;
    status.textContent = 'ONLINE';
    status.style.color = '';
    if(cfg.tts_enabled && fullText) speak(fullText);
  }
}

async function speak(text){
  fetch('/api/tts', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text})});
}

micBtn.onclick = async () => {
  if(busy) return;
  busy = true; micBtn.classList.add('rec');
  status.textContent = 'LISTENING';
  try {
    const res = await fetch('/api/record', {method:'POST'});
    const data = await res.json();
    micBtn.classList.remove('rec');
    if(data.text){
      busy = false;
      msgIn.value = data.text;
      sendChat();
    } else {
      status.textContent = 'ONLINE';
      busy = false;
    }
  } catch(e){
    status.textContent = 'ERROR';
    busy = false;
    micBtn.classList.remove('rec');
  }
};

msgIn.oninput = () => {
  msgIn.style.height = 'auto';
  msgIn.style.height = msgIn.scrollHeight + 'px';
  sendBtn.disabled = !msgIn.value.trim();
};
msgIn.onkeydown = e => { if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendChat(); } };
sendBtn.onclick = sendChat;

setBtn.onclick = () => setPan.classList.add('open');
setCls.onclick = () => setPan.classList.remove('open');
document.getElementById('sTemp').oninput = e => {
  document.getElementById('sTempVal').textContent = e.target.value;
  cfg.temperature = parseFloat(e.target.value);
};
document.getElementById('sTTS').onchange = e => cfg.tts_enabled = e.target.checked;
document.getElementById('sMax').onchange = e => cfg.max_tokens = parseInt(e.target.value);

async function boot(){
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    modelInfo.textContent = data.model + ' | ' + data.backend;
    status.textContent = 'ONLINE';
    setTimeout(() => { document.getElementById('splash').classList.add('gone'); }, 800);
  } catch(e){
    document.getElementById('bootMsg').textContent = 'Server Unreachable. Retrying...';
    setTimeout(boot, 2000);
  }
}
boot();
</script>
</body>
</html>"""


# ─────────────────────────────────────────────
#   Flask Routes
# ─────────────────────────────────────────────

@app.route("/")
def index():
    return render_template_string(PAGE)


@app.route("/api/status")
def api_status():
    if not _llm:
        return jsonify({"model": "not loaded", "backend": "unknown", "mode": "none"})
    return jsonify(_llm.status())


@app.route("/api/record", methods=["POST"])
def api_record():
    try:
        path = _audio.record_until_silence()
        text = _stt.transcribe(path)
        return jsonify({"text": text})
    except Exception as e:
        return jsonify({"error": str(e), "text": ""}), 500


@app.route("/api/chat/stream", methods=["POST"])
def api_chat_stream():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400

    with _history_lock:
        hist = list(_history)

    def gen():
        full = ""
        try:
            for tok in _llm.stream(
                text,
                system_prompt=data.get("system_prompt") or _settings["system_prompt"],
                max_tokens=data.get("max_tokens", _settings["max_tokens"]),
                temperature=data.get("temperature", _settings["temperature"]),
                top_p=data.get("top_p", _settings["top_p"]),
                history=hist,
            ):
                if tok is not None:
                    full += tok
                    yield f"data: {json.dumps({'token': tok})}\n\n"

            with _history_lock:
                _history.append({"role": "user", "content": text})
                _history.append({"role": "assistant", "content": full})
                while len(_history) > _MAX_HISTORY * 2:
                    _history.pop(0)

            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(gen()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/tts", methods=["POST"])
def api_tts():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text"}), 400
    try:
        _tts.speak(text)
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        payload = request.get_json(force=True, silent=True) or {}
        _settings.update({k: v for k, v in payload.items() if k in _settings})
    return jsonify(_settings)


@app.route("/api/clear", methods=["POST"])
def api_clear():
    with _history_lock:
        _history.clear()
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────────
#   Startup / Shutdown
# ─────────────────────────────────────────────

def _shutdown():
    if _llm:
        _llm.shutdown()
    if _tts:
        _tts.shutdown()


def main():
    global _stt, _llm, _audio, _tts
    atexit.register(_shutdown)

    print("\n" + "═" * 52)
    print("  HELIX ALPHA — Local AI Assistant")
    print("═" * 52)

    print("[Init] Loading speech recognition...")
    _stt = SpeechToText()

    print("[Init] Setting up microphone...")
    _audio = AudioManager()

    print("[Init] Loading TTS engine...")
    _tts = TTS()

    print("[Init] Loading language model (takes a moment)...")
    _llm = LLM()

    info = _llm.status()
    print(f"[Init] Mode: {info['backend']}")

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))

    print(f"\n[Ready] Open your browser at: http://{host}:{port}")
    print("[Ready] Press Ctrl+C to stop\n")

    try:
        app.run(host=host, port=port, debug=False, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown()


if __name__ == "__main__":
    main()
