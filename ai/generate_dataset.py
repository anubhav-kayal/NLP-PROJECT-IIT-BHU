import random
import json
import math
import string

random.seed(42)

INDIAN_FIRST_NAMES = [
    "Vikash", "Rahul", "Priya", "Anubhav", "Deepak", "Sunita", "Rajesh", "Pooja",
    "Amit", "Neha", "Sanjay", "Kavita", "Arjun", "Meera", "Rohit", "Anjali",
    "Vivek", "Smita", "Suresh", "Geeta", "Mahesh", "Rekha", "Naresh", "Savita",
    "Ramesh", "Usha", "Dinesh", "Lata", "Pankaj", "Nisha", "Vinay", "Asha",
    "Mohammad", "Fatima", "Abdul", "Zoya", "Imran", "Gurpreet", "Harpreet",
    "Manpreet", "Jaspreet", "Simran", "Venkatesh", "Lakshmi", "Krishnamurthy",
    "Padmavathi", "Ravi", "Subramanian", "Anand", "Srinivasan", "Bharathi",
    "Ganesh", "Mehta", "Verma", "Singh", "Gupta", "Ali", "Ansari", "Khan",
    "Joshi", "Devi", "Kaur", "Aditi", "Ishaan", "Aarav", "Sanya", "Armaan",
    "Kritika", "Harsh", "Tanya", "Nikhil", "Shreya", "Akash", "Swati", "Manoj",
    "Divya", "Prakash", "Kiran", "Naveen", "Sudha", "Vijay", "Lalita", "Aman",
    "Ritu", "Tarun", "Jyoti", "Hemant", "Pallavi", "Gaurav", "Shweta", "Dhruv",
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Das", "Patel", "Reddy",
    "Nair", "Menon", "Iyer", "Deshmukh", "Joshi", "Kulkarni", "Desai", "Pandey",
    "Mishra", "Tiwari", "Dubey", "Chaturvedi", "Saxena", "Srivastava", "Agarwal",
    "Jain", "Mehta", "Shah", "Kapoor", "Malhotra", "Chopra", "Bhatia", "Arora",
    "Sood", "Bajaj", "Kohli", "Choudhary", "Khatri", "Thakur", "Chauhan",
    "Singh Rathore", "Yadav", "Maurya", "Shukla", "Tripathi", "Pandit", "Rawat",
    "Negi", "Bisht", "Rana", "Bhandari", "Pradhan", "Mahapatra", "Swain",
    "Naidu", "Pillai", "Mohan", "Chandrasekhar", "Subramaniam", "Raghavan",
    "Venkatesan", "Ranganathan", "Varadharajan",
]

UPI_HANDLES = ["paytm", "okaxis", "okicici", "ybl", "ibl", "axl", "payu", "upi", "apl", "idfcbank", "icici", "sbi", "hdfc", "kotak", "bob", "pnb", "unionbankofindia", "canara", "dbs", "freecharge", "mobikwik", "phonepe", "googlepay", "amazonpay"]
UPI_PREFIXES = [
    "vikash.k", "rahul_12", "priya.sharma", "anubhav", "deepak88", "sunita123",
    "rajesh_verma", "pooja.gupta", "amit.singh", "neha.k", "sanjay_m", "kavita_12",
    "arjun.nair", "meera.iyer", "rohit06", "anjali_deshmukh", "vivek.joshi",
    "smita.pandey", "suresh.mishra", "geeta.tiwari", "mahesh.dubey", "rekha.saxena",
    "naresh.srivastava", "savita.agarwal", "ramesh.jain", "usha.mehta", "dinesh.shah",
    "lata.kapoor", "pankaj.malhotra", "nisha.chopra", "vinay.bhatia", "asha.arora",
    "mohammad.ali", "fatima.ansari", "abdul.khan", "zoya.k", "imran.hussain",
    "gurpreet.singh", "harpreet.kaur", "manpreet_s", "jaspreet_d", "simran123",
    "venkatesh.r", "lakshmi.nair", "krishnamurthy", "padmavathi", "ravi.shankar",
]

AADHAAR_SEEDS = [234567890123, 345678901234, 456789012345, 567890123456, 678901234567, 789012345678, 890123456789, 901234567890, 234567890124, 345678901235, 456789012346,
    876543210987, 765432109876, 654321098765, 543210987654, 432109876543, 321098765432, 210987654321, 998877665544, 887766554433, 776655443322, 665544332211]
PAN_SEEDS = ["ABCDE1234F", "BCDFE5678G", "CDEFG6789H", "GHIJK8901K", "HIJKL9012L", "IJKLM0123M", "JKLMN1234N", "KLMNO2345O", "LMNOP3456P", "MNOPQ4567Q", "NOPQR5678R", "OPQRS6789S",
    "PQRST7890T", "QRSTU8901U", "RSTUV9012V", "STUVW0123W", "TUVWX1234X", "UVWXY2345Y", "VWXYZ3456Z", "WXYZA4567A", "XYZAB5678B", "YZABC6789C", "ZABCD7890D", "ABCDE8901E",
    "FGHIJ2345K", "KLMNO6789P", "PQRST1234U", "UVWXY5678Z", "ABCDE9012F", "FGHIJ3456L", "KLMNO7890Q", "PQRST2345V", "UVWXY6789A"]
