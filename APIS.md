# Internshala Automation - Complete API Reference

This document lists all the APIs utilized across the entire registration, verification, student profile onboarding, autocomplete, and Google Gemini 12-month trial offer claim workflows.

---

## Table of Contents
1. [Session & CSRF Token Acquisition](#1-session--csrf-token-acquisition)
2. [Student Registration (Trigger OTP)](#2-student-registration-trigger-otp)
3. [Email OTP Verification](#3-email-otp-verification)
4. [OTP Resend Flow (Unverified Accounts)](#4-otp-resend-flow-unverified-accounts)
5. [Forgot Password Fallback](#5-forgot-password-fallback)
6. [Location Autocomplete API](#6-location-autocomplete-api)
7. [College Autocomplete API](#7-college-autocomplete-api)
8. [Stream Autocomplete API](#8-stream-autocomplete-api)
9. [Category Recommendation API](#9-category-recommendation-api)
10. [Student Personal Details Update](#10-student-personal-details-update)
11. [Preferences Submission (Step 1 - Categories)](#11-preferences-submission-step-1---categories)
12. [Preferences Submission (Step 2 - Others: Modes & Locations)](#12-preferences-submission-step-2---others-modes--locations)
13. [Google Gemini Landing Page](#13-google-gemini-landing-page)
14. [Claim Google Gemini 12-Month Trial Offer](#14-claim-google-gemini-12-month-trial-offer)

---

## 1. Session & CSRF Token Acquisition
* **Method**: `GET`
* **URL**: `https://internshala.com/registration/student`
* **Headers**:
  ```http
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36
  Accept: */*
  Accept-Language: en-US,en;q=0.9
  ```
* **Purpose**: Fetches the initial cookies (`PHPSESSID`, `AWSALB`, `AWSALBTG`) and genuine CSRF token from the `csrf_cookie_name` cookie to prevent CSRF rejection errors.

---

## 2. Student Registration (Trigger OTP)
* **Method**: `POST`
* **URL**: `https://internshala.com/registration/student_submit`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  X-Requested-With: XMLHttpRequest
  Accept: application/json, text/javascript, */*; q=0.01
  Referer: https://internshala.com/registration/student
  X-Csrf-Token: <csrf_token>
  ```
* **Payload (Form Data)**:
  | Key | Description | Example |
  |---|---|---|
  | `csrf_test_name` | CSRF Token | `5943cef610a651dee1f5e559de2b76d3` |
  | `utm_source` | Source tracking | `firstfold_hp` |
  | `utm_medium` | Medium tracking | `""` |
  | `utm_campaign` | Campaign tracking | `""` |
  | `student_referral` | Referral parameter | `""` |
  | `email` | User's email | `user@example.com` |
  | `password` | Account password | `Placement#1184` |
  | `first_name` | First name | `Aditi` |
  | `last_name` | Last name | `Chatterjee` |

* **Response Example (Success)**:
  ```json
  {
    "success": true,
    "successMsg": "Registration successful! Please verify your email with the OTP sent."
  }
  ```

---

## 3. Email OTP Verification
* **Method**: `POST`
* **URL**: `https://internshala.com/registration/verify_email_submit`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  X-Requested-With: XMLHttpRequest
  Accept: application/json, text/javascript, */*; q=0.01
  Referer: https://internshala.com/registration/verify_email
  X-Csrf-Token: <csrf_token>
  ```
* **Payload (Form Data)**:
  | Key | Description | Example |
  |---|---|---|
  | `csrf_test_name` | CSRF Token | `<csrf_token>` |
  | `user_email` | User email address | `user@example.com` |
  | `otp` | 6-digit OTP code | `451248` |

* **Response Example (Success)**:
  ```json
  {
    "success": true,
    "user_type": "student",
    "is_from_resume_checker": false
  }
  ```

---

## 4. OTP Resend Flow (Unverified Accounts)
Used when an account was already registered but not yet verified.

### Step 4A: Initialize Unconfirmed Session State
* **Method**: `GET`
* **URL**: `https://internshala.com/registration/verify_unconfirmed_login`
* **Headers**: Browser standard headers

### Step 4B: Trigger Resend OTP
* **Method**: `GET`
* **URL**: `https://internshala.com/registration/resend_otp`
* **Headers**:
  ```http
  X-Requested-With: XMLHttpRequest
  Referer: https://internshala.com/registration/verify_email
  Accept: application/json, text/javascript, */*; q=0.01
  X-Csrf-Token: <csrf_token>
  ```
* **Response Example**:
  ```json
  {
    "success": true,
    "successMsg": "OTP has been resent to your email address."
  }
  ```

---

## 5. Forgot Password Fallback
Used for already registered & verified accounts.
* **Method**: `POST`
* **URL**: `https://internshala.com/login/forgot_password_submit`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  X-Requested-With: XMLHttpRequest
  Accept: application/json, text/javascript, */*; q=0.01
  Referer: https://internshala.com/login/forgot_password
  X-Csrf-Token: <csrf_token>
  ```
* **Payload (Form Data)**:
  ```
  csrf_test_name: <csrf_token>
  user_type: student
  email: <user_email>
  campaign: ""
  action: forgot_password_submit
  ```
* **Note**: On the web client, Internshala integrates Google reCAPTCHA Enterprise (`action: forgot_password_submit`).

---

## 6. Location Autocomplete API
* **Method**: `GET`
* **URL**: `https://internshala.com/autocomplete/location/{city}`
  * Examples: `/autocomplete/location/kolkata`, `/autocomplete/location/delhi`, `/autocomplete/location/mumbai`
* **Headers**:
  ```http
  X-Requested-With: XMLHttpRequest
  Referer: https://internshala.com/student/personal_details
  Accept: application/json, text/javascript, */*; q=0.01
  ```
* **Response Example**:
  ```json
  {
    "success": true,
    "result": [
      {
        "id": 977,
        "name": "Mumbai, Maharashtra, India",
        "short_name": "Mumbai"
      },
      {
        "id": 131263,
        "name": "Mumbai Central, Mumbai, Konkan Division, Maharashtra, India",
        "short_name": "Mumbai Central"
      }
    ]
  }
  ```

---

## 7. College Autocomplete API
* **Method**: `GET`
* **URL**: `https://internshala.com/autocomplete/college/{query}`
  * Example: `https://internshala.com/autocomplete/college/IIT`
* **Headers**:
  ```http
  X-Requested-With: XMLHttpRequest
  Referer: https://internshala.com/student/personal_details
  Accept: application/json, text/javascript, */*; q=0.01
  ```
* **Response Example**:
  ```json
  {
    "success": true,
    "result": [
      "Indian Institute Of Technology Madras",
      "Indian Institute Of Technology Roorkee",
      "IIT Kharagpur",
      "Indian Institute Of Technology Bombay",
      "Indian Institute Of Technology Guwahati",
      "IIT Kanpur",
      "IIT (ISM) Dhanbad",
      "Indian Institute Of Technology Delhi"
    ]
  }
  ```

---

## 8. Stream Autocomplete API
* **Method**: `GET`
* **URL**: `https://internshala.com/autocomplete/stream/{query}`
  * Example: `https://internshala.com/autocomplete/stream/cse`
* **Headers**:
  ```http
  X-Requested-With: XMLHttpRequest
  Referer: https://internshala.com/student/personal_details
  Accept: application/json, text/javascript, */*; q=0.01
  ```
* **Response Example**:
  ```json
  {
    "success": true,
    "result": [
      "Computer Science & Engineering"
    ]
  }
  ```

---

## 9. Category Recommendation API
* **Method**: `POST`
* **URL**: `https://internshala.com/user_preference/load_category_recommendation`
* **Headers**:
  ```http
  X-Requested-With: XMLHttpRequest
  Referer: https://internshala.com/student/resume
  Accept: application/json, text/javascript, */*; q=0.01
  ```
* **Response Example**:
  ```json
  {
    "success": true,
    "category": {
      "popular": [
        { "name": "Web Development", "label": "Web Development" },
        { "name": "Software Development", "label": "Software Development" },
        { "name": "Programming", "label": "Programming" },
        { "name": "Data Science", "label": "Data Science" },
        { "name": "Python/Django", "label": "Python/Django" },
        { "name": "UI/UX", "label": "UI/UX" },
        { "name": "Software Testing", "label": "Software Testing" }
      ],
      "recommended": []
    }
  }
  ```

---

## 10. Student Personal Details Update
* **Method**: `POST`
* **URL**: `https://internshala.com/student/personal_details_update`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  X-Requested-With: XMLHttpRequest
  Accept: application/json, text/javascript, */*; q=0.01
  Referer: https://internshala.com/student/resume
  X-Csrf-Token: <csrf_token>
  ```
* **Payload (Form Data)**:
  | Key | Description | Example |
  |---|---|---|
  | `first_name` | Indian first name | `Aditi` |
  | `last_name` | Indian last name | `Chatterjee` |
  | `country_code` | Mandatory Country code | `+91` |
  | `phone_primary` | Unique 10-digit mobile number | `8359484258` |
  | `current_city_location_id` | Autocomplete Location ID | `977` |
  | `gender` | Gender | `Male` |
  | `languages[]` | Language | `English` |
  | `linkedin_url` | LinkedIn Profile URL | `""` |
  | `type` | Student type | `College student` |
  | `personal_details_resume_submit` | Action mode | `web_add` |
  | `course` | Degree course | `B.Tech` |
  | `college` | Autocomplete IIT College | `IIT (ISM) Dhanbad` |
  | `stream` | Autocomplete Stream | `Computer Science & Engineering` |
  | `start_year` | Graduation start year | `2025` or `2026` |
  | `end_year` | Graduation end year | `2029` or `2030` |
  | `csrf_test_name` | CSRF Token | `<csrf_token>` |

* **Response Example (Success)**:
  ```json
  {
    "success": true,
    "errorCode": "",
    "successMsg": "Personal details updated successfully."
  }
  ```

---

## 11. Preferences Submission (Step 1 - Categories)
* **Method**: `POST`
* **URL**: `https://internshala.com/user_preference/preferences_submit`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  X-Requested-With: XMLHttpRequest
  Accept: application/json, text/javascript, */*; q=0.01
  Referer: https://internshala.com/student/resume
  X-Csrf-Token: <csrf_token>
  ```
* **Payload (Form Data)**:
  ```
  referral: personal_details
  form_type: categories
  csrf_test_name: <csrf_token>
  categories[]: Web Development
  categories[]: Software Development
  categories[]: Programming
  ```
* **Response Example**:
  ```json
  {
    "success": true,
    "errorCode": "",
    "submit_cta_text": "Find me opportunities",
    "progress_percentage": 100,
    "success_page": "/internships"
  }
  ```

---

## 12. Preferences Submission (Step 2 - Others: Modes & Locations)
* **Method**: `POST`
* **URL**: `https://internshala.com/user_preference/preferences_submit`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  X-Requested-With: XMLHttpRequest
  Accept: application/json, text/javascript, */*; q=0.01
  Referer: https://internshala.com/student/resume
  X-Csrf-Token: <csrf_token>
  ```
* **Payload (Form Data)**:
  ```
  referral: personal_details
  form_type: others
  csrf_test_name: <csrf_token>
  preference_type[]: Internships
  mode[]: Work from home
  mode[]: In-office
  locations[]: <location_id>
  ```
* **Response Example**:
  ```json
  {
    "success": true,
    "errorCode": "",
    "success_page": "/internships"
  }
  ```

---

## 13. Google Gemini Landing Page
* **Method**: `GET`
* **URL**: `https://internshala.com/google-gemini-ai-plus`
* **Headers**: Standard browser session headers
* **Purpose**: Simulates navigating to the campaign landing page and setting the session referer context.

---

## 14. Claim Google Gemini 12-Month Trial Offer
Simulates clicking the **"Start FREE 12 months trial"** CTA button.
* **Method**: `POST`
* **URL**: `https://internshala.com/campaign/register_submit`
* **Headers**:
  ```http
  Content-Type: application/x-www-form-urlencoded; charset=UTF-8
  X-Requested-With: XMLHttpRequest
  Accept: application/json, text/javascript, */*; q=0.01
  Referer: https://internshala.com/google-gemini-ai-plus
  X-Csrf-Token: <csrf_token>
  ```
* **Payload (Form Data)**:
  | Key | Value |
  |---|---|
  | `campaign` | `google_gemini_jul_2026` |
  | `csrf_test_name` | `<csrf_token>` |

* **Response Example (Success)**:
  ```json
  {
    "success": true,
    "successPage": "https://one.google.com/offer/P5S790QW2STUYJ0MPV8A",
    "buttonText": "Close",
    "errorThrown": "",
    "csrf_token": "csrf_test_name",
    "csrf_hash": "5943cef610a651dee1f5e559de2b76d3"
  }
  ```
* **Result**: The script extracts the Google One trial URL (`successPage`), allowing the user to redeem the 12-month complimentary Google AI Plus subscription directly.
