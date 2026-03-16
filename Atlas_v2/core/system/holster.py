from core.logger import logger

class ToolHolster:
    """Агресивна кобура для інструментів (v3.1.5): Обмежує вибір до 10 релевантних скілів."""
    
    ESSENTIALS = ["speak", "search_memory", "get_tool_info", "get_workspace_summary", "capture_screen_snapshot"]

    @staticmethod
    def select_tools(user_input: str, all_tools: list) -> list:
        intent_map = {
            "Files": ["write_file", "read_file", "delete_file", "make_directory"],
            "Media": ["capture_screen_snapshot", "send_telegram_photo", "analyze_screen"],
            "System": ["execute_command", "run_batch_script", "os_control"],
            "Memory": ["save_to_memory", "forget_topic", "find_code_usages"],
            "Web": ["google_research", "perplexity_search", "fetch_website_content"],
            "Data": ["query_database", "get_db_schema"]
        }

        active_tools = set(ToolHolster.ESSENTIALS)
        user_input_lower = user_input.lower()

        # Шукаємо збіги за ключовими іменами інструментів
        category_keywords = {
            "Files": ["file", "драфт", "файл", "папка", "write", "read"],
            "Media": ["post", "instagram", "скрін", "screenshot", "фото", "зображення"],
            "System": ["cmd", "термінал", "виконати", "run", "setup"],
            "Memory": ["згадай", "факти", "історія", "history", "legacy", "архів"],
            "Web": ["знайди", "інтернет", "search", "google", "research"],
            "Data": ["sql", "database", "база", "даних", "sqlite", "query", "таблиця"]
        }

        matched_categories = []
        for cat, keywords in category_keywords.items():
            if any(word in user_input_lower for word in keywords):
                matched_categories.append(cat)
                # Додаємо конкретні інструменти цієї категорії
                active_tools.update(intent_map.get(cat, []))

        # 3. Пріоритезація та фільтрація (LIMIT 10)
        essentials = [t for t in all_tools if getattr(t, '__name__', str(t)) in ToolHolster.ESSENTIALS]
        matched = [t for t in all_tools if getattr(t, '__name__', str(t)) in active_tools and t not in essentials]
        
        filtered_tool_objs = (essentials + matched)[:10]

        # --- "THE ANCHOR" (v3.2.2): Guaranteed Fallback ---
        if len(filtered_tool_objs) < 5:
            anchors = ["list_directory", "read_file", "search_memory"]
            anchor_objs = [t for t in all_tools if getattr(t, '__name__', str(t)) in anchors 
                           and t not in filtered_tool_objs]
            filtered_tool_objs.extend(anchor_objs)
            # Re-sort to keep essentials first if needed, but extend is fine for safety
            filtered_tool_objs = filtered_tool_objs[:10]

        logger.info("holster.filtered_v3", categories=matched_categories, count=len(filtered_tool_objs))
        return filtered_tool_objs
