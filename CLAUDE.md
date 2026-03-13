# CLAUDE.md — Claude Integration Guidelines

## 🛠 Build & Development
- **Install Dependencies**: `pip install -e .`
- **Run Application**: `python Atlas_v2/main.py`
- **Maintenance**: `python Atlas_v2/scripts/rag_maintenance.py`

## 🧪 Testing & Quality
- **Run Tests**: `pytest`
- **Run Specific Test**: `pytest Atlas_v2/tests/test_brain.py`
- **Linting**: `ruff check .`
- **Type Checking**: `mypy .` (if configured)

## 📜 Coding Standards
- **Logging**: Use `structlog`. NO `print()` statements.
- **Typing**: Strict Type Hints required for all functions/classes.
- **Documentation**: Google-style docstrings are mandatory (used for tool manifest generation).
- **Architecture**:
    - Add logic only via `agent_skills/` (using `manifest.py`).
    - Use the `@agent_tool` decorator for all exported capabilities.
    - All tools must accept `**kwargs`.
- **Naming**: 
    - Variables/Functions: `snake_case`
    - Classes: `PascalCase`
    - Constants: `UPPER_SNAKE_CASE`

## 🛡 Security & Protocols
- **Firewall**: Respect the Command Firewall. Do not attempt to bypass security checks.
- **Self-Healing**: Follow the `[CRITICAL SYSTEM DIRECTIVE]` protocol: fix and re-execute failed commands silently.
- **Git**: Maintain atomic commits and ensure tests pass before completion.

---
*Optimized for AXIS v2.7 Framework.*
