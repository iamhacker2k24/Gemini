import sqlite3
import threading
from datetime import datetime
from config import DB_PATH, DEFAULT_REQUIRED_REFERRALS, FORCE_JOIN_DEFAULT

_lock = threading.Lock()


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_bot INTEGER DEFAULT 0,
                is_premium INTEGER DEFAULT 0,
                referrer_id INTEGER,
                referral_count INTEGER DEFAULT 0,
                referral_points INTEGER DEFAULT 0,
                claims_count INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Referrals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER UNIQUE,
                is_verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Required force-join channels/groups
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT UNIQUE,
                title TEXT,
                invite_link TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Bot key-value settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Gemini trial claim records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                email TEXT,
                offer_url TEXT,
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Broadcast history
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                total_sent INTEGER,
                total_failed INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Support messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                first_name TEXT,
                message_text TEXT,
                admin_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                replied_at TIMESTAMP
            )
        """)

        conn.commit()

        # Database safety migration: ensure is_bot and referral_points columns exist in users
        try:
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = [col[1] for col in cursor.fetchall()]
            if "is_bot" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN is_bot INTEGER DEFAULT 0")
            if "referral_points" not in existing_columns:
                cursor.execute("ALTER TABLE users ADD COLUMN referral_points INTEGER DEFAULT 0")
                cursor.execute("""
                    UPDATE users 
                    SET referral_points = max(0, referral_count - (claims_count * ?))
                """, (DEFAULT_REQUIRED_REFERRALS,))
            conn.commit()
        except Exception:
            pass

        # Initialize default settings if not present
        cursor.execute("SELECT key FROM settings WHERE key = 'required_referrals'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO settings (key, value) VALUES ('required_referrals', ?)", (str(DEFAULT_REQUIRED_REFERRALS),))

        cursor.execute("SELECT key FROM settings WHERE key = 'force_join_enabled'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO settings (key, value) VALUES ('force_join_enabled', ?)", ("1" if FORCE_JOIN_DEFAULT else "0",))

        cursor.execute("SELECT key FROM settings WHERE key = 'referral_system_enabled'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO settings (key, value) VALUES ('referral_system_enabled', '1')")

        conn.commit()
        conn.close()


# USER MANAGEMENT

def get_user(user_id: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None


def register_user(user_id: int, username: str, first_name: str, last_name: str, referrer_id: int = None, is_bot: bool = False):
    """
    Registers a new user or updates existing user profile.
    Ensures that bots cannot be registered as real users and cannot earn referrals.
    Returns (user_dict, is_new_user)
    """
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE users
                SET username = ?, first_name = ?, last_name = ?, is_bot = ?, last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (username, first_name, last_name, 1 if is_bot else 0, user_id))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = dict(cursor.fetchone())
            conn.close()
            return row, False
        else:
            # Check referrer validity:
            # 1. User cannot refer themselves
            # 2. Bots cannot be referred or count as referrals
            # 3. Referrer must exist in users database
            valid_referrer = None
            if not is_bot and referrer_id and referrer_id != user_id:
                cursor.execute("SELECT user_id, is_bot FROM users WHERE user_id = ?", (referrer_id,))
                ref_row = cursor.fetchone()
                if ref_row and not ref_row["is_bot"]:
                    valid_referrer = referrer_id

            cursor.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, is_bot, referrer_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, username, first_name, last_name, 1 if is_bot else 0, valid_referrer))

            if valid_referrer:
                cursor.execute("""
                    INSERT OR IGNORE INTO referrals (referrer_id, referred_id, is_verified)
                    VALUES (?, ?, 0)
                """, (valid_referrer, user_id))

            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = dict(cursor.fetchone())
            conn.close()
            return row, True


def get_user_referrals_list(referrer_id: int):
    """
    Returns list of real users referred by referrer_id with verification status.
    """
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.referred_id, r.is_verified, r.created_at,
                   u.first_name, u.last_name, u.username
            FROM referrals r
            LEFT JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        """, (referrer_id,))
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows


