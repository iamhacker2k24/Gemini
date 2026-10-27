import os
import random
import string
import requests
from config import (
    BASE_URL,
    STUDENT_REGISTRATION_PAGE,
    REGISTER_URL,
    VERIFY_EMAIL_URL,
    RESEND_OTP_URL,
    VERIFY_UNCONFIRMED_LOGIN_URL,
    FORGOT_PASSWORD_PAGE_URL,
    FORGOT_PASSWORD_SUBMIT_URL,
    PERSONAL_DETAILS_UPDATE_URL,
    PREFERENCES_SUBMIT_URL,
    GEMINI_PAGE_URL,
    CAMPAIGN_REGISTER_SUBMIT_URL,
    CAMPAIGN_NAME,
    PROXY_URL
)

# INDIAN DATA BUCKETS & POOLS

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
    "CloudGemini@{rand}",
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

PREFERENCES_REFERRAL = "personal_details"
PREFERENCES_FORM_TYPE_CATEGORIES = "categories"
PREFERENCES_FORM_TYPE_OTHERS = "others"
PREFERENCE_TYPES = ["Internships"]
PREFERENCE_MODES = ["Work from home", "In-office"]
PREFERENCE_LOCATIONS = ["156"]


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
    if not city:
        city = random.choice(INDIAN_SEARCH_CITIES)

    url = f"{BASE_URL}/autocomplete/location/{city}"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/student/personal_details",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }

    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            results = r.json().get("result", [])
            if results:
                chosen = random.choice(results)
                loc_id = str(chosen.get("id", "3674"))
                loc_name = chosen.get("name", "Kolkata, West Bengal, India")
                return loc_id, loc_name
    except requests.exceptions.RequestException:
        pass

    return "3674", "Kolkata, West Bengal, India"


def fetch_college_autocomplete(session):
    url = f"{BASE_URL}/autocomplete/college/IIT"
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/student/personal_details",
        "Accept": "application/json, text/javascript, */*; q=0.01"
    }

    try:
        r = session.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            colleges = r.json().get("result", [])
            if colleges:
                return random.choice(colleges)
    except requests.exceptions.RequestException:
        pass

    return "IIT Kharagpur"


def fetch_stream_autocomplete(session):
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
                return streams[0]
    except requests.exceptions.RequestException:
        pass

    return "Computer Science & Engineering"


def fetch_computer_category_recommendations(session):
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

    try:
        r = session.post(url, headers=headers, timeout=15)
        if r.status_code == 200:
            popular = r.json().get("category", {}).get("popular", [])
            tech_cats = [
                item.get("name") for item in popular
                if any(kw in item.get("name", "").lower() for kw in tech_keywords)
            ]
            if tech_cats:
                return random.sample(tech_cats, min(3, len(tech_cats)))
    except requests.exceptions.RequestException:
        pass

    return ["Web Development", "Software Development", "Javascript Development"]


def build_dynamic_student_profile(session):
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

    return {
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


def create_session(proxy_override=None):
    session = requests.Session()
    p_url = proxy_override or PROXY_URL or os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")
    if p_url:
        session.proxies = {"http": p_url, "https": p_url}

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        session.get(STUDENT_REGISTRATION_PAGE, timeout=25)
    except requests.exceptions.RequestException:
        pass

    return session


def register_account(session, email, profile=None):
    csrf_token = session.cookies.get("csrf_cookie_name", "")
    first_name = profile.get("first_name", "Aarav") if profile else "Aarav"
    last_name = profile.get("last_name", "Sharma") if profile else "Sharma"
    password = profile.get("password", "CloudPass@123") if profile else "CloudPass@123"

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

    try:
        response = session.post(REGISTER_URL, data=data, headers=headers, timeout=30)
        return response
    except requests.exceptions.RequestException as e:
        return None


def verify_email_otp(session, email, otp):
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

    try:
        response = session.post(VERIFY_EMAIL_URL, data=data, headers=headers, timeout=30)
        return response.json()
    except Exception:
        return None


def resend_email_otp(session, email):
    try:
        session.get(VERIFY_UNCONFIRMED_LOGIN_URL, timeout=20)
    except requests.exceptions.RequestException:
        pass

    csrf_token = session.cookies.get("csrf_cookie_name", "")
    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/registration/verify_email",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Csrf-Token": csrf_token
    }

    try:
        response = session.get(RESEND_OTP_URL, headers=headers, timeout=25)
        return response.json()
    except Exception:
        return None


def update_personal_details(session, profile=None):
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

    try:
        response = session.post(PERSONAL_DETAILS_UPDATE_URL, data=payload, headers=headers, timeout=30)
        return response.json()
    except Exception:
        return None


def submit_user_preference_categories(session, categories=None):
    if categories is None:
        categories = fetch_computer_category_recommendations(session)

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

    try:
        response = session.post(PREFERENCES_SUBMIT_URL, data=payload, headers=headers, timeout=30)
        return response.json()
    except Exception:
        return None


def submit_user_preference_others(session, location_id=None):
    locations = [str(location_id)] if location_id else PREFERENCE_LOCATIONS
    csrf_token = session.cookies.get("csrf_cookie_name", "")
    payload = {
        "referral": PREFERENCES_REFERRAL,
        "form_type": PREFERENCES_FORM_TYPE_OTHERS,
        "csrf_test_name": csrf_token,
        "preference_type[]": PREFERENCE_TYPES,
        "mode[]": PREFERENCE_MODES,
        "locations[]": locations
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": f"{BASE_URL}/student/resume",
        "X-Csrf-Token": csrf_token
    }

    try:
        response = session.post(PREFERENCES_SUBMIT_URL, data=payload, headers=headers, timeout=30)
        return response.json()
    except Exception:
        return None


def claim_google_gemini_offer(session):
    try:
        session.get(GEMINI_PAGE_URL, timeout=25)
    except requests.exceptions.RequestException:
        pass

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

    try:
        response = session.post(CAMPAIGN_REGISTER_SUBMIT_URL, data=payload, headers=headers, timeout=30)
        res_json = response.json()
        if res_json.get("success") is True:
            return res_json.get("successPage")
        return None
    except Exception:
        return None


def complete_onboarding_and_claim(session, profile):
    """
    Executes post-verification steps:
    1. Update personal details
    2. Preferences (categories)
    3. Preferences (others)
    4. Claim Google Gemini 12-Month offer
    Returns offer URL or None.
    """
    try:
        update_personal_details(session, profile=profile)
        submit_user_preference_categories(session)
        submit_user_preference_others(session, location_id=profile.get("current_city_location_id"))
        offer_url = claim_google_gemini_offer(session)
        return offer_url
    except Exception as e:
        print(f"Error completing onboarding: {e}")
        return None
