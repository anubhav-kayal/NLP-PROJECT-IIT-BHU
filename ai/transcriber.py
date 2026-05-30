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
        """Returns transcript text only. For internal/simple use."""
        result = self._run(audio_file_path)
        return result["text"].strip() if result else ""

    def transcribe_with_timestamps(self, audio_file_path):
        """
        Returns (text, word_timestamps).
        word_timestamps is a list of dicts:
            {"word": "Vikash", "start": 1.2, "end": 1.6}
        Used for Stage 2 audio beep replacement — we know exactly
        which audio samples to replace with a beep tone.
        """
        result = self._run(audio_file_path, word_timestamps=True)
        if not result:
            return "", []

        text = result["text"].strip()
        words = []
        for segment in result.get("segments", []):
            for w in segment.get("words", []):
                words.append({
                    "word":  w["word"].strip(),
                    "start": round(w["start"], 3),
                    "end":   round(w["end"],   3),
                })
        return text, words

    def _run(self, audio_file_path, word_timestamps=False):
        try:
            prompt = (
                "Smart home voice command. Indian English accent. "
                "Examples: turn on the lights, set a timer for ten minutes, "
                "play music in the bedroom, what is the weather today, "
                "turn off the fan, add milk to my shopping list."
            )
            return self.model.transcribe(
                audio_file_path,
                fp16=False,
                language="en",
                initial_prompt=prompt,
                word_timestamps=word_timestamps,
            )
        except Exception as e:
            print(f"Transcription error: {e}")
            return None

    @staticmethod
    def log_word_timestamps(words, pii_spans):
        """
        Prints a word-level timeline highlighting which words are PII.
        pii_spans: list of RedactedSpan from pii_mask.py

        This prepares for Stage 2: audio beep replacement.
        Each flagged word's start/end times = exact audio samples to replace.
        """
        if not words:
            return

        # Build a set of PII word strings for fast lookup
        pii_words = set()
        for span in pii_spans:
            for w in span.text.split():
                pii_words.add(w.lower().strip(".,!?"))

        print("\n  Word-level timeline (→ Stage 2 audio targets):")
        print(f"  {'Word':<20} {'Start':>7} {'End':>7}  {'Flag'}")
        print(f"  {'─'*50}")
        for w in words:
            clean = w["word"].lower().strip(".,!?'\"")
            is_pii = clean in pii_words
            flag = "🔴 PII — beep target" if is_pii else ""
            marker = "►" if is_pii else " "
            print(f"  {marker} {w['word']:<19} {w['start']:>6.2f}s {w['end']:>6.2f}s  {flag}")
        print()


if __name__ == "__main__":
    import os

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        if not os.path.exists(filename):
            print(f"Error: File '{filename}' not found.")
            sys.exit(1)
        t = LocalTranscriber()
        text, words = t.transcribe_with_timestamps(filename)
        print(f"\nTranscript: {text}")
        if words:
            print(f"\nWord timestamps ({len(words)} words):")
            for w in words:
                print(f"  {w['start']:>5.2f}s – {w['end']:>5.2f}s  {w['word']}")
    else:
        print("Usage: python3 transcriber.py <filename.wav>")