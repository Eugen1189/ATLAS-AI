# 🌌 AXIS v2.7.7 - Autonomous Spatial AI Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-2.7.7-blue.svg)]()
[![Core](https://img.shields.io/badge/Core-Local--First-green.svg)]()

**AXIS** (Autonomous eXtended Intelligence System) is a high-performance, local-first AI agent designed for advanced OS interaction, developer automation, and multi-agent coordination. Built with a focus on reliability, security, and "Ironclad" parsing.

---

## 🛠️ Key Technologies 2026

*   **Brain**: [Ollama](https://ollama.ai/) running **Qwen2.5-Coder:7b** (Specialized for Tool Calling & Logic).
*   **Security Architecture**: Universal `@agent_tool` decorator for fail-safe execution.
*   **Protocol**: MCP (Model Context Protocol) Hub ready.
*   **Connectivity**: Integrated **Telegram Bridge** for remote smartphone control.
*   **Audio**: 100% Offline TTS via `pyttsx3`.

---

## 🦾 Core Modules

### 📂 FileMaster (Smart Navigation)
Intelligent filesystem access with support for "magic" keywords (`Desktop`, `Documents`, `~`). Can physically open files/folders (`open_item`) like a real user.

### 💻 Terminal Operator
Secure PowerShell/CMD execution with a built-in **Command Firewall**. Prevents destructive actions (format, recursive deletion of system files) while returning rich feedback to the LLM.

### 🔍 Deep System Diagnostics
Real-time hardware monitoring (CPU, RAM, Disk) with accurate Windows 11 detection (build-aware detection protocol).

### 🛰️ Web Research (Advanced Analyst)
Deep multi-step research using Perplexity-style synthesis and recursive web scraping.

---

## 🚀 Quick Start

1.  **Environment**: Ensure Python 3.11+ and [Ollama](https://ollama.ai/) are installed.
2.  **Model**: `ollama run qwen2.5-coder:7b`
3.  **Dependencies**:
    ```bash
    pip install -e .
    ```
4.  **Configure**: Update `.env` with your API keys (Perplexity, Telegram).
5.  **Run**:
    ```bash
    python Atlas_v2/main.py
    ```

---

## 🛡️ "Ironclad" Reliability System

Unlike standard agents, AXIS implements a multi-layer defense:
1.  **The Parser**: Aggressive JSON repair for malformed LLM outputs.
2.  **The Wrapper**: Every skill is isolated; tool failures trigger a `SYSTEM_INSTRUCTION` instead of a crash.
3.  **The Firewall**: Regex-based command filtering prevents "AI hallucinations" from damaging the OS.

---

## 📱 Remote Control (Telegram)
Control your PC from anywhere. AXIS can send reports, screenshots of your work, and request Human-In-The-Loop (HITL) confirmations for critical actions.

---

## 📜 License
MIT License. Created by Eugen1189.
