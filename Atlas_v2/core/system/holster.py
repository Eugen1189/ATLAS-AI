from core.logger import logger

class ToolHolster:
    """Smart Tool Holster (v3.2.0): Context-aware filtering that GUARANTEES File tools are present."""
    
    # Always injected — the bare minimum needed to not go blind
    ESSENTIALS = [
        "list_directory",    # Must ALWAYS be present — agent needs to see where it is
        "read_file",         # Must ALWAYS be present — Disk Truth Rule
        "search_memory",     # RAG anchor
        "get_tool_info",     # Self-awareness tool
        "get_workspace_summary",
        "hot_reload_skills",
    ]

    @staticmethod
    def select_tools(user_input: str, all_tools: list) -> list:
        intent_map = {
            "Files": [
                "write_file", "read_file", "delete_file", "list_directory",
                "make_directory", "apply_ast_patch", "search_files",
                "refactor_code", "find_code_usages", "refresh_code_index"
            ],
            "Media": [
                "send_telegram_photo", "send_telegram_message"
            ],
            "System": [
                "execute_command", "run_batch_script", "analyze_performance",
                "deep_system_scan", "repair_environment", "refresh_environment_discovery"
            ],
            "Audit": [
                "find_dead_code", "find_code_duplicates", "audit_dependencies",
                "analyze_architecture", "analyze_impact", "run_qa_tests"
            ],
            "Memory": ["save_to_memory", "forget_topic", "get_memory_stats"],
            "Web": ["google_research", "perplexity_search", "fetch_website_content"],
            "Data": ["query_database", "get_db_schema"]
        }

        # Broad keyword detection (Ukrainian + English)
        category_keywords = {
            "Files": [
                # Discovery & Traversal
                "файл", "папка", "директор", "обхід", "проскануй", "зазирни",
                "перевір", "покажи", "структур", "список", "вміст", "читай",
                "проект", "відкрий", "знайди", "код", "скрипт", "налаштуван",
                "file", "folder", "directory", "scan", "list", "read", "write",
                "content", "structure", "show", "check", "find", "explore",
                "traverse", "walk", "tree", "patch", "ast", "refactor"
            ],
            "Media": [
                "скрін", "screenshot", "фото", "зображення", "камера", "telegram",
                "відправ", "photo", "image", "send"
            ],
            "System": [
                "термінал", "виконати", "команда", "діагностика", "залізо", "cpu", "ram", "скіл", "система", "статус",
                "пам'ять системи", "лог", "помилка", "cmd", "shell", "run", "execute", 
                "performance", "hardware", "system", "error", "log", "status", "skill"
            ],
            "Audit": [
                "аудит", "дублікат", "тест", "якість", "стандарт", "dead code",
                "audit", "duplicate", "test", "quality", "standard", "vulture", "pylint", 
                "deptry", "pydeps", "architecture", "impact", "qa", "pytest"
            ],
            "Memory": [
                "запам'ятай", "факти", "ваша пам'ять", "пам'ять", "архів", "перемішу",
                "memory", "remember", "history", "recall", "knowledge"
            ],
            "Web": [
                "знайди в інтернеті", "пошук", "google", "research", "web", "search"
            ],
            "Data": ["sql", "database", "база даних", "sqlite", "query", "таблиця"]
        }

        user_input_lower = user_input.lower()
        active_names = set(ToolHolster.ESSENTIALS)
        matched_categories = []

        for cat, keywords in category_keywords.items():
            if any(kw in user_input_lower for kw in keywords):
                matched_categories.append(cat)
                active_names.update(intent_map.get(cat, []))

        # If NO categories matched at all — activate Files as a safe default
        if not matched_categories:
            matched_categories = ["Files"]
            active_names.update(intent_map["Files"])

        # Build result lists
        essentials = [t for t in all_tools if getattr(t, '__name__', str(t)) in ToolHolster.ESSENTIALS]
        matched   = [t for t in all_tools if getattr(t, '__name__', str(t)) in active_names
                     and t not in essentials]

        # Raised limit to 15 — 7b handles this fine, reduces blind-spots
        filtered_tool_objs = (essentials + matched)[:15]

        logger.info("holster.filtered_v3", categories=matched_categories, count=len(filtered_tool_objs))
        return filtered_tool_objs
