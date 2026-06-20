import os
import json
import wave
import tempfile
import numpy as np
from typing import List, Optional, Tuple
from pii_mask import PIIMask, RedactedSpan
from transcriber import LocalTranscriber
from streaming_pipeline import AudioRedactor

SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2


class FileRedactor:
    def __init__(self, model_size="small"):
        print("  Loading PII Filter...")
        self.pii = PIIMask()
        print("  Loading Whisper...")
        self.transcriber = LocalTranscriber(model_size=model_size)
        self.audio_redactor = AudioRedactor()

    def _try_pydub(self, input_path: str) -> Optional[str]:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_file(input_path)
            audio = audio.set_frame_rate(SAMPLE_RATE).set_channels(CHANNELS).set_sample_width(SAMPLE_WIDTH)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            audio.export(tmp.name, format="wav")
            return tmp.name
        except Exception:
            return None

    def _to_wav(self, input_path: str) -> str:
        if input_path.lower().endswith(".wav"):
            return input_path
        wav_path = self._try_pydub(input_path)
        if wav_path:
            return wav_path
        raise RuntimeError(
            "Cannot convert to WAV. Install pydub + ffmpeg for MP3/other format support: "
            "pip install pydub && brew install ffmpeg"
        )

    def _load_audio_array(self, wav_path: str) -> Tuple[np.ndarray, int]:
        with wave.open(wav_path, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
        if sampwidth == 2:
            dtype = np.int16
        elif sampwidth == 1:
            dtype = np.uint8
        else:
            raise ValueError(f"Unsupported sample width: {sampwidth}")
        audio = np.frombuffer(raw, dtype=dtype).astype(np.float64)
        if n_channels > 1:
            audio = audio.reshape(-1, n_channels).mean(axis=1)
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / 32768.0
        return audio, framerate

    def redact_file(
        self, input_path: str, output_wav: Optional[str] = None,
        output_json: Optional[str] = None, output_txt: Optional[str] = None,
        context_mode: str = "all"
    ) -> dict:
        original_path = input_path
        needs_cleanup = False
        if not input_path.lower().endswith(".wav"):
            wav_path = self._to_wav(input_path)
            if wav_path != input_path:
                needs_cleanup = True
            input_path = wav_path

        try:
            result = self._redact_wav(input_path, context_mode)
        finally:
            if needs_cleanup and input_path != original_path:
                try:
                    os.unlink(input_path)
                except OSError:
                    pass

        base, ext = os.path.splitext(original_path)
        output_wav = output_wav or f"{base}_redacted.wav"
        output_json = output_json or f"{base}_report.json"
        output_txt = output_txt or f"{base}_redacted.txt"

        self._save_redacted_audio(result["redacted_audio"], output_wav)
        self._save_report(result, output_json)
        self._save_transcript(result["redacted_text"], output_txt)

        result["output_wav"] = output_wav
        result["output_json"] = output_json
        result["output_txt"] = output_txt
        return result

    def _redact_wav(self, wav_path: str, context_mode: str) -> dict:
        text, word_timestamps = self.transcriber.transcribe_with_timestamps(wav_path)

        if not text:
            return {
                "original_text": "",
                "redacted_text": "",
                "spans": [],
                "redacted_audio": None,
                "word_timestamps": [],
                "duration_seconds": 0.0,
                "num_words": 0,
                "pii_found": False,
                "pii_summary": "",
            }

        audio_array, framerate = self._load_audio_array(wav_path)
        duration = len(audio_array) / framerate
        redacted_text, spans = self.pii.analyze(text, context_mode=context_mode)

        if spans:
            redacted_audio = self.audio_redactor.redact_audio(
                audio_array, word_timestamps, spans
            )
        else:
            max_val = np.max(np.abs(audio_array))
            if max_val > 1.0:
                redacted_audio = (audio_array.astype(np.float64) / max_val * 0.99 * 32767).astype(np.int16)
            else:
                redacted_audio = (audio_array * 32767).astype(np.int16)

        summary = self.pii.get_redaction_summary(spans)

        return {
            "original_text": text,
            "redacted_text": redacted_text,
            "spans": [
                {"label": s.label, "text": s.text, "start": s.start, "end": s.end, "confidence": s.confidence}
                for s in spans
            ],
            "redacted_audio": redacted_audio,
            "word_timestamps": word_timestamps,
            "duration_seconds": round(duration, 2),
            "num_words": len(word_timestamps),
            "pii_found": len(spans) > 0,
            "pii_summary": summary,
            "pii_count": len(spans),
        }

    def _save_redacted_audio(self, audio_data: np.ndarray, path: str):
        if audio_data is None:
            return
        audio_int16 = np.clip(audio_data, -32768, 32767).astype(np.int16)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

    def _save_report(self, result: dict, path: str):
        report = {
            "original_text": result["original_text"],
            "redacted_text": result["redacted_text"],
            "duration_seconds": result["duration_seconds"],
            "num_words": result["num_words"],
            "pii_found": result["pii_found"],
            "pii_count": result["pii_count"],
            "pii_summary": result["pii_summary"],
            "detected_spans": result["spans"],
        }
        with open(path, "w") as f:
            json.dump(report, f, indent=2)

    def _save_transcript(self, text: str, path: str):
        with open(path, "w") as f:
            f.write(text + "\n")

    def batch_redact(
        self, file_paths: List[str], output_dir: str = "redacted_output",
        context_mode: str = "all"
    ) -> List[dict]:
        os.makedirs(output_dir, exist_ok=True)
        results = []
        for fpath in file_paths:
            base = os.path.splitext(os.path.basename(fpath))[0]
            out_wav = os.path.join(output_dir, f"{base}_redacted.wav")
            out_json = os.path.join(output_dir, f"{base}_report.json")
            out_txt = os.path.join(output_dir, f"{base}_redacted.txt")
            try:
                result = self.redact_file(fpath, out_wav, out_json, out_txt, context_mode)
                results.append(result)
                print(f"  OK: {fpath} -> {out_wav}")
            except Exception as e:
                print(f"  FAIL: {fpath} -> {e}")
                results.append({"file": fpath, "error": str(e)})
        return results
