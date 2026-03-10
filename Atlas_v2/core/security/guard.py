import re
import os
from pathlib import Path
from core.logger import logger

class SecurityGuard:
    """
    Centralized validation for commands, code, and paths to enforce system safety.
    Implements 'Scoped Trust': fluid access to workspace, restricted to system.
    """
    
    # Track the current active workspace to allow 'Fluid' access
    workspace_root = os.getcwd().replace("\\", "/").lower()

    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",            # Root deletion
        r"format\s+",               # Disk formatting
        r"del\s+.*system32",        # Windows system deletion
        r"rd\s+/s",                 # Recursive dir deletion
        r"mkfs",                    # Filesystem creation
        r"dd\s+if=",                # Direct disk write
        r"shutdown",                # OS shutdown
        r"reboot",                  # OS reboot
        r"\.exe",                   # Untrusted executables
        r"powershell\s+.*-ExecutionPolicy\s+Bypass", # Policy bypass
        r"> /dev/sd[a-z]",          # Direct disk write
        r":\(\){ :\|:& };:",        # Fork bomb
    ]

    # These are ALWAYS critical and require authorization/blocking
    CRITICAL_SYSTEM_PATHS = [
        "c:/windows",
        "c:/program files",
        "/etc/",
        "/bin/",
        "/sbin/",
        "/usr/bin/",
        "/usr/sbin/",
        "/root"
    ]

    @classmethod
    def set_workspace(cls, path: str):
        """Updates the trusted workspace root."""
        if path:
            cls.workspace_root = str(Path(path).resolve()).replace("\\", "/").lower()
            logger.info("security.workspace_trusted", path=cls.workspace_root)

    @staticmethod
    def is_safe_command(command: str) -> bool:
        """Checks if a shell command contains known dangerous patterns."""
        for pattern in SecurityGuard.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                logger.warning("security.dangerous_command", command=command, pattern=pattern)
                return False
        return True

    @staticmethod
    def is_safe_path(path_str: str, check_core: bool = False) -> bool:
        """
        Validates if a given path is safe to execute or modify.
        Returns a boolean.
        """
        if not path_str:
            return True
            
        p = str(Path(path_str).resolve()).replace("\\", "/").lower()
        
        # 1. System-Critical Block: ALWAYS block these regardless of workspace
        for critical in SecurityGuard.CRITICAL_SYSTEM_PATHS:
            if critical in p:
                logger.warning("security.critical_path_blocked", path=path_str)
                return False
        
        # 2. Workspace-Fluid Check: If it's inside the workspace, it's generally trusted
        is_in_workspace = p.startswith(SecurityGuard.workspace_root)
        
        # 3. Core Protection (Optional Layer)
        if check_core:
            # We prevent direct rewrites of core AXIS system files even inside workspace
            # unless they are explicitly marked as user-modifiable (like blueprints/configs)
            if "/core/" in p and "/ui/" not in p and "/config/" not in p:
                # If we are in the workspace, we might be the developer themselves!
                # Но для безпеки ми все одно попереджаємо, якщо це не UI або config
                if is_in_workspace:
                    logger.debug("security.core_access_in_workspace", path=path_str)
                else:
                    logger.warning("security.core_override_blocked", path=path_str)
                    return False

        return True
