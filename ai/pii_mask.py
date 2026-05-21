"""
PII Detection and Anonymization for Indian Data using Presidio, spaCy, and GLiNER
Handles: Names, Addresses, Aadhar, PAN, Voter ID, Medical, Legal, and other sensitive information
Uses GLiNER for enhanced Named Entity Recognition
"""

import re
from typing import Dict, List

import spacy
from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpEngineProvider, SpacyNlpEngine
from presidio_anonymizer import AnonymizerEngine


class IndianPIIRecognizers:
    """Custom recognizers for Indian-specific PII entities"""
    
    @staticmethod
    def create_aadhar_recognizer():
        """Aadhar Card recognizer - 12 digit number (with or without spaces/hyphens)"""
        aadhar_patterns = [
            Pattern(name="aadhar_pattern_1", regex=r"\b\d{4}\s?\d{4}\s?\d{4}\b", score=0.9),
            Pattern(name="aadhar_pattern_2", regex=r"\b\d{4}-\d{4}-\d{4}\b", score=0.9),
            Pattern(name="aadhar_pattern_3", regex=r"\b\d{12}\b", score=0.7),
        ]
        
        aadhar_recognizer = PatternRecognizer(
            supported_entity="IN_AADHAR",
            patterns=aadhar_patterns,
            context=["aadhar", "aadhaar", "uid", "uidai"]
        )
        return aadhar_recognizer
    
    @staticmethod
    def create_pan_recognizer():
        """PAN Card recognizer - Format: ABCDE1234F"""
        pan_pattern = [
            Pattern(name="pan_pattern", regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", score=0.9),
        ]
        
        pan_recognizer = PatternRecognizer(
            supported_entity="IN_PAN",
            patterns=pan_pattern,
            context=["pan", "pan card", "permanent account number"]
        )
        return pan_recognizer
    
    @staticmethod
    def create_voter_id_recognizer():
        """Voter ID recognizer - Format: ABC1234567"""
        voter_id_patterns = [
            Pattern(name="voter_id_pattern", regex=r"\b[A-Z]{3}[0-9]{7}\b", score=0.85),
        ]
        
        voter_id_recognizer = PatternRecognizer(
            supported_entity="IN_VOTER_ID",
            patterns=voter_id_patterns,
            context=["voter", "voter id", "epic", "election card"]
        )
        return voter_id_recognizer
    
    @staticmethod
    def create_indian_mobile_recognizer():
        """Indian mobile number recognizer"""
        mobile_patterns = [
            Pattern(name="mobile_pattern_1", regex=r"\b(\+91|91)?[\s-]?[6-9]\d{9}\b", score=0.85),
            Pattern(name="mobile_pattern_2", regex=r"\b[6-9]\d{2}[\s-]?\d{3}[\s-]?\d{4}\b", score=0.85),
        ]
        
        mobile_recognizer = PatternRecognizer(
            supported_entity="IN_PHONE_NUMBER",
            patterns=mobile_patterns,
            context=["phone", "mobile", "contact", "call"]
        )
        return mobile_recognizer
    
    @staticmethod
    def create_indian_pincode_recognizer():
        """Indian PIN code recognizer - 6 digit number"""
        pincode_pattern = [
            Pattern(name="pincode_pattern", regex=r"\b[1-9][0-9]{5}\b", score=0.6),
        ]
        
        pincode_recognizer = PatternRecognizer(
            supported_entity="IN_PINCODE",
            patterns=pincode_pattern,
            context=["pincode", "pin code", "postal code", "zip"]
        )
        return pincode_recognizer
    
    @staticmethod
    def create_medical_record_recognizer():
        """Medical record number recognizer"""
        medical_patterns = [
            Pattern(name="medical_record_1", regex=r"\b(MR|MRN|PATIENT ID)[\s:-]?\d+\b", score=0.85),
            Pattern(name="medical_record_2", regex=r"\b(UHID|HOSP ID)[\s:-]?\d+\b", score=0.85),
        ]
        
        medical_recognizer = PatternRecognizer(
            supported_entity="MEDICAL_RECORD",
            patterns=medical_patterns,
            context=["hospital", "patient", "medical", "diagnosis", "treatment"]
        )
        return medical_recognizer
    
    @staticmethod
    def create_case_number_recognizer():
        """Legal case number recognizer"""
        case_patterns = [
            Pattern(name="case_pattern_1", regex=r"\b(CASE NO|CASE NUMBER|FIR NO)[\s:-]?\d+/\d+\b", score=0.85),
            Pattern(name="case_pattern_2", regex=r"\b[A-Z]{2,4}/\d+/\d{4}\b", score=0.7),
        ]
        
        case_recognizer = PatternRecognizer(
            supported_entity="LEGAL_CASE_NUMBER",
            patterns=case_patterns,
            context=["case", "court", "fir", "legal", "petition"]
        )
        return case_recognizer


class IndianPIIAnonymizer:
    """Main class for PII detection and anonymization using spaCy with GLiNER"""
    
    def __init__(self, use_gliner=True):
        """
        Initialize the analyzer and anonymizer engines
        
        Args:
            use_gliner: Whether to use GLiNER for enhanced NER (default: True)
        """
        # Load spaCy model with GLiNER if available
        self.use_gliner = use_gliner
        self.nlp = self._load_spacy_model()
        
        # Configure spaCy NLP engine for Presidio
        configuration = {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
        }
        
        # Create custom NLP engine with our spaCy model
        provider = NlpEngineProvider(nlp_configuration=configuration)
        nlp_engine = provider.create_engine()
        
        # Replace the default spaCy model with our GLiNER-enhanced model
        if self.use_gliner:
            nlp_engine.nlp["en"] = self.nlp
        
        # Initialize analyzer with custom recognizers
        self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
        
        # Add custom Indian recognizers
        recognizers = IndianPIIRecognizers()
        self.analyzer.registry.add_recognizer(recognizers.create_aadhar_recognizer())
        self.analyzer.registry.add_recognizer(recognizers.create_pan_recognizer())
        self.analyzer.registry.add_recognizer(recognizers.create_voter_id_recognizer())
        self.analyzer.registry.add_recognizer(recognizers.create_indian_mobile_recognizer())
        self.analyzer.registry.add_recognizer(recognizers.create_indian_pincode_recognizer())
        self.analyzer.registry.add_recognizer(recognizers.create_medical_record_recognizer())
        self.analyzer.registry.add_recognizer(recognizers.create_case_number_recognizer())
        
        # Initialize anonymizer
        self.anonymizer = AnonymizerEngine()
        
        # Define entities to detect (including built-in ones)
        self.entity_types = [
            "PERSON",              # Names
            "LOCATION",            # Addresses/Places
            "DATE_TIME",           # Dates
            "EMAIL_ADDRESS",       # Email
            "PHONE_NUMBER",        # Generic phone
            "IN_PHONE_NUMBER",     # Indian phone
            "IN_AADHAR",           # Aadhar
            "IN_PAN",              # PAN
            "IN_VOTER_ID",         # Voter ID
            "IN_PINCODE",          # PIN code
            "MEDICAL_RECORD",      # Medical records
            "MEDICAL_LICENSE",     # Medical license
            "LEGAL_CASE_NUMBER",   # Legal case numbers
            "CREDIT_CARD",         # Credit cards
            "IBAN_CODE",           # Bank account info
            "NRP",                 # Named Recognizable Person
            "URL",                 # URLs
            "IP_ADDRESS"           # IP addresses
        ]
    
    def _load_spacy_model(self):
        """
        Load spaCy model with GLiNER integration for enhanced NER
        
        Returns:
            spaCy NLP model with GLiNER pipeline
        """
        try:
            # Load base spaCy model
            nlp = spacy.load("en_core_web_sm")
            
            if self.use_gliner:
                try:
                    # Add GLiNER to the pipeline
                    from gliner_spacy.pipeline import GlinerSpacy
                    
                    # Define entity labels for GLiNER to detect
                    # These are in plain English labels that GLiNER understands
                    gliner_labels = [
                        "person", "name", "full name",
                        "address", "location", "city", "state", "country",
                        "phone number", "mobile number", "telephone",
                        "email", "email address",
                        "date", "birth date",
                        "organization", "company",
                        "identity number", "identification",
                        "medical record", "patient id", "hospital",
                        "case number", "court case", "legal",
                        "bank account", "credit card",
                        "license number", "passport number"
                    ]
                    
                    # Add GLiNER component to pipeline
                    nlp.add_pipe(
                        "gliner_spacy",
                        config={
                            "gliner_model": "urchade/gliner_small-v2.1",
                            "labels": gliner_labels,
                            "chunk_size": 250,
                            "style": "ent"
                        }
                    )
                    print("✓ GLiNER successfully integrated with spaCy")
                except ImportError:
                    print("⚠ GLiNER not available, using standard spaCy NER")
                except Exception as e:
                    print(f"⚠ Could not load GLiNER: {e}. Using standard spaCy NER")
            
            return nlp
            
        except OSError:
            print("Error: spaCy model 'en_core_web_sm' not found.")
            print("Please download it with: python -m spacy download en_core_web_sm")
            raise
    
    def analyze(self, text: str, language: str = "en") -> List:
        """
        Analyze text for PII entities
        
        Args:
            text: Input text to analyze
            language: Language code (default: "en")
            
        Returns:
            List of detected PII entities
        """
        results = self.analyzer.analyze(
            text=text,
            language=language,
            entities=self.entity_types
        )
        return results
    
    def anonymize(self, text: str, language: str = "en") -> Dict:
        """
        Anonymize PII in text
        
        Args:
            text: Input text to anonymize
            language: Language code (default: "en")
            
        Returns:
            Dictionary with anonymized text and detected items
        """
        # Analyze for PII
        results = self.analyze(text, language)
        
        # Anonymize
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results
        )
        
        return {
            "original": text,
            "anonymized": anonymized_result.text,
            "detected_entities": [
                {
                    "entity_type": item.entity_type,
                    "text": text[item.start:item.end],
                    "start": item.start,
                    "end": item.end,
                    "score": item.score
                }
                for item in results
            ]
        }
    
    def anonymize_with_custom_operators(self, text: str, language: str = "en") -> Dict:
        """
        Anonymize with custom operators for better readability
        
        Args:
            text: Input text to anonymize
            language: Language code (default: "en")
            
        Returns:
            Dictionary with anonymized text and detected items
        """
        from presidio_anonymizer.entities import OperatorConfig
        
        # Analyze for PII
        results = self.analyze(text, language)
        
        # Define custom operators for different entity types
        operators = {
            "PERSON": OperatorConfig("replace", {"new_value": "[NAME_REDACTED]"}),
            "LOCATION": OperatorConfig("replace", {"new_value": "[LOCATION_REDACTED]"}),
            "IN_AADHAR": OperatorConfig("replace", {"new_value": "[AADHAR_REDACTED]"}),
            "IN_PAN": OperatorConfig("replace", {"new_value": "[PAN_REDACTED]"}),
            "IN_VOTER_ID": OperatorConfig("replace", {"new_value": "[VOTER_ID_REDACTED]"}),
            "IN_PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[PHONE_REDACTED]"}),
            "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[EMAIL_REDACTED]"}),
            "MEDICAL_RECORD": OperatorConfig("replace", {"new_value": "[MEDICAL_ID_REDACTED]"}),
            "LEGAL_CASE_NUMBER": OperatorConfig("replace", {"new_value": "[CASE_NO_REDACTED]"}),
            "IN_PINCODE": OperatorConfig("replace", {"new_value": "[PINCODE_REDACTED]"}),
            "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
        }
        
        # Anonymize with custom operators
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators=operators
        )
        
        return {
            "original": text,
            "anonymized": anonymized_result.text,
            "detected_entities": [
                {
                    "entity_type": item.entity_type,
                    "text": text[item.start:item.end],
                    "start": item.start,
                    "end": item.end,
                    "score": item.score
                }
                for item in results
            ]
        }


