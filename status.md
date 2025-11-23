# Development Log & Status Update

**Date Range:** November 16, 2025 – November 17, 2025  
**Status:** All Week 1 Pendings Cleared

---

## 📅 November 16, 2025

### 23:31 (11:31 PM)
> "Everything is working as expected. Session handling, update, and add issues have been resolved."

---

## 📅 November 17, 2025

### 14:58 (2:58 PM)
* **Git Update:** Created a backup commit before initiating major updates for the `develop` branch.

### 15:03 (3:03 PM) - Week 1 Pending Tasks
*Below is the status of tasks identified for Week 1 cleanup.*

- [x] **Sorting:** Implemented High-to-Low sorting logic. *(Fixed - 8:16 PM)*
- [x] **Description Formatting:** Removed raw `<p>` tags from the description output. *(Fixed - 8:23 PM)*
- [x] **UI Update:** Switched from Card view to List view for category listing. *(Fixed - 8:43 PM)*
- [x] **Validation:** Enforced minimum 3-image validation for uploads. *(Fixed - 9:07 PM)*
- [x] **User Session Issues:** Resolved session handling bugs on the user side. *(Details below)*
- [x] **Database Optimization:** Refactored Product Post slug generation. *(Details below)*

---

### 🛠 Technical Resolutions

#### 1. User Session Handling
**Issue:** Issues regarding session persistence and redundant code.
**Fixes:**
* **Refactoring:** Created a new `SecureUserMixin` in the Profile Page to reduce the redundant use of `@never_cache` decorators and `LoginRequiredMixin`.
* **URL Routing:** Updated Project URLs to use `allauth.socialaccount.providers.google.urls` instead of the generic `allauth.urls` (optimized for Google-only auth).
* **Settings:** Updated `LOGIN_URL` to `accounts/login` and added `ACCOUNT_AUTHENTICATED_LOGIN_REDIRECTS`.
* **Views:** Implemented `Google_callback_safe` in the Accounts View.
    * *Logic:* If a user is already logged in via Google, they are prevented from accessing login-related pages and are redirected immediately to the Home page.

#### 2. Slug Generation (N+1 Problem)
**Issue:** The previous `while` loop implementation for unique slugs caused performance issues.
* *Old Logic:* If "shirt" existed, it looped to try "shirt-1", checking the database every time. This resulted in an **N+1 problem** (multiple database hits for a single save).
**Fix:**
* Removed the manual `while` loop.
* Implemented **`django-autoslug`** to handle unique slug generation efficiently without excessive database queries.

---

### ✅ Summary
**Status:** All pending tasks cleared.
**Timestamp:** November 17, 2025 - 10:16 PM


# Cloudinary Implementation

I updated my static files to the Cloudinary database.  
**Time:** 10:17 AM


# ✏️ Edit Profile Information — Update Implemented

The **"Edit Profile Information"** functionality has been successfully implemented.  
Users can now update their personal details directly from the profile page.

---

## 🛠 Implementation Details

The following fields are now fully editable and state-managed:

- **First Name** (`fname`)
- **Last Name** (`lname`)
- **Phone Number** (`phonenumber`)
**Time:** 12:57 PM

- **Email** (`email`) 

(`New column is added to accounts.models (`is_varified`)`)

## 🛠 Implementation Details
---
**Email templates change from old normal design to a new look design**  
**Time:** 9:26 PM

## 🛠 Implementation Details
---
**Email Verification is add with a Modal**
**Time:** 12:48 PM

## Profile Implementation Is Completed
**Time:** 12 :50
-----

## 📇 Address Crud Operation is implemented
---
# Now user can add , edit, and delete their address
**Time:** 3:33PM 23-11-2025
 
## 🔐 Password Change 
---
# User can now change the password and change password
**Time :**  6:02 PM 23-11-2025

## 📷 Profile update 
---
# User can now Update/ change their profile
**Time :** 10:31PM 23-11-2025
