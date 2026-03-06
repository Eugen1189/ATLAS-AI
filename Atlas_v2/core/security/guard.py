import re
from pathlib import Path
from core.logger import logger

class SecurityGuard:
    """Centralized validation for commands, code, and paths to enforce system safety."""
    
    DANGEROUS_PATTERNS = [
        r"rm\s+-rf\s+/",            # Root deletion
        r"format\s+[A-Z]:",         # Disk formatting
        r"del\s+/s\s+/q\s+C:",      # Windows mass deletion
        r"powershell\s+.*-ExecutionPolicy\s+Bypass", # Policy bypass
        r"mkfs\..*",                 # Filesystem creation
        r"> /dev/sd[a-z]",          # Direct disk write
        r":\(\){ :\|:& };:",        # Fork bomb
    ]

    RESTRICTED_PATHS = [
        "c:\\windows",
        "c:/windows",
        "/etc/",
        "/bin/",
        "/sbin/",
        "/usr/bin/",
        "/usr/sbin/"
    ]

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
            
        p_original_slashes = path_str.replace("\\", "/").lower()
        p = str(Path(path_str).resolve()).replace("\\", "/").lower()
        
        for restricted in SecurityGuard.RESTRICTED_PATHS:
            if restricted in p or restricted in p_original_slashes:
                logger.warning("security.restricted_path", path=path_str)
                return False
        
        # If check_core flag is enabled, we prevent direct rewrites of core system files
        if check_core:
            # Basic check against overriding core files (except if appropriately sandboxed)
            if "core/" in p and "/ui/" not in p:
                logger.warning("security.core_override_blocked", path=path_str)
                return False

        return True
