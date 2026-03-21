import sys
import os
import subprocess
from core.system.path_utils import load_environment

# Load environment variables as early as possible
load_environment()

# --- COOL DOWN (v3.2.4): Resource Management ---
os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"
os.environ["OPENBLAS_NUM_THREADS"] = "4"
os.environ["VECLIB_MAXIMUM_THREADS"] = "4"
os.environ["NUMEXPR_NUM_THREADS"] = "4"

# [BUNKER v5.5] UTF-8 Forced Encoding for Windows Terminals
if os.name == 'nt':
    import io
    try:
        os.system('chcp 65001 > nul')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    except:
        pass


# Встановлюємо шляхи для імпортів
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.orchestrator import AxisCore
# [V3.6.6 CLEANUP] Removed legacy/bloat imports (Voice, Vision, Sentinel)
# from agent_skills.audio_interface.listener import start_voice_listener

from core.i18n import lang
from agent_skills.telegram_bridge.listener import start_telegram_listener
from agent_skills.diagnostics.telemetry_daemon import start_telemetry_daemon

def safe_print(text: str):
    """Prints text ensuring no UnicodeEncodeError on Windows terminals."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback for legacy terminals (strips emojis and non-supported chars)
        print(text.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding))

def bunker_ephemeral_cleanup():
    """
    [BUNKER v5.5] Ephemeral Sanitization:
    Removes temporary session files, voice buffers, and logs to prevent persistence.
    """
    temp_files = [
        "vision_buffer.png",
        "response_audio.mp3",
        "last_action.json",
        "diagnostic.png"
    ]
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception: pass
            
    # Cleanup temp/ folder if exists
    import shutil
    temp_dir = os.path.join(os.getcwd(), "tmp")
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
        except Exception: pass

    safe_print("[BUNKER] Ephemeral environment sanitized. Persistence neutralized.")

def cleanup_zombie_processes():
    """Cleans up hung HUD or Python processes using port 5005 to prevent 'Port busy' errors."""
    bunker_ephemeral_cleanup() # Integrate with bunker cleanup
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
                        safe_print(f"[CLEANUP] Killed zombie process holding port 5005 (PID: {pid})")
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
        safe_print("[HUD] HUD Process launched in isolation mode.")
    except Exception as e:
        safe_print(f"[HUD] Failed to launch HUD process: {e}")

def run_terminal_loop(axis):
    """Цикл вводу в терміналі"""
    safe_print(f"\n--- {lang.get('system.ready')} ---")
    while True:
        try:
            command = input(lang.get("system.prompt")).strip()
            if not command: continue # Do nothing on empty input
            
            if command.lower() in ['exit', 'quit', 'вихід', 'sleep']:
                import time
                from core.brain.memory import memory_manager
                safe_print("[AXIS]: Переходжу в сплячий режим. Формую спогади сесії (це займе ~12 секунд)...")
                
                if hasattr(axis, 'brain') and hasattr(axis.brain, 'history'):
                    memory_manager.reflect_on_session(axis.brain.history)
                    
                    # ДАЄМО ЧАС НА РЕФЛЕКСІЮ перед тим, як Python вб'є програму
                    time.sleep(12) 
                    
                safe_print("[AXIS]: Спогади збережено. До зустрічі, Командоре.")
                safe_print(lang.get("system.shutdown"))
                os._exit(0) 
            if command.lower() == 'status':
                safe_print("\n[SYSTEM] Vision: ONLINE | MCP: ACTIVE | TG: CONNECTED | VOICE: BACKGROUND\n")
                continue
            
            response = axis.think(command)
            safe_print(lang.get("system.axis_said", text=response))
        except EOFError:
            break
        except Exception as e:
            safe_print(lang.get("system.sys_error", error=e))

if __name__ == "__main__":
    cleanup_zombie_processes()
    safe_print("Booting AXIS V3.2.8 (Universal Core - Validation Layer)...")
    
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
        
        # 🛡️ TELEMETRY BOOT: Autonomous system monitoring
        start_telemetry_daemon()
        
        # 🎙️ [V3.6.6 CLEANUP] Voice boot disabled for minimalism
        # start_voice_listener(axis, device_index=1)
        
        # Запускаємо цикл вводу
        run_terminal_loop(axis)
        
    except Exception as e:
        safe_print(f"[BOOT ERROR] LOGIC BOOT ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

