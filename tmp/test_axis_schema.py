import sys
import os
from pathlib import Path

# Setup paths to the actual Atlas_v2 directory
atlas_v2_dir = r"C:\Projects\Atlas\Atlas_v2"
# Crucially, add the PARENT of the core/agent_skills directory so imports work
if atlas_v2_dir not in sys.path:
    sys.path.insert(0, atlas_v2_dir)

os.chdir(atlas_v2_dir)

from core.system.path_utils import load_environment
load_environment()

from core.orchestrator import AxisCore

# Initialize core
axis = AxisCore()

query = "Покажи мені схему бази даних C:/Projects/LegalMind/legal_mind.db за допомогою query_database та виведи її сюди"
print(f"--- RUNNING AXIS QUERY TEST ---")
print(f"Query: {query}")

response = axis.think(query)
print("\n--- AXIS FINAL RESPONSE ---")
print(response)
print("\n--- TEST COMPLETE ---")
