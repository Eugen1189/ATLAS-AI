import os
import sys

# Add project root to sys.path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

from Atlas_v2.agent_skills.telegram_bridge.manifest import ask_user_confirmation
from Atlas_v2.agent_skills.telegram_bridge.listener import start_telegram_listener

# Mock Atlas Core for test
class MockCore:
    def think(self, prompt):
        return f"Response to: {prompt}"

atlas_core = MockCore()
start_telegram_listener(atlas_core)

print("Sending test confirmation request...")
result = ask_user_confirmation("I am ready to run the test script. Confirm?")
print(f"Test result: {result}")
