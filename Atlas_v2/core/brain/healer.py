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
        },
        "mcp_invalid_params": {
            "patterns": [r"-32602", r"invalid params", r"invalid arguments for tool"],
            "suggestion": "check_mcp_docs_and_retry"
        },
        "regressive_research": {
            "patterns": [r"how to install", r"what is fastapi", r"install.*package", r"how to use.*library", r"how to handle .* error", r"python error .* fix"],
            "suggestion": "look_local_first_audit"
        },
        "placeholder_stubbing": {
            "patterns": [r"hello world", r"placeholder", r"todo", r"basic structure"],
            "suggestion": "zero_placeholder_violation"
        },
        "timeout_error": {
            "patterns": [r"timeout", r"timed out", r"deadline exceeded"],
            "suggestion": "increase_timeout_or_optimize"
        },
        "workspace_drift": {
            "patterns": [r"wrong projects", r"incorrect path", r"wrong workspace", r"not in the target project"],
            "suggestion": "switch_workspace_immediately"
        },
        "docker_daemon_missing": {
            "patterns": [r"failed to connect to the docker api", r"docker daemon is not running", r"error response from daemon"],
            "suggestion": "check_docker_service_and_report"
        },
        "language_mismatch": {
            "patterns": [r"invalid decimal literal", r"syntax error", r"cannot parse ast"],
            "suggestion": "do_not_use_python_tools_on_yaml"
        }
    }

    def __init__(self, rules_path="memories/dynamic_rules.json"):
        self.rules_path = rules_path

    def summarize_evolution(self):
        """Виводить список вивчених правил при старті системи."""
        if os.path.exists(self.rules_path):
            try:
                with open(self.rules_path, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                
                print("\n[AXIS EVOLUTION REPORT]")
                print("Learned Lessons (Dynamic Micro-Rules):")
                if not rules:
                    print("- No rules learned yet. System is in baseline state.")
                for i, rule in enumerate(rules, 1):
                    print(f"{i}. {rule}")
                print("-" * 30 + "\n")
            except Exception:
                print("[AXIS EVOLUTION]: Error loading dynamic rules.")
        else:
            print("[AXIS EVOLUTION]: Baseline state. No dynamic rules found.")

    @staticmethod
    def diagnose(error_message: str) -> str:
        """Визначає тип помилки за текстом"""
        err_lower = str(error_message).lower()
        for error_type, data in Healer.RECIPES.items():
            if any(re.search(p, err_lower) for p in data["patterns"]):
                return error_type
        return "unknown_anomaly"

    def propose_fix(self, error_type: str, last_action: dict) -> str:
        """Suggests a recovery strategy for the agent."""
        if error_type == "file_not_found":
            target = last_action.get("arguments", {}).get("path", last_action.get("target_file", "unknown"))
            return (
                f"### 🛑 PATH DISCOVERY ERROR: '{target}' not found.\n"
                "### 🔧 MANDATORY: Do NOT search the web. Do NOT guess subfolders.\n"
                "### 🔧 ACTION: Your NEXT action MUST be 'list_directory' on the current project root "
                "to see the actual structure (e.g., if there is a 'src/' folder)."
            )
        
        if error_type == "tool_not_found":
            tool = last_action.get("tool_name", "unknown")
            return f"🔧 TOOL ERROR: '{tool}' is missing. Initiating 'refresh_environment_discovery' to update environment data."

        if error_type == "missing_argument":
            return "❌ ARGUMENT ERROR: Incorrect arguments. Use 'get_tool_info' to see the exact schema before retrying."

        if error_type == "json_parse_error":
            return (
                "### 🛑 JSON CORRUPTION: Your input/output is not valid JSON.\n"
                "### 🔧 MANDATORY: Do NOT search the web. Use 'run_command' to write a Python script "
                "that reads the raw string and repairs it using regex or string splitting."
            )

        if error_type == "security_rejection":
            result = last_action.get("result", "Security block bypass attempt.")
            return f"🛡️ SECURITY BLOCK: {result} STOP. Do not retry the same path. Search within workspace."

        if error_type == "git_pathspec_error":
            return "⚠️ GIT ERROR: Use double quotes \"...\" for messages on Windows. Correct and retry."

        if error_type == "syntax_error":
             return (
                 "### 🛑 [PARSING ERROR]: Your patch failed (invalid syntax or file type).\n"
                 "### 🔧 RECOVERY: If the file is NOT a .py file (e.g., .md, .sql, .txt), "
                 "you MUST NOT use 'apply_ast_patch'. Switch to 'write_file' or 'append_to_file' immediately."
             )

        if error_type == "project_not_found":
            return "📁 WORKSPACE ERROR: Project not found. Use 'get_workspace_summary' or provide an absolute path."

        if error_type == "sql_no_such_column":
            return "🗄️ SQL SCHEMA ERROR: Guessing column names detected. Use 'get_db_schema' first."

        if error_type == "mcp_invalid_params":
            server = last_action.get("server", "target_server")
            tool = last_action.get("tool_name", "unknown")
            return f"🚨 MCP PARAMETER ERROR (-32602): Tool '{tool}' on '{server}' has invalid JSON arguments. Call 'list_mcp_capabilities' to verify schema."

        if error_type == "regressive_research":
            return "🧘 FOCUS LOSS: You are searching for general programming help or error handling. THIS IS FORBIDDEN. Your mission is LOCAL code. Use 'list_directory' to find files or 'read_file' to understand existing error handling in the project."

        if error_type == "placeholder_stubbing":
            return "🚫 ZERO-PLACEHOLDER VIOLATION: Stubbing (Hello World) is forbidden. Analyze src/ and implement a real solution."

        if error_type == "timeout_error":
            return "🕒 TIMEOUT: Operation too slow. Reduce depth or max_lines."

        if error_type == "unknown_anomaly" and "❌" in str(last_action.get("result", "")):
            return "🔧 TECHNICAL FAILURE: Command failed. Verify syntax and retry."

        return "Anomaly detected. Please review logs and manually intervene."
