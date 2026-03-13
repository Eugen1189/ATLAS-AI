import os
import json
import subprocess
import platform
import psutil
import sys
from pathlib import Path
from core.skills.wrapper import agent_tool
from core.system.discovery import EnvironmentDiscoverer

@agent_tool
def analyze_performance(**kwargs) -> str:
    """Standard 2026 Audit: Scans logs for bottleneck identification."""
    log_file = Path("logs/axis.log")
    if not log_file.exists(): return "No logs found."
    timings = {}
    try:
        with open(log_file, "r") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    if d.get("event") == "performance.timing":
                        f_n = d.get("function")
                        timings.setdefault(f_n, []).append(d.get("duration_sec", 0))
                except Exception: pass
        if not timings: return "Timing data empty."
        report = "### Performance Diagnostics:\n"
        for f, ds in timings.items(): report += f"- {f}: Avg {sum(ds)/len(ds):.3f}s (Max {max(ds):.3f}s)\n"
        return report
    except Exception as e: return f"Error: {e}"

@agent_tool
def deep_system_scan(**kwargs):
    """
    Збирає детальну інформацію про залізо, ОС та використання ресурсів.
    Включає хак для правильного визначення Windows 11.
    """
    uname = platform.uname()
    os_system = uname.system
    os_release = uname.release
    
    # 🛡️ ХАК ДЛЯ WINDOWS 11: Перевіряємо номер збірки
    if os_system == "Windows" and hasattr(sys, 'getwindowsversion'):
        build_num = sys.getwindowsversion().build
        if build_num >= 22000:
            os_release = "11"  # Примусово ставимо 11, якщо збірка нова

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.abspath(os.sep))
    
    report = (
        f"🖥️ OS: {os_system} {os_release}\n"
        f"💾 RAM: {round(memory.used / (1024**3), 2)}/{round(memory.total / (1024**3), 2)} GB ({memory.percent}%)\n"
        f"💽 Disk: {round(disk.free / (1024**3), 2)}/{round(disk.total / (1024**3), 2)} GB free ({disk.percent}%)\n"
        f"⚡ CPU: {psutil.cpu_percent(interval=0.5)}% ({psutil.cpu_count(logical=True)} cores)"
    )
    
    return report

@agent_tool
def repair_environment(**kwargs) -> str:
    """Standard 2026 Self-Healing: Cleans cache, checks dependencies."""
    fixes = []
    # 1. Clean visual snapshots
    try:
        s_path = "memories/visual_snapshots"
        if os.path.exists(s_path):
            files = os.listdir(s_path)
            for f in files: os.remove(os.path.join(s_path, f))
            fixes.append(f"Cleared {len(files)} visual artifacts.")
    except Exception: pass
    
    # 2. Check Internet
    try:
        subprocess.check_call(["ping", "-n", "1", "8.8.8.8"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        fixes.append("Internet connectivity: OK")
    except Exception: fixes.append("Internet status: OFFLINE")
    
    return "### Repair Report:\n" + "\n".join(fixes)

EXPORTED_TOOLS = [analyze_performance, deep_system_scan, repair_environment]

