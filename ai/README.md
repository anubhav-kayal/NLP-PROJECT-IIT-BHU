# Python Microphone Input

This folder contains starter code for capturing and processing audio input from a microphone using Python.

## Features

- Real-time microphone audio capture
- Audio recording with configurable duration
- Audio level monitoring (dB)
- Save recordings to WAV files
- List available audio devices
- Easy-to-extend class structure

## Requirements

- Python 3.6 or higher
- PyAudio library
- NumPy library

## Installation

### Windows

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   If PyAudio installation fails, download the appropriate wheel file:
   - Visit: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
   - Download the .whl file matching your Python version and system
   - Install with: `pip install PyAudio‑0.2.11‑cp39‑cp39‑win_amd64.whl`

### macOS

1. **Install PortAudio (PyAudio dependency):**
   ```bash
   brew install portaudio
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Linux (Ubuntu/Debian)

1. **Install PortAudio:**
   ```bash
   sudo apt-get update
   sudo apt-get install portaudio19-dev python3-pyaudio
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the starter script:
```bash
python microphone_input.py
```

The script will:
1. List all available audio input devices
2. Record a 5-second audio clip
3. Save the recording to a WAV file
4. Monitor audio levels for 5 seconds

### Using in Your Own Code

```python
from microphone_input import MicrophoneRecorder

# Create recorder
recorder = MicrophoneRecorder(sample_rate=44100, channels=1)

# Start recording
recorder.start_stream()
recorder.record_audio(duration_seconds=10)
recorder.save_recording("my_recording.wav")

# Clean up
recorder.cleanup()
```

### Real-time Audio Level Monitoring

```python
recorder = MicrophoneRecorder()
recorder.start_stream()

# Monitor for 10 seconds
import time
for i in range(100):
    level = recorder.get_audio_level()
    print(f"Audio Level: {level:.1f} dB")
    time.sleep(0.1)

recorder.cleanup()
```

## Configuration Options

The `MicrophoneRecorder` class accepts these parameters:

- `sample_rate`: Audio sampling rate in Hz (default: 44100)
- `channels`: Number of channels - 1 for mono, 2 for stereo (default: 1)
- `chunk_size`: Number of frames per buffer (default: 1024)
- `audio_format`: PyAudio format (default: pyaudio.paInt16)

## Troubleshooting

**"No Default Input Device Available":**
- Check that a microphone is connected and enabled
- On Windows: Check Sound settings → Input devices
- On macOS: System Preferences → Sound → Input
- On Linux: Check `alsamixer` or PulseAudio settings

**Import Error for PyAudio:**
- Make sure PyAudio is installed correctly
- On Windows, use the precompiled wheel file
- On macOS/Linux, ensure PortAudio is installed first

**Permission Denied:**
- On macOS: Grant microphone access in System Preferences → Security & Privacy → Privacy → Microphone
- On Linux: Add your user to the `audio` group: `sudo usermod -a -G audio $USER`

## Extending the Code

Here are some ideas for extending this starter code:

### 1. Speech Recognition
```python
import speech_recognition as sr

recognizer = sr.Recognizer()
with sr.Microphone() as source:
    print("Speak now...")
    audio = recognizer.listen(source)
    text = recognizer.recognize_google(audio)
    print(f"You said: {text}")
```

### 2. Frequency Analysis
```python
from scipy.fft import fft, fftfreq
import matplotlib.pyplot as plt

# After recording
audio_data = np.frombuffer(b''.join(recorder.frames), dtype=np.int16)
frequencies = fftfreq(len(audio_data), 1/recorder.sample_rate)
fft_values = np.abs(fft(audio_data))

plt.plot(frequencies[:len(frequencies)//2], fft_values[:len(fft_values)//2])
plt.xlabel('Frequency (Hz)')
plt.ylabel('Magnitude')
plt.show()
```

### 3. Audio Visualization
```python
import matplotlib.pyplot as plt
import matplotlib.animation as animation

fig, ax = plt.subplots()
x = np.arange(0, 2 * chunk_size, 2)
line, = ax.plot(x, np.random.rand(chunk_size))

def animate(i):
    data = stream.read(chunk_size)
    audio_data = np.frombuffer(data, dtype=np.int16)
    line.set_ydata(audio_data)
    return line,

ani = animation.FuncAnimation(fig, animate, blit=True)
plt.show()
```

## Resources

- [PyAudio Documentation](https://people.csail.mit.edu/hubert/pyaudio/docs/)
- [NumPy Documentation](https://numpy.org/doc/)
- [Python Audio Processing Tutorial](https://realpython.com/playing-and-recording-sound-python/)
- [Speech Recognition Library](https://pypi.org/project/SpeechRecognition/)

## License

This starter code is provided as-is for educational purposes.