PHONE_SEEDS = [9876543210, 9988776655, 9876543211, 9876543212, 7766554433, 8877665544, 9988776644, 9876543200, 8765432109, 7654321098, 6543210987, 5432109876,
    9876543120, 8899001122, 9765432100, 9900112233, 7788996655, 7788990011, 9988776640, 8877665533, 7766554422, 8899112233, 9900223344]
IFSC_SEEDS = ["HDFC0001234", "SBIN0001234", "ICIC0002345", "PUNB0001234", "BARB0VJHELL", "SBIN0000456", "HDFC0005678", "ICIC0007890", "AXIS0001234", "KOTB0000654",
    "YESB0000123", "UBIN0009876", "CBIN0001234", "CANB0005678", "IOBA0001234", "SYNB0001234", "FDRL0001234", "DCBL0001234",
    "DEUT0001234", "HSBC0001234", "SCBL0001234", "CITI0001234", "STBP0001234"]
EMAIL_LOCAL_PARTS = ["vikash.kayal", "rahul88", "priya.sharma", "anubhav.k", "deepak.kumar", "sunita.verma", "rajesh.singh", "pooja.gupta", "amit.jain", "neha.kapoor",
    "sanjay.malhotra", "kavita.arora", "arjun.mehta", "meera.shah", "rohit.sharma", "anjali.verma", "vivek.singh", "smita.joshi", "suresh.kulkarni", "geeta.desai",
    "mahesh.pandey", "rekha.mishra", "naresh.tiwari", "savita.dubey", "ramesh.chaturvedi", "usha.saxena", "dinesh.srivastava", "lata.agarwal", "pankaj.s77", "nisha_45",
    "contact.vinay", "asha.12", "mohammad.ali", "fatima.ansari", "abdul.k", "zoya.reddy", "imran.khan", "gurpreet.s", "harpreet.kaur", "venkatesh.iit",
    "lakshmi.nair", "krishna.m", "ravi.shankar", "anand.s", "bharathi.rao"]
DOMAINS = ["gmail.com", "yahoo.co.in", "rediffmail.com", "outlook.com", "iitbhu.ac.in", "hotmail.com", "protonmail.com", "zoho.com", "ymail.com", "rocketmail.com",
    "icloud.com", "godaddy.com", "mygov.in", "nic.in", "gov.in", "ac.in", "edu.in", "co.in", "in.com", "vsnl.net"]

LOCATIONS = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune",
    "Ahmedabad", "Jaipur", "Lucknow", "Varanasi", "Patna", "Bhopal", "Indore",
    "Chandigarh", "Amritsar", "Nagpur", "Surat", "Thane", "Allahabad", "Ranchi",
    "Guwahati", "Coimbatore", "Kochi", "Thiruvananthapuram", "Bhubaneswar",
    "Jodhpur", "Udaipur", "Goa", "Shimla", "Dehradun", "Agra", "Mathura",
    "Gaya", "Bodh Gaya", "Sarnath", "Haridwar", "Rishikesh", "Ayodhya", "Meerut",
    "Gurgaon", "Noida", "Faridabad", "Ghaziabad", "Kolkata", "Mysore", "Mangalore",
    "Vadodara", "Rajkot", "Jamnagar", "Raipur", "Bilaspur", "Jabalpur", "Ujjain",
]
PINCODES = list(range(110001, 110098)) + list(range(400001, 400091)) + list(range(700001, 700101)) + list(range(560001, 560081)) + list(range(600001, 600091)) + list(range(500001, 500091)) + [221005, 226001, 302001, 380001, 201301, 411001, 682001, 160001, 734001, 800001, 790001, 190001, 144001, 395001, 305001, 173001, 248001, 122001, 281001, 462001]

ORGS = [
    "Google", "Microsoft", "Amazon", "Flipkart", "Myntra", "Swiggy", "Zomato",
    "Ola", "Uber", "Paytm", "PhonePe", "Google Pay", "BharatPe", "CRED",
    "Tata Consultancy Services", "Infosys", "Wipro", "HCL Technologies",
    "Reliance Industries", "Bharti Airtel", "Jio", "Vodafone Idea", "BSNL",
    "State Bank of India", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra",
    "Punjab National Bank", "Bank of Baroda", "Canara Bank", "Union Bank of India",
    "Indian Institute of Technology", "IIT Bombay", "IIT Delhi", "IIT Kanpur",
    "IIT Kharagpur", "IIT Roorkee", "IIT Guwahati", "IIT BHU", "BHU",
    "Delhi University", "JNU", "Jamia Millia Islamia", "AMU", "BITS Pilani",
    "NIT Trichy", "NIT Surathkal", "IIM Ahmedabad", "IIM Bangalore", "IIM Calcutta",
    "AIIMS Delhi", "PGI Chandigarh", "CMC Vellore",
]

HINGLISH_TEMPLATES_SINGLE = [
    "Mera {pii} {verb} hai",
    "Mujhe {pii} {verb} hai",
    "Apna {pii} {verb} do",
    "Maine {pii} {verb} liya",
    "Unhone {pii} {verb} diya",
    "Sir ne {pii} {verb} kaha",
    "Madam ka {pii} {verb} hai",
    "Bhai ka {pii} {verb} karo",
    "Didi ka {pii} {verb} hai",
    "Uncle ne {pii} {verb} manga",
    "Mera dost ka {pii} {verb} hai",
    "Teacher ne {pii} {verb} kaha",
    "Manager ne {pii} {verb} diya",
    "Client ka {pii} {verb} check karo",
    "Patient ka {pii} {verb} update karo",
    "Customer ka {pii} {verb} verify karo",
    "Worker ka {pii} {verb} register karo",
    "Staff ka {pii} {verb} collect karo",
]

