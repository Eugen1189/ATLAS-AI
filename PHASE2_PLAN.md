# Implementation Plan: Phase 2 - Local-First (AXIS v3)

This plan outlines the refactoring of AXIS to support both cloud-based (Gemini) and local-first (Ollama) AI backends.

## Goals
1. **Decouple AI Logic**: Separate the orchestrator's tool loading and session management from the specific LLM implementation.
2. **Pluggable Architecture**: Introduce a `BaseBrain` interface.
3. **Multi-Backend Support**: 
   - `GeminiBrain` (Cloud)
   - `OllamaBrain` (Local)
   - `MockBrain` (For development/testing)
4. **Environment-Driven Selection**: Use `.env` to toggle between backends.

## Step 1: Core Refactoring
- Rename `core/orchestrator.py` logic or create `core/brain.py` to house the new structure.
- Define `BaseBrain` abstract class with methods:
  - `initialize(available_tools)`
  - `think(user_input) -> str`
- Implement `GeminiBrain` using existing `AxisCore` logic.

## Step 2: Ollama Integration
- Create `OllamaBrain` using the `ollama` Python library (or raw `requests` to the local API).
- Implement tool status handling for Ollama (since tool calling in local models varies).

## Step 3: Orchestrator Update
- Update `AxisCore` to use the selected Brain.
- Ensure tool discovery still works across both backends.

## Step 4: Fix Existing Bugs
- Fix the `lang` shadowing bug in `agent_skills/web_research/google_logic.py`.
- Ensure `mcp` library is properly handled or mocked if missing.

## Step 5: (Future) Local Vision & HUD
- Integrate `Moondream2` for local image analysis.
- Prepare PyQt6 HUD skeleton.

---

> [!NOTE]
> We will start with Step 1 and 4 to ensure the system is stable before adding Ollama.
