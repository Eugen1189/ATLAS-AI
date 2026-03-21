import os
import psutil
import signal
import time

def kill_hardcore():
    print("AXIS HARD TERMINATE: Commencing...")
    current_pid = os.getpid()
    
    # 1. Kill MCP Hub processes
    # 2. Kill Python main.py
    # 3. Kill HUD
    # 4. Kill Node.js MCP servers
    
    targets = ['main.py', 'hud.py', 'mcp_hub', 'telegram_bridge', 'rag_maintenance']
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            if pid == current_pid: continue
            
            name = (proc.info['name'] or "").lower()
            cmdline = proc.info['cmdline'] or []
            cmdline_str = " ".join(cmdline).lower()
            
            is_target = any(t.lower() in cmdline_str for t in targets)
            is_common = any(pkg in cmdline_str for pkg in ['atlas', 'brain', 'core\\system'])
            
            if is_target or is_common or 'python' in name or 'node' in name:
                # Be a bit careful with global python
                if 'atlas' not in name and 'atlas' not in cmdline_str and 'venv' not in cmdline_str:
                    # If it's a generic python but not in atlas/venv, maybe skip?
                    # But the user said CLOSE ALL PROCESSES.
                    if 'atlas' not in cmdline_str and 'venv' not in cmdline_str:
                        continue 

                print(f"[-] Nuking process {pid} | {name} | {cmdline_str[:150]}")
                try:
                    p = psutil.Process(pid)
                    p.kill()
                except:
                    import subprocess
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True)
                    
        except: continue
    
    print("NUCLEAR SILENCE ACHIEVED.")

if __name__ == "__main__":
    kill_hardcore()
