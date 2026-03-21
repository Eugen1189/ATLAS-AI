import json
import os
import re

from core.logger import logger

class Healer:
    """Модуль самокорекції для AXIS v2.7.27"""
    
    RECIPES = {
        "file_not_found": {
            "patterns": [r"no such file", r"file not found", r"cannot find the path", r"errno 2"],
            "suggestion": "search_and_retry"
        },
        "permission_denied": {
            "patterns": [r"permission denied", r"access is denied", r"errno 13"],
            "suggestion": "try_elevated_or_move"
        },
        "syntax_error": {
            "patterns": [r"syntaxerror", r"invalid syntax", r"unexpected indent"],
            "suggestion": "lint_and_overwrite"
        },
        "tool_not_found": {
            "patterns": [r"tool '.*' is not registered", r"not found", r"command not found", r"is not recognized", r"is not a registered tool"],
            "suggestion": "incremental_scan"
        },
        "missing_argument": {
            "patterns": [r"missing \d+ required positional argument", r"got an unexpected keyword argument", r"argument .* is required", r"called with empty arguments"],
            "suggestion": "check_docs_and_abort"
        },
        "json_parse_error": {
            "patterns": [r"json parsing failed", r"incomplete block", r"invalid control character", r"expecting value"],
            "suggestion": "fix_json_format"
        },
        "security_rejection": {
            "patterns": [r"security rejected", r"firewall blocked", r"dangerous command", r"access denied"],
            "suggestion": "find_alternative_path"
        },
        "git_pathspec_error": {
            "patterns": [r"pathspec '.*' did not match any file", r"is not a git command", r"unknown option"],
            "suggestion": "fix_git_quotes_and_args"
        },
        "project_not_found": {
            "patterns": [r"project '.*' not found", r"error: project '.*' not found"],
            "suggestion": "list_and_verify_workspaces"
        },
        "sql_no_such_column": {
            "patterns": [r"no such column", r"no such table", r"operationalerror"],
            "suggestion": "verify_database_schema"
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
            target = last_action.get("arguments", {}).get("path", "unknown")
            return f"The file '{target}' was not found. Use 'list_directory' to find the correct path and try again."
        
        if error_type == "tool_not_found":
            tool = last_action.get("tool_name", "unknown")
            return f"The tool or command '{tool}' is not currently available. I am initiating an 'refresh_environment_discovery' to update my environment data. Please try again after the scan."

        if error_type == "missing_argument":
            tool = last_action.get("tool_name", "unknown")
            return f"CRITICAL: Tool '{tool}' failed due to incorrect arguments. STOP guessing. Use 'get_tool_info' to see the exact schema before retrying. If the tool is fundamentally wrong for this task, switch to RAG search."

        if error_type == "json_parse_error":
            return "CRITICAL: Your last tool call was not valid JSON. Ensure all quotes, braces, and commas are correct. DO NOT include any text outside the JSON block. Close all open '{' and '[' blocks properly."

        if error_type == "security_rejection":
            return "🛡️ SECURITY ALERT: Your last command or path was rejected by the AXIS Firewall. DO NOT try to bypass the firewall with the same command. Instead, find a SAFER way to achieve the goal. (e.g., if 'python -c' was blocked, try writing a temporary .py file and then executing it)."

        if error_type == "git_pathspec_error":
            return "⚠️ GIT CONFIG ERROR: On Windows CMD/PowerShell, you MUST use double quotes \"...\" for git commit messages and file paths. Single quotes '...' cause 'pathspec' errors. Correct the quoting and retry."

        if error_type == "project_not_found":
            return "📁 WORKSPACE ERROR: The project was not found. 1) Use 'get_workspace_summary' to see tracked paths. 2) If the project is at a known path, call 'open_workspace' with the FULL ABSOLUTE PATH. 3) Check for typos (CafeAI vs Cafe AI)."

        if error_type == "sql_no_such_column":
            return "🗄️ SQL SCHEMA ERROR: You are guessing column or table names. STOP. Your next action MUST be to call 'get_db_schema' for the target database to verify the structure before retrying the query."

        if error_type == "unknown_anomaly" and "❌" in last_action.get("result", ""):
            return "🔧 TECHNICAL FAILURE: The command failed. Analyze the error output, correct the logic or syntax (check paths, quotes, or missing files), and retry immediately."

        return "Anomaly detected. Please review logs and manually intervene."
