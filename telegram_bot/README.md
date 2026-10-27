# 🤖 Google Gemini 12-Month Trial Telegram Bot

A high-performance, production-ready Telegram Bot in Python that automates claiming the **Google Gemini 12-Month Trial Offer** (Gemini Advanced AI + 2TB Google One Cloud Storage) for your Google account, featuring a **Force-Join Verification System**, an **Invite/Referral System with Premium Access Locking**, a **Direct Customer Support Desk**, a **Hardcoded Private Audit Log Group**, and a **Comprehensive Admin Dashboard & Broadcast Engine**.

---

## ✨ Features Overview

### 1. ⚡ Automated Gemini Claim Engine
- **Automated Profile Generation**: Verified Indian student profiles with unique 10-digit Indian phone numbers (+91), real Indian IIT colleges queried from autocomplete, CSE stream, and tech-focused preferences.
- **CSRF Token & Session Management**: Real browser headers and security cookies.
- **Interactive Chat Flow**:
  1. User clicks **"💎 Claim Gemini 12-Month Pro"**.
  2. Strict verification checks if user has joined all required channels and met referral/premium requirements.
  3. Prompts user for their `@gmail.com` address.
  4. Dispatches a 6-digit OTP code to the email.
  5. User enters the 6-digit OTP directly in Telegram.
  6. Bot verifies the OTP, completes onboarding, and claims the offer!
  7. Sends the user their unique Google One activation URL with a 1-click button!
- **Resend OTP Support**: Inline button to resend OTP if expired or delayed.

### 2. 📢 Mandatory Force-Join Channel / Group System
- Automatically verifies if the user has joined your required Telegram channel(s) or group(s) before unlocking bot features.
- If not joined, displays clickable channel buttons and a **"✅ Verify / Check Joined"** button.
- Real-time membership check using Telegram Bot API `getChatMember`.
- Channels can be added, removed, or toggled ON/OFF directly from the Admin Panel.

### 3. 👥 Referral & Premium Access System
- **Unique Referral Links**: Each user gets a personalized referral link: `https://t.me/<bot_username>?start=ref_<user_id>`.
- **Anti-Cheat Verification**: Referrals are only counted when the invited user joins the bot and completes the channel verification. Self-referrals and duplicates are blocked.
- **Referral Target & Progress Bar**: Visual progress indicator (e.g. `[██████░░░░] 2/3 (66%)`).
- **Automatic Premium Unlock**: Once a user reaches the required referral count (configurable by Admin, default: 3), their account is automatically upgraded to **⭐ PREMIUM** and they receive a congratulatory notification unlocking Gemini claim access!
- **Share Button**: 1-click button to instantly share the referral link across Telegram chats and groups.

### 4. 🛠️ Comprehensive Admin Dashboard (`/admin`)
- **📊 Real-Time Statistics**: Total registered users, Premium members, Free users, Successful Gemini claims, Total verified referrals, Active channels.
- **📢 Broadcast System**:
  - Broadcast Text (with HTML styling), Photos with captions, or Forwarded messages to all users.
  - Live progress counter that updates every 50 users.
  - Reports total sent vs. failed/blocked users and saves broadcast history in SQLite.
- **📢 Force-Join Manager**:
  - Add channels/groups via `CHAT_ID | TITLE | INVITE_LINK`.
  - Remove existing channels with 1 click.
  - Toggle Force Join ON/OFF globally.
- **⚙️ Referral System Settings**:
  - Change the number of required referrals (e.g., 1, 2, 3, 5).
  - Toggle the Referral Gate ON/OFF (when OFF, all users get immediate free access without needing referrals).
- **👑 User Management**:
  - Grant or revoke Premium status manually by Telegram User ID.
  - User Lookup: Inspect any user's profile, referrals, and claimed Gemini links history.

---

## 📁 File Structure

```
telegram_bot/
│
├── bot.py                  # Core Telegram Bot logic & message handlers
├── config.py               # Configuration & environment variable loader
├── database.py             # SQLite database layer (users, referrals, settings, claims)
├── internshala_engine.py   # Automation engine for Google Gemini Pro 12-Month Trial
├── requirements.txt        # Python package dependencies
├── .env.example            # Environment variables template
├── .env                    # Active configuration file (Add BOT_TOKEN here)
├── setup.bat               # Windows 1-click dependency installer
├── run.bat                 # Windows 1-click bot runner with auto-restart
├── run.sh                  # Linux / VPS startup script
└── README.md               # Complete documentation
```

---

## 🚀 Quick Start Guide

### Step 1: Install Python
Ensure Python 3.9+ is installed on your machine.

### Step 2: Install Dependencies
- **On Windows**: Double-click [`setup.bat`](file:///c:/Users/mrdeb/Desktop/ProjectCompleted/gemini/telegram_bot/setup.bat), OR run:
  ```bash
  pip install -r requirements.txt
  ```
- **On Linux / Mac**:
  ```bash
  pip3 install -r requirements.txt
  ```

### Step 3: Configure `.env`
Open [`telegram_bot/.env`](file:///c:/Users/mrdeb/Desktop/ProjectCompleted/gemini/telegram_bot/.env) and set your credentials:

```ini
# Bot token obtained from @BotFather on Telegram
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRstuVWXyz

# Your Telegram User ID (find using @userinfobot or @raw_data_bot)
ADMIN_IDS=123456789

# Number of referrals needed to unlock Premium Gemini Access
REQUIRED_REFERRALS=3

# Force Join Status (True / False)
FORCE_JOIN_ENABLED=True

# Private Log Channel ID (Must add bot as Administrator with Post Messages permission)
LOG_CHANNEL_ID=-1001234567890

# Optional HTTP/HTTPS proxy if needed
PROXY_URL=
```

### Step 4: Run the Bot
- **On Windows**: Double-click [`run.bat`](file:///c:/Users/mrdeb/Desktop/ProjectCompleted/gemini/telegram_bot/run.bat), OR run:
  ```bash
  python bot.py
  ```
- **On Linux / VPS**:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```

---

## 👑 Commands & Emoji Menu Reference

| Command / Button | Description |
|---|---|
| `💎 Claim Gemini 12-Month Pro` or `/claim` | Interactive wizard to input Gmail, verify OTP, and claim 12-Month Gemini Trial |
| `👥 Refer Friends (Earn Premium)` or `/refer` | Shows your unique link, real referral stats, and transparent list of real referred users |
| `💬 Contact Support` or `/support` | Direct 1-to-1 help desk to send messages to Admins with 1-click admin replies |
| `👤 My Account & Claims` or `/account` | View your Telegram ID, registration date, referral count, and claimed Gemini links |
| `📖 Tutorial & FAQ` or `/help` | Explains how the automation, OTP verification, and referral systems work |
| `🛠️ Admin Dashboard` or `/admin` | Complete control dashboard for Broadcasts, Force-Join channels, and settings (Admins only) |

### Setting Up Required Channels
1. Add your bot as an **Administrator** in your Telegram Channel or Group (with invite users / view members permission).
2. Open the bot as Admin, click **🛠️ Admin Panel** > **📢 Force-Join Channels** > **➕ Add New Channel/Group**.
3. Send the channel information in this format:
   ```
   @mychannel | My Channel Title | https://t.me/mychannel
   ```
   Or for private channels:
   ```
   -1001234567890 | VIP Chat | https://t.me/+AbCdEfGhIjK
   ```
4. Done! All new users will now be required to join this channel before claiming the offer or using bot features.
