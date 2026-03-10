import os
import re
import json
import inspect
import traceback
from typing import get_type_hints
from core.logger import logger, time_it
from core.brain.blueprints import BlueprintManager
from core.brain.memory import memory_manager
from core.security.guard import SecurityGuard
from core.system.discovery import EnvironmentDiscoverer
from .base import BaseBrain

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

def parse_llm_response(response_text: str) -> dict | None:
    """
    Агресивно витягує ПЕРШИЙ валідний або ремонтний JSON-об'єкт виклику інструменту.
    Підтримує автокорекцію незакритих фігурних дужок.
    """
    # 1. Пошук першої дужки {
    start_index = response_text.find('{')
    if start_index == -1: return None
    
    # Витягуємо текст починаючи з першої дужки
    candidate = response_text[start_index:]
    
    # 2. Спроба знайти валідний блок через регулярний вираз (найкращий варіант)
    pattern = r'\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}'
    match = re.search(pattern, candidate, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0), strict=False)
            if isinstance(data, dict) and "tool_name" in data:
                return data
        except: pass

    # 3. БРОНЕБІЙНИЙ ПАРСЕР (Ремонт)
    # Якщо попередній крок не спрацював, модель могла просто обірвати відповідь.
    # Рахуємо баланс дужок і доставляємо ті, яких не вистачає.
    content = candidate.strip()
    open_braces = content.count('{')
    close_braces = content.count('}')
    
    if open_braces > close_braces:
        content += '}' * (open_braces - close_braces)
        
    try:
        # Спроба розпарсити відремонтований JSON
        # Шукаємо останню закриваючу дужку для відсікання зайвого тексту після JSON
        last_brace = content.rfind('}')
        if last_brace != -1:
            repaired_json = content[:last_brace+1]
            data = json.loads(repaired_json, strict=False)
            if isinstance(data, dict) and "tool_name" in data:
                logger.info(f"Successfully repaired and extracted tool call: {data['tool_name']}")
                return data
    except Exception as e:
        logger.debug(f"JSON Repair failed: {e}")

    return None

