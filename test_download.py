
import os
import torch
import requests

MODEL_URL = "https://models.silero.ai/models/tts/ua/v3_ua.pt"
MODEL_PATH = "model/v3_ua.pt"

def download_model():
    if not os.path.exists("model"):
        os.makedirs("model")
    
    if os.path.exists(MODEL_PATH):
        print(f"Model already exists at {MODEL_PATH}")
        return

    print(f"Downloading model from {MODEL_URL}...")
    try:
        response = requests.get(MODEL_URL, stream=True)
        response.raise_for_status()
        with open(MODEL_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print("Download complete.")
    except Exception as e:
        print(f"Download failed: {e}")

def load_local_model():
    try:
        print(f"Loading model from {MODEL_PATH}...")
        model = torch.jit.load(MODEL_PATH)
        print("Model loaded successfully!")
        return model
    except Exception as e:
        print(f"Failed to load model: {e}")
        return None

if __name__ == "__main__":
    download_model()
    model = load_local_model()
    
    if model:
        print("Testing synthesis...")
        # Silero V3 models usually take just text, speaker, and sample_rate
        # But we need to check the forward signature.
        # Usually: model.apply_tts(text=..., speaker=..., sample_rate=...)
        # Wait, apply_tts is a method on the hub object wrapper usually?
        # No, the JIT model itself has apply_tts as a method I believe if loaded correctly?
        # Actually, for V3 models, it might be model(text, speaker, sample_rate).
        # But let's check.
        pass
