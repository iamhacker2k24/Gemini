import os
import sys
import uuid
import random
import string
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
ACTIVE_SESSIONS = {}

# ============================================================
# CONFIGURATION & CONSTANTS
# ============================================================
BASE_URL = "https://internshala.com"

# Registration, verification, and fallback endpoints
STUDENT_REGISTRATION_PAGE = f"{BASE_URL}/registration/student"
REGISTER_URL = f"{BASE_URL}/registration/student_submit"
SEND_OTP_URL = REGISTER_URL  # Alias for backward compatibility
VERIFY_EMAIL_URL = f"{BASE_URL}/registration/verify_email_submit"
VERIFY_OTP_URL = VERIFY_EMAIL_URL  # Alias for backward compatibility
RESEND_OTP_URL = f"{BASE_URL}/registration/resend_otp"
VERIFY_UNCONFIRMED_LOGIN_URL = f"{BASE_URL}/registration/verify_unconfirmed_login"
FORGOT_PASSWORD_PAGE_URL = f"{BASE_URL}/login/forgot_password"
FORGOT_PASSWORD_SUBMIT_URL = f"{BASE_URL}/login/forgot_password_submit"

# Student onboarding endpoints
PERSONAL_DETAILS_UPDATE_URL = f"{BASE_URL}/student/personal_details_update"
PREFERENCES_SUBMIT_URL = f"{BASE_URL}/user_preference/preferences_submit"

# Google Gemini 12-Month Trial Offer endpoints
GEMINI_PAGE_URL = f"{BASE_URL}/google-gemini-ai-plus"
CAMPAIGN_REGISTER_SUBMIT_URL = f"{BASE_URL}/campaign/register_submit"
CAMPAIGN_NAME = "google_gemini_jul_2026"

# ============================================================
# INDIAN DATA BUCKETS & POOLS
# ============================================================
INDIAN_FIRST_NAMES = [
    "Aarav", "Aditya", "Rohan", "Rahul", "Amit", "Vikram", "Abhishek",
    "Karan", "Varun", "Siddharth", "Kunal", "Manish", "Deepak", "Rajesh",
    "Suresh", "Ishaan", "Priya", "Ananya", "Sneha", "Riya", "Neha",
    "Pooja", "Kavya", "Shreya", "Tanvi", "Meera", "Swati", "Nikhil",
    "Gaurav", "Harsh", "Prateek", "Ayush", "Divya", "Ritika", "Akash",
    "Sanjay", "Aniket", "Vivek", "Simran", "Tanya", "Aditi", "Tarun"
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Kumar", "Singh", "Patel", "Mishra",
    "Joshi", "Deshmukh", "Chatterjee", "Banerjee", "Das", "Sen", "Ghosh",
    "Mukherjee", "Reddy", "Nair", "Iyer", "Pillai", "Choudhury", "Mehta",
    "Shah", "Bhat", "Kulkarni", "Malhotra", "Kapoor", "Agarwal", "Saxena"
]

PASSWORD_TEMPLATES = [
    "Internshala@{rand}",
    "TechCareer#{rand}",
    "CampusHire@{rand}",
    "Placement#{rand}",
    "DevScholar@{rand}",
    "CodeMaster#{rand}",
    "SecurePass@{rand}",
    "IITianDev#{rand}"
]

INDIAN_SEARCH_CITIES = [
    "kolkata", "delhi", "mumbai", "bangalore", "hyderabad",
    "pune", "chennai", "ahmedabad", "jaipur", "lucknow", "chandigarh"
]

# Default fallback values
COUNTRY_CODE = "+91"
GENDER = "Male"
LANGUAGES = "English"
TYPE = "College student"
PERSONAL_DETAILS_RESUME_SUBMIT = "web_add"
COURSE = "B.Tech"
STREAM = "Computer Science & Engineering"
COLLEGE = "IIT Kharagpur"
CURRENT_CITY_LOCATION_ID = "3674"
START_YEAR = "2026"
END_YEAR = "2030"

# Preferences payload - Categories (Step 1)
PREFERENCES_REFERRAL = "personal_details"
PREFERENCES_FORM_TYPE_CATEGORIES = "categories"
PREFERENCE_CATEGORIES = [
    "Web Development",
    "Software Development",
    "Javascript Development"
]

# Preferences payload - Others (Step 2)
PREFERENCES_FORM_TYPE_OTHERS = "others"
PREFERENCE_TYPES = ["Internships"]
PREFERENCE_MODES = ["Work from home", "In-office"]
PREFERENCE_LOCATIONS = ["156"]


