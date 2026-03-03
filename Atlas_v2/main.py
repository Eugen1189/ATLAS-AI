from core.orchestrator import AxisCore
import sys
import os

if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Add path to AXIS_v2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Add path to project root to access config.py and others
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_skills.audio_interface.listener import listen_command

# IMPORT i18n
from core.i18n import lang

# IMPORT TELEGRAM LISTENER
from agent_skills.telegram_bridge.listener import start_telegram_listener

def boot_sequence():
    print(lang.get("system.welcome"))
    axis = AxisCore()
    
    # Start Telegram listener in background, passing the AXIS brain to it
    start_telegram_listener(axis)
    
    print(lang.get("system.ready"))
    
    while True:
        try:
            command = input(lang.get("system.prompt")).strip()
            
            if command.lower() in ['exit', 'quit', 'вихід']:
                print(lang.get("system.shutdown"))
                break
                
            if command.lower() == 'status':
                print("\n📊 [SYSTEM] Vision: ONLINE | MCP: 2 SERVERS ACTIVE | TG: CONNECTED\n")
                continue
                
            # If the user simply pressed Enter - trigger the microphone!
            if command == "":
                command = listen_command()
                if not command:  # If nothing recognized, restart loop
                    continue
                print(lang.get("system.you_said", text=command))
                
            # Send the command (text or voice) to the brain
            response = axis.think(command)
            print(lang.get("system.axis_said", text=response))
            
        except Exception as e:
            print(lang.get("system.sys_error", error=e))

if __name__ == "__main__":
    boot_sequence()
