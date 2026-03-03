# 🌌 AXIS V2.5 — Phase 1 Complete: Project Overview

> **For NotebookLM Presentation**  
> Version: 2.5 (Cloud-Based) | Date: March 2026 | Phase: 1 of 3

---

## What is AXIS?

**AXIS** (Agentic X-interface Intelligent System) is a multimodal AI agent that bridges the gap between physical human gestures, local OS operations, and cloud intelligence. It is not a chatbot or a simple LLM wrapper — it is a fully autonomous agentic framework with persistent memory, real-time computer vision, and human approval controls.

Built by a solo developer in under 3 months using Python, AXIS currently runs on a personal laptop and communicates with the user via a Telegram app on their smartphone — no screen required.

---

## 🏗️ Overall Architecture

AXIS follows a **modular plugin architecture**. On every boot, the Orchestrator scans for skills and loads them dynamically — no hardcoded tool lists.

```
AXIS_v2/
│
├── main.py                    ← Entry point. Boots AXIS and starts all threads.
│
├── core/
│   ├── orchestrator.py        ← AxisCore class. Manages Gemini API + tool dispatch.
│   └── i18n.py                ← Language module. Loads locale JSON based on .env
│
├── agent_skills/              ← Plugin folder. Each subfolder = one autonomous skill.
│   ├── audio_interface/       ← Microphone (STT) + Speaker (TTS via OpenAI)
│   ├── file_master/           ← Read/write any file on the local filesystem
│   ├── mcp_hub/               ← Node.js MCP bridge (Filesystem + GitHub servers)
│   ├── memory_manager/        ← SQLite long-term memory (save + search facts)
│   ├── os_control/            ← Screen automation (PyAutoGUI: click, type, screenshot)
│   ├── telegram_bridge/       ← Async Telegram bot (send messages, files, confirmations)
│   ├── terminal_operator/     ← Execute shell commands (PowerShell/CMD)
│   ├── vision_eye/            ← Computer Vision (MediaPipe hand tracking + HUD)
│   ├── web_research/          ← Google Search + Perplexity AI deep research
│   └── workspace_manager/     ← Find and open projects in Cursor / VS Code
│
├── config/
│   └── locales/
│       ├── en.json            ← English (default)
│       ├── uk.json            ← Ukrainian
│       └── es.json            ← Spanish
│
└── memories/
    ├── axis_memory.db         ← SQLite database for long-term facts
    └── vision/                ← Auto-saved screenshots from gesture commands
```

---

## 🧠 The Brain: AxisCore (Orchestrator)

**File:** `core/orchestrator.py`

The `AxisCore` class is the central intelligence. It:

1. **Loads all skills** by scanning `agent_skills/*/manifest.py` on boot
2. **Passes tools to Gemini 2.0 Flash** as native function declarations
3. **Manages a persistent chat session** (short-term memory via conversation history)
4. **Dispatches tool calls** automatically via `enable_automatic_function_calling=True`

```python
class AxisCore:
    """Main logic for the AXIS agent orchestrator."""
    def __init__(self):
        self.available_tools = self._load_skills()   # Dynamic plugin discovery
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            tools=self.available_tools
        )
        self.chat_session = self.model.start_chat(
            history=[],
            enable_automatic_function_calling=True   # Gemini calls tools autonomously
        )
```

**Result on boot:**
```
🚀 Booting AXIS V2.5... (Modular Architecture)
✅ [Kernel]: Skill 'telegram_bridge' loaded.
✅ [Kernel]: Skill 'vision_eye' loaded.
✅ [Kernel]: Skill 'memory_manager' loaded.
🧠 [AXIS Core]: Initialization successful. Loaded 17 tools.
--- AXIS is ready ---
```

---

## 🛡️ Feature 1: The Guardian Protocol (Human-in-the-Loop)

**Files:** `agent_skills/telegram_bridge/manifest.py`, `listener.py`

