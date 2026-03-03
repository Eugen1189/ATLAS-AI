import os
import sys

# Додаємо корінь проекту до sys.path
root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_path not in sys.path:
    sys.path.append(root_path)

from Atlas_v2.agent_skills.telegram_bridge.manifest import ask_user_confirmation
from Atlas_v2.agent_skills.telegram_bridge.listener import start_telegram_listener

# Mock Atlas Core for test
class MockCore:
    def think(self, prompt):
        return f"Відповідь на: {prompt}"

atlas_core = MockCore()
start_telegram_listener(atlas_core)

print("Відправляю тестовий запит на підтвердження...")
result = ask_user_confirmation("Я готовий запустити тестовий скрипт. Підтвердити?")
print(f"Результат тесту: {result}")
