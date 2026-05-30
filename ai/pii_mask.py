import re
import spacy
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class RedactedSpan:
    start: int
    end: int
    text: str
    label: str
    confidence: float

class PIIMask:
    """
    Lightweight PII detector for Indian context.
    Uses spaCy NER + rule-based patterns for Indian-specific PII.
    No GLiNER dependency — runs fast on CPU, <150MB.
    """

    INDIAN_PII_PATTERNS = {
        "AADHAAR": r"\b[2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b",
        "PAN":     r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
        "UPI_ID":  r"\b[\w.\-]{2,256}@[a-zA-Z]{2,64}\b",
        "PHONE":   r"\b(?:\+91|91|0)?[6-9][0-9]{9}\b",
        "IFSC":    r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        "EMAIL":   r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
        "BANK_ACC":r"\b[0-9]{9,18}\b",
        "PINCODE": r"\b[1-9][0-9]{5}\b",
    }

    LABEL_MAP = {
        "PERSON":   "NAME_REDACTED",
        "PER":      "NAME_REDACTED",
        "ORG":      "ORG_REDACTED",
        "GPE":      "LOCATION_REDACTED",
        "LOC":      "LOCATION_REDACTED",
        "AADHAAR":  "AADHAAR_REDACTED",
        "PAN":      "PAN_REDACTED",
        "UPI_ID":   "UPI_REDACTED",
        "PHONE":    "PHONE_REDACTED",
        "IFSC":     "IFSC_REDACTED",
        "EMAIL":    "EMAIL_REDACTED",
        "BANK_ACC": "BANK_REDACTED",
        "PINCODE":  "PINCODE_REDACTED",
    }

    CONFIDENCE_THRESHOLD = 0.75

    def __init__(self):
        self.nlp = self._load_spacy()

    def _load_spacy(self):
        models = ["en_core_web_md", "en_core_web_sm", "en_core_web_lg"]
        for model in models:
            try:
                nlp = spacy.load(model)
                print(f"  Loaded spaCy model: {model}")
                return nlp
            except OSError:
                continue
        print("  No spaCy model found. Run: python3 -m spacy download en_core_web_sm")
        return None

    def _rule_based_spans(self, text: str) -> List[RedactedSpan]:
        spans = []
        for label, pattern in self.INDIAN_PII_PATTERNS.items():
            for match in re.finditer(pattern, text):
                # Avoid flagging short standalone numbers as bank accounts
                if label == "BANK_ACC":
                    matched = match.group()
                    if len(matched) < 11:
                        continue
                spans.append(RedactedSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    label=label,
                    confidence=1.0
                ))
        return spans

    def _spacy_spans(self, text: str) -> List[RedactedSpan]:
        if not self.nlp:
            return []
        doc = self.nlp(text)
        spans = []
        for ent in doc.ents:
            if ent.label_ in self.LABEL_MAP:
                spans.append(RedactedSpan(
                    start=ent.start_char,
                    end=ent.end_char,
                    text=ent.text,
                    label=ent.label_,
                    confidence=0.85
                ))
        return spans

    def _merge_spans(self, spans: List[RedactedSpan]) -> List[RedactedSpan]:
        if not spans:
            return []
        sorted_spans = sorted(spans, key=lambda s: s.start)
        merged = [sorted_spans[0]]
        for current in sorted_spans[1:]:
            prev = merged[-1]
            if current.start < prev.end:
                # Overlap — keep the one with higher confidence, extend end
                if current.confidence >= prev.confidence:
                    merged[-1] = RedactedSpan(
                        start=prev.start,
                        end=max(prev.end, current.end),
                        text=current.text,
                        label=current.label,
                        confidence=current.confidence
                    )
            else:
                merged.append(current)
        return merged

    def analyze(self, text: str) -> Tuple[str, List[RedactedSpan]]:
        """
        Returns (redacted_text, list_of_detected_spans)
        """
        all_spans = self._rule_based_spans(text) + self._spacy_spans(text)
        all_spans = [s for s in all_spans if s.confidence >= self.CONFIDENCE_THRESHOLD]
        merged = self._merge_spans(all_spans)

        # Build redacted text
        result = []
        prev_end = 0
        for span in merged:
            result.append(text[prev_end:span.start])
            tag = self.LABEL_MAP.get(span.label, "PII_REDACTED")
            result.append(f"[{tag}]")
            prev_end = span.end
        result.append(text[prev_end:])

        redacted = "".join(result)
        return redacted, merged

    def get_redaction_summary(self, spans: List[RedactedSpan]) -> str:
        if not spans:
            return "No PII detected."
        parts = []
        for span in spans:
            tag = self.LABEL_MAP.get(span.label, span.label)
            parts.append(f"{span.label}: '{span.text}'")
        return " | ".join(parts)


if __name__ == "__main__":
    mask = PIIMask()
    tests = [
        "Hey Alexa, call Mr. Vikash Kumar Kayal.",
        "My Aadhaar is 2345 6789 0123 and PAN is ABCDE1234F",
        "Transfer 5000 to rohit@paytm and my phone is 9876543210",
        "I live in Mumbai near Andheri, my IFSC is HDFC0001234",
        "Call Dr. Priya Sharma at 9988776655 or email her at priya@gmail.com",
    ]
    print("\n" + "="*60)
    print("PII DETECTION TEST")
    print("="*60)
    for t in tests:
        redacted, spans = mask.analyze(t)
        print(f"\nInput:    {t}")
        print(f"Redacted: {redacted}")
        if spans:
            print(f"Found:    {mask.get_redaction_summary(spans)}")
    print("="*60)