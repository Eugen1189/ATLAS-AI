# 🌌 AXIS Project Development Playbook

> **Edition:** Antigravity & Google Agents  
> **Last Updated:** 2026-03-03

---

## 1. Project Context

**AXIS** (Agentic X-interface Intelligent System) is a Spatial AI Agentic Framework designed for multimodal, hands-free human-computer interaction.

| Layer | Technology |
| :--- | :--- |
| **Core** | Python 3.11.9 |
| **Vision** | MediaPipe + OpenCV (Gesture Control) |
| **Remote Bridge** | Telegram (Guardian Protocol) |
| **MCP Infrastructure** | Node.js v24 (Model Context Protocol) |
| **Localization** | i18n (JSON-based, `config/locales/`) |

---

## 2. Golden Rules (Mandatory for All Contributions)

### 🌍 Rule 1 — Zero Hardcoded Strings (i18n)

**No plain text** is allowed inside code (`print`, `logging`, Telegram messages, etc.).  
Every user-facing string must be retrieved via the `lang.get()` method.

```python
# ❌ WRONG
print("Starting AXIS system...")

# ✅ CORRECT
print(lang.get("system.start"))
```

- All new string keys **must** be added to both `config/locales/en.json` and `config/locales/uk.json`.
- Spanish (`es.json`) should be updated as well for completeness.

---

### 🛡️ Rule 2 — Guardian Protocol (Human-in-the-Loop)

Any **destructive or irreversible action** must route through Telegram confirmation before execution.

**Actions that require confirmation:**
- File deletion or overwriting
- System-level changes (registry, startup, autorun)
- `git push`, `git commit`, `git reset`
- Any command executed via `terminal_operator`

Use the existing `ask_user_confirmation()` tool from `telegram_bridge`:
```python
from agent_skills.telegram_bridge.manifest import ask_user_confirmation

confirmed = ask_user_confirmation("Are you sure you want to delete /data/logs?")
if confirmed:
    # proceed
```

---

### 🐍 Rule 3 — Python Code Standards

| Practice | Requirement |
| :--- | :--- |
| **Type Hints** | Mandatory on all function signatures |
| **Docstrings** | Google-style for all classes and public methods |
| **Logging** | Use `logs/axis.log` via `logging` module — avoid raw `print()` in production |
| **Error Handling** | All exceptions must be caught and reported via `lang.get()` or logged |

```python
def execute_command(command: str) -> str:
    """Executes a shell command and returns its output.
    
    Args:
        command: The shell command string to execute.
        
    Returns:
        A string containing stdout/stderr of the command.
    """
    ...
```

---

## 3. Architectural Structure

```text
AXIS_v2/
├── core/              # 🧠 Brain, Orchestrator, i18n — DO NOT mix skill logic here
├── agent_skills/      # 🧩 Isolated plugins — one skill per subfolder
│   └── my_skill/
│       └── manifest.py  # Must export: EXPORTED_TOOLS = [func1, func2]
├── vision_eye/        # 👁️ ONLY computer vision logic (MediaPipe, OpenCV)
├── config/
│   └── locales/       # 🌐 Language dictionaries (en.json, uk.json, es.json)
└── memories/          # 💾 Persistent storage (SQLite, JSON logs, screenshots)
```

**Rules:**
- `core/` is a **protected zone** — only orchestration and infrastructure live here.
- Each `agent_skills/` subfolder is **self-contained** — it must not import from other skill folders directly.
- Skills communicate through the `orchestrator`, not through direct imports.

---

## 4. Agent Workflow Algorithm

When implementing any new feature, follow these steps **in order**:

1. **Analyze** — Read the existing code of the affected module(s) before writing anything.
2. **Plan** — Document the proposed changes (ADR-style) before coding.
3. **i18n Check** — Ensure every new user-facing string is added to the locale JSON files.
4. **Safety Check** — Ask: *"Does this action require a Guardian Protocol confirmation?"*
5. **Implement** — Write code in small, iterative changes. Commit frequently.
6. **Verify** — Run the module and confirm no regressions in existing functionality.

---

## 5. Environment Specifics

- **OS Target:** Windows (paths use `\\`, `pyautogui` is tuned for Windows screen resolution).
- **MCP Access:** Use `mcp_hub` for standardized filesystem and GitHub API operations — do not access files directly when an MCP tool is available.
- **Background Threads:** Use `daemon=True` for all background threads to ensure clean shutdown.
- **Encoding:** Always use `encoding='utf-8'` when opening files. Set `PYTHONIOENCODING=utf-8` when running the app.

---

## 6. Adding a New Skill (Checklist)

- [ ] Create folder: `agent_skills/your_skill_name/`
- [ ] Create `manifest.py` with typed functions and Google-style docstrings
- [ ] Export tools: `EXPORTED_TOOLS = [your_function]`
- [ ] Add any new string keys to `config/locales/en.json`, `uk.json`, `es.json`
- [ ] Import `from core.i18n import lang` and use `lang.get()` for all output
- [ ] Apply Guardian Protocol to any destructive actions
- [ ] Test: restart AXIS and confirm the skill appears in the loaded tools list
