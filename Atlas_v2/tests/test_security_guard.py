import pytest
import os
from core.security.guard import SecurityGuard

def test_is_safe_command():
    assert SecurityGuard.is_safe_command("echo hello") == True
    assert SecurityGuard.is_safe_command("ls -la") == True
    
    # Dangerous commands
    assert SecurityGuard.is_safe_command("rm -rf /") == False
    assert SecurityGuard.is_safe_command("format C:") == False
    
    # New aggressive checks
    assert SecurityGuard.is_safe_command("del /s /q test.txt") == False
    assert SecurityGuard.is_safe_command("rd /s /q folder") == False
    assert SecurityGuard.is_safe_command("del c:\\windows\\system32\\file.dll") == False
    
    assert SecurityGuard.is_safe_command("powershell -ExecutionPolicy Bypass") == False

def test_is_safe_path():
    # Setup workspace root for testing
    root = os.getcwd().replace("\\", "/").lower()
    SecurityGuard.set_workspace(root)

    safe, msg = SecurityGuard.validate_path(root, check_core=False)
    assert safe == True
    
    safe, msg = SecurityGuard.validate_path(root, check_core=True)
    assert safe == True
    
    # Restricted system directories
    safe, msg = SecurityGuard.validate_path("c:\\windows\\system32", check_core=False)
    assert safe == False
    assert "protected system directory" in msg
    
    # Blacklist check
    safe, msg = SecurityGuard.validate_path(".env", check_core=False)
    assert safe == False
    assert "blacklisted pattern" in msg
    
    # Core check (Inside Workspace) - Should be True (Safe for Developers)
    safe, msg = SecurityGuard.validate_path(f"{root}/core/utils.py", check_core=True)
    assert safe == True