HINGLISH_TEMPLATES_DOUBLE = [
    "{name} ka {pii} {verb} hai aur {pii2} {verb2} hai",
    "Maine {name} se {pii} {verb} aur {pii2} {verb2}",
    "{name} ne {pii} {verb} diya aur {pii2} bhi {verb2}",
    "{name} ka {pii} and {pii2} dono verify karo",
    "{name} se {pii} aur {pii2} mangwao",
]

HINGLISH_CONTEXT = [
    "kal", "aaj", "abhi", "subah", "shaam", "raat ko", "dopahar mei",
    "office mein", "ghar par", "school mein", "hospital mein", "bank mein",
    "market mein", "station par", "airport par",
]

ENGLISH_TEMPLATES_SINGLE = [
    "My {pii} is {pii_val}",
    "Please note my {pii} {pii_val}",
    "Could you please share your {pii}",
    "The {pii} for this transaction is {pii_val}",
    "I need your {pii} for verification",
    "Your {pii} has been updated to {pii_val}",
    "Please provide your {pii} as {pii_val}",
    "The registered {pii} is {pii_val}",
    "Kindly share your {pii} details",
    "For KYC, please submit your {pii}",
    "Your account {pii} has been changed to {pii_val}",
    "The {pii} provided is {pii_val}",
    "I have noted your {pii} as {pii_val}",
    "We verified your {pii} as {pii_val}",
    "Confirm your {pii} which is {pii_val}",
    "The system shows your {pii} as {pii_val}",
    "Enter your {pii} which is {pii_val}",
    "Update your {pii} to {pii_val}",
    "The {pii} on record is {pii_val}",
    "Please mention your {pii} as {pii_val}",
]

ENGLISH_TEMPLATES_DOUBLE = [
    "My {pii} is {pii_val} and {pii2} is {pii_val2}",
    "My {pii} {pii_val} and {pii2} {pii_val2} are registered",
    "Please update my {pii} to {pii_val} and {pii2} to {pii_val2}",
    "The {pii} {pii_val} and {pii2} {pii_val2} are for the same account",
    "I need to update my {pii} {pii_val} along with {pii2} {pii_val2}",
    "Both my {pii} {pii_val} and {pii2} {pii_val2} need verification",
    "Please confirm {pii} {pii_val} and {pii2} {pii_val2}",
    "The registered {pii} is {pii_val} and {pii2} is {pii_val2}",
    "I changed my {pii} to {pii_val} and {pii2} to {pii_val2}",
    "For KYC, my {pii} is {pii_val} and {pii2} is {pii_val2}",
]

