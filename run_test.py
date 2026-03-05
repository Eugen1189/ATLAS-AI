import sys
import os

if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

sys.path.insert(0, os.path.abspath("Atlas_v2"))
from core.orchestrator import AxisCore

axis = AxisCore()
query = "Create a new skill called 'Weather' that just returns 'Sunny, 25°C' and make sure it follows all project rules."
print(f"User > {query}")
print("--- Axis Thinking ---")
response = axis.think(query)
print("--- Final Response ---")
print(response)
