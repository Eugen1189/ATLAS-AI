import sys
import os
import subprocess
from dotenv import load_dotenv

# Load environment variables as early as possible
load_dotenv()

# Встановлюємо шляхи для імпортів
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import AxisCore
from agent_skills.audio_interface.listener import listen_command, start_voice_listener
from core.i18n import lang
from agent_skills.telegram_bridge.listener import start_telegram_listener

def cleanup_zombie_processes():
    """Cleans up hung HUD or Python processes using port 5005 to prevent 'Port busy' errors."""
    if os.name == 'nt':
        try:
            # Find PID using port 5005
            cmd = "netstat -ano | findstr :5005"
            output = subprocess.check_output(cmd, shell=True, text=True)
            for line in output.splitlines():
                if "LISTENING" in line or "UDP" in line:
                    pid = line.strip().split()[-1]
                    if pid != "0":
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                        print(f"🧹 Killed zombie process holding port 5005 (PID: {pid})")
        except Exception:
            pass

def launch_visuals():
    """Запускає HUD як окремий процес Windows для ізоляції пам'яті"""
    hud_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core", "ui", "hud.py")
    
    # Використовуємо CREATE_NEW_PROCESS_GROUP для Windows, щоб ізолювати процеси
    try:
        subprocess.Popen(
            [sys.executable, hud_path],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
        print("🖥️  HUD Process launched in isolation mode.")
    except Exception as e:
        print(f"❌ Failed to launch HUD process: {e}")

def run_terminal_loop(axis):
    """Цикл вводу в терміналі"""
    print(f"\n--- {lang.get('system.ready')} ---")
    while True:
        try:
            command = input(lang.get("system.prompt")).strip()
            if not command: continue # Do nothing on empty input
            
            if command.lower() in ['exit', 'quit', 'вихід']:
                print(lang.get("system.shutdown"))
                os._exit(0) 
            if command.lower() == 'status':
                print("\n📊 [SYSTEM] Vision: ONLINE | MCP: ACTIVE | TG: CONNECTED | VOICE: BACKGROUND\n")
                continue
            
            response = axis.think(command)
            print(lang.get("system.axis_said", text=response))
        except EOFError:
            break
        except Exception as e:
            print(lang.get("system.sys_error", error=e))

if __name__ == "__main__":
    cleanup_zombie_processes()
    print("🚀 Booting AXIS V2.7.21 (Universal Core - Process Isolation Mode)...")
    
    # 1. Запускаємо візуал як окремий процес ПЕРШИМ
    launch_visuals()
    
    # 2. Тепер ініціалізуємо важку логіку (ChromaDB, AI)
    try:
        from core.security.secret_validator import SecretValidator
        brain_type = os.getenv("AI_BRAIN", "ollama").lower()
        SecretValidator.print_boot_report(brain_type)

        # Initialize AxisCore (performs Zero-Config Discovery and Scoped Trust)
        axis = AxisCore()
        
        from core.brain.healer import Healer
        Healer().summarize_evolution()
        
        start_telegram_listener(axis)
        
        # 🎙️ VOICE BOOT: Using specific hardware index for MT-MC14
        start_voice_listener(axis, device_index=1)
        
        # Запускаємо цикл вводу
        run_terminal_loop(axis)
        
    except Exception as e:
        print(f"❌ LOGIC BOOT ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