NO_PII_SENTENCES = [
    "The weather is nice today, it reminds me of my trip to the hills last winter.",
    "Can you please turn on the lights in the living room?",
    "I need to buy groceries from the store near my house.",
    "What time does the meeting start tomorrow morning?",
    "Please set an alarm for 6 AM.",
    "The movie we watched last night was really interesting.",
    "I am feeling hungry, let us order some food.",
    "Can you play some music while I work?",
    "The traffic was terrible on my way to work today.",
    "I need to finish this report by evening.",
    "The coffee at this cafe is excellent.",
    "How was your day at the office?",
    "Please book a cab for me to the airport.",
    "I am going to the market to buy some vegetables.",
    "The internet connection is very slow today.",
    "Can you help me with this assignment?",
    "What is the capital of India?",
    "The train to Delhi departs at 9 PM.",
    "I love reading books on philosophy.",
    "Please remind me to call my friend tomorrow.",
    "The sunset at Marine Drive is beautiful.",
    "Can you check the weather forecast for this weekend?",
    "I need to recharge my mobile phone with some data.",
    "What is the recipe for butter chicken?",
    "The garden needs to be watered every morning.",
    "Please turn down the volume on the television.",
    "I am learning Python programming these days.",
    "The flight to Bangalore has been delayed.",
    "Can you send me the presentation slides?",
    "I need to book a hotel room for three nights.",
    "What time does the pharmacy open on Sunday?",
    "The children are playing in the park outside.",
    "Please check the tire pressure in my car.",
    "I want to learn how to play the guitar.",
    "The museum opens at 10 AM on weekdays.",
    "Can you recommend a good restaurant nearby?",
    "I need to visit the bank to update my passbook.",
    "The package has been delivered to your address.",
    "Please schedule a dentist appointment for next week.",
    "What is the exchange rate for US dollars today?",
    "The washing machine is not working properly.",
    "Can you help me move this furniture?",
    "I am planning a trip to Kerala next month.",
    "The laptop battery needs to be replaced.",
    "Please send me the agenda for the conference.",
    "The street dogs in our area are very friendly.",
    "I need to file my income tax returns this week.",
    "Can you teach me how to make chai?",
    "The graduation ceremony is next Saturday.",
    "I am taking a break from social media for a month.",
    "We should visit the zoo this weekend.",
    "Can you fix the leaking tap in the kitchen?",
    "The new policy will be implemented from next quarter.",
    "I need to change the password on my laptop.",
    "What are your plans for the holiday season?",
    "The office will remain closed on Republic Day.",
    "Can you pick me up from the railway station?",
    "I am practicing yoga every morning now.",
    "The exam results will be announced next week.",
    "Please add milk, eggs, and bread to the shopping list.",
    "The festival celebrations will start from tomorrow.",
    "Can you translate this document to Hindi?",
    "I need to renew my passport before the trip.",
    "The air conditioner is making a strange noise.",
    "Please prepare a summary of today's meeting.",
    "I am going for a walk in the park.",
    "The library has a great collection of science fiction.",
    "Can you book two tickets for the concert?",
    "I need to clean my desk and organize the papers.",
    "The construction work on the new bridge is almost done.",
    "Please check if the door is locked before leaving.",
    "I am attending a workshop on data science next week.",
    "The cake you baked was absolutely delicious.",
    "Can you drop the kids at school on your way?",
    "I need to buy a gift for my friend's wedding.",
    "The new software update has a lot of new features.",
    "Please turn off the lights when you leave the room.",
    "I am going to the gym after work today.",
    "The experiment results were better than expected.",
    "Can you water the plants while I am away?",
    "I need to submit the project report by Friday.",
    "The neighborhood watch meeting is at 7 PM.",
    "Please check the expiration date on the milk carton.",
    "I am participating in a marathon next month.",
    "The lecture hall is on the third floor of the building.",
    "Can you charge my phone for me?",
    "I need to sort out the insurance papers for my car.",
    "The kite festival is celebrated with great enthusiasm.",
    "Please draft an email to the client regarding the proposal.",
    "I am trying to reduce my screen time before bed.",
    "The train journey from Delhi to Varanasi is scenic.",
    "Can you reserve a table for dinner tonight?",
    "I need to find a plumber to fix the bathroom fittings.",
    "The annual day function will be held in the auditorium.",
    "Please check the spelling in the document before printing.",
    "I am thinking of adopting a pet from the shelter.",
    "The meeting has been rescheduled to next Tuesday.",
    "Can you explain the concept of machine learning briefly?",
    "I need to buy stationery supplies for the office.",
    "The sunrise at the ghats is a mesmerizing sight.",
    "Please ensure the windows are closed before it rains.",
    "I am learning to cook traditional dishes from my grandmother.",
    "The football match ended in a draw.",
    "Can you recommend a good book for improving vocabulary?",
]
NO_PII_USE_CASE = [
    "Alexa play some music",
    "Hey Google what is the weather today",
    "Turn on the bedroom light",
    "Set a timer for ten minutes",
    "What time is it in Tokyo right now",
    "Play my morning playlist",
    "Increase the volume to 40 percent",
    "What is the news today",
    "Add eggs to my shopping list",
    "Remind me to call mom at 7 pm",
    "How many steps did I walk today",
    "What is the capital of France",
    "Tell me a joke",
    "What is the stock price of Reliance",
    "Open the garage door",
    "Lock the front door",
    "What is the meaning of serendipity",
    "Show me photos from last Diwali",
    "Navigate to the nearest petrol pump",
    "What is the score of the India match",
    "How do you say thank you in Japanese",
    "What is the recipe for biryani",
    "Send a message to Rohan saying I will be late",
    "Schedule a meeting for tomorrow at 3 PM",
    "Turn off the fan in the living room",
]

PERSON_CONTEXT_1 = [
    "Call {name} right now please",
    "Hey Alexa call {name}",
    "Please call {name} on the phone",
    "I need to contact {name} urgently",
    "Can you find {name} in the directory",
    "Message {name} that I am on my way",
    "Send a WhatsApp to {name}",
    "Where is {name} right now",
    "Tell {name} I will call them back",
    "Get me the number of {name}",
]
PERSON_CONTEXT_2 = [
    "My friend {name} is a doctor",
    "Meet my colleague {name}",
    "This is {name} my brother",
    "{name} is coming to the party",
    "I am going with {name} to the market",
    "{name} works at Google now",
    "I met {name} yesterday at the cafe",
    "{name} is the project manager",
    "Our team lead {name} approved it",
    "{name} helped me with the project",
    "Dr. {name} will see you now",
    "Professor {name} teaches mathematics",
    "Mr. {name} is our new neighbor",
    "Mrs. {name} invited us for dinner",
    "{name} is handling the client account",
]
PERSON_CONTEXT_3 = [
    "Call Dr. {name} and ask about the appointment time",
    "Please connect me to Mr. {name} in the HR department",
    "I need to speak with {name} regarding the invoice",
    "Can you transfer this call to {name} please",
    "{name} from the IT team will help you with the setup",
    "The letter is addressed to Mrs. {name}",
    "Please forward this email to {name}",
    "{name} is the point of contact for this project",
    "I have a meeting scheduled with {name} at 2 PM",
    "The feedback from {name} was very positive",
]

