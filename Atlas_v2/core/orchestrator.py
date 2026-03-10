import os
import importlib
import sys
from pathlib import Path
from dotenv import load_dotenv
from core.i18n import lang
from core.logger import logger

# 1. Get the absolute path to the folder where this script resides (AXIS_v2/core)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Go up two levels (AXIS_v2/core -> AXIS_v2 -> project root) to find .env
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))

# 3. Load keys using absolute path
load_dotenv(dotenv_path=env_path)

from core.brain import BrainFactory

class AxisCore:
    """Main logic for the AXIS agent orchestrator."""
    def __init__(self):
        logger.info("system.booting", version="2.7.21")
        
        # 1. First Pass: Discovery (Zero-Config)
        primary_workspace = None
        try:
            from core.system.discovery import EnvironmentDiscoverer
            discoverer = EnvironmentDiscoverer()
            findings = discoverer.run_full_discovery(store_in_memory=False)
            primary_workspace = findings.get("primary_workspace")
            
            # Security: Apply Scoped Trust
            from core.security.guard import SecurityGuard
            if primary_workspace:
                SecurityGuard.set_workspace(primary_workspace)
            else:
                SecurityGuard.set_workspace(os.getcwd())
        except Exception as e:
            logger.warning("system.discovery_failed", error=str(e))

        # 2. Memory Context: Set Namespace
        namespace = "default"
        if primary_workspace:
            # Use folder name as namespace, or a hash if we want more precision
            namespace = os.path.basename(primary_workspace).lower()

        # Update global memory_manager namespace before brain init
        from core.brain.memory import memory_manager
        memory_manager.switch_namespace(namespace)

        # 3. Load skills
        self.available_tools = self._load_skills()
        
        # 4. Initialize the brain
        self.brain = BrainFactory.create_brain()
        
        try:
            success = self.brain.initialize(self.available_tools)
            if not success:
                logger.error("system.brain_init_failed", reason="Missing API Key or config")
                raise ValueError(lang.get("system.missing_gemini_key", path=env_path))
        except Exception as e:
            logger.critical("system.core_fatal_error", error=str(e))
            raise

        logger.info("system.core_init_success", count=len(self.available_tools), namespace=namespace)

    def _load_skills(self):
        """Scans the agent_skills folder and loads EXPORTED_TOOLS from each skill's manifest.py."""
        tools = []
        skills_dir = Path(__file__).parent.parent / "agent_skills"
        
        # Add AXIS_v2 to sys.path for correct imports
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        if not skills_dir.exists():
            logger.warning("system.skills_dir_missing", path=str(skills_dir))
            return tools

        for skill_folder in skills_dir.iterdir():
            if skill_folder.is_dir() and (skill_folder / "manifest.py").exists():
                try:
                    module_path = f"agent_skills.{skill_folder.name}.manifest"
                    # Reset importlib cache to ensure fresh load if needed
                    if module_path in sys.modules:
                        importlib.reload(sys.modules[module_path])
                    
                    module = importlib.import_module(module_path)
                    
                    if hasattr(module, "EXPORTED_TOOLS"):
                        tools.extend(module.EXPORTED_TOOLS)
                        logger.info("system.skill_loaded", name=skill_folder.name)
                except ImportError as e:
                    logger.error("system.skill_dependency_missing", name=skill_folder.name, error=str(e))
                    # Graceful degradation: skip this skill but keep AXIS running
                except Exception as e:
                    logger.error("system.skill_load_error", name=skill_folder.name, error=str(e))
        
        return tools

    def think(self, user_input: str, source: str = "terminal") -> str:
        """
        Process user input. Applies Firewall checks before delegating to Brain.
        source: 'terminal' | 'telegram:<chat_id>' | 'api'
        """
        from core.security.firewall import axis_firewall, SecurityViolation

        # --- Layer 1: Rate Limiter ---
        if not axis_firewall.is_request_allowed(source=source):
            logger.warning("system.rate_limited", source=source)
            return f"⛔ Rate limit exceeded. Maximum {axis_firewall.max_requests} requests per {axis_firewall.window_sec}s. Please wait before sending another command."

        # --- Layer 2: Prompt Injection + Payload Validator ---
        try:
            user_input = axis_firewall.sanitize_input(user_input, source=source)
        except SecurityViolation as e:
            logger.warning("system.security_violation", source=source, error=str(e))
            return f"🛡️ Security violation: {e}"

        logger.debug("system.user_input", content=user_input)
        response = self.brain.think(user_input)
        logger.debug("system.agent_response", content=response)
        return response
