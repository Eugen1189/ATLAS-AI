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
        r"del\s+/s",                # Recursive Windows deletion
        r"del\s+.*system32",        # Windows system folder deletion
        r"rd\s+/s",                 # Recursive directory deletion
        r"mkfs",                    # Filesystem creation
        r"dd\s+if=",                # Direct disk write
        r"shutdown",                # OS shutdown
        r"reboot",                  # OS reboot
        r"\.exe\b",                 # Untrusted executables (boundary check)
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

    # Sensitive project files blocked for reading/writing even within workspace
    BLACKLIST = [
        ".env",
        ".git/config",
        ".axis_session.json", # [v3.8.23] Block self-tampering
        "facts_atlas.json",
        "facts_default.json",
        "embeddings_",
        ".key",
        "shadow",
        "passwd",
        ".antigravityignore"
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
    def is_safe_path(path_str: str, check_core: bool = True) -> bool:
        """
        Backward-compatible boolean check for path safety.
        """
        safe, _ = SecurityGuard.validate_path(path_str, check_core)
        return safe

    @staticmethod
    def validate_path(path_str: str, check_core: bool = True) -> tuple[bool, str]:
        """
        Validates if a given path is safe to execute or modify.
        Returns (is_safe: bool, error_message: str).
        """
        if not path_str:
            return True, ""
            
        p = str(Path(path_str).resolve()).replace("\\", "/").lower()
        
        # 1. System-Critical Block: ALWAYS block these regardless of workspace
        for critical in SecurityGuard.CRITICAL_SYSTEM_PATHS:
            if critical in p:
                logger.warning("security.critical_path_blocked", path=path_str)
                return False, f"🚨 [SECURITY]: Path '{path_str}' targets protected system directory ({critical})."

        # 2. Blacklist Check: Block access to credentials and sensitive config
        for sensitive in SecurityGuard.BLACKLIST:
            if sensitive in p:
                logger.warning("security.blacklist_blocked", path=path_str, pattern=sensitive)
                return False, f"🚨 [SECURITY]: Access denied. Path '{path_str}' contains blacklisted pattern '{sensitive}' (BUNKER v5.5 Policy)."
        
        # 3. Core Protection (v3.8.23)
        if check_core:
            # Strictly forbid direct rewrites of core AXIS system files
            if "/core/" in p and not any(x in p for x in ["/ui/", "/config/", "/mascot/"]):
                logger.warning("security.core_override_blocked", path=path_str)
                return False, "🚨 [SECURITY]: Direct override of system core modules is strictly forbidden. Please use project-level skills or templates."

        return True, ""

        return True, ""