AADHAAR_CONTEXT = [
    "My Aadhaar number is {aadhaar}",
    "For KYC my Aadhaar is {aadhaar}",
    "Please verify my Aadhaar {aadhaar}",
    "The Aadhaar I provided is {aadhaar}",
    "Kindly use Aadhaar {aadhaar} for verification",
    "I registered with Aadhaar {aadhaar}",
    "Aadhaar number {aadhaar} is linked to my account",
    "My Aadhaar {aadhaar} has been submitted for verification",
    "Please update my Aadhaar to {aadhaar}",
    "The Aadhaar on file is {aadhaar}",
    "Aadhaar {aadhaar} is already linked to this number",
    "I forgot my Aadhaar number it is {aadhaar}",
    "Enter Aadhaar {aadhaar} in the form",
    "Sending Aadhaar {aadhaar} for eKYC",
    "Use Aadhaar {aadhaar} for the LPG subsidy",
]

PAN_CONTEXT = [
    "My PAN card number is {pan}",
    "For income tax my PAN is {pan}",
    "Please use PAN {pan} for the transaction",
    "The PAN I provided is {pan}",
    "PAN {pan} is linked to my account",
    "I have submitted PAN {pan} for ITR filing",
    "My PAN {pan} is already registered",
    "For TDS deduction use PAN {pan}",
    "Please update PAN to {pan} in the records",
    "The PAN on my account is {pan}",
    "I need to link PAN {pan} with Aadhaar",
    "PAN card {pan} is with the HR department",
    "My salary account has PAN {pan}",
    "The auditor asked for my PAN which is {pan}",
    "PAN {pan} is required for the mutual fund investment",
    "Tax returns filed with PAN {pan} last year",
    "GST registration uses my PAN {pan}",
    "Business partnership deed includes PAN {pan}",
]

PHONE_CONTEXT = [
    "My mobile number is {phone}",
    "Call me on {phone}",
    "My phone number is {phone}",
    "Please contact me at {phone}",
    "You can reach me on {phone}",
    "The registered number is {phone}",
    "Please call {phone} for more details",
    "My WhatsApp is also {phone}",
    "Send a message to {phone}",
    "Contact customer care at {phone}",
    "The helpline number is {phone}",
    "For emergencies dial {phone}",
    "My alternate number is {phone}",
    "Use {phone} to reach the support team",
    "The billing department can be reached at {phone}",
    "Our office number is {phone}",
    "Please verify your mobile {phone}",
    "OTP has been sent to {phone}",
    "The delivery boy will call at {phone}",
    "You can SMS your complaint to {phone}",
]

UPI_CONTEXT = [
    "My UPI ID is {upi}",
    "Send money to {upi}",
    "Pay via {upi}",
    "Transfer to {upi}",
    "My payment address is {upi}",
    "Please make the payment to {upi}",
    "Send the amount to {upi}",
    "The UPI for this account is {upi}",
    "Use {upi} for the transaction",
    "My Google Pay is {upi}",
    "Pay using {upi}",
    "You can transfer to {upi}",
    "The vendor UPI is {upi}",
    "Please send funds to {upi}",
    "My brother UPI ID is {upi}",
    "For refund use {upi}",
    "Split the bill through {upi}",
    "Collect payment via {upi}",
    "My UPI handle is {upi}",
    "The merchant UPI ID is {upi}",
]

IFSC_CONTEXT = [
    "The IFSC code is {ifsc}",
    "My branch IFSC is {ifsc}",
    "Use IFSC {ifsc} for the transfer",
    "The bank IFSC is {ifsc}",
    "Please use IFSC {ifsc} for NEFT",
    "IFSC {ifsc} is for my branch",
    "For RTGS use IFSC {ifsc}",
    "The IFSC provided is {ifsc}",
    "Our branch IFSC code is {ifsc}",
    "Please confirm IFSC {ifsc}",
    "The IFSC on the cheque is {ifsc}",
    "Use {ifsc} for the IMPS transfer",
    "My salary account IFSC is {ifsc}",
    "The IFSC printed is {ifsc}",
    "I need IFSC {ifsc} for the online transfer",
]

EMAIL_CONTEXT = [
    "My email ID is {email}",
    "Send the documents to {email}",
    "Please email me at {email}",
    "You can reach me at {email}",
    "The invoice should go to {email}",
    "My official email is {email}",
    "Contact me via {email}",
    "Please forward to {email}",
    "The report was sent to {email}",
    "Register with your email {email}",
    "Send a copy to {email}",
    "Use {email} for the newsletter",
    "My work email is {email}",
    "The confirmation will go to {email}",
    "Please update my email to {email}",
    "I prefer communication via {email}",
    "The team email is {email}",
    "For support write to {email}",
    "All notifications go to {email}",
    "My recovery email is {email}",
]

BANK_ACC_CONTEXT = [
    "My bank account number is {bank}",
    "The account number is {bank}",
    "Please transfer to account {bank}",
    "Deposit into account {bank}",
    "My savings account is {bank}",
    "The beneficiary account is {bank}",
    "Credit to account {bank}",
    "Account {bank} is for salary",
    "The refund will go to {bank}",
    "Please use account {bank} for the wire",
    "My current account number is {bank}",
    "Deposit funds to account {bank}",
    "The vendor account is {bank}",
    "I hold a joint account {bank}",
    "NEFT to account number {bank}",
]

PINCODE_CONTEXT = [
    "The pincode is {pincode}",
    "My area pincode is {pincode}",
    "Please use pincode {pincode}",
    "The postal code is {pincode}",
    "Our office pincode is {pincode}",
    "The delivery address pincode is {pincode}",
    "Pincode {pincode} is near the station",
    "My home pincode is {pincode}",
    "The branch pincode is {pincode}",
    "Please verify the pincode {pincode}",
    "Send it to pincode {pincode} area",
    "The pin code for this locality is {pincode}",
]