# ============================================================
# DYNAMIC PROFILE & AUTOCOMPLETE DATA FETCHERS
# ============================================================
def generate_random_phone():
    """Generates a unique 10-digit Indian phone number starting with 6, 7, 8, or 9."""
    first_digit = random.choice(["6", "7", "8", "9"])
    remaining = "".join(random.choices(string.digits, k=9))
    return f"{first_digit}{remaining}"


def generate_random_password():
    """Generates a strong password from the password bucket with randomized digits."""
    template = random.choice(PASSWORD_TEMPLATES)
    rand_num = "".join(random.choices(string.digits, k=4))
    return template.replace("{rand}", rand_num)


def fetch_location_autocomplete(session, city=None):
    """
    Calls https://internshala.com/autocomplete/location/<city>
    using browser referer headers to retrieve a real location name and ID.
    """
    if not city:
        city = random.choice(INDIAN_SEARCH_CITIES)

    url = f"{BASE_URL}/autocomplete/location/{city}"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/student/personal_details",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }

    print(f"Fetching location autocomplete for '{city}'...")
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            results = r.json().get("result", [])
            if results:
                chosen = random.choice(results)
                loc_id = str(chosen.get("id", "3674"))
                loc_name = chosen.get("name", "Kolkata, West Bengal, India")
                print(f"[+] Autocomplete Location: {loc_name} (ID: {loc_id})")
                return loc_id, loc_name
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning fetching location autocomplete: {e}")

    return "3674", "Kolkata, West Bengal, India"


def fetch_college_autocomplete(session):
    """
    Calls https://internshala.com/autocomplete/college/IIT
    to dynamically retrieve and select an IIT college from India.
    """
    url = f"{BASE_URL}/autocomplete/college/IIT"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/student/personal_details",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }

    print("Fetching IIT colleges from autocomplete API...")
    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            colleges = r.json().get("result", [])
            if colleges:
                chosen = random.choice(colleges)
                print(f"[+] Autocomplete College: {chosen}")
                return chosen
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning fetching college autocomplete: {e}")

    return "IIT Kharagpur"


def fetch_stream_autocomplete(session):
    """
    Calls https://internshala.com/autocomplete/stream/cse
    to select Computer Science & Engineering.
    """
    url = f"{BASE_URL}/autocomplete/stream/cse"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/student/personal_details",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }

    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            streams = r.json().get("result", [])
            if streams:
                chosen = streams[0]
                print(f"[+] Autocomplete Stream: {chosen}")
                return chosen
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning fetching stream autocomplete: {e}")

    return "Computer Science & Engineering"


def fetch_computer_category_recommendations(session):
    """
    Calls https://internshala.com/user_preference/load_category_recommendation
    and filters for computer / B.Tech related preferences.
    """
    url = f"{BASE_URL}/user_preference/load_category_recommendation"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/student/resume",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }

    tech_keywords = [
        "development", "programming", "software", "python",
        "data science", "web", "testing", "ui/ux", "frontend",
        "backend", "javascript"
    ]

    print("Fetching category recommendations from API...")
    try:
        r = session.post(url, headers=headers, timeout=15)
        if r.status_code == 200:
            popular = r.json().get("category", {}).get("popular", [])
            tech_cats = [
                item.get("name") for item in popular
                if any(kw in item.get("name", "").lower() for kw in tech_keywords)
            ]
            if tech_cats:
                selected = random.sample(tech_cats, min(3, len(tech_cats)))
                print(f"[+] Selected Computer/B.Tech categories: {selected}")
                return selected
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning loading category recommendation: {e}")

    return ["Web Development", "Software Development", "Javascript Development"]


def build_dynamic_student_profile(session):
    """
    Constructs a complete randomized Indian student profile meeting all criteria:
    - First and last names from Indian name buckets
    - Unique 10-digit Indian phone number
    - Country code: +91
    - Secure password from template bucket
    - Location ID dynamically queried from /autocomplete/location/<city>
    - College dynamically queried from /autocomplete/college/IIT
    - Stream dynamically queried from /autocomplete/stream/cse (CSE / Computer Science & Engineering)
    - Start year: 2025 or 2026, End year: 2029 or 2030
    """
    first_name = random.choice(INDIAN_FIRST_NAMES)
    last_name = random.choice(INDIAN_LAST_NAMES)
    password = generate_random_password()
    phone_primary = generate_random_phone()
    country_code = "+91"

    start_year = random.choice(["2025", "2026"])
    end_year = "2029" if start_year == "2025" else "2030"

    loc_id, loc_name = fetch_location_autocomplete(session)
    college = fetch_college_autocomplete(session)
    stream = fetch_stream_autocomplete(session)

    profile = {
        "first_name": first_name,
        "last_name": last_name,
        "password": password,
        "country_code": country_code,
        "phone_primary": phone_primary,
        "current_city_location_id": loc_id,
        "current_city_name": loc_name,
        "college": college,
        "stream": stream,
        "start_year": start_year,
        "end_year": end_year,
        "course": "B.Tech",
        "gender": "Male",
        "languages": "English",
        "type": "College student",
        "personal_details_resume_submit": "web_add"
    }

    return profile


