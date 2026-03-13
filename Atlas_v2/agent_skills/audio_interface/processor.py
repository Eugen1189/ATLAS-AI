import os
import time
import subprocess
import re
from core.logger import logger


def convert_to_wav(file_path: str) -> str:
    """Converts various formats (ogg, mp3, mp4) to .wav using ffmpeg (v2.9.6)."""
    if file_path.lower().endswith(".wav"):
        return file_path
        
    wav_path = os.path.splitext(file_path)[0] + "_converted.wav"
    try:
        # -y to overwrite, -ac 1 for mono (standard for STT)
        subprocess.run(["ffmpeg", "-y", "-i", file_path, "-ac", "1", wav_path], 
                       check=True, capture_output=True, timeout=15)
        return wav_path
    except Exception as e:
        logger.error(f"audio.ffmpeg_conversion_failed: {e}")
        return ""

def transcribe_audio(audio_source, language: str = "uk-UA") -> str:
    """
    Universal Transcriber: Handles sr.AudioData, local file paths, and Telegram voices.
    """
    import speech_recognition as sr
    recognizer = sr.Recognizer()

    try:
        if isinstance(audio_source, str):
            # Handle directory paths or file paths
            if not os.path.exists(audio_source):
                return ""
                
            # Convert if not wav
            wav_path = convert_to_wav(audio_source)
            if not wav_path: return ""
            
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
                
            # Cleanup temp wav if it was converted
            if wav_path != audio_source:
                try: os.remove(wav_path)
                except: pass
        else:
            # Assume it's sr.AudioData from Microphone
            audio_data = audio_source
            
        # Standard: Recognize via Google (v2.9.6)
        text = recognizer.recognize_google(audio_data, language=language)
        return text or ""
    except Exception:
        return ""

def clean_text_for_speech(text: str) -> str:
    """Removes Markdown and technical symbols for clear speech (v2.9.7)."""
    # 1. Remove markdown code blocks
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # 2. Remove URLs
    text = re.sub(r'http\S+', '', text)
    # 3. Remove technical JSON/Dict symbols
    text = re.sub(r'[{}#"\'\[\]:;]', ' ', text)
    # 4. Remove common technical markers
    text = re.sub(r'\b(json|tool_name|arguments|tool_call)\b', '', text, flags=re.IGNORECASE)
    # 5. Remove markdown formatting chars
    text = re.sub(r'[*_#`~>|-]', ' ', text)
    # 6. Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def speak(text: str, speed_factor: float = 1.0, voice_idx: int = None) -> str:
    """
    Offline TTS Engine: Used for immediate feedback and autonomous responses.
    """
    clean_text = clean_text_for_speech(text)
    if not clean_text: return "Empty text."
    import pyttsx3

    try:
        engine = pyttsx3.init()

        # Rate settings
        base_rate = 170
        engine.setProperty('rate', int(base_rate * speed_factor))
        
        # Voice selection
        voices = engine.getProperty('voices')
        if voice_idx is not None and 0 <= int(voice_idx) < len(voices):
            engine.setProperty('voice', voices[int(voice_idx)].id)
        else:
            uk_keywords = ["ukrainian", "uk-ua", "olena", "anatol", "ирина", "ukr"]
            for v in voices:
                if any(k in v.name.lower() or k in v.id.lower() for k in uk_keywords):
                    engine.setProperty('voice', v.id)
                    break
        
        engine.say(clean_text)
        engine.runAndWait()
        engine.stop()
        return f"Spoke: {clean_text}"
    except Exception as e:
        logger.error(f"audio.tts_error: {e}")
        return f"Error: {e}"

def generate_voice_file(text: str, output_path: str = None) -> str:
    """
    Generates an .ogg voice file for Telegram using Offline TTS + FFmpeg.
    """
    import tempfile
    clean_text = clean_text_for_speech(text)
    if not clean_text: return ""

    # 1. Create temporary wav
    temp_wav = os.path.join(tempfile.gettempdir(), f"voice_{int(time.time())}.wav")
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), f"voice_{int(time.time())}.ogg")

    try:
        import pyttsx3
        engine = pyttsx3.init()

        engine.setProperty('rate', 170)
        
        # SAPI5 on Windows saves to wav format
        engine.save_to_file(clean_text, temp_wav)
        engine.runAndWait()
        
        # 2. Convert wav to ogg (opus) for Telegram compatibility (v2.9.7)
        # We try libopus first, then fallback to libvorbis
        try:
            subprocess.run(["ffmpeg", "-y", "-i", temp_wav, "-c:a", "libopus", "-b:a", "16k", output_path], 
                           check=True, capture_output=True)
        except subprocess.CalledProcessError:
            # Fallback to libvorbis if libopus is missing
            subprocess.run(["ffmpeg", "-y", "-i", temp_wav, "-c:a", "libvorbis", output_path], 
                           check=True, capture_output=True)
        
        # Cleanup
        if os.path.exists(temp_wav): os.remove(temp_wav)
        return output_path
    except Exception as e:
        logger.error(f"audio.generate_voice_failed: {e}")
        if os.path.exists(temp_wav): os.remove(temp_wav)
        return ""
