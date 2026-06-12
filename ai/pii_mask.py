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

    INDIAN_FIRST_NAMES = {
        "Vikash","Rahul","Priya","Anubhav","Deepak","Sunita","Rajesh","Pooja",
        "Amit","Neha","Sanjay","Kavita","Arjun","Meera","Rohit","Anjali",
        "Vivek","Smita","Suresh","Geeta","Mahesh","Rekha","Naresh","Savita",
        "Ramesh","Usha","Dinesh","Lata","Pankaj","Nisha","Vinay","Asha",
        "Mohammad","Fatima","Abdul","Zoya","Imran","Gurpreet","Harpreet",
        "Manpreet","Jaspreet","Simran","Venkatesh","Lakshmi","Krishnamurthy",
        "Padmavathi","Ravi","Subramanian","Anand","Srinivasan","Bharathi",
        "Ganesh","Aditi","Ishaan","Aarav","Sanya","Armaan","Kritika","Harsh",
        "Tanya","Nikhil","Shreya","Akash","Swati","Manoj","Divya","Prakash",
        "Kiran","Naveen","Sudha","Vijay","Lalita","Aman","Ritu","Tarun",
        "Jyoti","Hemant","Pallavi","Gaurav","Shweta","Dhruv",
    }

    INDIAN_LAST_NAMES = {
        "Sharma","Verma","Gupta","Singh","Kumar","Das","Patel","Reddy",
        "Nair","Menon","Iyer","Deshmukh","Joshi","Kulkarni","Desai","Pandey",
        "Mishra","Tiwari","Dubey","Chaturvedi","Saxena","Srivastava","Agarwal",
        "Jain","Mehta","Shah","Kapoor","Malhotra","Chopra","Bhatia","Arora",
        "Sood","Bajaj","Kohli","Choudhary","Khatri","Thakur","Chauhan",
        "Yadav","Maurya","Shukla","Tripathi","Pandit","Rawat","Negi","Bisht",
        "Rana","Bhandari","Pradhan","Mahapatra","Swain","Naidu","Pillai",
        "Mohan","Chandrasekhar","Subramaniam","Raghavan","Venkatesan",
    }

    INDIAN_CITIES = {
        "Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Kolkata","Pune",
        "Ahmedabad","Jaipur","Lucknow","Varanasi","Patna","Bhopal","Indore",
        "Chandigarh","Amritsar","Nagpur","Surat","Thane","Allahabad","Ranchi",
        "Guwahati","Coimbatore","Kochi","Thiruvananthapuram","Bhubaneswar",
        "Jodhpur","Udaipur","Goa","Shimla","Dehradun","Agra","Mathura",
        "Gaya","Haridwar","Rishikesh","Ayodhya","Meerut","Gurgaon","Noida",
        "Mysore","Mangalore","Vadodara","Rajkot","Jamnagar","Raipur",
        "Jabalpur","Ujjain","Nashik","Aurangabad","Solapur","Kolhapur",
        "Amravati","Srinagar","Jammu","Leh","Panaji","Margao","Pondicherry",
        "Tiruchirappalli","Madurai","Salem","Tirunelveli","Hubli","Belgaum",
        "Mangaluru","Shivamogga","Vijayawada","Visakhapatnam","Guntur",
        "Kurnool","Warangal","Kakinada","Rajahmundry","Thrissur","Kozhikode",
        "Kannur","Alappuzha","Kollam","Siliguri","Asansol","Durgapur",
        "Bardhaman","Howrah","Bhilai","Bilaspur","Korba","Raigarh",
        "Jamshedpur","Dhanbad","Bokaro","Deoghar","Jhansi","Agra","Aligarh",
        "Gorakhpur","Moradabad","Saharanpur","Muzaffarnagar","Kota","Bikaner",
        "Ajmer","Bhilwara","Udaipur","Bathinda","Patiala","Ludhiana",
        "Jalandhar","Mohali","Panchkula","Faridabad","Ghaziabad",
    }

    ORG_FP_KEYWORDS = {
        "PAN","Aadhaar","ITR","IFSC","UPI","KYC","NEFT","RTGS","IMPS",
        "OTP","GST","TDS","TAN","DIN","CIN","LLP","HUF","NRI","FEMA",
        "RBI","SEBI","IRDAI","EPFO","ESIC","PF","EPS","NPS","PPF",
        "FD","RD","SIP","SWP","STP","AML","CAGR",
    }

    RULE_PRIORITY = {
        "AADHAAR": 10,
        "PAN":     10,
        "EMAIL":   10,
        "PHONE":    9,
        "UPI_ID":   8,
        "IFSC":     8,
        "PINCODE":  7,
        "PERSON":   6,
        "PER":      6,
        "BANK_ACC": 5,
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

    def _dictionary_spans(self, text: str) -> List[RedactedSpan]:
        spans = []
        words = re.split(r"(\s+|[.,!?;:'\"()\[\]{}])", text)
        tokens = [t for t in words if t.strip()]
        raw_positions = []
        pos = 0
        for t in words:
            if t.strip():
                raw_positions.append((t, pos, pos + len(t)))
            pos += len(t)

        idx = 0
        while idx < len(tokens):
            tok = tokens[idx]
            t_start, t_end = raw_positions[idx][1], raw_positions[idx][2]
            lower = tok.strip(".,!?").lower()

            first_name_match = None
            for name in self.INDIAN_FIRST_NAMES:
                if tok.strip(".,!?").lower() == name.lower():
                    first_name_match = name
                    break

            if first_name_match and idx + 1 < len(tokens):
                next_tok = tokens[idx + 1]
                n_start, n_end = raw_positions[idx + 1][1], raw_positions[idx + 1][2]
                next_clean = next_tok.strip(".,!?").lower()
                for lname in self.INDIAN_LAST_NAMES:
                    if next_clean == lname.lower():
                        span_text = text[t_start:n_end]
                        spans.append(RedactedSpan(
                            start=t_start, end=n_end,
                            text=span_text, label="PERSON", confidence=0.9
                        ))
                        idx += 1
                        break
                else:
                    spans.append(RedactedSpan(
                        start=t_start, end=t_end,
                        text=tok, label="PERSON", confidence=0.85
                    ))
            elif first_name_match:
                spans.append(RedactedSpan(
                    start=t_start, end=t_end,
                    text=tok, label="PERSON", confidence=0.85
                ))

            elif tok.strip(".,!?").lower() in {c.lower() for c in self.INDIAN_CITIES}:
                spans.append(RedactedSpan(
                    start=t_start, end=t_end,
                    text=tok, label="GPE", confidence=0.85
                ))

            idx += 1

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
                if ent.label_ == "ORG" and ent.text.strip() in self.ORG_FP_KEYWORDS:
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
        all_spans = self._rule_based_spans(text) + self._dictionary_spans(text) + self._spacy_spans(text)
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