ORGANIZATION_CONTEXT = [
    "I work at {org}",
    "My company is {org}",
    "I am from {org}",
    "{org} is hiring for multiple positions",
    "The project is with {org}",
    "Our partner is {org}",
    "I have an interview at {org}",
    "{org} launched a new product",
    "The campus of {org} is huge",
    "Training at {org} was excellent",
    "I got an offer from {org}",
    "{org} has a great work culture",
    "The conference was at {org}",
    "My collaboration with {org} was fruitful",
    "I am consulting for {org}",
]

LOCATION_CONTEXT = [
    "I live in {loc}",
    "I am from {loc}",
    "The office is in {loc}",
    "I am going to {loc} next week",
    "My hometown is {loc}",
    "The conference is in {loc}",
    "I moved to {loc} last year",
    "The meeting is in {loc}",
    "Our headquarters is in {loc}",
    "I am visiting {loc} for work",
    "The college is located in {loc}",
    "My family lives in {loc}",
    "The branch office is in {loc}",
    "I studied in {loc} for five years",
    "The flight lands in {loc} at 8 PM",
]

MIXED_PARAGRAPHS = [
    "Hi this is {name}. My Aadhaar number is {aadhaar} and my PAN is {pan}. You can reach me at {phone} or email me at {email}. My UPI ID for payments is {upi}. I live in {loc} and work at {org}.",
    "Customer {name} with Aadhaar {aadhaar} and PAN {pan} has requested an account update. Registered mobile {phone} and email {email}. The IFSC for their branch is {ifsc} and account number is {bank}. Correspondence address pincode is {pincode}.",
    "Dear Sir/Madam, I {name} am submitting my documents for KYC verification. My Aadhaar is {aadhaar} and PAN is {pan}. My contact number is {phone} and my email is {email}. I reside in {loc} near the {org} office. My bank details are IFSC {ifsc} and account {bank}.",
    "Patient {name} admitted to hospital. Aadhaar {aadhaar} for identification. Contact {phone} for emergency. Email {email} for reports. Insurance linked to PAN {pan}. Residence in {loc} pincode {pincode}. Payment via UPI {upi}. Bills to account {bank} IFSC {ifsc}.",
    "Student {name} enrolled in course. Aadhaar {aadhaar} submitted. Parent contact {phone}. Email {email} for correspondence. Address in {loc} pincode {pincode}. Fee payment via UPI {upi}. Bank account {bank} with IFSC {ifsc} for refunds. PAN {pan} on record.",
    "New employee {name} joining {org} in {loc}. Aadhaar {aadhaar} and PAN {pan} submitted for background check. Personal email {email} and mobile {phone}. Salary account {bank} with IFSC {ifsc}. UPI {upi} for expense reimbursements. Home pincode {pincode}.",
    "Vendor {name} registration form. Aadhaar {aadhaar} PAN {pan}. Business location {loc} pincode {pincode}. Payment via NEFT to account {bank} IFSC {ifsc}. UPI {upi} for small payments. Contact {phone} and email {email} for purchase orders. GST linked to PAN {pan}.",
    "Tax filing for {name} PAN {pan}. Aadhaar {aadhaar} linked. Refund to account {bank} IFSC {ifsc}. Contact {phone} and email {email}. Address {loc} pincode {pincode}. Previous year returns filed from this location. UPI {upi} used for tax payment.",
]

PII_TYPES = {
    "PERSON": lambda: random.choice(INDIAN_FIRST_NAMES) + " " + random.choice(INDIAN_LAST_NAMES),
    "AADHAAR": lambda: format_number(random.choice(AADHAAR_SEEDS), (4,4,4)),
    "PAN": lambda: random.choice(PAN_SEEDS),
    "PHONE": lambda: format_phone(random.choice(PHONE_SEEDS)),
    "UPI_ID": lambda: random.choice(UPI_PREFIXES) + "@" + random.choice(UPI_HANDLES),
    "IFSC": lambda: random.choice(IFSC_SEEDS),
    "EMAIL": lambda: random.choice(EMAIL_LOCAL_PARTS) + "@" + random.choice(DOMAINS),
    "BANK_ACC": lambda: str(random.randint(10**11, 10**12 - 1)),
    "PINCODE": lambda: str(random.choice(PINCODES)),
    "ORG": lambda: random.choice(ORGS),
    "GPE": lambda: random.choice(LOCATIONS),
}

def format_number(num, groups):
    s = str(num)
    result = []
    idx = 0
    for g in groups:
        result.append(s[idx:idx+g])
        idx += g
    return " ".join(result)

def format_phone(num):
    s = str(num)
    if random.random() < 0.3:
        return "+91" + s
    elif random.random() < 0.5:
        return "0" + s
    return s

HINGLISH_VERBS = ["hai", "diya", "liya", "karo", "check karo", "submit karo", "manga", "bhejo", "dalo", "rakho", "likho", "do", "lo", "dikhao"]

