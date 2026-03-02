import os
import google.generativeai as genai
from dotenv import load_dotenv
from pathlib import Path

# Завантаження ключів
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path)

api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("❌ No API Key found")
else:
    genai.configure(api_key=api_key)
    print("🔍 Available models:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f" - {m.name}")
    except Exception as e:
        print(f"❌ Error: {e}")
