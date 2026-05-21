#!/usr/bin/env python3
"""
Python Microphone Input Starter Code

This script captures audio input from the system's microphone using PyAudio.
It provides a basic template for recording, processing, and analyzing audio data.

Requirements:
    - Python 3.6+
    - PyAudio
    - NumPy

Installation:
    pip install -r requirements.txt

Usage:
    python microphone_input.py
"""

import pyaudio
import numpy as np
import wave
import sys
from datetime import datetime


class MicrophoneRecorder:
    """
    A class to handle microphone input recording and processing.
    """
    
    def __init__(self, 
                 sample_rate=44100, 
                 channels=1, 
                 chunk_size=1024,
                 audio_format=pyaudio.paInt16):
        """
        Initialize the microphone recorder.
        
        Args:
            sample_rate (int): Audio sampling rate in Hz (default: 44100)
            channels (int): Number of audio channels (1=mono, 2=stereo)
            chunk_size (int): Number of frames per buffer
            audio_format: PyAudio format (default: 16-bit int)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.audio_format = audio_format
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        
    def list_audio_devices(self):
        """
        List all available audio input devices.
        """
        print("\nAvailable Audio Devices:")
        print("=" * 50)
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')
        
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"Device {i}: {device_info.get('name')}")
                print(f"  - Max Input Channels: {device_info.get('maxInputChannels')}")
                print(f"  - Default Sample Rate: {device_info.get('defaultSampleRate')}")
        print("=" * 50)
    
    def start_stream(self):
        """
        Start the audio input stream.
        """
        try:
            self.stream = self.audio.open(
                format=self.audio_format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            print(f"\n✓ Microphone stream started")
            print(f"  Sample Rate: {self.sample_rate} Hz")
            print(f"  Channels: {self.channels}")
            print(f"  Chunk Size: {self.chunk_size} frames")
            return True
        except Exception as e:
            print(f"✗ Error starting stream: {e}")
            return False
    
    def stop_stream(self):
        """
        Stop and close the audio input stream.
        """
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            print("\n✓ Microphone stream stopped")
    
    def record_audio(self, duration_seconds=5):
        """
        Record audio for a specified duration.
        
        Args:
            duration_seconds (int): Duration to record in seconds
        """
        if not self.stream:
            print("✗ Error: Stream not started. Call start_stream() first.")
            return
        
        print(f"\n🎤 Recording for {duration_seconds} seconds...")
        print("Speak into the microphone now!")
        
        self.frames = []
        num_chunks = int(self.sample_rate / self.chunk_size * duration_seconds)
        
        try:
            for i in range(num_chunks):
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
                
                # Show progress
                if (i + 1) % 10 == 0:
                    progress = (i + 1) / num_chunks * 100
                    print(f"Progress: {progress:.1f}%", end='\r')
            
            print(f"\n✓ Recording complete!")
            return True
        except Exception as e:
            print(f"\n✗ Error during recording: {e}")
            return False
    
    def save_recording(self, filename=None):
        """
        Save the recorded audio to a WAV file.
        
        Args:
            filename (str): Output filename (default: auto-generated timestamp)
        """
        if not self.frames:
            print("✗ Error: No audio data to save. Record audio first.")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}.wav"
        
        try:
            wf = wave.open(filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.audio_format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            print(f"✓ Recording saved to: {filename}")
            return filename
        except Exception as e:
            print(f"✗ Error saving file: {e}")
            return None
    
    def get_audio_level(self):
        """
        Get the current audio level (useful for real-time monitoring).
        
        Returns:
            float: Audio level in dB
        """
        if not self.stream:
            return 0
        
        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Calculate RMS (Root Mean Square)
            rms = np.sqrt(np.mean(audio_data**2))
            
            # Convert to dB
            if rms > 0:
                db = 20 * np.log10(rms)
            else:
                db = -np.inf
            
            return db
        except Exception as e:
            print(f"Error reading audio level: {e}")
            return 0
    
    def cleanup(self):
        """
        Clean up resources.
        """
        self.stop_stream()
        self.audio.terminate()
        print("✓ Resources cleaned up")


def main():
    """
    Main function demonstrating microphone input usage.
    """
    print("=" * 50)
    print("Python Microphone Input Starter Code")
    print("=" * 50)
    
    # Create recorder instance
    recorder = MicrophoneRecorder()
    
    # List available audio devices
    recorder.list_audio_devices()
    
    # Start the audio stream
    if not recorder.start_stream():
        print("Failed to start audio stream. Exiting.")
        recorder.cleanup()
        sys.exit(1)
    
    try:
        # Option 1: Record for a fixed duration
        print("\n[Option 1] Recording a 5-second audio clip...")
        recorder.record_audio(duration_seconds=5)
        recorder.save_recording()
        
        # Option 2: Real-time audio level monitoring
        print("\n[Option 2] Monitoring audio levels for 5 seconds...")
        print("(Speak into the microphone to see the levels change)")
        import time
        for i in range(50):
            level = recorder.get_audio_level()
            if level > -np.inf:
                bar_length = int((level + 60) / 2)  # Scale for display
                bar = "█" * max(0, bar_length)
                print(f"Audio Level: {level:6.1f} dB |{bar}", end='\r')
            time.sleep(0.1)
        print("\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠ Recording interrupted by user")
    
    finally:
        # Clean up
        recorder.cleanup()
        print("\nProgram ended successfully!")


if __name__ == "__main__":
    main()


"""
Additional Features You Can Add:
---------------------------------
1. Real-time audio visualization (use matplotlib)
2. Frequency analysis using FFT (Fast Fourier Transform)
3. Voice activity detection (VAD)
4. Audio streaming to file or network
5. Speech recognition using speech_recognition library
6. Audio filtering and noise reduction
7. Integration with machine learning models for audio classification
8. WebSocket server for streaming audio to web clients

Example Extensions:
------------------
# Speech Recognition:
import speech_recognition as sr
recognizer = sr.Recognizer()
with sr.Microphone() as source:
    audio = recognizer.listen(source)
    text = recognizer.recognize_google(audio)

# FFT for Frequency Analysis:
from scipy.fft import fft, fftfreq
frequencies = fftfreq(len(audio_data), 1/sample_rate)
fft_values = np.abs(fft(audio_data))
"""
