# HELIX ALPHA — Complete How-To Guide

> **Helix Alpha** is a local, offline-capable voice AI assistant powered by the Qwen2.5-3B language model running on your AMD GPU via Vulkan.

---

## Table of Contents

1. [System Requirements](#1-system-requirements)  
2. [Install Python](#2-install-python)  
3. [Open the Project Folder](#3-open-the-project-folder)  
4. [Create a Python Virtual Environment](#4-create-a-python-virtual-environment)
5. [Install Dependencies](#5-install-dependencies)  
6. [Download the LLM Model](#6-download-the-llm-model)  
7. [Copy the Vulkan Binaries](#7-copy-the-vulkan-binaries)  
8. [Configure Environment](#8-configure-environment)  
9. [First Run — Test Each Module](#9-first-run--test-each-module)  
10. [Start Helix — CLI Mode](#10-start-helix--cli-mode)  
11. [Start Helix — Web GUI Mode](#11-start-helix--web-gui-mode)  
12. [How to Use the Web Interface](#12-how-to-use-the-web-interface)  
13. [How the LLM Connects to Your GPU](#13-how-the-llm-connects-to-your-gpu)  
14. [How to Stop Helix](#14-how-to-stop-helix)  
15. [Troubleshooting](#15-troubleshooting)  
16. [Project Structure](#16-project-structure)  
17. [Extending Helix Alpha](#17-extending-helix-alpha)

---

## 1. System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| OS        | Windows 10 64-bit | Windows 11 64-bit |
| Python    | 3.11  | 3.12 |
| RAM       | 6 GB  | 8 GB+ |
| GPU       | AMD RX 550 4 GB (Vulkan) | Any AMD/NVIDIA with Vulkan |
| Disk      | 3 GB free     | 5 GB free |
| Microphone| Any USB or built-in | Dedicated USB microphone |

---

## 2. Install Python

**Step 2.1** — Open **Windows Terminal** or **PowerShell**  
Press `Win + X` on your keyboard → click **"Windows Terminal"** or **"PowerShell"**.

**Step 2.2** — Check if Python is already installed:
```powershell
python --version
```

If you see `Python 3.11.x` or `Python 3.12.x`, skip to Step 3.

**Step 2.3** — If Python is NOT installed:
1. Go to: **https://www.python.org/downloads/**
2. Click the big yellow **"Download Python 3.12.x"** button
3. Run the installer
4. ✅ **CRITICAL:** Check the box **"Add Python to PATH"** at the bottom before clicking Install
5. Click **Install Now**, wait for it to finish
6. After install, close and reopen PowerShell, then run `python --version` again

---

## 3. Open the Project Folder

In PowerShell, navigate to the project:

```powershell
cd E:\Project\HELIX-ALPHA
```

> Replace `E:\Project\HELIX-ALPHA` with your actual project path if different.

Verify you are in the right folder:
```powershell
dir
```
You should see files like: `audio.py`, `speechtt.py`, `llm.py`, `main.py`, `gui.py`, `requirements.txt`

---

## 4. Create a Python Virtual Environment

A virtual environment keeps Helix's packages separate from your system Python — recommended for clean installs.

**Step 4.1** — Create the virtual environment:
```powershell
python -m venv venv
```

**Step 4.2** — Activate it:
```powershell
venv\Scripts\activate
```

You will see `(venv)` appear at the start of your prompt — this means it's active.

> **Note:** Every time you open a new terminal to run Helix, you must activate the venv first with `venv\Scripts\activate`

---

## 5. Install Dependencies

With your venv active, install all required packages in one command:

```powershell
pip install -r requirements.txt
```

This installs:
- `sounddevice` — microphone recording
- `numpy` — audio processing
- `vosk` — offline speech-to-text
- `flask` — web server for the GUI
- `python-dotenv` — environment config
- `edge-tts` — text-to-speech (online, Microsoft voices)
- `pyttsx3` — offline TTS fallback

Wait for all packages to download and install. This may take 2-5 minutes.

---

## 6. Download the LLM Model

Helix uses the **Qwen2.5-3B-Instruct Q4_K_M** quantized model (~2 GB).

**Step 6.1** — Download the model file:

Click this direct link in your browser:  
```
https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf
```

Or use PowerShell to download directly:
```powershell
curl -L -o "models\Qwen2.5-3B-Instruct-Q4_K_M.gguf" "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/Qwen2.5-3B-Instruct-Q4_K_M.gguf"
```

**Step 6.2** — Move the file to the `models\` folder:
```
E:\Project\HELIX-ALPHA\models\Qwen2.5-3B-Instruct-Q4_K_M.gguf
```

**Step 6.3** — Verify it's there:
```powershell
Test-Path "models\Qwen2.5-3B-Instruct-Q4_K_M.gguf"
```
Should print: `True`

> The Vosk speech model (~1.8 GB) downloads **automatically** on first run. Please wait for it to complete.

---

## 7. Copy the Vulkan Binaries

For AMD GPU acceleration, Helix uses a pre-built `llama-server.exe` compiled with Vulkan support.

**Step 7.1** — Get the Vulkan build of llama.cpp for Windows:
- Download from: https://github.com/ggerganov/llama.cpp/releases
- Look for a release asset named like: `llama-*-bin-win-vulkan-x64.zip`
- Download and extract it

**Step 7.2** — Copy all files from that zip into:
```
E:\Project\HELIX-ALPHA\llama_vulkan\
```

The folder must contain at minimum:
- `llama-server.exe`
- `ggml-vulkan.dll`
- `ggml.dll`
- `llama.dll`

**Step 7.3** — Verify:
```powershell
Test-Path "llama_vulkan\llama-server.exe"
```
Should print: `True`

> If you skip this step, Helix will still work in **CPU mode** — just slower responses.

---

## 8. Configure Environment

**Step 8.1** — Copy the example environment file:
```powershell
Copy-Item .env.example .env
```

**Step 8.2** — (Optional) Edit `.env` to customize ports or thresholds:
```powershell
notepad .env
```

The defaults work fine for most users — you do not need to change anything.

---

## 9. First Run — Test Each Module

Before starting the full assistant, test that each piece works:

**Test audio recording (microphone):**
```powershell
python -c "from audio import AudioManager; a=AudioManager(); a.record_until_silence('temp/test.wav'); print('Audio OK')"
```
Speak into your mic for 2 seconds. If it prints `Audio OK` — microphone works.

**Test speech recognition:**
```powershell
python -c "from speechtt import SpeechToText; s=SpeechToText(); print(s.transcribe('temp/test.wav'))"
```
This will auto-download the Vosk model if needed (first time only).

**Test the LLM:**
```powershell
python -c "from llm import LLM; m=LLM(); print(m.generate('Say hello')); m.shutdown()"
```
This will start the GPU server (or CPU fallback) and print Helix's response.

---

## 10. Start Helix — CLI Mode

The CLI mode runs in the terminal — voice in, text response out.

```powershell
python main.py
```

You will see the Helix ASCII banner, then:
```
[STT] Vosk model ready
[Audio] Microphone: <your mic name>
[LLM] Starting Vulkan GPU server...
[LLM] GPU acceleration ON
[Helix] All systems online. Listening...
```

**To use it:**
1. Wait for `Listening...` to appear
2. Speak clearly into your microphone
3. Wait ~0.6s of silence — recording stops automatically
4. Watch the transcription and Helix's response appear
5. Repeat for next question

**Exit CLI mode:** Say **"exit"**, **"quit"**, or press **Ctrl + C**

---

## 11. Start Helix — Web GUI Mode

The web interface gives you a browser-based chat + voice input.

```powershell
python gui.py
```

Wait until you see:
```
[Ready] Open your browser at: http://127.0.0.1:5000
```

Then open your browser and go to:
```
http://127.0.0.1:5000
```

You will see the **HELIX ALPHA** splash screen with the spinning orbital animation. Wait ~5-15 seconds for the model to load. The splash disappears when Helix is ready.

---

## 12. How to Use the Web Interface

### Sending a text message
1. Click the input box at the bottom
2. Type your question
3. Press **Enter** or click the **→ send button**
4. Helix's response streams in real-time

### Using voice input
1. Click the **🎤 microphone button** (bottom left)
2. Speak your message clearly
3. The animated bars show recording is active
4. Stop speaking — Helix auto-detects silence and stops recording
5. Your speech is transcribed and sent automatically

### Status indicator (top right)
- 🟢 **ONLINE** — Helix is ready
- 🔵 **THINKING** — Processing your request
- 🔵 **LISTENING** — Recording your voice
- 🔴 **ERROR** / **OFFLINE** — Something went wrong

### Settings panel (⚙ gear icon)
- **Temperature** — Creativity (0 = focused, 2 = wild)
- **Top P** — Token sampling diversity
- **Max Tokens** — Response length limit
- **Text-to-Speech** — Toggle Helix speaking responses aloud
- **Personality** — Edit Helix's system prompt

### TTS (🔊 speaker icon)
Click to toggle text-to-speech. When enabled, Helix reads its responses aloud using Microsoft Edge TTS voices (requires internet). Falls back to offline pyttsx3 if offline.

### Copy response
Hover over any Helix response to reveal the **Copy** button.

### Clear conversation
Click the 🗑 trash icon (top right) → confirm to wipe the conversation.

---

## 13. How the LLM Connects to Your GPU

Helix uses a **two-tier architecture** for GPU inference:

1. **Vulkan Server Path** (fast — AMD GPU):
   - `gui.py` or `main.py` starts
   - `llm.py` finds `llama_vulkan\llama-server.exe`
   - Launches it as a background process with flags:
     - `--model models/Qwen2.5-3B-Instruct-Q4_K_M.gguf`
     - `-ngl 99` (offload all 99 layers to GPU)
     - `--host 127.0.0.1 --port 8081`
   - Waits up to 30 seconds for the server to become healthy
   - All inference goes through `http://127.0.0.1:8081/v1/chat/completions`
   - Your **AMD RX 550 4 GB** holds the full Q4_K_M model (~2 GB VRAM)
   - Terminal shows: `[LLM] GPU acceleration ON: Vulkan GPU (99 layers offloaded)`

2. **CPU Fallback Path**:
   - If Vulkan server fails or `llama_vulkan\llama-server.exe` is missing
   - Uses `llama-cpp-python` library directly in Python
   - Slower but always works
   - Terminal shows: `[LLM] CPU mode — llama-cpp-python CPU`

**Verify GPU is being used:**
```powershell
python -c "from llm import LLM; m=LLM(); s=m.status(); print(s); m.shutdown()"
```
Look for `'mode': 'vulkan'` in the output.

---

## 14. How to Stop Helix

### CLI Mode (`main.py`):
- Say **"exit"** or **"quit"** into the microphone
- Or press **Ctrl + C** in the terminal

### Web GUI Mode (`gui.py`):
- Press **Ctrl + C** in the PowerShell window where `gui.py` is running
- The Vulkan server subprocess shuts down automatically

> Do NOT close the PowerShell window without pressing Ctrl+C — the Vulkan server may keep running in the background.

**If the Vulkan server gets stuck running:**
```powershell
Get-Process -Name "llama-server" | Stop-Process -Force
```

---

## 15. Troubleshooting

### "No module named vosk"
```powershell
pip install vosk
```

### "No module named sounddevice"
```powershell
pip install sounddevice
```

### "No module named llama_cpp"
Only needed for CPU fallback mode (Vulkan server is preferred):
```powershell
pip install llama-cpp-python
```

### "Model not found"
Make sure the GGUF file is at exactly:
```
E:\Project\HELIX-ALPHA\models\Qwen2.5-3B-Instruct-Q4_K_M.gguf
```

### "Vulkan server not ready within 30s"
- Your model file may be corrupt — re-download it
- Antivirus may be blocking `llama-server.exe` — add an exclusion
- Vulkan drivers not installed — update AMD Adrenalin drivers from amd.com
- Helix falls back to CPU automatically

### "No audio device found" or microphone not working
1. Open Windows Settings → Sound → Input
2. Make sure your microphone is set as default
3. Speak into the mic and check the input level bar moves

### "Port 5000 already in use"
Edit `.env` and change:
```
PORT=5001
```
Then restart Helix.

### "Port 8081 already in use"
The Vulkan LLM server port is 8081. If something else uses it:
- Edit `llm.py`, line `SERVER_PORT = 8081` → change to e.g. `8082`

### Helix's responses are slow
- Normal on CPU (30-60 seconds for 100 words)
- On GPU (Vulkan): 5-15 seconds for 100 words
- Reduce `Max Tokens` in Settings to get shorter, faster responses

### "Low VRAM" errors
The Q4_K_M model uses ~2.3 GB VRAM, which fits comfortably in your 4 GB RX 550.
If you get errors, reduce context size in `llm.py`:
```python
CONTEXT_SIZE = 1024  # reduce from 2048
```

### Web page not loading
1. Make sure `python gui.py` is running in PowerShell
2. Try `http://localhost:5000` instead of `http://127.0.0.1:5000`
3. Check Windows Firewall isn't blocking port 5000

---

## 16. Project Structure

```
E:\Project\HELIX-ALPHA\
│
├── audio.py          ← Microphone recording + silence detection
├── speechtt.py       ← Speech-to-text (Vosk offline, auto-downloads model)
├── llm.py            ← LLM inference (Vulkan GPU server + CPU fallback)
├── main.py           ← CLI voice assistant (terminal mode)
├── gui.py            ← Web GUI (Flask server + browser interface)
├── tts.py            ← Text-to-speech (edge-tts + pyttsx3 fallback)
│
├── requirements.txt  ← Python package list
├── .env.example      ← Environment config template
├── .env              ← Your config (copy from .env.example)
├── .gitignore        ← Files excluded from git
├── GUIDE.md          ← This file
│
├── models\
│   ├── Qwen2.5-3B-Instruct-Q4_K_M.gguf    ← LLM model (you download)
│   └── vosk-model-en-us-0.22\             ← STT model (auto-downloaded)
│
├── llama_vulkan\     ← Pre-built Vulkan llama.cpp binaries (you copy)
│   ├── llama-server.exe
│   ├── ggml-vulkan.dll
│   └── ...
│
└── temp\             ← Temporary audio files (auto-managed)
```

---

## 17. Extending Helix Alpha

The code is designed to be modular and easy to extend:

### Add a Command Classifier
Create `classifier.py` with a function `classify(text) -> str` that returns an intent.
In `main.py`, call it between STT and LLM:
```python
from classifier import classify
intent = classify(text)
if intent == "weather":
    response = get_weather()
else:
    response = llm.generate(text)
```

### Add Tool-Calling Agents
Create `agents/` folder. Each agent file has a `run(query)` function. Route intents from the classifier to agents.

### Add a Wake Word
Use `pvporcupine` (Porcupine library) for "Hey Helix" always-on detection:
```python
pip install pvporcupine
```

### Switch to a Larger Model
Change `MODEL_PATH` in `llm.py` to any other GGUF model. The Qwen2.5-7B model also fits on 8 GB VRAM.

### Add Web Search
Use `requests` + DuckDuckGo's API to give Helix internet access when needed.

---

## Quick Reference Card

| Action | Command |
|--------|---------|
| Activate venv | `venv\Scripts\activate` |
| Start CLI mode | `python main.py` |
| Start Web GUI | `python gui.py` |
| Open browser | `http://127.0.0.1:5000` |
| Stop Helix | `Ctrl + C` in terminal |
| Kill stuck server | `Get-Process llama-server \| Stop-Process` |

---

*Helix Alpha — built for low-end hardware, designed for real intelligence.*