def verify_referral_reward(referred_id: int):
    """
    Called when a user finishes force-join or verifies their join.
    If they joined via a referrer and haven't been verified yet:
    - Marks referral verified
    - Increments referrer's referral_count
    - If referrer reaches required_referrals, unlocks premium automatically!
    Returns (referrer_id, new_count, reached_premium) or None.
    """
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT referrer_id, is_verified FROM referrals
            WHERE referred_id = ?
        """, (referred_id,))
        row = cursor.fetchone()

        if not row or row["is_verified"] == 1:
            conn.close()
            return None

        referrer_id = row["referrer_id"]

        # Mark verified
        cursor.execute("UPDATE referrals SET is_verified = 1 WHERE referred_id = ?", (referred_id,))

        # Increment referrer count and available referral points
        cursor.execute("""
            UPDATE users 
            SET referral_count = referral_count + 1,
                referral_points = referral_points + 1 
            WHERE user_id = ?
        """, (referrer_id,))

        # Fetch referrer's new stats
        cursor.execute("SELECT referral_count, referral_points, is_premium FROM users WHERE user_id = ?", (referrer_id,))
        ref_user = cursor.fetchone()

        reached_premium = False
        new_count = 0
        new_points = 0

        if ref_user:
            new_count = ref_user["referral_count"]
            new_points = ref_user["referral_points"]
            # Fetch required referrals setting
            cursor.execute("SELECT value FROM settings WHERE key = 'required_referrals'")
            req_row = cursor.fetchone()
            required = int(req_row["value"]) if req_row else DEFAULT_REQUIRED_REFERRALS

            if new_points >= required:
                reached_premium = True

        conn.commit()
        conn.close()
        return (referrer_id, new_count, new_points, reached_premium)


def set_user_premium(user_id: int, is_premium: bool):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (1 if is_premium else 0, user_id))
        conn.commit()
        conn.close()


def get_all_user_ids():
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        rows = [row["user_id"] for row in cursor.fetchall()]
        conn.close()
        return rows


def get_bot_stats():
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM users")
        total_users = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as premium FROM users WHERE is_premium = 1")
        premium_users = cursor.fetchone()["premium"]

        cursor.execute("SELECT COUNT(*) as claims FROM claims")
        total_claims = cursor.fetchone()["claims"]

        cursor.execute("SELECT COUNT(*) as referrals FROM referrals WHERE is_verified = 1")
        total_referrals = cursor.fetchone()["referrals"]

        cursor.execute("SELECT COUNT(*) as channels FROM required_channels")
        total_channels = cursor.fetchone()["channels"]

        conn.close()
        return {
            "total_users": total_users,
            "premium_users": premium_users,
            "free_users": total_users - premium_users,
            "total_claims": total_claims,
            "total_referrals": total_referrals,
            "total_channels": total_channels
        }


# REQUIRED CHANNELS / FORCE JOIN

def get_required_channels():
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM required_channels ORDER BY id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


def add_required_channel(chat_id: str, title: str, invite_link: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO required_channels (chat_id, title, invite_link)
                VALUES (?, ?, ?)
            """, (chat_id.strip(), title.strip(), invite_link.strip()))
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            cursor.execute("""
                UPDATE required_channels
                SET title = ?, invite_link = ?
                WHERE chat_id = ?
            """, (title.strip(), invite_link.strip(), chat_id.strip()))
            conn.commit()
            success = True
        conn.close()
        return success


def remove_required_channel(channel_id: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM required_channels WHERE id = ?", (channel_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted


# SETTINGS MANAGEMENT

def get_setting(key: str, default: str = "") -> str:
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        return row["value"] if row else default


def set_setting(key: str, value: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, str(value)))
        conn.commit()
        conn.close()


def is_force_join_enabled() -> bool:
    val = get_setting("force_join_enabled", "1")
    return val in ("1", "true", "True")


def get_required_referrals() -> int:
    val = get_setting("required_referrals", str(DEFAULT_REQUIRED_REFERRALS))
    try:
        return int(val)
    except ValueError:
        return DEFAULT_REQUIRED_REFERRALS


# CLAIMS & BROADCAST LOGS

def record_claim(user_id: int, email: str, offer_url: str, points_to_deduct: int = 3):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO claims (user_id, email, offer_url)
            VALUES (?, ?, ?)
        """, (user_id, email, offer_url))
        cursor.execute("""
            UPDATE users 
            SET claims_count = claims_count + 1,
                referral_points = max(0, referral_points - ?)
            WHERE user_id = ?
        """, (points_to_deduct, user_id))
        conn.commit()
        conn.close()


def get_top_claimers(limit: int = 10):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, first_name, last_name, claims_count, referral_count, referral_points
            FROM users
            WHERE claims_count > 0
            ORDER BY claims_count DESC, referral_count DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


def get_top_referrers(limit: int = 10):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, username, first_name, last_name, referral_count, referral_points, claims_count
            FROM users
            WHERE referral_count > 0
            ORDER BY referral_count DESC, claims_count DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


def add_user_points(user_id: int, points: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET referral_points = max(0, referral_points + ?) WHERE user_id = ?
        """, (points, user_id))
        conn.commit()
        conn.close()


def get_detailed_user_info(user_id: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        u = cursor.fetchone()
        if not u:
            conn.close()
            return None
        user_data = dict(u)

        # Referrer info
        referrer_data = None
        if user_data.get("referrer_id"):
            cursor.execute("SELECT user_id, username, first_name, last_name FROM users WHERE user_id = ?", (user_data["referrer_id"],))
            ref_row = cursor.fetchone()
            if ref_row:
                referrer_data = dict(ref_row)
        user_data["referrer_info"] = referrer_data

        # Claims
        cursor.execute("SELECT email, offer_url, claimed_at FROM claims WHERE user_id = ? ORDER BY claimed_at DESC", (user_id,))
        user_data["claims"] = [dict(r) for r in cursor.fetchall()]

        conn.close()
        return user_data


def get_user_claims(user_id: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM claims WHERE user_id = ? ORDER BY claimed_at DESC", (user_id,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows


def record_broadcast(admin_id: int, sent: int, failed: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO broadcasts (admin_id, total_sent, total_failed)
            VALUES (?, ?, ?)
        """, (admin_id, sent, failed))
        conn.commit()
        conn.close()


# SUPPORT SYSTEM

def save_support_message(user_id: int, username: str, first_name: str, message_text: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO support_messages (user_id, username, first_name, message_text)
            VALUES (?, ?, ?, ?)
        """, (user_id, username or "", first_name or "", message_text))
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return ticket_id


def save_admin_reply(ticket_id: int, admin_reply: str):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE support_messages
            SET admin_reply = ?, replied_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (admin_reply, ticket_id))
        conn.commit()
        conn.close()


def get_support_message(ticket_id: int):
    with _lock:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM support_messages WHERE id = ?", (ticket_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
