import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the telegram_bot directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin Telegram IDs (list of ints)
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = []
if raw_admins:
    for item in raw_admins.split(","):
        item = item.strip()
        if item.isdigit():
            ADMIN_IDS.append(int(item))

# Fallback default if not specified
DEFAULT_REQUIRED_REFERRALS = int(os.getenv("REQUIRED_REFERRALS", "3"))

# Private Log Channel ID for user logs (masked with ****)
raw_log_channel = os.getenv("LOG_CHANNEL_ID", "").strip()
LOG_CHANNEL_ID = int(raw_log_channel) if (raw_log_channel and raw_log_channel.lstrip("-").isdigit()) else None

# Private Admin Channel ID for full raw user data, chats, claims, stats & leaderboard
raw_priv_channel = (os.getenv("PRIVATE_CHANNEL_ID") or os.getenv("PRIVATE_CHNALE_ID") or os.getenv("PRIVATE_GROUP_ID", "")).strip()
PRIVATE_CHANNEL_ID = int(raw_priv_channel) if (raw_priv_channel and raw_priv_channel.lstrip("-").isdigit()) else None
PRIVATE_GROUP_ID = PRIVATE_CHANNEL_ID

# Force Join Enabled Default
FORCE_JOIN_DEFAULT = os.getenv("FORCE_JOIN_ENABLED", "True").lower() in ("true", "1", "yes")

# Database Path (Supports local or Railway Persistent Volume mount)
DATA_DIR = os.getenv("DATA_DIR", "").strip()
if DATA_DIR:
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
    DB_PATH = str(Path(DATA_DIR) / "bot_database.db")
else:
    DB_PATH = str(BASE_DIR / "bot_database.db")

# Optional Proxy
PROXY_URL = os.getenv("PROXY_URL", "").strip()

# Internshala Automation Constants
BASE_URL = "https://internshala.com"
STUDENT_REGISTRATION_PAGE = f"{BASE_URL}/registration/student"
REGISTER_URL = f"{BASE_URL}/registration/student_submit"
VERIFY_EMAIL_URL = f"{BASE_URL}/registration/verify_email_submit"
RESEND_OTP_URL = f"{BASE_URL}/registration/resend_otp"
VERIFY_UNCONFIRMED_LOGIN_URL = f"{BASE_URL}/registration/verify_unconfirmed_login"
FORGOT_PASSWORD_PAGE_URL = f"{BASE_URL}/login/forgot_password"
FORGOT_PASSWORD_SUBMIT_URL = f"{BASE_URL}/login/forgot_password_submit"
PERSONAL_DETAILS_UPDATE_URL = f"{BASE_URL}/student/personal_details_update"
PREFERENCES_SUBMIT_URL = f"{BASE_URL}/user_preference/preferences_submit"
GEMINI_PAGE_URL = f"{BASE_URL}/google-gemini-ai-plus"
CAMPAIGN_REGISTER_SUBMIT_URL = f"{BASE_URL}/campaign/register_submit"
CAMPAIGN_NAME = "google_gemini_jul_2026"
