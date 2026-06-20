import pyaudio
import numpy as np
import wave
import sys
import threading
import time
from datetime import datetime
from typing import Optional, Callable

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


class MicrophoneRecorder:
    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS,
                 chunk_size=CHUNK, audio_format=FORMAT, use_callback=False):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.recording = False
        self._callback_fn = None
        self.use_callback = use_callback

    def list_audio_devices(self):
        print("\nAvailable Audio Devices:")
        print("=" * 50)
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            if info.get('maxInputChannels') > 0:
                print(f"Device {i}: {info.get('name')}")
                print(f"  - Max Input Channels: {info.get('maxInputChannels')}")
                print(f"  - Default Sample Rate: {info.get('defaultSampleRate')}")
        print("=" * 50)

    def _pyaudio_callback(self, in_data, frame_count, time_info, status):
        if self.recording:
            self.frames.append(in_data)
            if self._callback_fn:
                self._callback_fn(in_data)
        return (in_data, pyaudio.paContinue)

    def start_stream(self, callback: Optional[Callable] = None):
        try:
            self._callback_fn = callback
            if self.use_callback:
                self.stream = self.audio.open(
                    format=self.audio_format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self._pyaudio_callback,
                )
            else:
                self.stream = self.audio.open(
                    format=self.audio_format,
                    channels=self.channels,
                    rate=self.sample_rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                )
            print(f"\nMicrophone stream started ({self.sample_rate}Hz, {self.channels}ch)")
            return True
        except Exception as e:
            print(f"Error starting stream: {e}")
            return False

    def stop_stream(self):
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except OSError:
                pass
            print("Microphone stream stopped")

    def record_audio(self, duration_seconds=5):
        if not self.stream:
            print("Error: Stream not started.")
            return False
        print(f"\nRecording for {duration_seconds} seconds...")
        self.frames = []
        self.recording = True
        num_chunks = int(self.sample_rate / self.chunk_size * duration_seconds)
        try:
            buffer_underruns = 0
            for i in range(num_chunks):
                try:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    self.frames.append(data)
                except OSError:
                    buffer_underruns += 1
                    data = b'\x00' * (self.chunk_size * 2)
                    self.frames.append(data)
                if (i + 1) % 10 == 0:
                    progress = (i + 1) / num_chunks * 100
                    print(f"Progress: {progress:.1f}%", end='\r')
            if buffer_underruns:
                print(f"\n({buffer_underruns} buffer underruns handled)")
            print("\nRecording complete!")
            return True
        except Exception as e:
            print(f"\nError during recording: {e}")
            return False
        finally:
            self.recording = False

    def save_recording(self, filename=None):
        if not self.frames:
            print("Error: No audio data to save.")
            return None
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))
            print(f"Saved: {filename}")
            return filename
        except Exception as e:
            print(f"Error saving file: {e}")
            return None

    def get_audio_level(self):
        if not self.stream:
            return 0
        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_data ** 2))
            if rms > 0:
                return 20 * np.log10(rms)
            return -np.inf
        except Exception:
            return 0

    def cleanup(self):
        self.stop_stream()
        self.audio.terminate()
        print("Resources cleaned up")


class SoundDeviceRecorder:
    def __init__(self, sample_rate=SAMPLE_RATE, channels=CHANNELS,
                 blocksize=CHUNK, latency='low'):
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        self.latency = latency
        self.sd = None
        self._available = False
        self._try_import()

    def _try_import(self):
        try:
            import sounddevice as sd
            self.sd = sd
            self._available = True
        except ImportError:
            pass

    def is_available(self):
        return self._available

    def list_devices(self):
        if not self._available:
            print("sounddevice not installed. pip install sounddevice")
            return
        print(self.sd.query_devices())

    def record_stream(self, callback: Callable[[np.ndarray], None]):
        if not self._available:
            raise RuntimeError("sounddevice not installed. pip install sounddevice")

        def _callback(in_data, frames, time_info, status):
            if status:
                print(f"sounddevice status: {status}")
            callback(in_data[:, 0] if in_data.shape[1] > 1 else in_data.flatten())

        with self.sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.blocksize,
            latency=self.latency,
            callback=_callback,
            dtype='int16',
        ):
            while True:
                time.sleep(0.1)

    def record_chunk(self, duration_seconds=5) -> Optional[np.ndarray]:
        if not self._available:
            return None
        try:
            recording = self.sd.rec(
                int(duration_seconds * self.sample_rate),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
            )
            self.sd.wait()
            if self.channels > 1:
                recording = recording.mean(axis=1, keepdims=True)
            return recording.flatten()
        except Exception as e:
            print(f"sounddevice record error: {e}")
            return None


if __name__ == "__main__":
    print("=" * 50)
    print("Python Microphone Input")
    print("=" * 50)
    recorder = MicrophoneRecorder()
    recorder.list_audio_devices()
    if recorder.start_stream():
        try:
            recorder.record_audio(duration_seconds=5)
            recorder.save_recording()
            print("\nMonitoring audio levels...")
            for i in range(50):
                level = recorder.get_audio_level()
                if level > -np.inf:
                    bar_length = int((level + 60) / 2)
                    bar = "█" * max(0, bar_length)
                    print(f"Audio Level: {level:6.1f} dB |{bar}", end='\r')
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            recorder.cleanup()
