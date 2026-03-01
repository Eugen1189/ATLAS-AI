import pyaudio
p = pyaudio.PyAudio()
print("Available Audio Devices:")
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if info.get('maxInputChannels') > 0: # Only show input devices
        print(f"ID {i}: {info.get('name')} (Channels: {info.get('maxInputChannels')})")
p.terminate()
