import pytest
from core.security.guard import SecurityGuard

def test_is_safe_command():
    assert SecurityGuard.is_safe_command("echo hello") == True
    assert SecurityGuard.is_safe_command("ls -la") == True
    
    # Dangerous commands
    assert SecurityGuard.is_safe_command("rm -rf /") == False
    assert SecurityGuard.is_safe_command("format C:") == False
    assert SecurityGuard.is_safe_command("del /s /q C:") == False
    assert SecurityGuard.is_safe_command("powershell -ExecutionPolicy Bypass") == False
    
def test_is_safe_path():
    assert SecurityGuard.is_safe_path("c:\\Projects\\Atlas", check_core=False) == True
    assert SecurityGuard.is_safe_path("c:\\Projects\\Atlas", check_core=True) == True
    
    # Empty path is considered safe (or handled correctly by the check)
    assert SecurityGuard.is_safe_path("", check_core=True) == True
    
    # Restricted directories
    assert SecurityGuard.is_safe_path("c:\\windows\\system32", check_core=False) == False
    assert SecurityGuard.is_safe_path("/etc/passwd", check_core=False) == False
    assert SecurityGuard.is_safe_path("/bin/bash", check_core=False) == False
    
    # Core check
    assert SecurityGuard.is_safe_path("c:\\Projects\\Atlas\\core\\utils.py", check_core=True) == False
    # UI in core is allowed (if your regex handles it correctly)
    assert SecurityGuard.is_safe_path("c:\\Projects\\Atlas\\core\\ui\\hud.py", check_core=True) == True
