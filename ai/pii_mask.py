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
        "AADHAAR": r"\b[2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b",
        "PAN":     r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b",
        "UPI_ID":  r"\b[\w.\-]{2,256}@[a-zA-Z]{2,64}\b",
        "PHONE":   r"\b(?:\+91|91|0)?[5-9][0-9]{9}\b",
        "IFSC":    r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
        "EMAIL":   r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b",
        "BANK_ACC":r"\b[0-9]{9,18}\b",
        "PINCODE": r"\b[1-9][0-9]{5}\b",
    }

    INDIAN_PII_PATTERNS_HINDI = {
        "AADHAAR": r"(?<!\d)[२-९][०-९]{3}\s?[०-९]{4}\s?[०-९]{4}(?!\d)",
        "PHONE":   r"(?<!\d)(?:\+९१|९१|०)?[५-९][०-९]{9}(?!\d)",
        "PINCODE": r"(?<!\d)[१-९][०-९]{5}(?!\d)",
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

    HINDI_FIRST_NAMES = {
        "अमित","अंजलि","अर्जुन","आदिति","आरव","ईशान","कविता","किरण",
        "कृष्णा","गणेश","गीता","गौरव","ज्योति","तरुण","तान्या","दीपक",
        "दिव्या","ध्रुव","नवीन","निखिल","निशा","नीता","नीलम","पंकज",
        "पल्लवी","प्रकाश","पूजा","प्रिया","फातिमा","बाला","मनोज",
        "मनीष","मोहम्मद","यश","रजनीश","रमेश","रवि","राजेश","राधा",
        "राम","रितु","रीना","लता","लक्ष्मी","विजय","विनय","विवेक",
        "विकास","शर्मिला","शशि","शिवानी","शीला","श्वेता","सरिता",
        "सविता","सागर","सान्या","सिमरन","सुनीता","सुरेश","सुमन",
        "स्वाति","हेमंत","हर्ष","रोहित","आकाश","अनुभव","गोपाल",
        "किशोर","दिनेश","नरेश","पंकज","संजय","विनोद","मुकेश",
        "सुनील","कमला","उषा","आशा","रेखा","सीमा","गीता","नेहा",
    }

    HINDI_LAST_NAMES = {
        "अग्रवाल","अली","अंसारी","आचार्य","उपाध्याय","कपूर","कुमार",
        "कौर","खत्री","खान","गांधी","गोस्वामी","गुप्ता","चंद्रशेखर",
        "चतुर्वेदी","चौहान","चोपड़ा","जैन","जोशी","ठाकुर","तिवारी",
        "त्रिपाठी","दास","दुबे","देशमुख","देसाई","नायर","निगम",
        "पंडित","पटेल","पांडे","पिल्लई","प्रधान","बाजाज",
        "बिष्ट","भंडारी","भट्ट","महापात्र","मिश्रा","मुखर्जी","मेनन",
        "मेहता","यादव","रावत","राघवन","रेड्डी","लाल","वर्मा","वशिष्ठ",
        "विक्रम","विश्वकर्मा","व्यास","शर्मा","शुक्ला","श्रीवास्तव",
        "सक्सेना","सिंह","स्वामी",
    }

    INDIAN_ORGS = {
        "IIT","IIT Bombay","IIT Delhi","IIT Kanpur","IIT Kharagpur",
        "IIT Madras","IIT Roorkee","IIT Guwahati","NIT","NIT Trichy",
        "NIT Surathkal","NIT Warangal","IIIT","IIIT Hyderabad",
        "BITS Pilani","BITS","BITSAT",
        "IISC","IISc Bangalore","ISI Kolkata","ISI",
        "AIIMS","AIIMS Delhi","PGI Chandigarh","CMC Vellore",
        "Tata","Tata Motors","Tata Consultancy Services","TCS",
        "Infosys","Wipro","HCL","Tech Mahindra","LTI","Mindtree",
        "Reliance","Reliance Industries","Jio","Airtel","Vodafone",
        "Idea","BSNL","MTNL","Bharat Electronics","BEL","BHEL",
        "ONGC","IOCL","BPCL","HPCL","GAIL","NTPC","Power Grid",
        "Adani","Adani Group","Mahindra","Mahindra & Mahindra",
        "Bajaj","Bajaj Auto","Maruti Suzuki","Hyundai","Toyota",
        "Honda","Tata Steel","JSW Steel","SAIL","Hindalco",
        "HDFC","HDFC Bank","ICICI","ICICI Bank","SBI","State Bank",
        "Axis Bank","Kotak Mahindra","Yes Bank","PNB","Canara Bank",
        "Bank of Baroda","Union Bank","Indian Bank","IDBI",
        "LIC","IRDAI","SEBI","RBI","NSE","BSE","NSDL","CDSL",
        "Google","Microsoft","Amazon","Flipkart","Myntra","Swiggy",
        "Zomato","Ola","Uber","Rapido","PhonePe","Paytm","Google Pay",
        "GPay","BHIM","CRED","PolicyBazaar","Urban Company",
        "Nykaa","Meesho","BYJU'S","Unacademy","Vedantu",
        "MakeMyTrip","IRCTC","RedBus","OYO","BookMyShow",
        "Zee","Star Plus","Colors TV","Sony TV","Times Now",
        "Times of India","Hindustan Times","The Hindu",
        "Indian Railways","ISRO","DRDO","BARC","TIFR",
        "Supreme Court","High Court","Parliament","Rashtrapati Bhavan",
    }

    CASTE_RELIGION_TERMS = {
        "BRAHMIN","BRAHMAN","THAKUR","RAJPUT","JAT","GURJAR","MARATHA",
        "KUNBI","PATIDAR","PATEL","YADAV","KURMI","KOERI","SHARMA",
        "MISHRA","DUBEY","TIWARI","CHAUDHARY","KHATRI","ARORA","BANIYA",
        "VAISHYA","GUPTA","AGARWAL","JAIN","KAYASTHA","BHUMIHAR","TYAGI",
        "SAINI","KASHYAP","MAURYA","PRAJAPATI","NISHAD","BHAT",
        "MUSLIM","HINDU","SIKH","CHRISTIAN","JAIN","BUDDHIST","PARSI",
        "ISLAM","ISLAMIC","DHARMIC","ATHEIST","SPIRITUAL",
        "OBC","SC","ST","GENERAL","EWS","CREAMY","NON-CREAMY",
        "DALIT","ADIVASI","TRIBE","FORWARD","BACKWARD","MINORITY",
        "UPPER CASTE","LOWER CASTE","RESERVED","UNRESERVED",
        "हिंदू","मुसलमान","सिख","ईसाई","बौद्ध","जैन","यादव",
        "ठाकुर","जाट","गुर्जर","मराठा","कुर्मी","कोइरी","चौधरी",
        "अग्रवाल","बनिया","दलित","आदिवासी","पिछड़ा","सामान्य",
    }

    MEDICAL_TERMS = {
        "DIABETES","HYPERTENSION","BLOOD PRESSURE","BP","SUGAR",
        "THYROID","ASTHMA","CANCER","TUMOUR","TUMOR","HEART DISEASE",
        "KIDNEY FAILURE","LIVER CIRRHOSIS","HEPATITIS","TUBERCULOSIS",
        "TB","MALARIA","DENGUE","CHIKUNGUNYA","TYPHOID","CHOLERA",
        "ANAEMIA","ANEMIA","ARTHRITIS","OSTEOPOROSIS","MIGRAINE",
        "EPILEPSY","PARKINSON","ALZHEIMER","DEMENTIA","STROKE",
        "INFARCTION","ATTACK","COVID","CORONA","HIV","AIDS",
        "ULCER","GASTRITIS","ACIDITY","INDIGESTION","CONSTIPATION",
        "PNEUMONIA","BRONCHITIS","SINUSITIS","ALLERGY","ECZEMA",
        "PSORIASIS","DERMATITIS","GLAUCOMA","CATARACT","RETINOPATHY",
        "DEPRESSION","ANXIETY","BIPOLAR","SCHIZOPHRENIA","INSOMNIA",
        "FRACTURE","SPRAIN","DISLOCATION","BURN","WOUND","INFECTION",
        "INSULIN","METFORMIN","ASPIRIN","PARACETAMOL","IBUPROFEN",
        "ANTIBIOTIC","ANTIDEPRESSANT","ANTIHISTAMINE","VACCINE",
        "CHEMOTHERAPY","RADIATION","SURGERY","TRANSPLANT","DIALYSIS",
        "BLOOD TEST","URINE TEST","X-RAY","MRI","CT SCAN","ECG",
        "EEG","SONOGRAPHY","ULTRASOUND","MAMMOGRAPHY","BIOPSY",
        "PATHOLOGY","RADIOLOGY","CARDIOLOGY","NEUROLOGY","ONCOLOGY",
        "ORTHOPAEDICS","PAEDIATRICS","GYNAECOLOGY","DERMATOLOGY",
        "MEDICAL RECORD","MRN","IPD NO","OPD NO","BED NO","WARD NO",
        "INSURANCE NO","POLICY NO","CLAIM NO","HEALTH CARD",
        "डायबिटीज","मधुमेह","हाइपरटेंशन","बीपी","थायराइड",
        "अस्थमा","दमा","कैंसर","टीबी","तपेदिक","मलेरिया",
        "डेंगू","टाइफाइड","हैजा","निमोनिया","बुखार","खांसी",
        "जुकाम","सिरदर्द","बदन दर्द","दस्त","उल्टी","एलर्जी",
        "ऑपरेशन","सर्जरी","इलाज","दवाई","गोली","इंजेक्शन",
        "मरीज","रोगी","अस्पताल","क्लिनिक","डॉक्टर","डॉ.",
        "ब्लड टेस्ट","एक्स-रे","अल्ट्रासाउंड","ईसीजी","एमआरआई",
    }

    ORG_FP_KEYWORDS = {
        "PAN","Aadhaar","ITR","IFSC",        "UPI","UPI ID","KYC","NEFT","RTGS","IMPS",
        "OTP","GST","TDS","TAN","DIN","CIN","LLP","HUF","NRI","FEMA",
        "RBI","SEBI","IRDAI","EPFO","ESIC","PF","EPS","NPS","PPF",
        "FD","RD","SIP","SWP","STP","AML","CAGR",
        "Alexa","Siri","Google Assistant","Cortana","Bixby",
        "WhatsApp","Telegram","Signal","Facebook","Instagram",
        "Snapchat","Twitter","LinkedIn","YouTube","Chrome","Firefox",
        "Safari","Edge","Opera","Android","iOS","Windows","MacOS",
        "Linux","Ubuntu","Debian","Fedora","Python","Java","C++",
        "Monday","Tuesday","Wednesday","Thursday","Friday","Saturday",
        "Sunday","January","February","March","April","May","June",
        "July","August","September","October","November","December",
        "Spring","Summer","Autumn","Winter","Rainy","Monsoon",
        "LPG","CNG","PNG","GST","HRA","LTA","ITDA",
    }

    BANK_ACC_KEYWORDS = {
        "account","ac","a/c","acc","transfer","deposit","credit","debit",
        "neft","rtgs","imps","wire","bank","savings","current","saving",
        "a/c","account no","account number","acc no","acc number",
        "beneficiary","ifsc","branch","fund","payment","salary",
        "remit","transaction","folio",
    }

    AADHAAR_KEYWORDS = {
        "aadhaar","aadhar","uid","unique id","aadhaar number",
        "aadhar number","uidai","biometric","identity",
    }

    RULE_PRIORITY = {
        "AADHAAR": 10,
        "PAN":     10,
        "EMAIL":   10,
        "PHONE":    9,
        "UPI_ID":   8,
        "IFSC":     8,
        "MEDICAL":  7,
        "PINCODE":  7,
        "PERSON":   6,
        "PER":      6,
        "BANK_ACC": 5,
        "CASTE_RELIGION": 5,
        "GPE":      5,
        "LOC":      5,
        "ORG":      4,
    }

    LABEL_MAP = {
        "PERSON":         "NAME_REDACTED",
        "PER":            "NAME_REDACTED",
        "ORG":            "ORG_REDACTED",
        "GPE":            "LOCATION_REDACTED",
        "LOC":            "LOCATION_REDACTED",
        "AADHAAR":        "AADHAAR_REDACTED",
        "PAN":            "PAN_REDACTED",
        "UPI_ID":         "UPI_REDACTED",
        "PHONE":          "PHONE_REDACTED",
        "IFSC":           "IFSC_REDACTED",
        "EMAIL":          "EMAIL_REDACTED",
        "BANK_ACC":       "BANK_REDACTED",
        "PINCODE":        "PINCODE_REDACTED",
        "CASTE_RELIGION": "CASTE_RELIGION_REDACTED",
        "MEDICAL":        "MEDICAL_REDACTED",
    }

    NOT_GPE_WORDS_SPACY = {
        "hai","ho","hain","ka","ki","ke","ko","se","mein","me","par",
        "aur","ya","to","bhi","hi","tha","the","thi","thay",
    }

    NOT_PERSON_WORDS = {
        "person","people","someone","anyone","everyone","nobody",
        "name","your","my","his","her","our","their","its",
        "kyc","pan","aadhaar","aadhar","pin","otp","ifsc","upi",
        "hello","hey","hi","good","morning","evening","night",
        "please","thanks","thank","sorry","okay","ok","yes","no",
        "call","text","email","send","get","set","put","make","do",
        "one","two","three","four","five","six","seven","eight",
        "nine","ten","first","second","third","last","next",
        "mister","mr","mrs","ms","dr","doctor","sir","madam","ma'am",
        "brother","sister","father","mother","uncle","aunt",
        "manager","owner","admin","user","customer","client",
        "colleague","friend","partner","spouse","wife","husband",
        "self","helped","like","reply","provided","joined",
        "works","worked","working","based","located","joined",
        "from","into","about","with","without","through",
        "staff","didi","bhai","bhaiya","boss","sir","madam",
        "mam","teacher","professor","principal","director",
        "chairman","ceo","founder","coach","captain","leader",
        "member","volunteer","representative","agent","officer",
        "inspector","constable","judge","lawyer","advocate",
        "engineer","architect","designer","developer","coder",
        "analyst","consultant","specialist","expert","trainer",
        "instructor","mentor","guide","assistant","secretary",
        "treasurer","auditor","accountant","cashier","teller",
        "guard","watchman","driver","pilot","steward","attendant",
        "nurse","compound","sweeper","peon","clerk","staff",
        "minister","secretary","commissioner","mayor","counselor",
    }

    NOT_GPE_WORDS = {
        "person","people","someone","anyone","everyone","nobody",
        "name","your","my","his","her","our","their","its",
        "kyc","otp","pin","ifsc","upi","aadhaar","aadhar",
        "hello","hey","hi","good","please","thanks","thank",
        "ok","yes","no","maybe","sure","right","left","top",
        "bottom","front","back","side","inside","outside",
        "one","two","three","four","five","six","seven","eight",
        "nine","ten","first","second","third","last","next",
        "house","home","office","room","place","area","zone",
        "section","part","block","sector","phase","stage",
        "street","road","lane","avenue","society","colony",
        "pincode","pin","code","zip","address","location",
        "city","town","village","state","country","district",
        "ward","zone","region","territory","province",
        "from","into","about","with","without","through",
        "works","worked","working","based","located","joined",
        "report","submit","share","provide","update","upload",
        "download","view","check","verify","confirm","review",
        "for","the","and","but","or","nor","not","very",
        "just","only","also","too","yet","so","now","then",
        "here","there","where","when","why","how","what","which",
        "this","that","these","those","all","each","every",
        "some","any","no","none","both","either","neither",
        "self","helped","like","reply","provided",
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
                if self._skip_rule_match(text, match, label):
                    continue
                spans.append(RedactedSpan(
                    start=match.start(), end=match.end(),
                    text=match.group(), label=label, confidence=1.0
                ))
        for label, pattern in self.INDIAN_PII_PATTERNS_HINDI.items():
            for match in re.finditer(pattern, text):
                spans.append(RedactedSpan(
                    start=match.start(), end=match.end(),
                    text=match.group(), label=label, confidence=1.0
                ))
        return spans

    def _context_around(self, text: str, pos: int, window: int = 40) -> str:
        start = max(0, pos - window)
        end = min(len(text), pos + window)
        around = text[start:end].lower()
        return around

    def _skip_rule_match(self, text, match, label):
        if label == "BANK_ACC":
            matched = match.group()
            if len(matched) < 11:
                return True
            phone_pat = self.INDIAN_PII_PATTERNS["PHONE"]
            if re.fullmatch(phone_pat, matched):
                return True
        if label == "AADHAAR":
            if match.start() > 0 and text[match.start() - 1] == "+":
                return True
            context = self._context_around(text, match.start())
            has_aadhaar_kw = any(kw in context for kw in self.AADHAAR_KEYWORDS)
            has_bank_kw = any(kw in context for kw in self.BANK_ACC_KEYWORDS)
            if has_bank_kw and not has_aadhaar_kw:
                return True
        return False

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

        city_lower = {c.lower() for c in self.INDIAN_CITIES}
        caste_lower = {c.lower() for c in self.CASTE_RELIGION_TERMS}
        medical_lower = {m.lower() for m in self.MEDICAL_TERMS}

        all_first = list(self.INDIAN_FIRST_NAMES) + list(self.HINDI_FIRST_NAMES)
        all_last = list(self.INDIAN_LAST_NAMES) + list(self.HINDI_LAST_NAMES)
        all_first_lower = {n.lower() for n in all_first}
        all_last_lower = {n.lower() for n in all_last}

        not_person_lower = {w.lower() for w in self.NOT_PERSON_WORDS}
        not_gpe_lower = {w.lower() for w in self.NOT_GPE_WORDS}

        orgs_lower = {o.lower() for o in self.INDIAN_ORGS}
        orgs_by_first_word = {}
        for org in self.INDIAN_ORGS:
            first_word = org.split()[0].lower()
            orgs_by_first_word.setdefault(first_word, []).append(org.lower())

        idx = 0
        while idx < len(tokens):
            tok = tokens[idx]
            t_start, t_end = raw_positions[idx][1], raw_positions[idx][2]
            clean = tok.strip(".,!?")
            lower = clean.lower()

            org_found = False
            if lower in orgs_by_first_word:
                for candidate in orgs_by_first_word[lower]:
                    candidate_tokens = candidate.split()
                    if idx + len(candidate_tokens) > len(tokens):
                        continue
                    match = True
                    for j, ct in enumerate(candidate_tokens):
                        c_tok = tokens[idx + j].strip(".,!?")
                        if c_tok.lower() != ct:
                            match = False
                            break
                    if match:
                        org_end = raw_positions[idx + len(candidate_tokens) - 1][2]
                        spans.append(RedactedSpan(
                            start=t_start, end=org_end,
                            text=text[t_start:org_end], label="ORG", confidence=0.9
                        ))
                        idx += len(candidate_tokens) - 1
                        org_found = True
                        break

            if org_found:
                idx += 1
                continue

            is_first = lower in all_first_lower and lower not in not_person_lower

            if is_first and idx + 1 < len(tokens):
                next_tok = tokens[idx + 1]
                n_start, n_end = raw_positions[idx + 1][1], raw_positions[idx + 1][2]
                nclean = next_tok.strip(".,!?")
                nlower = nclean.lower()
                if nlower in all_last_lower:
                    spans.append(RedactedSpan(
                        start=t_start, end=n_end,
                        text=text[t_start:n_end], label="PERSON", confidence=0.9
                    ))
                    idx += 1
                elif nlower not in not_person_lower:
                    spans.append(RedactedSpan(
                        start=t_start, end=t_end,
                        text=tok, label="PERSON", confidence=0.85
                    ))
            elif is_first:
                spans.append(RedactedSpan(
                    start=t_start, end=t_end, text=tok, label="PERSON", confidence=0.85
                ))
            elif lower in city_lower and lower not in not_gpe_lower:
                spans.append(RedactedSpan(
                    start=t_start, end=t_end, text=tok, label="GPE", confidence=0.85
                ))
            elif lower in caste_lower:
                spans.append(RedactedSpan(
                    start=t_start, end=t_end, text=tok, label="CASTE_RELIGION", confidence=0.85
                ))
            elif lower in medical_lower:
                spans.append(RedactedSpan(
                    start=t_start, end=t_end, text=tok, label="MEDICAL", confidence=0.85
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

    def _is_known_city(self, text: str) -> bool:
        clean = text.strip(".,!?").lower()
        return clean in {c.lower() for c in self.INDIAN_CITIES}

    def _spacy_spans(self, text: str) -> List[RedactedSpan]:
        if not self.nlp:
            return []
        doc = self.nlp(text)
        spans = []
        for ent in doc.ents:
            if ent.label_ not in self.LABEL_MAP:
                continue
            if self._spacy_span_near_pii(text, ent):
                continue
            if ent.label_ == "ORG" and ent.text.strip() in self.ORG_FP_KEYWORDS:
                continue
            if ent.label_ in ("ORG", "PERSON") and self._is_known_city(ent.text):
                continue
            if ent.label_ == "PERSON":
                tokens = ent.text.lower().split()
                if any(t.strip(".,!?") in self.NOT_PERSON_WORDS for t in tokens):
                    continue
            if ent.label_ == "GPE" and ent.text.strip().lower() in self.NOT_GPE_WORDS | self.NOT_GPE_WORDS_SPACY:
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