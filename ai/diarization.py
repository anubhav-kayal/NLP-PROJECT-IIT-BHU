import warnings
import numpy as np
import wave
import struct
warnings.filterwarnings("ignore")

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SpeakerSegment:
    start: float
    end: float
    speaker: str


@dataclass
class WordSpeaker:
    word: str
    start: float
    end: float
    speaker: str


class SpeakerDiarizer:
    def __init__(self, use_pyannote=True):
        self.pipeline = None
        self.sample_rate = 16000
        if use_pyannote:
            self._try_load_pyannote()

    def _try_load_pyannote(self):
        try:
            from pyannote.audio import Pipeline
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=None,
            )
            print("  Loaded pyannote speaker diarization pipeline")
        except Exception as e:
            print(f"  Note: pyannote not available ({e}). Using energy-based VAD.")

    def diarize(self, audio_path: str) -> List[SpeakerSegment]:
        if self.pipeline is not None:
            segs = self._diarize_pyannote(audio_path)
            if segs:
                return segs
        return self._diarize_energy_vad(audio_path)

    def _diarize_pyannote(self, audio_path: str) -> List[SpeakerSegment]:
        try:
            output = self.pipeline(audio_path)
            segments = []
            for segment, _, speaker in output.itertracks(yield_label=True):
                segments.append(SpeakerSegment(
                    start=round(segment.start, 3),
                    end=round(segment.end, 3),
                    speaker=speaker,
                ))
            return segments
        except Exception as e:
            print(f"  Diarization error: {e}")
            return []

    def _load_audio(self, audio_path: str) -> Optional[np.ndarray]:
        try:
            with wave.open(audio_path, "rb") as wf:
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
                return None
            audio = np.frombuffer(raw, dtype=dtype).astype(np.float64)
            if n_channels > 1:
                audio = audio.reshape(-1, n_channels).mean(axis=1)
            if np.max(np.abs(audio)) > 1.0:
                audio = audio / 32768.0
            self.sample_rate = framerate
            return audio
        except Exception:
            return None

    def _diarize_energy_vad(self, audio_path: str) -> List[SpeakerSegment]:
        audio = self._load_audio(audio_path)
        if audio is None or len(audio) == 0:
            return []

        frame_len = int(0.025 * self.sample_rate)
        hop_len = int(0.010 * self.sample_rate)
        frames = []
        for start in range(0, len(audio) - frame_len + 1, hop_len):
            frame = audio[start:start + frame_len]
            rms = np.sqrt(np.mean(frame ** 2))
            frames.append(rms)

        if not frames:
            return []

        noise_floor = np.percentile(frames, 15)
        signal_floor = np.percentile(frames, 60)
        threshold = noise_floor + 0.3 * (signal_floor - noise_floor)
        threshold = max(threshold, noise_floor * 2.0)

        is_speech = np.array(frames) > threshold

        segments = []
        in_speech = False
        seg_start = 0.0
        min_duration = 0.1
        merge_gap = 0.3

        for i, speech in enumerate(is_speech):
            t = i * hop_len / self.sample_rate
            if speech and not in_speech:
                in_speech = True
                seg_start = t
            elif not speech and in_speech:
                seg_end = t
                if seg_end - seg_start >= min_duration:
                    segments.append(SpeakerSegment(
                        start=round(seg_start, 3),
                        end=round(seg_end, 3),
                        speaker="SPEAKER_00"
                    ))
                in_speech = False

        if in_speech:
            seg_end = len(audio) / self.sample_rate
            if seg_end - seg_start >= min_duration:
                segments.append(SpeakerSegment(
                    start=round(seg_start, 3),
                    end=round(seg_end, 3),
                    speaker="SPEAKER_00"
                ))

        if not segments:
            return [SpeakerSegment(start=0.0, end=len(audio) / self.sample_rate, speaker="SPEAKER_00")]

        merged = [segments[0]]
        for seg in segments[1:]:
            prev = merged[-1]
            if seg.start - prev.end <= merge_gap and seg.speaker == prev.speaker:
                merged[-1] = SpeakerSegment(
                    start=prev.start,
                    end=seg.end,
                    speaker=prev.speaker
                )
            else:
                merged.append(seg)

        return merged

    def assign_words_to_speakers(
        self, word_timestamps: List[dict], segments: List[SpeakerSegment]
    ) -> List[WordSpeaker]:
        if not segments:
            return [
                WordSpeaker(word=w["word"], start=w["start"], end=w["end"], speaker="SPEAKER_00")
                for w in word_timestamps
            ]

        result = []
        for w in word_timestamps:
            assigned = "SPEAKER_00"
            for seg in segments:
                mid = (w["start"] + w["end"]) / 2
                if seg.start <= mid <= seg.end:
                    assigned = seg.speaker
                    break
            result.append(WordSpeaker(
                word=w["word"], start=w["start"], end=w["end"], speaker=assigned
            ))
        return result

    def is_available(self) -> bool:
        return self.pipeline is not None