# ============================================================
# SESSION SETUP & CSRF TOKEN RETRIEVAL
# ============================================================
def create_session():
    """
    Creates a requests session with browser-like headers and
    pre-fetches the genuine CSRF cookie from Internshala.
    Supports optional proxy configuration via PROXY_URL or HTTP_PROXY environment variables.
    """
    session = requests.Session()

    proxy_url = os.environ.get("PROXY_URL") or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if proxy_url:
        session.proxies = {
            "http": proxy_url,
            "https": proxy_url
        }
        print(f"[+] Proxy configured: {proxy_url}")

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })

    print("\nConnecting to Internshala to fetch security cookies & CSRF token...")
    try:
        resp = session.get(STUDENT_REGISTRATION_PAGE, timeout=30)
        csrf_token = session.cookies.get("csrf_cookie_name")
        if csrf_token:
            print(f"[+] CSRF token acquired: {csrf_token}")
        else:
            print("[!] Warning: csrf_cookie_name not found in response cookies.")
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning: Failed to pre-fetch CSRF token: {e}")

    return session


# ============================================================
# REGISTRATION / SEND OTP
# ============================================================
def register_account(session, email, profile=None):
    """
    Submits student registration details to Internshala with the valid CSRF token.
    If the email is new, Internshala generates and sends a 6-digit OTP to the inbox.
    """
    csrf_token = session.cookies.get("csrf_cookie_name", "")

    first_name = profile.get("first_name", "Aarav") if profile else "Aarav"
    last_name = profile.get("last_name", "Sharma") if profile else "Sharma"
    password = profile.get("password", "Internshala@123") if profile else "Internshala@123"

    data = {
        "csrf_test_name": csrf_token,
        "utm_source": "firstfold_hp",
        "utm_medium": "",
        "utm_campaign": "",
        "student_referral": "",
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": STUDENT_REGISTRATION_PAGE,
        "X-Csrf-Token": csrf_token
    }

    print(f"\nSending registration request for '{email}'...")
    try:
        response = session.post(
            REGISTER_URL,
            data=data,
            headers=headers,
            timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"Network error during registration: {e}")
        return None

    print(f"Registration HTTP Status: {response.status_code}")
    return response


# ============================================================
# VERIFY OTP
# ============================================================
def verify_email_otp(session, email, otp=None):
    """
    Submits the 6-digit OTP received on email to verify the account.
    """
    print("\n" + "=" * 40)
    print("        OTP VERIFICATION")
    print("=" * 40)

    if not otp:
        try:
            otp = input("Enter OTP received on email: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nInput cancelled.")
            return None

    if not otp:
        print("Error: OTP cannot be empty.")
        return None

    csrf_token = session.cookies.get("csrf_cookie_name", "")

    data = {
        "csrf_test_name": csrf_token,
        "user_email": email,
        "otp": otp
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"{BASE_URL}/registration/verify_email",
        "X-Csrf-Token": csrf_token
    }

    print(f"\nSubmitting OTP '{otp}' for verification...")
    try:
        response = session.post(
            VERIFY_EMAIL_URL,
            data=data,
            headers=headers,
            timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"Network error during OTP verification: {e}")
        return None

    print(f"OTP verification HTTP Status: {response.status_code}")

    try:
        result = response.json()
        return result
    except ValueError:
        print("Server response was not JSON:")
        print(response.text)
        return None


