# 🌌 ATLAS V2: Autonomous Spatial AI & MCP Framework

**ATLAS (SystemCOO)** is a sophisticated, multi-modal AI Agentic Framework built on **Google Gemini 2.0 Flash**. Unlike traditional assistants, Atlas V2 bridges the gap between physical gestures, local OS operations, and cloud intelligence through a standardized **Model Context Protocol (MCP)** architecture.

---

## 🚀 Core Pillars

### 👁️ Spatial Computing & Computer Vision
Atlas transforms your workspace into a 3D interface using MediaPipe and OpenCV:
- **Visual Hotkeys:** Gesture "L" triggers smart screenshots with automated JSON logging and Telegram transmission.
- **Virtual Zones 2.0:**
  - **Volume Zone (Top 15%):** Intuitive hand-tracking for system audio control.
  - **Media Zone (Bottom 15%):** Swipe gestures for track navigation and "Pinch" for Play/Pause.
- **Fist Gesture:** Instant tracking pause for seamless workflow transitions.

### � MCP Native Ecosystem
Full integration with the **Model Context Protocol** (Anthropic) allows Atlas to act as a secure host for local resources:
- **Filesystem MCP:** Standardized read/write access to project directories.
- **GitHub MCP:** Autonomous repository management (commits, issues, and PRs).
- **Background Bridge:** Automated Node.js (npx) server orchestration with path-resolution for Windows.

### 🔍 Hybrid Intelligence Engine
A dual-layered research module located in `agent_skills/web_research`:
- **Google Search:** Low-latency tool for fetching direct links and real-time news.
- **Perplexity AI:** High-reasoning synthesis for deep technical research.
- **Dynamic Orchestration:** Atlas automatically chooses the most cost-effective tool based on the query.

### 📱 Real-time Telegram Bridge
A robust, asynchronous communication layer providing:
- Instant visual reports (screenshots + logs).
- Remote command execution.
- System status notifications with sanitized Unicode logging for Windows stability.

---

## 🏗️ Architecture (V2 Modular)

Atlas V2 utilizes a **Dynamic Skill Discovery** system:
- **Orchestrator:** Located in `core/orchestrator.py`, it scans `agent_skills/*/manifest.py` on boot.
- **Function Calling:** Native Gemini 2.0 implementation for zero-latency tool selection.
- **Memory Manager:** Persistent SQLite-backed context for user preferences and long-term facts.

---

## 🛠️ Technical Stack

- **Language:** Python 3.11.9
- **Environment:** Node.js v24.14.0 (for MCP runtimes)
- **Computer Vision:** MediaPipe 0.10.14, OpenCV 4.13
- **Automation:** PyAutoGUI
- **AI Models:** Gemini 2.0 Flash, OpenAI (Voice), Perplexity

---

## ⚡ Quick Start

1. **Environment Setup:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure .env:**
   Add your `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, and `TELEGRAM_CHAT_ID`. (For MCP servers, also add `GITHUB_PERSONAL_ACCESS_TOKEN`, `GOOGLE_API_KEY`, etc. if configured).

3. **Launch Atlas:**
   ```bash
   python Atlas_v2/main.py
   ```
