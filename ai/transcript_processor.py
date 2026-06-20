import re
import os
import json
from typing import List, Optional, Tuple
from pii_mask import PIIMask, RedactedSpan


class TranscriptProcessor:
    def __init__(self):
        self.pii = PIIMask()

    def parse_zoom_vtt(self, vtt_path: str) -> Tuple[str, List[dict]]:
        with open(vtt_path, "r") as f:
            content = f.read()

        lines = content.split("\n")
        segments = []
        current_start = None
        current_end = None
        current_text = []
        speaker = None

        for line in lines:
            line = line.strip()
            if "-->" in line:
                if current_text:
                    segments.append({
                        "start": current_start,
                        "end": current_end,
                        "speaker": speaker or "Unknown",
                        "text": " ".join(current_text),
                    })
                parts = line.split("-->")
                current_start = self._parse_vtt_timestamp(parts[0].strip())
                current_end = self._parse_vtt_timestamp(parts[1].strip())
                current_text = []
                speaker = None
            elif line and not line.startswith("WEBVTT") and not line.startswith("NOTE"):
                colon_idx = line.find(":")
                if colon_idx > 0 and colon_idx < 20:
                    potential_speaker = line[:colon_idx].strip()
                    if potential_speaker and not potential_speaker[0].isdigit():
                        speaker = potential_speaker
                        current_text.append(line[colon_idx + 1:].strip())
                    else:
                        current_text.append(line)
                else:
                    current_text.append(line)

        if current_text:
            segments.append({
                "start": current_start,
                "end": current_end,
                "speaker": speaker or "Unknown",
                "text": " ".join(current_text),
            })

        full_text = "\n".join(s["text"] for s in segments if s["text"])
        return full_text, segments

    def parse_zoom_txt(self, txt_path: str) -> Tuple[str, List[dict]]:
        with open(txt_path, "r") as f:
            content = f.read()

        segments = []
        lines = content.split("\n")
        current_speaker = None
        current_text = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            ts_match = re.match(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$", line)
            if ts_match:
                if current_text:
                    segments.append({
                        "speaker": current_speaker or "Unknown",
                        "text": " ".join(current_text),
                        "timestamp": ts_match.group(1),
                    })
                current_text = [ts_match.group(2)]
                current_speaker = None
            elif line.endswith(":") or re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)*:\s", line):
                if current_text:
                    segments.append({
                        "speaker": current_speaker or "Unknown",
                        "text": " ".join(current_text),
                    })
                colon_idx = line.index(":")
                current_speaker = line[:colon_idx].strip()
                current_text = [line[colon_idx + 1:].strip()]
            else:
                current_text.append(line)

        if current_text:
            segments.append({
                "speaker": current_speaker or "Unknown",
                "text": " ".join(current_text),
            })

        full_text = "\n".join(s["text"] for s in segments if s["text"])
        return full_text, segments

    def _parse_vtt_timestamp(self, ts: str) -> float:
        ts = ts.strip()
        parts = ts.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2].replace(",", "."))
        elif len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1].replace(",", "."))
        return 0.0

    def process_transcript(self, input_path: str, context_mode: str = "all",
                           output_json: Optional[str] = None,
                           output_txt: Optional[str] = None,
                           output_vtt: Optional[str] = None) -> dict:
        ext = os.path.splitext(input_path)[1].lower()

        if ext == ".vtt":
            full_text, segments = self.parse_zoom_vtt(input_path)
        elif ext == ".txt":
            full_text, segments = self.parse_zoom_txt(input_path)
        else:
            with open(input_path, "r") as f:
                full_text = f.read()
            segments = [{"speaker": "Unknown", "text": full_text}]

        redacted_text, spans = self.pii.analyze(full_text, context_mode=context_mode)

        redacted_segments = []
        for seg in segments:
            seg_redacted, seg_spans = self.pii.analyze(seg["text"], context_mode=context_mode)
            redacted_segments.append({
                "speaker": seg.get("speaker", "Unknown"),
                "original": seg["text"],
                "redacted": seg_redacted,
                "spans": [
                    {"label": s.label, "text": s.text, "confidence": s.confidence}
                    for s in seg_spans
                ],
                "timestamp": seg.get("timestamp", ""),
            })

        base, _ = os.path.splitext(input_path)
        output_json = output_json or f"{base}_redacted.json"
        output_txt = output_txt or f"{base}_redacted.txt"
        output_vtt = output_vtt or f"{base}_redacted.vtt"

        result = {
            "original_text": full_text,
            "redacted_text": redacted_text,
            "spans": [{"label": s.label, "text": s.text, "start": s.start, "end": s.end}
                      for s in spans],
            "num_segments": len(segments),
            "pii_found": len(spans) > 0,
            "pii_count": len(spans),
            "segments": redacted_segments,
        }

        with open(output_json, "w") as f:
            json.dump(result, f, indent=2)
        with open(output_txt, "w") as f:
            f.write(self._format_redacted_txt(redacted_segments))
        self._write_redacted_vtt(redacted_segments, output_vtt)

        result["output_json"] = output_json
        result["output_txt"] = output_txt
        result["output_vtt"] = output_vtt
        return result

    def _format_redacted_txt(self, segments: List[dict]) -> str:
        lines = []
        for seg in segments:
            speaker = seg.get("speaker", "Unknown")
            timestamp = seg.get("timestamp", "")
            ts_str = f" [{timestamp}]" if timestamp else ""
            lines.append(f"{speaker}{ts_str}: {seg['redacted']}")
        return "\n\n".join(lines)

    def _write_redacted_vtt(self, segments: List[dict], path: str):
        lines = ["WEBVTT", ""]
        for seg in segments:
            timestamp = seg.get("timestamp", "00:00:00.000")
            speaker = seg.get("speaker", "Unknown")
            lines.append(f"{timestamp} --> {timestamp}")
            lines.append(f"{speaker}: {seg['redacted']}")
            lines.append("")
        with open(path, "w") as f:
            f.write("\n".join(lines))