# ============================================================
# RESEND OTP (FOR UNVERIFIED ACCOUNTS)
# ============================================================
def resend_email_otp(session, email):
    """
    Triggers an OTP resend for an account that is registered but not yet verified.
    Follows /registration/verify_unconfirmed_login and calls /registration/resend_otp.
    """
    print("\n" + "=" * 40)
    print("      RESEND OTP (UNVERIFIED ACCOUNT)")
    print("=" * 40)
    print(f"Triggering OTP resend for unverified email: {email}...")

    # Step 1: Follow verify_unconfirmed_login
    try:
        session.get(VERIFY_UNCONFIRMED_LOGIN_URL, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning accessing verify_unconfirmed_login: {e}")

    # Step 2: Call resend_otp endpoint
    csrf_token = session.cookies.get("csrf_cookie_name", "")
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/registration/verify_email",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Csrf-Token": csrf_token
    }

    try:
        response = session.get(RESEND_OTP_URL, headers=headers, timeout=30)
        print(f"Resend OTP HTTP Status: {response.status_code}")
        try:
            result = response.json()
            print("Resend OTP JSON Response:", result)
            if result.get("success") is True:
                print(f"[+] Success: New OTP has been resent to {email}!")
                return result
            else:
                error = result.get("errorThrown") or result.get("errorCode") or "Unable to resend OTP"
                print(f"[-] Resend notice: {error}")
                return result
        except ValueError:
            return None
    except requests.exceptions.RequestException as e:
        print(f"[!] Network error during OTP resend: {e}")
        return None


