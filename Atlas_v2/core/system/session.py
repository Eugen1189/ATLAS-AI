import json
import os
from core.logger import logger

# [ANTIGRAVITY v6.0.0] Strategic Session Persistence
# This ensures AXIS doesn't 'forget' its project or goal between prompts.

SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".axis_session.json")

class SessionManager:
    @staticmethod
    def save_state(project_root: str, goal: str = ""):
        try:
            state = {
                "project_root": str(project_root),
                "current_goal": goal,
                "timestamp": str(os.path.getmtime(SESSION_FILE)) if os.path.exists(SESSION_FILE) else "0"
            }
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=4)
            logger.info("session.state_saved", path=project_root)
        except Exception as e:
            logger.warning("session.save_failed", error=str(e))

    @staticmethod
    def load_state() -> dict:
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.info("session.state_loaded", path=state.get("project_root"))
                    return state
            except Exception as e:
                logger.warning("session.load_failed", error=str(e))
        return {}

    @staticmethod
    def clear_session():
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
            logger.info("session.cleared")
