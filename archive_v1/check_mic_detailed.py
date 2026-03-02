import pyaudio
import sys

p = pyaudio.PyAudio()

print(f"PyAudio version: {pyaudio.__version__}")
print(f"PortAudio version: {pyaudio.get_portaudio_version()}")

print("\n--- Scanning Input Devices ---")
info = p.get_host_api_info_by_index(0)
numdevices = info.get('deviceCount')

target_rate = 16000
target_channels = 1
target_format = pyaudio.paInt16
target_chunk = 512

found_working = False

for i in range(p.get_device_count()):
    dev_info = p.get_device_info_by_index(i)
    if dev_info.get('maxInputChannels') > 0:
        print(f"\nDevice ID {i}: {dev_info.get('name')}")
        print(f"  Max Input Channels: {dev_info.get('maxInputChannels')}")
        print(f"  Default Sample Rate: {dev_info.get('defaultSampleRate')}")
        
        # Try to open stream
        try:
            stream = p.open(
                rate=target_rate,
                channels=target_channels,
                format=target_format,
                input=True,
                frames_per_buffer=target_chunk,
                input_device_index=i
            )
            print(f"  ✅ SUCCESS: Opened at {target_rate}Hz, 1 channel, 512 buffer")
            stream.close()
            found_working = True
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            
            # Try 44100 as fallback check
            try:
                stream = p.open(
                    rate=44100,
                    channels=target_channels,
                    format=target_format,
                    input=True,
                    frames_per_buffer=target_chunk,
                    input_device_index=i
                )
                print(f"  ⚠️ Partiat Success: Opened at 44100Hz (HW incompatible with 16000Hz?)")
                stream.close()
            except Exception as e2:
                print(f"  ❌ 44.1k Check Failed: {e2}")

p.terminate()

if not found_working:
    print("\nSUMMARY: No device accepted the required settings (16kHz, Mono).")
else:
    print("\nSUMMARY: Found working devices.")
