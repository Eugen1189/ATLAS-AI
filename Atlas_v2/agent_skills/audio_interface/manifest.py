import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from core.i18n import lang

# Dynamically find the path to .env (just like in the Core)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=env_path)

def speak(text: str) -> str:
    """
    Speaks out text via computer speakers (OpenAI TTS).
    Use this tool when the user asks you to "say", "speak" something or 
    when you want to notify the user of something important audibly.
    WARNING: Do not pass long texts or code here, only short, natural conversational phrases.
    
    Args:
        text: Text to speak aloud (preferably up to 2-3 sentences).
    """
    print(lang.get("audio.generating")) # Close enough to 'Speaking:'
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return lang.get("audio.env_error")
        
    try:
        client = OpenAI(api_key=api_key)
        
        # Create folder for audio memory
        output_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "memories", "audio"))
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f"speech_{int(time.time())}.mp3")
        
        # Generate audio (Voice 'onyx' - Jarvis style)
        response = client.audio.speech.create(
            model="tts-1",
            voice="onyx",
            input=text,
            speed=0.9
        )
        response.stream_to_file(file_path)
        
        # Play audio in the background
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Wait until the file is done playing
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
                
            pygame.mixer.quit()
        except ImportError:
            # Fallback if pygame is not installed
            os.system(f'start /min "" "{file_path}"')
            
        return "Text voiced successfully."
        
    except Exception as e:
        return lang.get("audio.play_error", error=e)

# Export tool
EXPORTED_TOOLS = [speak]