def make_hinglish(pii, pii_val, label):
    temp = random.choice(HINGLISH_TEMPLATES_SINGLE)
    verb = random.choice(HINGLISH_VERBS)
    ctx = random.choice(HINGLISH_CONTEXT)
    if random.random() < 0.4:
        template = f"{ctx} " + temp
    else:
        template = temp
    if label == "PERSON":
        text = template.format(pii="", verb=verb).replace("  ", " ").strip()
        text = text.replace("   ", " ")
        text = text.replace(" ka  hai", " ka naam " + pii_val + " hai")
        text = text.replace(" ne  ", " ne " + pii_val + " ")
        text = text.replace(" ka  ", " ka " + pii_val + " ")
        if "naam" not in text and pii_val not in text:
            text = random.choice(HINGLISH_CONTEXT) + " " + pii_val + " " + verb
        return text
    text = template.format(pii=pii_val, verb=verb)
    return text

def make_hinglish_double(items):
    if len(items) < 2:
        return make_hinglish(items[0][0], items[0][1], items[0][0])
    temp = random.choice(HINGLISH_TEMPLATES_DOUBLE)
    name = random.choice(INDIAN_FIRST_NAMES) + " " + random.choice(INDIAN_LAST_NAMES)
    i1, i2 = items[0], items[1]
    text = temp.format(name=name, pii=i1[1], pii2=i2[1])
    return text

def make_english(pii, pii_val, label):
    templates = random.choice(ENGLISH_TEMPLATES_SINGLE)
    if label == "PERSON":
        text = templates.format(pii=pii.lower(), pii_val=pii_val)
        context = random.choice(PERSON_CONTEXT_2 + PERSON_CONTEXT_3)
        if random.random() < 0.5:
            return context.format(name=pii_val)
        return text
    elif label == "AADHAAR":
        ctx = random.choice(AADHAAR_CONTEXT)
        return ctx.format(aadhaar=pii_val)
    elif label == "PAN":
        ctx = random.choice(PAN_CONTEXT)
        return ctx.format(pan=pii_val)
    elif label == "PHONE":
        ctx = random.choice(PHONE_CONTEXT)
        return ctx.format(phone=pii_val)
    elif label == "UPI_ID":
        ctx = random.choice(UPI_CONTEXT)
        return ctx.format(upi=pii_val)
    elif label == "IFSC":
        ctx = random.choice(IFSC_CONTEXT)
        return ctx.format(ifsc=pii_val)
    elif label == "EMAIL":
        ctx = random.choice(EMAIL_CONTEXT)
        return ctx.format(email=pii_val)
    elif label == "BANK_ACC":
        ctx = random.choice(BANK_ACC_CONTEXT)
        return ctx.format(bank=pii_val)
    elif label == "PINCODE":
        ctx = random.choice(PINCODE_CONTEXT)
        return ctx.format(pincode=pii_val)
    elif label == "ORG":
        ctx = random.choice(ORGANIZATION_CONTEXT)
        return ctx.format(org=pii_val)
    elif label == "GPE":
        ctx = random.choice(LOCATION_CONTEXT)
        return ctx.format(loc=pii_val)
    return templates.format(pii=pii.lower(), pii_val=pii_val)

def make_english_double(items):
    if len(items) < 2:
        return make_english(items[0][0], items[0][1], items[0][0])
    temp = random.choice(ENGLISH_TEMPLATES_DOUBLE)
    i1, i2 = items[0], items[1]
    label_map1 = {"PERSON": "name", "AADHAAR": "Aadhaar", "PAN": "PAN", "PHONE": "phone", "UPI_ID": "UPI ID", "IFSC": "IFSC", "EMAIL": "email", "BANK_ACC": "bank account", "PINCODE": "pincode", "ORG": "organisation", "GPE": "location"}
    label_map2 = {"PERSON": "name", "AADHAAR": "Aadhaar", "PAN": "PAN", "PHONE": "phone", "UPI_ID": "UPI ID", "IFSC": "IFSC", "EMAIL": "email", "BANK_ACC": "bank account", "PINCODE": "pincode", "ORG": "organisation", "GPE": "location"}
    text = temp.format(pii=label_map1.get(i1[0], "PII"), pii_val=i1[1], pii2=label_map2.get(i2[0], "PII"), pii_val2=i2[1])
    return text

_TEMPLATE_CACHE = {}

def _get_template_keys(template):
    if template not in _TEMPLATE_CACHE:
        keys = [fn for _, fn, _, _ in string.Formatter().parse(template) if fn]
        _TEMPLATE_CACHE[template] = keys
    return _TEMPLATE_CACHE[template]

def make_paragraph(items):
    mapped = {}
    for label, val in items:
        if label == "PERSON":
            mapped["name"] = val
        elif label == "AADHAAR":
            mapped["aadhaar"] = val
        elif label == "PAN":
            mapped["pan"] = val
        elif label == "PHONE":
            mapped["phone"] = val
        elif label == "UPI_ID":
            mapped["upi"] = val
        elif label == "IFSC":
            mapped["ifsc"] = val
        elif label == "EMAIL":
            mapped["email"] = val
        elif label == "BANK_ACC":
            mapped["bank"] = val
        elif label == "PINCODE":
            mapped["pincode"] = val
        elif label == "ORG":
            mapped["org"] = val
        elif label == "GPE":
            mapped["loc"] = val

    T = MIXED_PARAGRAPHS
    indices = list(range(len(T)))
    random.shuffle(indices)
    for idx in indices:
        template = T[idx]
        needed = _get_template_keys(template)
        if all(k in mapped for k in needed):
            return template.format(**mapped)

    safe = " ".join(str(v) for v in mapped.values())
    return safe if safe else "General conversation today."

