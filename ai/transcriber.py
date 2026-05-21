import ssl
import sys
import warnings
import whisper

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

warnings.filterwarnings("ignore")


class LocalTranscriber:
    def __init__(self, model_size="small"):
        print(f"Loading Whisper model ({model_size})...")
        self.model = whisper.load_model(model_size)
        print("Model loaded.")

    def transcribe(self, audio_file_path):
        try:
            prompt = (
                "Smart home voice command. Indian English accent. "
                "Examples: turn on the lights, set a timer for ten minutes, "
                "play music in the bedroom, what is the weather today, "
                "turn off the fan, add milk to my shopping list."
            )
            result = self.model.transcribe(
                audio_file_path,
                fp16=False,
                language="en",
                initial_prompt=prompt
            )
            return result["text"].strip()
        except Exception as e:
            print(f"Transcription error: {e}")
            return ""


if __name__ == "__main__":
    import os

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' not found.")
            sys.exit(1)
        t = LocalTranscriber()
        text = t.transcribe(filename)
        print(text)
    else:
        print("Usage: python3 transcriber.py <filename.wav>")