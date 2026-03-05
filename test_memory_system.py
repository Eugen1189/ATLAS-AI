import sys
import os

# Add project path
sys.path.insert(0, os.path.abspath("Atlas_v2"))
from core.brain.memory import memory_manager

print("Testing AXIS Memory System...")
memory_manager.store_fact("test_key", "Memory integration is successful!")
print("Fact stored.")

context = memory_manager.get_context_for_prompt()
print("Context for prompt:")
print(context)

facts_path = os.path.abspath(os.path.join("memories", "facts.json"))
if os.path.exists(facts_path):
    print(f"File created at: {facts_path}")
    with open(facts_path, "r", encoding="utf-8") as f:
        print("File content:")
        print(f.read())
else:
    print("Error: facts.json not found!")