def generate_dataset(total=7000):
    samples = []
    label = None
    
    # Define target distribution
    targets = {
        "PERSON": 0.12,
        "AADHAAR": 0.08,
        "PAN": 0.08,
        "PHONE": 0.10,
        "UPI_ID": 0.07,
        "IFSC": 0.06,
        "EMAIL": 0.07,
        "BANK_ACC": 0.06,
        "PINCODE": 0.04,
        "ORG": 0.05,
        "GPE": 0.05,
        "hinglish_single": 0.06,
        "english_double": 0.05,
        "paragraph": 0.05,
        "no_pii": 0.06,
    }

    for i in range(total):
        r = random.random()
        cumulative = 0.0
        
        if r < (cumulative := cumulative + targets["PERSON"]):
            val = PII_TYPES["PERSON"]()
            label = "PERSON"
            text = make_english("person", val, "PERSON")
            expected = [label]
        elif r < (cumulative := cumulative + targets["AADHAAR"]):
            val = PII_TYPES["AADHAAR"]()
            label = "AADHAAR"
            text = make_english("aadhaar", val, "AADHAAR")
            expected = [label]
        elif r < (cumulative := cumulative + targets["PAN"]):
            val = PII_TYPES["PAN"]()
            label = "PAN"
            text = make_english("pan", val, "PAN")
            expected = [label]
        elif r < (cumulative := cumulative + targets["PHONE"]):
            val = PII_TYPES["PHONE"]()
            label = "PHONE"
            text = make_english("phone", val, "PHONE")
            expected = [label]
        elif r < (cumulative := cumulative + targets["UPI_ID"]):
            val = PII_TYPES["UPI_ID"]()
            label = "UPI_ID"
            text = make_english("upi", val, "UPI_ID")
            expected = [label]
        elif r < (cumulative := cumulative + targets["IFSC"]):
            val = PII_TYPES["IFSC"]()
            label = "IFSC"
            text = make_english("ifsc", val, "IFSC")
            expected = [label]
        elif r < (cumulative := cumulative + targets["EMAIL"]):
            val = PII_TYPES["EMAIL"]()
            label = "EMAIL"
            text = make_english("email", val, "EMAIL")
            expected = [label]
        elif r < (cumulative := cumulative + targets["BANK_ACC"]):
            val = PII_TYPES["BANK_ACC"]()
            label = "BANK_ACC"
            text = make_english("bank", val, "BANK_ACC")
            expected = [label]
        elif r < (cumulative := cumulative + targets["PINCODE"]):
            val = PII_TYPES["PINCODE"]()
            label = "PINCODE"
            text = make_english("pincode", val, "PINCODE")
            expected = [label]
        elif r < (cumulative := cumulative + targets["ORG"]):
            val = PII_TYPES["ORG"]()
            label = "ORG"
            text = make_english("organisation", val, "ORG")
            expected = [label]
        elif r < (cumulative := cumulative + targets["GPE"]):
            val = PII_TYPES["GPE"]()
            label = "GPE"
            text = make_english("location", val, "GPE")
            expected = [label]
        elif r < (cumulative := cumulative + targets["hinglish_single"]):
            ptype = random.choice(["PERSON", "PHONE", "UPI_ID", "AADHAAR", "PAN"])
            val = PII_TYPES[ptype]()
            label = ptype
            text = make_hinglish(ptype, val, ptype)
            expected = [label]
        elif r < (cumulative := cumulative + targets["english_double"]):
            types = random.sample(["PERSON", "PHONE", "UPI_ID", "EMAIL", "AADHAAR", "PAN", "IFSC", "BANK_ACC", "PINCODE"], 2)
            items = []
            for t in types:
                items.append((t, PII_TYPES[t]()))
            text = make_english_double(items)
            expected = [t for t, v in items]
        elif r < (cumulative := cumulative + targets["paragraph"]):
            types = random.sample(["PERSON", "AADHAAR", "PAN", "PHONE", "EMAIL", "UPI_ID", "IFSC", "BANK_ACC", "PINCODE", "ORG", "GPE"], random.randint(5, 8))
            items = []
            for t in types:
                items.append((t, PII_TYPES[t]()))
            text = make_paragraph(items)
            expected = [t for t, v in items]
        else:
            if random.random() < 0.5:
                text = random.choice(NO_PII_SENTENCES)
            else:
                text = random.choice(NO_PII_USE_CASE)
            expected = []
            label = None

        samples.append({"text": text, "expected": expected})

    return samples

if __name__ == "__main__":
    random.seed(42)
    samples = generate_dataset(7000)
    
    with open("test_dataset_7000.json", "w") as f:
        json.dump({"samples": samples}, f, indent=2)
    
    print(f"Generated {len(samples)} test samples")
    
    counts = {}
    for s in samples:
        for e in s["expected"]:
            counts[e] = counts.get(e, 0) + 1
    print("\nCategory distribution:")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {k:<10}: {v:>5}")
    print(f"  {'no_pii':<10}: {sum(1 for s in samples if not s['expected']):>5}")
    print(f"\nSaved to test_dataset_7000.json")