# ============================================================
# FORGOT PASSWORD FALLBACK (FOR REGISTERED & VERIFIED ACCOUNTS)
# ============================================================
def send_forgot_password(session, email):
    """
    Fallback for already registered and verified accounts:
    Calls https://internshala.com/login/forgot_password_submit
    to trigger a password reset OTP / reset link to the email.
    Note: Internshala protects this endpoint with Google reCAPTCHA Enterprise on the web client.
    """
    print("\n" + "=" * 40)
    print("      FORGOT PASSWORD FALLBACK")
    print("=" * 40)
    print(f"Calling endpoint: {FORGOT_PASSWORD_SUBMIT_URL}")

    # Ensure fresh csrf from the forgot password page
    try:
        session.get(FORGOT_PASSWORD_PAGE_URL, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning accessing forgot password page: {e}")

    csrf_token = session.cookies.get("csrf_cookie_name", "")

    payload = {
        "csrf_test_name": csrf_token,
        "user_type": "student",
        "email": email,
        "campaign": "",
        "action": "forgot_password_submit"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": FORGOT_PASSWORD_PAGE_URL,
        "X-Csrf-Token": csrf_token
    }

    print("\nPayload:")
    for key, value in payload.items():
        print(f"  {key}: {value}")

    print(f"\nSubmitting forgot password request for '{email}'...")
    try:
        response = session.post(
            FORGOT_PASSWORD_SUBMIT_URL,
            data=payload,
            headers=headers,
            timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"Network error during forgot password submit: {e}")
        return None

    print(f"Forgot password HTTP Status: {response.status_code}")
    print("Response body:")
    print(response.text)

    try:
        result = response.json()
        print("\nJSON Response:")
        print(result)
        if result.get("success") is True:
            print(f"\n[+] Password reset request succeeded for {email}!")
            return result
        else:
            error = result.get("errorThrown") or result.get("errorCode") or "Failed to submit forgot password"
            print(f"\n[-] Notice: {error}")
            return result
    except ValueError:
        print("\nResponse is not JSON.")
        return response.text


# ============================================================
# UPDATE PERSONAL DETAILS
# ============================================================
def update_personal_details(session, profile=None):
    """
    Calls https://internshala.com/student/personal_details_update
    using the authenticated session cookies and profile details.
    """
    print("\n" + "=" * 40)
    print("   1. PERSONAL DETAILS UPDATE")
    print("=" * 40)

    csrf_token = session.cookies.get("csrf_cookie_name", "")

    if profile is None:
        profile = {}

    payload = {
        "first_name": profile.get("first_name", "Aarav"),
        "last_name": profile.get("last_name", "Sharma"),
        "country_code": profile.get("country_code", "+91"),
        "phone_primary": profile.get("phone_primary", "9093013608"),
        "current_city_location_id": profile.get("current_city_location_id", "3674"),
        "gender": profile.get("gender", "Male"),
        "languages[]": profile.get("languages", "English"),
        "linkedin_url": "",
        "type": profile.get("type", "College student"),
        "personal_details_resume_submit": profile.get("personal_details_resume_submit", "web_add"),
        "course": profile.get("course", "B.Tech"),
        "college": profile.get("college", "IIT Kharagpur"),
        "stream": profile.get("stream", "Computer Science & Engineering"),
        "start_year": profile.get("start_year", "2026"),
        "end_year": profile.get("end_year", "2030"),
        "csrf_test_name": csrf_token
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"{BASE_URL}/student/resume",
        "X-Csrf-Token": csrf_token
    }

    print(f"Calling endpoint: {PERSONAL_DETAILS_UPDATE_URL}")
    print("\nPayload:")
    for key, value in payload.items():
        print(f"  {key}: {value}")

    print("\nSending personal details update request...")
    try:
        response = session.post(
            PERSONAL_DETAILS_UPDATE_URL,
            data=payload,
            headers=headers,
            timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"Network error during personal details update: {e}")
        return None

    print(f"\nPersonal details update HTTP Status: {response.status_code}")
    print("Response body:")
    print(response.text)

    try:
        result = response.json()
        print("\nJSON Response:")
        print(result)
        return result
    except ValueError:
        print("\nResponse is not JSON.")
        return response.text


# ============================================================
# SUBMIT USER PREFERENCES - CATEGORIES (STEP 1)
# ============================================================
def submit_user_preference_categories(session, categories=None):
    """
    Calls https://internshala.com/user_preference/preferences_submit
    with form_type='categories' using the authenticated session cookies.
    If categories are not provided, queries /user_preference/load_category_recommendation
    and selects relevant Computer / B.Tech preferences.
    """
    if categories is None:
        categories = fetch_computer_category_recommendations(session)

    print("\n" + "=" * 40)
    print("   2. PREFERENCES (CATEGORIES)")
    print("=" * 40)

    csrf_token = session.cookies.get("csrf_cookie_name", "")

    payload = {
        "referral": PREFERENCES_REFERRAL,
        "form_type": PREFERENCES_FORM_TYPE_CATEGORIES,
        "csrf_test_name": csrf_token,
        "categories[]": categories
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"{BASE_URL}/student/resume",
        "X-Csrf-Token": csrf_token
    }

    print(f"Calling endpoint: {PREFERENCES_SUBMIT_URL}")
    print("\nPayload:")
    for key, value in payload.items():
        print(f"  {key}: {value}")

    print("\nSending categories preferences submission...")
    try:
        response = session.post(
            PREFERENCES_SUBMIT_URL,
            data=payload,
            headers=headers,
            timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"Network error during categories preferences submission: {e}")
        return None

    print(f"\nCategories preferences HTTP Status: {response.status_code}")
    print("Response body:")
    print(response.text)

    try:
        result = response.json()
        print("\nJSON Response:")
        print(result)
        return result
    except ValueError:
        print("\nResponse is not JSON.")
        return response.text


# ============================================================
# SUBMIT USER PREFERENCES - OTHERS (STEP 2)
# ============================================================
def submit_user_preference_others(session, preference_types=None, modes=None, locations=None, location_id=None):
    """
    Calls https://internshala.com/user_preference/preferences_submit
    with form_type='others' (Internships, Work from home, In-office, locations)
    using the authenticated session cookies.
    """
    if preference_types is None:
        preference_types = PREFERENCE_TYPES
    if modes is None:
        modes = PREFERENCE_MODES
    if locations is None:
        if location_id:
            locations = [str(location_id)]
        else:
            locations = PREFERENCE_LOCATIONS

    print("\n" + "=" * 40)
    print("   3. PREFERENCES (OTHERS)")
    print("=" * 40)

    csrf_token = session.cookies.get("csrf_cookie_name", "")

    payload = {
        "referral": PREFERENCES_REFERRAL,
        "form_type": PREFERENCES_FORM_TYPE_OTHERS,
        "csrf_test_name": csrf_token,
        "preference_type[]": preference_types,
        "mode[]": modes,
        "locations[]": locations
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"{BASE_URL}/student/resume",
        "X-Csrf-Token": csrf_token
    }

    print(f"Calling endpoint: {PREFERENCES_SUBMIT_URL}")
    print("\nPayload:")
    for key, value in payload.items():
        print(f"  {key}: {value}")

    print("\nSending others preferences submission...")
    try:
        response = session.post(
            PREFERENCES_SUBMIT_URL,
            data=payload,
            headers=headers,
            timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"Network error during others preferences submission: {e}")
        return None

    print(f"\nOthers preferences HTTP Status: {response.status_code}")
    print("Response body:")
    print(response.text)

    try:
        result = response.json()
        print("\nJSON Response:")
        print(result)
        return result
    except ValueError:
        print("\nResponse is not JSON.")
        return response.text


# ============================================================
# CLAIM GOOGLE GEMINI 12-MONTHS TRIAL OFFER
# ============================================================
def claim_google_gemini_offer(session):
    """
    Simulates visiting https://internshala.com/google-gemini-ai-plus
    and clicking 'Start FREE 12 months trial', submitting to
    https://internshala.com/campaign/register_submit with campaign='google_gemini_jul_2026',
    and returning the exact Google One offer URL.
    """
    print("\n" + "=" * 40)
    print("   4. GOOGLE GEMINI 12-MONTHS TRIAL OFFER")
    print("=" * 40)

    # Step A: Visit the landing page to ensure referrer and fresh cookies
    print(f"Visiting landing page: {GEMINI_PAGE_URL} ...")
    try:
        session.get(GEMINI_PAGE_URL, timeout=30)
    except requests.exceptions.RequestException as e:
        print(f"[!] Warning accessing landing page: {e}")

    csrf_token = session.cookies.get("csrf_cookie_name", "")

    payload = {
        "csrf_test_name": csrf_token,
        "campaign": CAMPAIGN_NAME
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": GEMINI_PAGE_URL,
        "X-Csrf-Token": csrf_token
    }

    print(f"Calling endpoint: {CAMPAIGN_REGISTER_SUBMIT_URL}")
    print("\nPayload:")
    for key, value in payload.items():
        print(f"  {key}: {value}")

    print("\nSubmitting 'Start FREE 12 months trial' request...")
    try:
        response = session.post(
            CAMPAIGN_REGISTER_SUBMIT_URL,
            data=payload,
            headers=headers,
            timeout=30
        )
    except requests.exceptions.RequestException as e:
        print(f"Network error during Gemini offer claim: {e}")
        return None

    print(f"\nCampaign register HTTP Status: {response.status_code}")
    print("Response body:")
    print(response.text)

    try:
        result = response.json()
        print("\nJSON Response:")
        print(result)

        if result.get("success") is True:
            google_offer_url = result.get("successPage")
            print("\n" + "*" * 60)
            print("🎉 SUCCESS! GOOGLE ONE 12-MONTHS TRIAL CLAIMED!")
            print("*" * 60)
            print(f"Google One Offer URL: {google_offer_url}")
            print("*" * 60)
            return google_offer_url
        else:
            error_msg = result.get("errorThrown") or result.get("errorCode") or "Failed to claim offer"
            print(f"\n[-] Could not claim offer: {error_msg}")
            return None
    except ValueError:
        print("\nResponse is not JSON.")
        return response.text


# Compatibility alias
def submit_user_preferences(session):
    """Submits both categories and others preferences in sequence."""
    submit_user_preference_categories(session)
    submit_user_preference_others(session)


# ============================================================
# MAIN ENTRY POINT
# ============================================================
def main():
    print("=" * 40)
    print("     INTERNSHALA REGISTRATION FLOW")
    print("=" * 40)

    # Prompt user for email (or accept command-line arg)
    otp_from_args = None
    if len(sys.argv) > 1:
        email = sys.argv[1].strip()
        print(f"Email provided via argument: {email}")
        if len(sys.argv) > 2:
            otp_from_args = sys.argv[2].strip()
            print(f"OTP provided via argument: {otp_from_args}")
    else:
        try:
            email = input("Enter email: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nInput cancelled.")
            return

    if not email:
        print("Error: Email cannot be empty.")
        return

    # Step 1: Create session & fetch real CSRF token
    session = create_session()

    # Step 2: Build dynamic Indian student profile
    profile = build_dynamic_student_profile(session)

    print("\n" + "=" * 40)
    print("      DYNAMIC STUDENT PROFILE")
    print("=" * 40)
    print("Name       :", f"{profile['first_name']} {profile['last_name']}")
    print("Email      :", email)
    print("Password   :", profile['password'])
    print("Phone      :", f"{profile['country_code']} {profile['phone_primary']}")
    print("City/Loc ID:", f"{profile['current_city_name']} (ID: {profile['current_city_location_id']})")
    print("College    :", profile['college'])
    print("Stream     :", profile['stream'])
    print("Batch      :", f"{profile['start_year']} - {profile['end_year']}")
    print("=" * 40)

    # Step 3: Submit Registration with dynamic profile
    registration_response = register_account(session, email, profile=profile)
    if registration_response is None:
        print("[-] Registration request failed to complete.")
        return

    # Display session cookies
    if session.cookies:
        print("\n" + "=" * 40)
        print("COOKIES RECEIVED")
        print("=" * 40)
        for cookie in session.cookies:
            print(f"{cookie.name} = {cookie.value}")

    # Parse registration JSON response
    registration_json = {}
    try:
        registration_json = registration_response.json()
        print("\nRegistration response JSON:")
        print(registration_json)
    except ValueError:
        print("\nRegistration response body (not JSON):")
        print(registration_response.text)
        if "CSRF" in registration_response.text:
            print("\n[!] CSRF Error: Internshala rejected the CSRF token.")
            return

    # Analyze registration result
    is_success = registration_json.get("success")
    error_code = str(registration_json.get("errorCode", ""))
    error_thrown = str(registration_json.get("errorThrown", ""))

    proceed_to_otp = False
    if is_success is True:
        success_msg = registration_json.get("successMsg") or "Registration successful! OTP sent."
        print(f"\n[+] {success_msg}")
        proceed_to_otp = True
    elif (
        "registered but not yet verified" in error_code
        or "registered but not yet verified" in error_thrown
        or "already been sent to you thrice" in error_code
        or "already been sent to you thrice" in error_thrown
    ):
        print("\n" + "!" * 55)
        print("NOTICE: THIS EMAIL IS REGISTERED BUT NOT YET VERIFIED")
        print("!" * 55)
        if "already been sent to you thrice" in error_code or "already been sent to you thrice" in error_thrown:
            print("Internshala notice: Verification emails have already been sent thrice.")
            print("Please check your email spam/promotions tab for the 6-digit OTP.")
        else:
            print("Triggering OTP resend for unverified account...")
            resend_email_otp(session, email)
        print("!" * 55)
        proceed_to_otp = True
    else:
        print("\n[-] Registration returned an error:")
        print(error_thrown or error_code or registration_response.text)

        # Fallback 1: Resend OTP for unverified account
        try:
            resend_input = input("\nDo you want to attempt resending OTP via '/registration/resend_otp'? (y/n): ").strip().lower()
            if resend_input in ["y", "yes"]:
                resend_email_otp(session, email)
                proceed_to_otp = True
        except (EOFError, KeyboardInterrupt):
            pass

        # Fallback 2: Forgot password for already registered & verified account
        try:
            forgot_input = input("\nDo you want to send a password reset / OTP request via forgot password ('https://internshala.com/login/forgot_password_submit')? (y/n): ").strip().lower()
            if forgot_input in ["y", "yes"]:
                send_forgot_password(session, email)
        except (EOFError, KeyboardInterrupt):
            pass

        if not proceed_to_otp:
            try:
                proceed_input = input("\nDo you still want to enter an OTP for verification? (y/n): ").strip().lower()
                proceed_to_otp = proceed_input in ["y", "yes"]
            except (EOFError, KeyboardInterrupt):
                proceed_to_otp = False

    # Step 4: OTP Verification
    if proceed_to_otp:
        result = verify_email_otp(session, email, otp=otp_from_args)

        print("\n" + "=" * 40)
        print("OTP VERIFICATION RESULT")
        print("=" * 40)

        if result is None:
            print("No valid response received for OTP verification.")
            return

        print(result)
        if result.get("success") is True:
            print("\n[SUCCESS] Email verification successful! Account is activated.")
            # Step 5: Automatically call personal_details_update with dynamic profile
            update_personal_details(session, profile=profile)
            # Step 6: Automatically call preferences (categories) with dynamic tech categories
            submit_user_preference_categories(session)
            # Step 7: Automatically call preferences (others) with dynamic location ID
            submit_user_preference_others(session, location_id=profile["current_city_location_id"])
            # Step 8: Automatically claim Google Gemini 12-months trial offer
            claim_google_gemini_offer(session)
        else:
            reason = result.get("errorThrown") or result.get("errorCode") or "Verification failed"
            print(f"\n[FAILED] Email verification failed: {reason}")
            try:
                force_update = input("\nDo you still want to run onboarding requests (personal details + preferences + Gemini trial) anyway? (y/n): ").strip().lower()
                if force_update in ["y", "yes"]:
                    update_personal_details(session, profile=profile)
                    submit_user_preference_categories(session)
                    submit_user_preference_others(session, location_id=profile["current_city_location_id"])
                    claim_google_gemini_offer(session)
            except (EOFError, KeyboardInterrupt):
                pass


# ============================================================
# FLASK WEB APPLICATION ROUTES (FOR RENDER & WEB HOSTING)
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    if not email:
        return jsonify({"success": False, "error": "Email address is required."}), 400

    session_id = uuid.uuid4().hex
    session = create_session()
    profile = build_dynamic_student_profile(session)

    reg_resp = register_account(session, email, profile=profile)
    if reg_resp is None:
        return jsonify({"success": False, "error": "Failed to connect to Internshala. Please check server network/proxy."}), 500

    try:
        reg_json = reg_resp.json()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid response received from Internshala."}), 500

    is_success = reg_json.get("success")
    error_code = str(reg_json.get("errorCode", ""))
    error_thrown = str(reg_json.get("errorThrown", ""))

    message = "OTP has been sent to your email address."

    if is_success is True:
        message = reg_json.get("successMsg") or "Registration successful! OTP sent to your email."
    elif (
        "registered but not yet verified" in error_code
        or "registered but not yet verified" in error_thrown
        or "already been sent to you thrice" in error_code
        or "already been sent to you thrice" in error_thrown
    ):
        if "already been sent to you thrice" in error_code or "already been sent to you thrice" in error_thrown:
            message = "This email is registered. Verification emails were already sent thrice. Please enter the OTP from your inbox/spam folder."
        else:
            resend_email_otp(session, email)
            message = "Account is registered but unverified. New OTP has been sent to your email."
    else:
        err = error_thrown or error_code or "Registration failed."
        return jsonify({"success": False, "error": err}), 400

    # Store active session flow in memory for OTP verification
    ACTIVE_SESSIONS[session_id] = {
        "session": session,
        "email": email,
        "profile": profile
    }

    return jsonify({
        "success": True,
        "session_id": session_id,
        "profile": profile,
        "message": message
    })


@app.route("/api/verify_otp", methods=["POST"])
def api_verify_otp():
    data = request.get_json() or {}
    session_id = data.get("session_id", "").strip()
    otp = data.get("otp", "").strip()

    if not session_id or session_id not in ACTIVE_SESSIONS:
        return jsonify({"success": False, "error": "Session expired or invalid. Please refresh the page and enter email again."}), 400

    if not otp or len(otp) != 6:
        return jsonify({"success": False, "error": "Please enter a valid 6-digit OTP."}), 400

    flow_state = ACTIVE_SESSIONS[session_id]
    session = flow_state["session"]
    email = flow_state["email"]
    profile = flow_state["profile"]

    # Step A: Verify OTP
    result = verify_email_otp(session, email, otp=otp)
    if result is None:
        return jsonify({"success": False, "error": "Network error while submitting OTP."}), 500

    if result.get("success") is not True:
        # WRONG OTP: Keep session active so user can re-enter OTP without losing progress!
        err = result.get("errorThrown")
        if isinstance(err, dict):
            err_msg = ", ".join(f"{k}: {v}" for k, v in err.items())
        else:
            err_msg = str(err or result.get("errorCode") or "Invalid or expired OTP. Please try again.")
        return jsonify({"success": False, "error": err_msg})

    # Step B: OTP is verified! Complete onboarding & claim offer
    try:
        update_personal_details(session, profile=profile)
        submit_user_preference_categories(session)
        submit_user_preference_others(session, location_id=profile.get("current_city_location_id"))
        offer_url = claim_google_gemini_offer(session)

        if offer_url:
            return jsonify({
                "success": True,
                "offer_url": offer_url,
                "message": "Google Gemini 12-Month Free Trial claimed successfully!"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Account verified, but offer link could not be claimed. Please check eligibility."
            })
    except Exception as e:
        return jsonify({"success": False, "error": f"Error during onboarding: {str(e)}"}), 500


@app.route("/api/resend_otp", methods=["POST"])
def api_resend_otp():
    data = request.get_json() or {}
    session_id = data.get("session_id", "").strip()

    if not session_id or session_id not in ACTIVE_SESSIONS:
        return jsonify({"success": False, "error": "Session expired or invalid."}), 400

    flow_state = ACTIVE_SESSIONS[session_id]
    session = flow_state["session"]
    email = flow_state["email"]

    res = resend_email_otp(session, email)
    if res and res.get("success") is True:
        return jsonify({"success": True, "message": "A new OTP has been sent to your email inbox."})
    else:
        err = (res and (res.get("errorThrown") or res.get("errorCode"))) or "Unable to resend OTP at this time."
        return jsonify({"success": False, "error": err})


if __name__ == "__main__":
    # If command-line arguments are passed, run CLI mode
    if len(sys.argv) > 1 and ("@" in sys.argv[1] or sys.argv[1] in ["-c", "--cli"]):
        main()
    else:
        # Default to web server mode (Render, cloud host, or local browser)
        port = int(os.environ.get("PORT", 5000))
        print("\n" + "=" * 55)
        print("🚀 STARTING GOOGLE GEMINI TRIAL CLAIMER WEB APP")
        print(f"📡 Web server running on: http://0.0.0.0:{port}")
        print(f"🌐 Access locally at:      http://localhost:{port}")
        print("=" * 55 + "\n")
        app.run(host="0.0.0.0", port=port, debug=False)