def test_indian_pii_anonymization():
    """Test the PII anonymization with Indian sample data using GLiNER + Presidio"""
    
    print("=" * 80)
    print("TESTING INDIAN PII DETECTION AND ANONYMIZATION")
    print("Using: Presidio Analyzer + spaCy + GLiNER NER")
    print("=" * 80)
    
    # Initialize anonymizer with GLiNER support
    print("\n🔧 Initializing PII Anonymizer with GLiNER...")
    anonymizer = IndianPIIAnonymizer(use_gliner=True)
    print("✓ Initialization complete\n")
    
    # Test cases with various Indian PII
    test_cases = [
        # Test Case 1: General personal information
        """
        Name: Rajesh Kumar Sharma
        Address: 45, Nehru Nagar, Indore, Madhya Pradesh 452001
        Email: rajesh.sharma@example.com
        Phone: +91 9876543210
        Aadhar: 1234 5678 9012
        PAN: ABCDE1234F
        Voter ID: ABC1234567
        """,
        
        # Test Case 2: Medical information
        """
        Patient Name: Priya Patel visited Apollo Hospital on January 15, 2024.
        Patient ID: MRN-123456
        Diagnosis: The patient was diagnosed with diabetes and prescribed medication.
        Contact: 8765432109
        Address: Mumbai, Maharashtra 400001
        """,
        
        # Test Case 3: Legal information
        """
        Case No: CRL/2023/12345 filed by Advocate Suresh Singh.
        FIR No: 234/2023 was registered at Police Station, Delhi.
        The accused, Amit Verma (Aadhar: 9876-5432-1098), resides at Bangalore 560001.
        Contact: amit.verma@email.com, Phone: 7654321098
        """,
        
        # Test Case 4: Banking and financial
        """
        Account holder: Deepak Agarwal
        PAN Card: PQRST5678M
        Mobile: 9123456789
        Aadhar: 2345 6789 0123
        Address: Kolkata, West Bengal, PIN: 700001
        """,
        
        # Test Case 5: Mixed comprehensive data
        """
        Application submitted by Neha Reddy (neha.reddy@company.in) on 2024-02-15.
        Aadhar Number: 3456 7890 1234
        PAN: XYZAB9876C
        Voter ID: DEF7654321
        Phone: +91-8899776655
        Residential Address: Plot 123, Hitech City, Hyderabad, Telangana 500081
        Medical History: Patient treated at KIMS Hospital, UHID: 987654
        Legal Case: Involved in Case No: 456/2023
        """
    ]
    
    for i, test_text in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}")
        print('=' * 80)
        print(f"\nORIGINAL TEXT:")
        print(test_text.strip())
        
        # Anonymize with custom operators
        result = anonymizer.anonymize_with_custom_operators(test_text)
        
        print(f"\n{'*' * 80}")
        print(f"ANONYMIZED TEXT:")
        print('*' * 80)
        print(result["anonymized"])
        
        print(f"\n{'-' * 80}")
        print(f"DETECTED ENTITIES ({len(result['detected_entities'])} found):")
        print('-' * 80)
        for entity in sorted(result["detected_entities"], key=lambda x: x["start"]):
            print(f"  • {entity['entity_type']:20s} | '{entity['text']}' (confidence: {entity['score']:.2f})")
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    # Test the anonymization
    test_indian_pii_anonymization()
