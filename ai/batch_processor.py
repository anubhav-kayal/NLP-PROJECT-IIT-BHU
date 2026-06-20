import os
import json
import glob
from typing import List, Optional
from datetime import datetime
from file_redactor import FileRedactor
from transcript_processor import TranscriptProcessor


class BatchProcessor:
    def __init__(self):
        self.file_redactor = FileRedactor()
        self.transcript_processor = TranscriptProcessor()

    def process_directory(self, input_dir: str, output_dir: str = "redacted_output",
                          context_mode: str = "all", recursive: bool = False) -> dict:
        os.makedirs(output_dir, exist_ok=True)

        audio_exts = ("*.wav", "*.mp3", "*.m4a", "*.ogg", "*.flac")
        transcript_exts = ("*.vtt", "*.txt")

        audio_files = []
        transcript_files = []

        for ext in audio_exts:
            pattern = os.path.join(input_dir, ext)
            audio_files.extend(glob.glob(pattern))
            if recursive:
                audio_files.extend(glob.glob(os.path.join(input_dir, "**", ext), recursive=True))

        for ext in transcript_exts:
            pattern = os.path.join(input_dir, ext)
            transcript_files.extend(glob.glob(pattern))
            if recursive:
                transcript_files.extend(glob.glob(os.path.join(input_dir, "**", ext), recursive=True))

        audio_results = []
        for fpath in audio_files:
            base = os.path.splitext(os.path.basename(fpath))[0]
            out_wav = os.path.join(output_dir, f"{base}_redacted.wav")
            out_json = os.path.join(output_dir, f"{base}_report.json")
            out_txt = os.path.join(output_dir, f"{base}_redacted.txt")
            try:
                result = self.file_redactor.redact_file(fpath, out_wav, out_json, out_txt, context_mode)
                audio_results.append(result)
                print(f"  [AUDIO] {os.path.basename(fpath)} -> {base}_redacted.wav")
            except Exception as e:
                print(f"  [AUDIO] {os.path.basename(fpath)} -> FAILED: {e}")
                audio_results.append({"file": fpath, "error": str(e)})

        transcript_results = []
        for fpath in transcript_files:
            base = os.path.splitext(os.path.basename(fpath))[0]
            out_json = os.path.join(output_dir, f"{base}_redacted.json")
            out_txt = os.path.join(output_dir, f"{base}_redacted.txt")
            out_vtt = os.path.join(output_dir, f"{base}_redacted.vtt")
            try:
                result = self.transcript_processor.process_transcript(
                    fpath, context_mode, out_json, out_txt, out_vtt
                )
                transcript_results.append(result)
                print(f"  [TEXT]  {os.path.basename(fpath)} -> {base}_redacted.txt")
            except Exception as e:
                print(f"  [TEXT]  {os.path.basename(fpath)} -> FAILED: {e}")
                transcript_results.append({"file": fpath, "error": str(e)})

        report = self._generate_report(audio_results, transcript_results, output_dir)
        report_path = os.path.join(output_dir, "batch_report.json")
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        html_path = self._generate_html_report(report, output_dir)
        print(f"\n  Batch report: {report_path}")
        print(f"  HTML report:  {html_path}")

        return report

    def _generate_report(self, audio_results: List[dict], transcript_results: List[dict],
                         output_dir: str) -> dict:
        total_audio = len(audio_results)
        total_transcripts = len(transcript_results)
        audio_ok = sum(1 for r in audio_results if "error" not in r)
        transcript_ok = sum(1 for r in transcript_results if "error" not in r)

        total_pii = 0
        pii_by_category = {}
        for r in audio_results + transcript_results:
            for s in r.get("spans", []):
                label = s.get("label", s.get("label", "UNKNOWN"))
                pii_by_category[label] = pii_by_category.get(label, 0) + 1
                total_pii += 1

        return {
            "batch_timestamp": datetime.now().isoformat(),
            "output_directory": output_dir,
            "summary": {
                "audio_files": total_audio,
                "audio_success": audio_ok,
                "audio_failed": total_audio - audio_ok,
                "transcript_files": total_transcripts,
                "transcript_success": transcript_ok,
                "transcript_failed": total_transcripts - transcript_ok,
                "total_pii_detected": total_pii,
                "pii_by_category": pii_by_category,
            },
            "audio_results": [
                {
                    "file": r.get("file", r.get("output_wav", "?")),
                    "original_text": r.get("original_text", "")[:100],
                    "pii_count": r.get("pii_count", 0),
                    "pii_summary": r.get("pii_summary", ""),
                    "duration_seconds": r.get("duration_seconds", 0),
                } for r in audio_results if "error" not in r
            ],
            "audio_errors": [
                {"file": r["file"], "error": r["error"]}
                for r in audio_results if "error" in r
            ],
            "transcript_results": [
                {
                    "file": r.get("output_json", "?"),
                    "pii_count": r.get("pii_count", 0),
                    "num_segments": r.get("num_segments", 0),
                } for r in transcript_results if "error" not in r
            ],
            "transcript_errors": [
                {"file": r["file"], "error": r["error"]}
                for r in transcript_results if "error" in r
            ],
        }

    def _generate_html_report(self, report: dict, output_dir: str) -> str:
        s = report["summary"]
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Batch Redaction Report</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; background: #f5f5f5; }}
h1, h2 {{ color: #1a1a2e; }}
.card {{ background: #fff; border-radius: 8px; padding: 1.5em; margin: 1em 0; box-shadow: 0 1px 3px rgba(0,0,0,0.12); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1em; }}
.stat {{ text-align: center; padding: 1em; background: #f0f0f5; border-radius: 6px; }}
.stat-value {{ font-size: 2em; font-weight: bold; color: #16213e; }}
.stat-label {{ color: #666; font-size: 0.85em; margin-top: 0.3em; }}
table {{ width: 100%; border-collapse: collapse; margin: 1em 0; }}
th, td {{ text-align: left; padding: 0.5em; border-bottom: 1px solid #ddd; }}
th {{ background: #16213e; color: #fff; }}
.error {{ color: #e74c3c; }}
.success {{ color: #27ae60; }}
.timestamp {{ color: #888; font-size: 0.85em; }}
</style>
</head>
<body>
<h1>Batch Redaction Report</h1>
<p class="timestamp">Generated: {report["batch_timestamp"]}</p>
<div class="card">
<h2>Summary</h2>
<div class="stats">
<div class="stat"><div class="stat-value">{s["audio_files"]}</div><div class="stat-label">Audio Files</div></div>
<div class="stat"><div class="stat-value">{s["audio_success"]}</div><div class="stat-label">Audio Success</div></div>
<div class="stat"><div class="stat-value">{s["transcript_files"]}</div><div class="stat-label">Transcript Files</div></div>
<div class="stat"><div class="stat-value">{s["transcript_success"]}</div><div class="stat-label">Transcript Success</div></div>
<div class="stat"><div class="stat-value">{s["total_pii_detected"]}</div><div class="stat-label">PII Items Detected</div></div>
</div>
</div>
<div class="card">
<h2>PII by Category</h2>
<table>
<tr><th>Category</th><th>Count</th></tr>
"""
        for cat, count in sorted(s["pii_by_category"].items()):
            html += f"<tr><td>{cat}</td><td>{count}</td></tr>\n"

        html += """</table>
</div>
"""
        if report.get("audio_results"):
            html += """<div class="card">
<h2>Audio File Results</h2>
<table>
<tr><th>File</th><th>PII</th><th>Duration</th><th>Summary</th></tr>
"""
            for r in report["audio_results"]:
                html += f"<tr><td>{r['file'][:50]}</td><td>{r['pii_count']}</td><td>{r['duration_seconds']}s</td><td>{r['pii_summary'][:60]}</td></tr>\n"
            html += "</table>\n</div>\n"

        if report.get("audio_errors"):
            html += """<div class="card">
<h2 class="error">Errors</h2>
<table>
<tr><th>File</th><th>Error</th></tr>
"""
            for r in report["audio_errors"]:
                html += f"<tr><td>{r['file']}</td><td class=\"error\">{r['error']}</td></tr>\n"
            html += "</table>\n</div>\n"

        html += """</body>
</html>"""

        html_path = os.path.join(output_dir, "batch_report.html")
        with open(html_path, "w") as f:
            f.write(html)
        return html_path
