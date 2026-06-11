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
        "PHONE":   r"\b(?:\+91|91|0)?[5-9][0-9]{9}\b",
        "IFSC":    r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        "EMAIL":   r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
        "BANK_ACC":r"\b[0-9]{9,18}\b",
        "PINCODE": r"\b[1-9][0-9]{5}\b",
    }

    RULE_PRIORITY = {
        "AADHAAR": 10,
        "PAN":     10,
        "PHONE":    9,
        "UPI_ID":   9,
        "EMAIL":    9,
        "IFSC":     8,
        "BANK_ACC": 5,
        "PINCODE":  7,
        "PERSON":   6,
        "PER":      6,
        "ORG":      4,
        "GPE":      4,
        "LOC":      4,
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
                if label == "BANK_ACC":
                    matched = match.group()
                    if len(matched) < 11:
                        continue
                    phone_pat = self.INDIAN_PII_PATTERNS["PHONE"]
                    if re.fullmatch(phone_pat, matched):
                        continue
                if label == "AADHAAR":
                    if match.start() > 0 and text[match.start() - 1] == "+":
                        continue
                spans.append(RedactedSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    label=label,
                    confidence=1.0
                ))
        return spans

    def _spacy_span_near_pii(self, text: str, ent) -> bool:
        for label, pattern in self.INDIAN_PII_PATTERNS.items():
            if label == "BANK_ACC":
                continue
            for m in re.finditer(pattern, text):
                if (m.start() <= ent.end_char and m.end() >= ent.start_char):
                    return True
                if abs(m.start() - ent.end_char) <= 1:
                    return True
                if abs(m.end() - ent.start_char) <= 1:
                    return True
        return False

    def _spacy_spans(self, text: str) -> List[RedactedSpan]:
        if not self.nlp:
            return []
        doc = self.nlp(text)
        spans = []
        for ent in doc.ents:
            if ent.label_ not in self.LABEL_MAP:
                continue
            if ent.label_ in ("ORG", "GPE", "LOC"):
                if self._spacy_span_near_pii(text, ent):
                    continue
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
                prio_current = self.RULE_PRIORITY.get(current.label, 0)
                prio_prev = self.RULE_PRIORITY.get(prev.label, 0)
                if prio_current > prio_prev or (prio_current == prio_prev and current.confidence >= prev.confidence):
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