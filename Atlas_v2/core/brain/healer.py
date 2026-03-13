import json
import os
import re

from core.logger import logger

class Healer:
    """Модуль самокорекції для AXIS v2.7.27"""
    
    RECIPES = {
        "file_not_found": {
            "patterns": [r"no such file", r"file not found", r"cannot find the path"],
            "suggestion": "search_and_retry"
        },
        "permission_denied": {
            "patterns": [r"permission denied", r"access is denied"],
            "suggestion": "try_elevated_or_move"
        },
        "syntax_error": {
            "patterns": [r"syntaxerror", r"invalid syntax"],
            "suggestion": "lint_and_fix"
        },
        "tool_not_found": {
            "patterns": [r"tool '.*' is not registered", r"not found", r"command not found", r"is not recognized"],
            "suggestion": "incremental_scan"
        },
        "missing_argument": {
            "patterns": [r"missing \d+ required positional argument", r"got an unexpected keyword argument", r"argument .* is required"],
            "suggestion": "check_docs_and_abort"
        }
    }

    def __init__(self, rules_path="memories/dynamic_rules.json"):
        self.rules_path = rules_path

    def summarize_evolution(self):
        """Виводить список вивчених правил при старті системи."""
        if os.path.exists(self.rules_path):
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            
            print("\n[AXIS EVOLUTION REPORT]")
            print("Learned Lessons (Dynamic Micro-Rules):")
            if not rules:
                print("- No rules learned yet. System is in baseline state.")
            for i, rule in enumerate(rules, 1):
                print(f"{i}. {rule}")
            print("-" * 30 + "\n")
        else:
            print("[AXIS EVOLUTION]: Baseline state. No dynamic rules found.")


    @staticmethod
    def diagnose(error_message: str) -> str:
        """Визначає тип помилки за текстом"""
        err_lower = error_message.lower()
        for error_type, data in Healer.RECIPES.items():
            if any(re.search(p, err_lower) for p in data["patterns"]):
                return error_type
        return "unknown_anomaly"

    def propose_fix(self, error_type: str, last_action: dict):
        """Формує нову стратегію виправлення"""
        if error_type == "file_not_found":
            target = last_action.get("arguments", {}).get("filepath", "unknown")
            return f"The file '{target}' was not found. Use 'list_directory' to find the correct path and try again."
        
        if error_type == "tool_not_found":
            tool = last_action.get("tool_name", "unknown")
            return f"The tool or command '{tool}' is not currently available. I am initiating an 'incremental_scan' to update my environment data. Please try again after the scan."

        if error_type == "missing_argument":
            tool = last_action.get("tool_name", "unknown")
            return f"CRITICAL: Tool '{tool}' failed due to incorrect arguments. STOP guessing. Use 'get_tool_info' to see the exact schema before retrying. If the tool is fundamentally wrong for this task, switch to RAG search."

        return "Anomaly detected. Please review logs and manually intervene."
