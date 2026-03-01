import os
import time
import struct
import wave
import threading
import queue
import logging
import audioop # For resampling
from pathlib import Path
from datetime import datetime

# Root for config
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# Third-party libraries
try:
    import pvporcupine
    import pyaudio
    from openai import OpenAI
    import numpy as np
    HAS_DEPS = True
except ImportError as e:
    print(f"❌ [VOICE] Missing dependencies: {e}")
    HAS_DEPS = False

class VoiceControl:
    """
    Cloud-Hybrid Voice Activation Module for ATLAS.
    Stage 1: 'Wake Word' (PvPorcupine) - Local, ultra-fast.
    Stage 2: 'OpenAI Whisper Cloud' - High accuracy transcription without Torch/DLLs.
    """

    def __init__(self, 
                 access_key=None, 
                 command_callback=None, 
                 status_callback=None,
                 wake_word_path=None,
                 sensitivity=0.5):
        
        self.access_key = access_key or os.getenv("PICOVOICE_ACCESS_KEY")
        self.command_callback = command_callback
        self.status_callback = status_callback
        self.wake_word_path = wake_word_path
        self.sensitivity = sensitivity
        
        self.is_running = False
        self.thread = None
        
        # Audio Configuration
        self.chunk_size = 512
        self.format = 8 # pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        
        self.porcupine = None
        self.pa = None
        self.audio_stream = None
        self.openai_client = None
        
        # Silence Detection
        self.silence_threshold = 600
        self.silence_duration = 1.2
        self.calibrated = False
        
        # Initialize OpenAI Client
        if config.OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
        
        print("🎙️ [VOICE] VoiceControl (Cloud-Whisper) Initialized")

    def _initialize_resources(self):
        """Initializes Porcupine and Audio stream."""
        if not HAS_DEPS: return False
        if not self.access_key:
            print("⚠️ [VOICE] No Picovoice Access Key provided.")
            return False
            
        try:
            # 1. Initialize Porcupine (Local Wake Word)
            kw_args = {}
            if self.wake_word_path:
                 kw_args["keyword_paths"] = [self.wake_word_path]
            else:
                 kw_args["keywords"] = ["jarvis"] # Use internal 'jarvis' keyword
            
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                sensitivities=[self.sensitivity] * len(kw_args.get("keywords", [""])),
                **kw_args
            )
            
            self.chunk_size = self.porcupine.frame_length
            self.pa = pyaudio.PyAudio()
            
            # Microphone search
            working_index = None
            device_count = self.pa.get_device_count()
            search_order = [1, 15, 0] + [i for i in range(device_count) if i not in [1, 15, 0]]
            
            for i in search_order:
                try:
                    if i >= device_count: continue
                    info = self.pa.get_device_info_by_index(i)
                    if info.get('maxInputChannels', 0) < 1: continue
                    
                    self.pa.open(rate=16000, channels=1, format=pyaudio.paInt16, input=True, input_device_index=i).close()
                    working_index = i
                    break
                except: continue
            
            if working_index is None:
                raise Exception("No working microphone found.")

            self.audio_stream = self.pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.chunk_size,
                input_device_index=working_index
            )
            
            print("✅ [VOICE] Porcupine & Audio Stream ready.")
            return True
            
        except Exception as e:
            print(f"❌ [VOICE] Initialization failed: {e}")
            return False

    def start(self):
        if self.is_running: return
        if not self._initialize_resources(): return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        # Calibration
        threading.Thread(target=self._calibrate_noise, daemon=True).start()
        print("👂 [VOICE] Listening for 'Jarvis' (Cloud-Whisper Mode)...")

    def _calibrate_noise(self):
        if not self.audio_stream: return
        try:
            frames = [self.audio_stream.read(self.chunk_size) for _ in range(10)]
            rms_values = []
            for f in frames:
                ints = struct.unpack('h' * (len(f) // 2), f)
                rms_values.append((sum(i**2 for i in ints) / len(ints)) ** 0.5)
            self.silence_threshold = max(600, int(sum(rms_values)/len(rms_values) + 300))
            self.calibrated = True
            print(f"✅ [VOICE] Threshold Set: {self.silence_threshold}")
        except: pass

    def stop(self):
        self.is_running = False
        if self.audio_stream: self.audio_stream.close()
        if self.pa: self.pa.terminate()
        if self.porcupine: self.porcupine.delete()

    def _run_loop(self):
        while self.is_running:
            try:
                pcm_bytes = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
                pcm = struct.unpack_from("h" * self.porcupine.frame_length, pcm_bytes)
                if self.porcupine.process(pcm) >= 0:
                    print("⚡ [VOICE] Wake Word Detected!")
                    self._on_wake()
            except Exception as e:
                time.sleep(1)

    def _on_wake(self):
        if self.status_callback: self.status_callback("listening")
        audio_data = self._record_variable_length()
        
        if audio_data:
             if self.status_callback: self.status_callback("thinking")
             text = self._transcribe_cloud(audio_data)
             if text:
                 print(f"📝 [VOICE] Cloud Transcribed: '{text}'")
                 if self.command_callback: self.command_callback(text)
        
        if self.status_callback: self.status_callback("idle")

    def _record_variable_length(self):
        frames = []
        silent_chunks = 0
        silence_thresh_chunks = int(self.silence_duration * 16000 / self.chunk_size)
        start_time = time.time()
        has_started_talking = False
        
        while (time.time() - start_time) < 10:
             data = self.audio_stream.read(self.chunk_size, exception_on_overflow=False)
             frames.append(data)
             ints = struct.unpack('h' * (len(data) // 2), data)
             rms = (sum(i**2 for i in ints) / len(ints)) ** 0.5 if ints else 0
             
             if rms < self.silence_threshold:
                 silent_chunks += 1
                 if not has_started_talking and (time.time() - start_time) > 3.0: return None
             else:
                 silent_chunks = 0
                 has_started_talking = True
             
             if has_started_talking and silent_chunks > silence_thresh_chunks: break
        
        return b''.join(frames) if frames else None

    def _transcribe_cloud(self, audio_data):
        """Transcribes via OpenAI Whisper API."""
        if not self.openai_client:
            print("❌ [VOICE] OpenAI client not initialized.")
            return None
            
        temp_wav = f"temp_cmd_{int(time.time())}.wav"
        with wave.open(temp_wav, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(audio_data)
            
        try:
            with open(temp_wav, "rb") as audio_file:
                transcript = self.openai_client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file,
                    language="uk"
                )
            return transcript.text.strip()
        except Exception as e:
            print(f"❌ [VOICE] Cloud Transcription Error: {e}")
            return None
        finally:
            if os.path.exists(temp_wav): os.remove(temp_wav)

if __name__ == "__main__":
    vc = VoiceControl(command_callback=print)
    vc.start()
    time.sleep(30)
