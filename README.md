# Instagram Toolkit — @kuromirage

A set of Python scripts for Instagram account management.
Built for Android/Termux — no Selenium or ChromeDriver needed.

## Requirements
```bash
pip install requests
```

---

## Scripts

### hunter15.py — Follower Analyzer & Auto-Unfollower
Parses your Instagram data export to find who doesn't follow
you back, then automatically unfollows them using Instagram's
web API directly.

**Features:**
- Parses `following.html` + `followers_*.html` from data export
- Bulk fetches user IDs from your own following list (avoids rate limits)
- Auto-unfollows non-followers with human-like delays
- Handles login checkpoint/verification flow
- Saves session to avoid re-logging in
- Caches user IDs across sessions

**Usage:**
```bash
python hunter15.py
# [1] Parse only
# [2] Auto-unfollow (saved session)
# [3] Parse + unfollow in one go
# [4] Clear saved session
```

**How to get your Instagram data export:**
1. Instagram app → Settings → Your Activity
2. Download Your Information → Download to Device
3. Format: HTML | Date range: All time
4. Wait for email → download → extract
5. Place `following.html` + `followers_*.html` in same folder as script

---

### geo_grow.py — Growth Manager
Automatically grows your following by targeting quality accounts
in your niche (tech/Africa).

**Features:**
- Fetches followers of seed accounts (e.g. similar tech creators)
- Filters accounts: 500–10K followers, active, not brands
- Auto-follows + likes 2 recent posts per user
- Hashtag targeting (#kenyatech #africatech etc.)
- Auto-unfollows non-followers after 3 days
- Daily limit: 25 follows, 60 likes (safe limits)
- Tracks everything in `follow_log.json`

**Usage:**
```bash
python geo_grow.py
# [1] Follow seed account followers
# [2] Follow + like via hashtags
# [3] Unfollow non-followers (3+ days)
# [4] View growth stats
# [5] Full session (1 + 2 + 3)
```

**Recommended schedule:**
```
Daily       → run option 1 or 2
Every 3-4 days → run option 3
```

---

## Files Created at Runtime
| File | Purpose |
|------|---------|
| `ig_session.json` | Saved login session (shared by both scripts) |
| `instagram_results.json` | Parsed follower analysis results |
| `follow_log.json` | Growth tracking — who you followed + follow-back status |
| `id_cache.json` | Cached numeric user IDs |
| `unfollow_log.json` | Log of all unfollow actions |

---

## ⚠️ Disclaimer
Automated actions may violate Instagram's Terms of Service.
Use at your own risk. Recommended limits:
- Max 25 follows per day
- Max 60 likes per day  
- Run in small batches with delays
