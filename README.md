# 🌌 AXIS V2.5: Autonomous Spatial AI & MCP Framework

**AXIS** (Agentic X-interface Intelligent System) is a state-of-the-art multimodal AI Agentic Framework powered by **Google Gemini 2.0 Flash**. Unlike traditional LLM wrappers, AXIS bridges the gap between physical human gestures, local OS operations, and cloud intelligence through a standardized **Model Context Protocol (MCP)** architecture.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/Node.js-v24.14.0-green.svg)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.11.9-blue.svg)](https://www.python.org/)
[![Localization](https://img.shields.io/badge/Localization-EN%20%7C%20UK%20%7C%20ES-orange.svg)](#-internationalization-i18n)

---

## 🚀 Core Pillars

### 👁️ Spatial Computing & Computer Vision
AXIS transforms your workspace into a 3D interface using MediaPipe and OpenCV:
- **Visual Hotkeys:** A gesture "L" triggers smart screenshots with automated JSON logging and instant Telegram transmission.
- **Virtual Zones 2.0:**
  - **Volume Zone (Top 15%):** Intuitive hand-tracking for system audio control.
  - **Media Zone (Bottom 15%):** Swipe gestures for track navigation and "Pinch" for Play/Pause.
- **🙅‍♂️ Sleep Gesture (Kill-Switch):** Cross your arms for 1.5 seconds to fully shut down the Vision Engine, releasing the camera and all CPU resources.

### 🔌 MCP Native Ecosystem
Deep integration with the **Model Context Protocol** (Anthropic) allows AXIS to act as a secure host for local resources:
- **Filesystem MCP:** Standardized read/write access to project directories.
- **GitHub MCP:** Autonomous repository management (commits, issues, and PRs).
- **Background Bridge:** Automated Node.js (`npx`) server orchestration with robust path-resolution for Windows environments.

### 🛡️ The Guardian Protocol & SecurityGuard
- **Enterprise Pre-flight Check:** A `SecurityGuard` layer intercepts all tool executions, performing directory-level sandbox validations and preventing accidental core system rewrites (like `rm -rf` or UI modification).
- **Human-in-the-Loop:** AXIS pauses critical operations (e.g., file deletion, `git push`) and waits for your explicit ✅ / ❌ confirmation via Telegram before proceeding.
- **Privacy HUD:** High-visibility `🟢 LIVE` / `⚪ IDLE` indicators on the Vision overlay ensure you are always aware of your camera's active status.

### 🧠 Adaptive Artificial Intelligence
Unlike static agents, AXIS learns from its mistakes:
- **Healer Brain (Post-Mortem):** When a tool loop fails, AXIS summons a localized "Healer" instance to analyze the error trace and synthesize a new *Dynamic Micro-Rule*.
- **Self-Improving System Prompt:** Learned rules are stored in `dynamic_rules.json` and injected into the prompt upon every boot, meaning AXIS becomes smarter and more tailored to your specific project over time.
- **Double-Pass Reasoning:** High-risk actions undergo an "Internal Review" pass. If the AI is `<70%` confident in its generated tool arguments, execution is blocked.

### 🔍 Hybrid Intelligence Engine
A dual-layered research module located in `agent_skills/web_research`:
- **Google Search:** Low-latency tool for fetching direct links and real-time news.
- **Perplexity AI:** High-reasoning synthesis for deep technical research and documentation lookup.

### 📱 Real-time Telegram Bridge
A robust, asynchronous communication layer providing:
- Instant visual reports (screenshots + JSON logs).
- Remote command execution from anywhere.
- System status notifications and Guardian confirmations.

---

## 🏗️ Architecture (V2.5 Modular)

AXIS utilizes a **Dynamic Skill Discovery** system — drop a new folder into `agent_skills/` and it's automatically loaded on the next boot.

```text
AXIS_v2/
├── agent_skills/          # 🧩 Pluggable skills
│   ├── audio_interface/   # Voice Speech-To-Text & TTS
│   ├── file_master/       # File system read/write operations
│   ├── mcp_hub/           # Node.js MCP Bridge connection
│   ├── memory_manager/    # SQLite long-term memory
│   ├── os_control/        # PyAutoGUI screen automation
│   ├── telegram_bridge/   # Async Telegram bot & confirmations
│   ├── terminal_operator/ # PowerShell/CMD command execution
│   ├── vision_eye/        # Computer Vision & MediaPipe logic
│   ├── web_research/      # Google Search & Perplexity AI
│   └── workspace_manager/ # Project discovery & IDE launcher
├── config/
│   └── locales/           # 🌐 i18n JSON files (en.json, uk.json, es.json)
├── core/
│   ├── orchestrator.py    # 🧠 Gemini/Ollama brain & tool dispatcher
│   ├── security/guard.py  # 🛡️ Centralized SecurityGuard validation
│   └── i18n.py            # Language module
├── memories/              # 💾 SQLite DB and vision snapshots
└── main.py                # 🚀 Bootloader
```

- **Orchestrator:** Scans `agent_skills/*/manifest.py` on boot to dynamically register function-calling tools for Gemini or Ollama.
- **Memory Manager:** Persistent SQLite-backed context for user preferences, long-term fact retention, and `dynamic_rules.json` storage.
- **Localization (i18n):** Full multi-language support (EN, UK, ES) via `core/i18n.py` and JSON locale files.

---

## 🛠️ Technical Stack

| Component | Technology |
| :--- | :--- |
| **Core Language** | Python 3.11.9+ |
| **AI Brains** | Google Gemini 2.0 Flash / **Local Ollama** (Llama 3.2) |
| **MCP Runtime** | Node.js v24.14.0 *(bleeding-edge MCP support)* |
| **Vision Engine** | MediaPipe 0.10.14, OpenCV 4.13 |
| **Adaptive Logic** | Dynamic Healer Instance, Self-Modifying System Prompts |
| **Research** | Perplexity AI (sonar model) |

---

## ⚡ Quick Start

### 1. Prerequisites
- **Webcam** — required for the Spatial Computing module
- **Windows OS** — currently optimized for Windows filesystem and UI automation
- **Telegram Account** — required for the Guardian Protocol and remote control
- **Python 3.11+** and **Node.js v18+**

### 2. Environment Setup
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration (`.env`)
Create a `.env` file in the `AXIS_v2/` directory:
```env
# --- Required ---
GEMINI_API_KEY=your_google_ai_studio_key
TELEGRAM_BOT_TOKEN=your_botfather_token
TELEGRAM_CHAT_ID=your_numeric_chat_id

# --- Localization ---
LANGUAGE=en  # Options: en | uk | es

# --- Optional Skills ---
OPENAI_API_KEY=your_openai_key         # For TTS voice output
PERPLEXITY_API_KEY=your_perplexity_key # For deep web research
GITHUB_PERSONAL_ACCESS_TOKEN=your_pat  # For GitHub MCP
```

> **How to get your credentials:**
> - `GEMINI_API_KEY` → [Google AI Studio](https://aistudio.google.com/)
> - `TELEGRAM_BOT_TOKEN` → Create a bot via [@BotFather](https://t.me/BotFather)
> - `TELEGRAM_CHAT_ID` → Send a message to your bot, then call `https://api.telegram.org/bot<TOKEN>/getUpdates`

### 4. Launch AXIS
```bash
python AXIS_v2/main.py
```

---

## 💬 Usage Examples

AXIS accepts natural language commands via terminal text, voice input (press ENTER), or Telegram messages:

| Input | Action |
| :--- | :--- |
| *"Open my project SystemCOO in Cursor IDE."* | Finds and launches the project workspace |
| *"Take a screenshot and send it to Telegram."* | Captures screen, saves JSON log, forwards to Telegram |
| *"Search Perplexity for the latest Node.js 22 features."* | Deep research query with synthesized answer |
| *"Turn on the vision system."* | Activates hand-gesture tracking via webcam |
| *"Remember that my preferred language is Python."* | Stores fact in long-term SQLite memory |
| *"Push my current changes to GitHub."* | Triggers Guardian Protocol — waits for your ✅ or ❌ in Telegram |

---

## 🏔️ Roadmap: The Journey to Local-First (AXIS V3)

Our mission is **100% data privacy, zero token costs, and total autonomy**.

| Component | Current (Cloud-Based) | Transitioning To (Local-First) |
| :--- | :--- | :--- |
| **LLM Core** | Google Gemini 2.0 Flash | **[Completed]** Ollama (Llama 3.2 / Mistral) natively supported via `AI_BRAIN=ollama` |
| **Reasoning Engine**| Cloud-based one-shot queries | **[Completed]** Double-Pass Internal Review & Streaming Thought parsing |
| **Vision Analysis** | Gemini Vision API | **[Next]** Moondream2 or LLaVA integration |
| **Speech-to-Text** | Google STT | **[Next]** OpenAI Whisper (local) |

### Migration Phases
1. ✅ **Phase 1 — Local LLM Integration:** Full Ollama ReAct adapter, Multi-JSON tool parsing, and streaming `<thought>` tags implemented.
2. 🔄 **Phase 2 — Autonomous Immunity:** The "Healer Brain", dynamic rule discovery, and SecurityGuard sandbox limits. *(Done)*
3. 🚧 **Phase 3 — Iron Man HUD:** A PyQt6 semi-transparent desktop overlay for real-time gesture zone visualization.

---

## 🤝 Contributing

Contributions are welcome! To add a new skill:
1. Create a new folder under `agent_skills/your_skill_name/`.
2. Add a `manifest.py` file that exports a list `EXPORTED_TOOLS` of Python functions.
3. Write clear docstrings — Gemini reads them to decide when to call your tool.
4. Restart AXIS. Your skill is automatically discovered.

---

*Built for the future of human-computer interaction.*
