import warnings
warnings.filterwarnings("ignore")

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class SpeakerSegment:
    start: float
    end: float
    speaker: str


class SpeakerDiarizer:
    def __init__(self, use_pyannote=True):
        self.pipeline = None
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
            print(f"  Note: pyannote not available ({e}). Using fallback mode.")
            self.pipeline = None

    def diarize(self, audio_path: str) -> List[SpeakerSegment]:
        if self.pipeline is not None:
            return self._diarize_pyannote(audio_path)
        return self._diarize_fallback(audio_path)

    def _diarize_pyannote(self, audio_path: str) -> List[SpeakerSegment]:
        try:
            from pyannote.core import Annotation
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

    def _diarize_fallback(self, audio_path: str) -> List[SpeakerSegment]:
        return []

    def is_available(self) -> bool:
        return self.pipeline is not None
