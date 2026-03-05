import sys
import os

if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

sys.path.insert(0, os.path.abspath("Atlas_v2"))
from core.brain import OllamaBrain

print("Starting Ollama Health Check...")
brain = OllamaBrain()
print(f"Checking model: {brain.model_name}")
is_healthy = brain.check_model_health()

print(f"Health check result: {is_healthy}")
