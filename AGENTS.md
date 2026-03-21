# 🤖 AGENTS.md — AXIS Project Constitution

## 📝 Overview
This document serves as the primary "constitution" for AI agents (AXIS, Claude, Antigravity, etc.) interacting with this repository. It defines the technical standards, naming conventions, and operational protocols to ensure safe and efficient autonomous development.

---

## 🏗️ Technical Stack (2026)
- **Core Engine**: Python 3.11+
- **Security Protocol**: Bunker v5.5 (Egress Filtering + HITL + Ephemeral Sandboxing)
- **Brain**: [Ollama](https://ollama.ai/) (Optimized for Qwen2.5-Coder:7b)
- **RAG & Memory**: [ChromaDB](https://www.trychroma.com/)
- **Protocol**: MCP (Model Context Protocol)
- **Interface**: PyQt6 (HUD) & Telegram (Remote Control)

---

## 🛠️ Development Standards & Naming

### 1. Skill Isolation
- All autonomous capabilities must be implemented as separate "Skills".
- **Location**: `Atlas_v2/agent_skills/`
- **Structure**: Each skill must be in its own directory with a `manifest.py` containing `@agent_tool` decorated functions.
- **Registration**: Do NOT modify the orchestrator; use the auto-discovery system.

### 2. Tool Calls
- All tool definitions must include Google-style docstrings (crucial for Ollama manifest generation).
- All tool functions must support `**kwargs` to remain resilient against hallucinated LLM arguments.
- **Discovery-First Architecture**: BEFORE calling unknown or external tools (MCP), the agent MUST call `list_server_tools` to verify signatures. Use `search_web` for missing documentation.
- Use `structlog` for all logging. **NO `print()` statements allowed.**

---

## 🛡️ Operational Protocols

### 1. The Firewall & Security Guard
- Destructive commands (format, rm -rf /, etc.) are blocked at the code level.
- **Firewall Cooperation**: Access to `.env` and `.git` is restricted. If a tool call is blocked by `security.blacklist_blocked`, the agent MUST adapt by using templates (`.env.example`) or requesting specific permission, NEVER by silently skipping.

### 2. Self-Healing: The [CRITICAL SYSTEM DIRECTIVE]
To prevent LLM deadlocks (waiting for external fix), the system implements an autonomous self-correction loop.

**Logic**:
- When `execute_command` (or similar) fails, it returns a message containing `[CRITICAL SYSTEM DIRECTIVE]`.
- **Agent Action**: If you see this directive, you MUST NOT apologize or explain the failure to the user.
- **Procedure**:
    1.  Analyze the provided error message.
    2.  Correct the syntax or logic of the command.
    3.  Immediately re-execute the tool with the corrected parameters.
    4.  Remain silent and focused on the corrective loop until success.

---

## 🧪 Quality Assurance
- **Testing**: `pytest` is mandatory for all core changes.
- **Coverage**: Maintain >80% coverage.
- **Linting**: Rules are enforced by `ruff`.

---

## 🛡️ Anti-Looping & Protection
- **Infinite Loop Prevention**: If a tool fails more than twice with the same or similar arguments, AXIS must STOP and request Human-In-The-Loop (HITL) clarification.
- **Argument Mapping**: When in doubt about argument names, always use `path` for file-related tasks and `text` for strings/prompts.
- **Zero-Placeholder Policy**: Agents are strictly forbidden from using `[Insert Here]`, `TODO`, or placeholders in code. All output must be PRODUCTION READY.
- **Evidence-Based Completion**: "MISSION ACCOMPLISHED" must only be reported if backed by successful tool execution and/or test results (`pytest`/`verify_code`).
- **Fail-Fast**: If `parser_healer` (Healer 2.0) is triggered twice on the same step, abort current plan and ask the user for help.

---
*Created as part of the 2026 AI standard integration.*
