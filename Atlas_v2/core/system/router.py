import re
from core.logger import logger
from core.vision_engine import vision_engine

class SemanticRouter:
    """
    Semantic Router (Phase 1): Fast regex-based classifier for instant command execution.
    Bypasses the main LLM for common unambiguous patterns to save time/tokens.
    """
    def __init__(self, axis_core):
        self.axis = axis_core
        # Pattern -> (Plugin_Folder, Tool_Name, Fixed_Arguments)
        # We use Plugin_Folder mainly for logging, the real call happens via brain.tool_map
        self.routes = {
            r"^(скріншот|screenshot|зроби скрін|екран)$": ("vision_eye", "take_screenshot", {}),
            r"^(статус|status|інфо|info|система|system)$": ("diagnostics", "get_system_status", {}),
            r"^(що вдома|як справи|звіт|home report)$": ("telegram_bridge", "send_home_report", {}),
            r"^(допомога|help|що ти вмієш)$": ("system", "list_available_commands", {}),
            # Additional routing for memory
            r"^(очисти історію|clear history)$": ("brain", "clear_history", {}),
            r"^(дерево|tree|структура папок)$": ("file_master", "axis_force_tree", {})
        }

    def route(self, user_input: str) -> str | None:
        """ Checks if input matches any fast-route patterns. Returns result or None."""
        clean_input = user_input.lower().strip()
        
        # Direct Action Mandate (v2.7.26/v2.7.27.2) for specific fast-track tree
        if any(word in clean_input for word in ["дерев", "структур", "схем", "tree"]) and "core" in clean_input:
            safe_dir = "core"
            
            if hasattr(self.axis, "brain") and hasattr(self.axis.brain, "tool_map"):
                tm = self.axis.brain.tool_map
                if "execute_command" in tm and "send_telegram_photo" in tm:
                    try:
                        import asyncio
                        import nest_asyncio
                        nest_asyncio.apply()
                        loop = asyncio.get_event_loop()

                        logger.info("system.router_direct_action", action="tree_dynamic", target=safe_dir)
                        tree_result = loop.run_until_complete(self.axis.execute_tool("execute_command", {"command": f"tree /f {safe_dir}"}))
                        
                        # Use Vision Engine Diagram Generator instead of raw screenshot
                        snap_path = vision_engine.draw_tree_diagram(tree_result, title=f"File Tree: {safe_dir}")
                        
                        tg_result = loop.run_until_complete(self.axis.execute_tool("send_telegram_photo", {
                            "filepath": snap_path,
                            "caption": f"🌳 Візуальна структура {safe_dir}:\n{tree_result[:100]}..."
                        }))
                        logger.info("system.telegram_status", result=tg_result)
                        
                        if "❌" in tg_result:
                            return f"❌ [AXIS FAST-TRACK]: Дерево згенеровано, але помилка Telegram: {tg_result}"
                        return f"✅ Fast-track execution complete. Дерево `{safe_dir}` відправлено в Telegram."
                    except Exception as e:
                        logger.error("system.router_direct_action_failed", error=str(e))
                        return f"❌ [AXIS FAST-TRACK Error]: {e}"
        
        for pattern, route_data in self.routes.items():
            plugin, tool_name, args = route_data
            if re.match(pattern, clean_input):
                logger.info("system.router_match", input=clean_input, tool=tool_name)
                
                # Special cases or tool calls?
                if tool_name == "list_available_commands":
                    return self._list_commands()
                
                if tool_name == "clear_history":
                    if hasattr(self.axis.brain, "history"):
                        self.axis.brain.history = [self.axis.brain.history[0]] # Keep system prompt
                        return "✅ Історія діалогу очищена."
                        
                if tool_name == "axis_force_tree":
                    if hasattr(self.axis.brain, "tool_map"):
                        try:
                            import asyncio
                            import nest_asyncio
                            nest_asyncio.apply()
                            loop = asyncio.get_event_loop()

                            tree_result = loop.run_until_complete(self.axis.execute_tool("get_file_tree", {"path": "."}))
                            logger.info("system.router", action="forced_tree")
                            
                            if "take_screenshot" in self.axis.brain.tool_map and "send_telegram_photo" in self.axis.brain.tool_map:
                                snap_path = loop.run_until_complete(self.axis.execute_tool("take_screenshot", {}))
                                loop.run_until_complete(self.axis.execute_tool("send_telegram_photo", {
                                    "image_path": snap_path,
                                    "caption": "🌳 Ось запитане дерево файлів (перейшов у швидкий режим)"
                                }))
                            return f"✅ [AXIS FAST-TRACK]: Дерево згенеровано (без участі LLM).\n\n{tree_result[:1000]}...\n[Усі дані відправлено в Telegram]"
                        except Exception as e:
                            logger.error("system.router_tree_failed", error=str(e))
                            return f"❌ [AXIS FAST-TRACK Error]: {e}"
                
                # Dynamic Tool Call from Brain Map (v2.8.9 Unified MCP)
                if hasattr(self.axis.brain, "tool_map") and tool_name in self.axis.brain.tool_map:
                    try:
                        import asyncio
                        import nest_asyncio
                        nest_asyncio.apply()
                        loop = asyncio.get_event_loop()
                        
                        # Use orchestrator's unified execution logic
                        return loop.run_until_complete(self.axis.execute_tool(tool_name, args))
                    except Exception as e:
                        logger.error("system.router_execution_failed", tool=tool_name, error=str(e))
                        return None # Fallback to LLM if execution failed
                        
        return None

    def _list_commands(self) -> str:
        """Fast help response."""
        help_text = "🚀 **AXIS Fast Commands:**\n"
        help_text += "- `screenshot` / `скріншот`: Зробити знімок екрана.\n"
        help_text += "- `status` / `статус`: Стан системи (CPU/RAM).\n"
        help_text += "- `звіт`: Повний звіт у Telegram.\n"
        help_text += "- `clear history`: Очистити пам'ять поточної сесії.\n\n"
        help_text += "Всі інші запити обробляються основним інтелектом (Ollama/Gemini)."
        return help_text
