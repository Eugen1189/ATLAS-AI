import os
import sys

# Add project root to sys.path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

# Add Atlas_v2 dir itself so agent_skills imports resolve correctly
axis_root = os.path.abspath(os.path.dirname(__file__))
if axis_root not in sys.path:
    sys.path.append(axis_root)

from agent_skills.telegram_bridge.manifest import ask_user_confirmation
from agent_skills.telegram_bridge.listener import start_telegram_listener

# Mock AXIS Core for test
class MockCore:
    def think(self, prompt: str) -> str:
        return f"Response to: {prompt}"

axis_core = MockCore()
start_telegram_listener(axis_core)

print("Sending test confirmation request...")
result = ask_user_confirmation("I am ready to run the test script. Confirm?")
print(f"Test result: {result}")
