# 🏔️ Migration to Local-First Architecture (Atlas V3 Roadmap)

This document outlines the strategic transition of the **Atlas** project from cloud-dependent APIs (Google Gemini) to a fully local-first infrastructure. Our mission is to ensure 100% data privacy, zero token costs, and total independence from third-party service providers.

---

## 🎯 Why Local-First?

1. **Privacy & Security:** Your sensitive data (screenshots, files accessed via MCP, system logs) never leave your machine.
2. **Cost Efficiency:** Leverage your own GPU/CPU power instead of recurring API subscriptions.
3. **Autonomy:** Atlas remains fully functional without an active internet connection.
4. **Low Latency:** Instant gesture processing and command execution without round-trip delays to external servers.

---

## 🛠️ Technical Stack Evolution (V3)

| Component | Current (Cloud-Based) | Future (Local-First) |
| :--- | :--- | :--- |
| **LLM Core** | Google Gemini 2.0 Flash | **Ollama** (Llama 3 / Mistral / DeepSeek) |
| **Vision Analysis** | Gemini Vision API | **Moondream2** or **Llava** (via Ollama) |
| **Speech-to-Text** | Google STT | **OpenAI Whisper** (Local Deployment) |
| **Embedding** | Google Embeddings | **nomic-embed-text** (Local) |

---

## 🏗️ Migration Roadmap

### Phase 1: Ollama Bridge Integration
- Implement the `OllamaClient` within `core/brain.py`.
- Configure automated model pulling (e.g., `llama3`, `mistral`) on first launch.
- Maintain full **MCP (Model Context Protocol)** compatibility for local models.

### Phase 2: Offline Vision & Multimodal Capabilities
- Replace cloud-based screenshot analysis with local Vision-Language Models (VLM) like Llava.
- Optimize **MediaPipe** gesture processing to run concurrently with local LLMs without GPU bottlenecking.

### Phase 3: "Mock & Dev" Environment
- Introduce a Developer Mode that simulates AI responses for testing gesture logic, file operations, and Telegram notifications without consuming compute resources during debugging.

---

## 🚀 Getting Started (Preview)

To prepare your environment for the V3 transition, please install **Ollama** on your system:

1. Download Ollama from [ollama.com](https://ollama.com).
2. Run the following command in your terminal:
   ```bash
   ollama run llama3
   ```

Atlas V3 will automatically attempt to connect to the local API at port :11434.

Status: Work in Progress 🛠️

We are actively re-engineering the core to make Atlas the most private and powerful local AI agent available in 2026.