Before any destructive or irreversible action, AXIS pauses and sends an interactive Telegram message with **inline keyboard buttons** (✅ Confirm / ❌ Decline).

**How it works technically:**
1. `ask_user_confirmation(prompt)` tool is called by Gemini
2. A Telegram message with inline keyboard is sent
3. The Python thread blocks on `threading.Event.wait(timeout=300)`
4. The `listener.py` background thread receives the button callback
5. It sets the `threading.Event` — the blocked thread resumes
6. The decision is returned to Gemini (True/False)

**Actions requiring confirmation:**
- File deletion or overwrite
- `git push` / `git commit`
- Any system-level command via `terminal_operator`

---

## 👁️ Feature 2: Vision Eye (Spatial Computing)

**Files:** `agent_skills/vision_eye/logic.py`, `manifest.py`

The `VisionManager` class opens the webcam and runs MediaPipe hand tracking in a background thread. A custom HUD is rendered on the live video feed.

### Gesture Dictionary:

| Gesture | Detection Method | Action |
|:--------|:----------------|:-------|
| **Index finger point** | 1 finger extended | Mouse move (mapped to screen coords via EMA smoothing) |
| **Pinch** (thumb + index) | Distance threshold | Left click |
| **Fist** | All fingers curled | Pause tracking |
| **"L" shape** | Index + thumb extended | Take screenshot → save JSON log → send to Telegram |
| **Crossed arms 🙅‍♂️** | Both hands detected, wrists swapped | Sleep gesture — shuts down camera after 45 frames (~1.5s) |

### HUD Indicators:
- **`🟢 LIVE`** — camera is active and tracking
- **`⚪ IDLE`** — camera paused
- **Counter bar** — shows cross-arms detection progress (0→45)

### Sleep Gesture Test Result (March 3, 2026):
```
[VISION] Crossed Arms detected! Counter: 1/45
[VISION] Crossed Arms detected! Counter: 12/45
...
[VISION] Crossed Arms detected! Counter: 45/45
💤 Sleep gesture detected. Shutting down Vision Manager to save CPU.
```

---

## 🔌 Feature 3: MCP Hub — Model Context Protocol

**Files:** `agent_skills/mcp_hub/bridge.py`, `config.json`

AXIS acts as a **host** for two MCP servers running as background Node.js processes:

| Server | Technology | What it provides |
|:-------|:-----------|:----------------|
| **Filesystem MCP** | `@modelcontextprotocol/server-filesystem` | Standardized read/write access to the project directory |
| **GitHub MCP** | `@modelcontextprotocol/server-github` | Autonomous commit, push, PR creation |

MCP bridges the gap between the Python AI agent and the Node.js ecosystem, following the Anthropic standard for context sharing.

---

## 💾 Feature 4: Long-Term Memory

**File:** `agent_skills/memory_manager/manifest.py`

SQLite-backed persistent memory that survives reboots.

```python
def save_to_memory(topic: str, fact: str) -> str:
    """Save a fact, preference, or project path for future use."""

def search_memory(query: str) -> str:
    """Search memory before saying 'I don't know'."""
```

**Database:** `memories/axis_memory.db`  
**Table:** `memory (id, topic, fact, timestamp)`

Example queries Gemini might make:
- *"Remember that my Python path is C:\Projects"* → saved
- *"What IDE do I prefer?"* → searches memory first, then responds

---

## 🌍 Feature 5: i18n Localization System

**Files:** `core/i18n.py`, `config/locales/*.json`

A custom singleton `LangModule` that loads translations from JSON at boot. Zero hardcoded strings in the codebase.

```python
# ❌ Old way:
print("Starting AXIS...")

# ✅ AXIS way:
print(lang.get("system.welcome"))
```

**Supported languages:** English (default), Ukrainian, Spanish  
**Switch language:** Set `LANGUAGE=uk` in `.env`

---

## 📱 Feature 6: Telegram Bridge

**Files:** `agent_skills/telegram_bridge/manifest.py`, `listener.py`