class OllamaBrain(BaseBrain):
    """
    Brain implementation using local Ollama.
    (Phase 2: Local-First Core)
    """
    
    def __init__(self):
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.available_tools = []
        self.tool_map = {}
        self.system_prompt = ""
        self.history = []
        self.dynamic_rules_path = "memories/dynamic_rules.json"
        self.dynamic_rules = []
        if OLLAMA_AVAILABLE:
            self.client = ollama.Client(host=self.base_url)
        else:
            self.client = None

    def _load_dynamic_rules(self):
        try:
            if os.path.exists(self.dynamic_rules_path):
                with open(self.dynamic_rules_path, 'r', encoding='utf-8') as f:
                    self.dynamic_rules = json.load(f)
        except Exception:
            self.dynamic_rules = []

    def _add_dynamic_rule(self, rule: str):
        self.dynamic_rules.append(rule)
        os.makedirs(os.path.dirname(self.dynamic_rules_path), exist_ok=True)
        try:
            with open(self.dynamic_rules_path, 'w', encoding='utf-8') as f:
                json.dump(self.dynamic_rules, f, indent=4)
        except Exception:
            pass

    def _get_dynamic_context(self) -> str:
        """Dynamically identifies current system environment and project context."""
        cwd = os.path.abspath(os.getcwd())
        discovery_info = ""
        try:
            discoverer = EnvironmentDiscoverer()
            findings = discoverer.run_full_discovery(store_in_memory=False)
            
            ides = ", ".join(findings.get("ides", {}).keys()) or "None detected"
            tools = ", ".join(findings.get("tools", {}).keys()) or "Standard CLI"
            
            discovery_info = (
                f"### DETECTED ENVIRONMENT:\n"
                f"- **Working Directory**: `{cwd}`\n"
                f"- **Installed IDEs**: {ides}\n"
                f"- **Active Dev Tools**: {tools}\n"
                f"Note: This is a fresh, local environment. Never rely on past projects. "
                f"Always use `list_directory` to scan the filesystem before making assumptions.\n"
            )
        except Exception:
            discovery_info = f"### DETECTED ENVIRONMENT:\n- **Working Directory**: `{cwd}`\n"

        return discovery_info

    def _build_tool_manifest(self, tools: list) -> str:
        """Converts Python callables into a precise specification for the local model."""
        dynamic_context = self._get_dynamic_context()
        
        manifest = (
            "You are AXIS, a highly capable OS-agent and developer assistant.\n"
            f"{dynamic_context}\n\n"
            "### MISSION PROTOCOL (v2.7.8):\n"
            "1. **Task Focus**: Complete the USER's primary request BEFORE performing secondary analysis. If the user asks for a 'click', do not explore folders or read .env files.\n"
            "2. **Thought Phase**: Start with <thought>. First sentence MUST be: 'Моя головна мета зараз: [ціль користувача]'. Discuss ONLY steps needed for this goal.\n"
            "3. **Self-Exploration Block**: DO NOT read `.env`, `.git/` or your own core source files unless explicitly asked to debug them. This is a MAJOR security violation.\n"
            "4. **Truth Authority**: Tool results are the absolute truth. If a tool works, DO NOT say it failed. If a text is not found, DO NOT hallucinate its coordinates.\n"
            "5. **Format**: One JSON `<tool_call>` per reasoning step. If arguments are unknown, ask the user instead of guessing `null`.\n"
            "6. **Silence Rule**: IF YOU GENERATE A JSON TOOL CALL, DO NOT WRITE ANY OTHER TEXT. Just output the JSON and stop.\n"
            "7. **Environment**: Windows 11. Today: March 10, 2026. Relative path root is `c:\\Projects\\Atlas`.\n"
            "8. **КРИТИЧНЕ ПРАВИЛО**: ТИ НЕ МАЄШ ПРАВА ВИГАДУВАТИ ВИВІД КОМАНД! Використовуй тільки реальні дані з інструментів.\n"
            "9. **ПРОТОКОЛ ВИКОНАННЯ (EXECUTION ONLY)**:\n"
            "   - Якщо користувач просить виконати дію (зробити скріншот, знайти файл, надіслати звіт), ТИ НЕ МАЄШ ПРАВА ПОЯСНЮВАТИ, ЯК ЦЕ ЗРОБИТИ.\n"
            "   - ТИ МАЄШ НЕГАЙНО ВИКЛИКАТИ ВІДПОВІДНІ ІНСТРУМЕНТИ.\n"
            "   - Після отримання результату від інструменту, просто коротко відзвітуй: \"Готово, Командоре\".\n"
            "   - НІКОЛИ не пиши код на Python у відповідь, якщо тебе не просили написати код. ВИКОРИСТОВУЙ JSON ДЛЯ ДІЙ.\n\n"
            "### AVAILABLE TOOLS:\n"
        )
        
        for tool in tools:
            name = getattr(tool, '__name__', str(tool))
            self.tool_map[name] = tool
            
            doc = getattr(tool, '__doc__', '') or 'No description available.'
            try:
                sig = inspect.signature(tool)
                schema = {}
                for p_name, param in sig.parameters.items():
                    if p_name in ["kwargs", "args"]: continue
                    p_type = "any"
                    if param.annotation != inspect.Parameter.empty:
                        p_type = getattr(param.annotation, '__name__', str(param.annotation).replace('typing.', ''))
                    schema[p_name] = p_type
                
                # Format as clean readable block
                manifest += f"#### {name}\n"
                manifest += f"- **Purpose**: {doc.strip()}\n"
                manifest += f"- **JSON Schema**: `{{\"tool_name\": \"{name}\", \"arguments\": {json.dumps(schema)}}}`\n\n"
            except Exception:
                manifest += f"#### {name}\n- **Purpose**: {doc.strip()}\n- **Schema**: (Dynamic arguments)\n\n"
                
        return manifest

    def initialize(self, available_tools: list):
        if not OLLAMA_AVAILABLE:
            logger.error("ollama.missing", reason="ollama python package is not installed")
            return False

        self.bp_manager = BlueprintManager()
        self.bp_manager.load_blueprint(os.getenv("AXIS_BLUEPRINT", "default"))
        self.memory = memory_manager

        if self.memory.rag and self.memory.rag.is_available:
            self.memory.rag.ensure_indexed()

        self.available_tools = available_tools
        self.system_prompt = self._build_tool_manifest(available_tools)
        self.system_prompt += self.bp_manager.get_system_prompt_addon()
        self.system_prompt += self.memory.get_context_for_prompt()

        self._load_dynamic_rules()
        if self.dynamic_rules:
            self.system_prompt += "\n\n### ADAPTIVE MICRO-RULES (Learned from past errors):\n"
            for i, rule in enumerate(self.dynamic_rules, 1):
                self.system_prompt += f"{i}. {rule}\n"
        
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.tool_map["switch_personality_blueprint"] = self.switch_personality_blueprint
        
        logger.info("ollama.initialized", 
                    model=self.model_name, 
                    tools_count=len(self.tool_map),
                    blueprint=self.bp_manager.active_blueprint.get("name"))
        return True

    def switch_personality_blueprint(self, name: str) -> str:
        result = self.bp_manager.switch_blueprint(name)
        self.system_prompt = self._build_tool_manifest(self.available_tools)
        self.system_prompt += self.bp_manager.get_system_prompt_addon()
        self.system_prompt += self.memory.get_context_for_prompt()
        self.history[0] = {"role": "system", "content": self.system_prompt}
        return result

    def check_model_health(self) -> bool:
        if not self.client:
            logger.error("ollama.health_check_failed", reason="Ollama client is not initialized.")
            return False
            
        try:
            models_response = self.client.list()
            downloaded_models = [m.get("model", "") for m in models_response.get("models", [])]
            model_exists = any(self.model_name in m for m in downloaded_models)
            
            if model_exists:
                logger.info("ollama.model_ready", model=self.model_name, status="OK")
                return True
            else:
                logger.warning("ollama.model_missing", model=self.model_name)
                return False
        except Exception as e:
            logger.error("ollama.server_offline", error=str(e))
            return False

    def think(self, user_input: str) -> str:
        if not self.client:
            return "[OLLAMA OFFLINE]: Processing disabled due to missing 'ollama' package."

        if not self.tool_map:
            logger.error("brain.tool_blindness_detected")
            return "[AXIS FATAL ERROR]: Tool map is empty."

        rag_context = ""
        if self.memory.rag and self.memory.rag.is_available:
            rag_context = self.memory.rag.get_context_block(user_input, n_results=5)

        full_message = f"{rag_context}\n\nUser question: {user_input}" if rag_context else user_input
        self.history.append({"role": "user", "content": full_message})
        
        max_depth = 12
        depth = 0
        last_tool_sig = None
        
        while depth < max_depth:
            depth += 1
            try:
                response = self.client.chat(model=self.model_name, messages=self.history)
            except Exception as e:
                logger.error("ollama.api_error", error=str(e))
                return f"[AXIS Error] Failed to generate response: {e}"
                
            msg_content = response['message']['content']
            
            # --- Repeat Loop Protection ---
            current_sig = hash(msg_content)
            if current_sig == last_tool_sig:
                 return "🛑 [AXIS LOOP BREAKER]: You are stuck repeating the same tool call. Check parameters or explain the failure to the user."
            last_tool_sig = current_sig

            thought_match = re.search(r'<thought>(.*?)</thought>', msg_content, re.DOTALL)
            if thought_match:
                logger.info("ollama.streaming_thought", thought=thought_match.group(1).strip())
                
            self.history.append({"role": "assistant", "content": msg_content})
            
            # --- Ironclad Parser Interaction ---
            tool_call = parse_llm_response(msg_content)
            
            if tool_call:
                try:
                    tool_name = tool_call.get("tool_name")
                    args = tool_call.get("arguments", {})

                    if not tool_name:
                         raise ValueError("Missing 'tool_name' in extracted JSON.")

                    if tool_name not in self.tool_map:
                         raise NameError(f"Tool '{tool_name}' is not registered.")

                    # --- Security Check ---
                    # We sanitize target for path/command tools
                    target = str(args.get("filepath", args.get("path", args.get("command", ""))))
                    is_safe = SecurityGuard.is_safe_command(target) if "command" in args else SecurityGuard.is_safe_path(target, check_core=True)
                    
                    if not is_safe:
                        result = f"🚨 [SECURITY REJECTED]: Access forbidden."
                    else:
                        logger.info("ollama.executing_tool", tool=tool_name, args=args)
                        result = self.tool_map[tool_name](**args)
                        
                    self.history.append({"role": "user", "content": f"### Result of {tool_name}:\n{result}"})
                    continue

                except Exception as e:
                    error_msg = f"❌ [TOOL_ERROR]: {str(e)}"
                    logger.error("ollama.tool_failed", error=str(e))
                    self.history.append({"role": "user", "content": error_msg})
                    continue
            
            clean_response = re.sub(r'<thought>.*?</thought>', '', msg_content, flags=re.DOTALL).strip()
            # Emergency fallback for hallucinations after error
            if len(self.history) > 2:
                prev_user_msg = self.history[-2].get("content", "")
                if "### Result of" in str(prev_user_msg) and "❌ [TOOL_ERROR]" in str(prev_user_msg):
                    if len(clean_response) < 15 or "success" in clean_response.lower():
                         return "⚠️ [SYSTEM ALERT]: Attempt to ignore tool error detected. Explain the failure honestly."

            return clean_response if clean_response else msg_content
            
        return "[AXIS Error]: Exceeded maximum tool call depth."
