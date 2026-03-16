# 🌌 AXIS v5.5 "Bunker" - Autonomous Spatial AI Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/Version-5.5--Bunker-blue.svg)]()
[![Core](https://img.shields.io/badge/Core-Local--First-green.svg)]()

**AXIS** (Autonomous eXtended Intelligence System) is a high-performance, local-first AI agent designed for advanced OS interaction. Built for extreme reliability via **Bunker v5.5 Security Protocol**.

---

## 🏛️ Pure Architecture & Inheritance
Starting with v2.7.19, AXIS implements a unified brain inheritance model:
*   **BaseBrain**: Centralized core for Blueprint loading, RAG initialization, and Memory management.
*   **OllamaBrain**: Local execution optimized for Qwen2.5-Coder.
*   **GeminiBrain**: High-reasoning cloud fallback.
*   **Unified Vision**: A centralized `VisionEngine` singleton prevents camera/screen access conflicts across processes.

---

## 🛠️ Key Technologies 2026

*   **Brain**: [Ollama](https://ollama.ai/) running **Qwen2.5-Coder:7b**.
*   **Security**: Aggressive JSON repair + Command Firewall.
*   **Audio**: Single-pass calibration for instant voice responsiveness.
*   **Vision**: Regional high-res analysis via `VisionEngine`.

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

## 📅 ROADMAP 2026
*   **Wait-Word 2.0** - Instant-start audio capture [COMPLETED].
*   **Pure Architecture** - Elimination of dead code and redundant logic [COMPLETED].
*   **Q2: Multi-Agent Protocol** - Collaboration between Skill-Shards.

---

## 🚀 Setup

1.  **Dependencies** (Cleaned for v2.7.20):
    ```bash
    pip install -e .
    ```
2.  **Environment**: Update `.env` (Ollama, Gemini, Telegram tokens).
3.  **Run**: `python Atlas_v2/main.py`

---

## 🛡️ "Ironclad" Reliability System
1.  **The Parser**: Intercepts teacher-hallucinations and repairs malformed JSON.
2.  **The Wrapper**: Every `@agent_tool` is functionally isolated.
3.  **The Firewall**: Blocks destructive OS commands via regex protection.

---

## 📱 Remote Control (Telegram)
Control your PC from anywhere. AXIS sends screenshots, hardware reports, and asks for confirmations before critical operations.

---

## 📜 License
MIT License. Created by Eugen1189.