A fully asynchronous two-way Telegram interface:
- **Sending:** messages, photos, documents, confirmation keyboards
- **Receiving:** background polling thread intercepts messages and routes them to `AxisCore.think()`
- **Guardian Protocol:** inline keyboard callback_query handling with thread synchronization

---

## ⚡ Feature 7: OS Automation & Terminal

| Skill | Key Tools | Technology |
|:------|:---------|:-----------|
| `os_control` | take_screenshot, mouse_click, type_text, hotkey | PyAutoGUI |
| `terminal_operator` | execute_command | subprocess (PowerShell) |
| `file_master` | list_dir, read_file, write_file | Python stdlib |
| `workspace_manager` | open_project_in_cursor | os.walk + subprocess |

---

## 📊 Phase 1 — What Was Accomplished

| Category | Items Delivered |
|:---------|:---------------|
| **Core Architecture** | Dynamic skill discovery, Gemini 2.0 Flash integration, persistent chat |
| **Skills (tools)** | 17 tools across 8 skill modules |
| **Security** | Guardian Protocol (Telegram confirmation for destructive actions) |
| **Vision** | Hand tracking, 5 gestures, HUD, Sleep Gesture kill-switch |
| **Remote Control** | Full bidirectional Telegram bridge (commands + screenshots + approvals) |
| **Memory** | SQLite long-term memory with topic-based search |
| **MCP** | Filesystem + GitHub MCP server bridge |
| **Localization** | 3-language i18n system (EN, UK, ES) |
| **Documentation** | README.md, AXIS_PLAYBOOK.md, .cursorrules, MIGRATION_TO_LOCAL.md |

---

## 🔬 Technical Stack Summary

| Layer | Technology | Version |
|:------|:-----------|:--------|
| Core Language | Python | 3.11.9 |
| AI Brain | Google Gemini 2.0 Flash | Latest |
| Vision | MediaPipe Hands | 0.10.14 |
| Vision Rendering | OpenCV | 4.13 |
| Remote Bridge | Telegram Bot API | v6+ |
| Long-term Memory | SQLite3 | stdlib |
| OS Automation | PyAutoGUI | 0.9.54 |
| MCP Bridge | Node.js | v24.14.0 |
| MCP Protocol | @modelcontextprotocol | 1.x |
| Voice Input | SpeechRecognition | 3.x |
| Voice Output | OpenAI TTS | gpt-4o-mini-tts |
| Localization | Custom i18n (JSON) | Internal |

---

## ⚠️ Phase 1 Known Limitations

1. **Cloud dependency** — all AI inference goes through Google Gemini API (token costs, rate limits, privacy)
2. **Windows-only** — PyAutoGUI and path handling are Windows-specific
3. **`mcp` library not installed** — MCP Hub skill doesn't load (Python `mcp` package unavailable)
4. **`googlesearch` library** — web_research Google search sub-module disabled
5. **Gemini 429 rate limit** — free tier exhausted quickly under heavy use

---

## 🏔️ Phase 2 Preview: Local-First (AXIS V3)

This is the strategic transition already planned and documented in `MIGRATION_TO_LOCAL.md`:

| Component | Phase 1 (Cloud) | Phase 2 (Local) |
|:----------|:---------------|:----------------|
| **LLM** | Google Gemini 2.0 Flash | Ollama (Llama 3 / Mistral) |
| **Vision Analysis** | Gemini Vision API | Moondream2 / LLaVA |
| **Speech-to-Text** | Google STT | OpenAI Whisper (local) |
| **Desktop UI** | Terminal output | PyQt6 "Iron Man" HUD overlay |

**Goal:** 100% offline operation, zero token costs, zero data leaving the machine.

---

## 🔗 Repository

**GitHub:** [github.com/Eugen1189/ATLAS-AI](https://github.com/Eugen1189/ATLAS-AI)

---

*AXIS Phase 1 — Built March 2026. Transitioning to local-first in Phase 2.*
