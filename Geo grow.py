"""
geo_grow.py — Instagram Growth Manager for @kuromirage
=======================================================
Strategy:
  1. Fetch followers of seed accounts
  2. Filter for quality accounts (500-10K followers, active, not brands)
  3. Auto-follow + like 2-3 posts (increases notice rate)
  4. After 3 days unfollow anyone who didn't follow back
  5. Hashtag targeting for tech niche

Works on Android/Termux — no Selenium needed.

Requirements:
    pip install requests

Usage:
    python geo_grow.py
"""

import os, sys, json, time, random, re
from datetime import datetime, timedelta

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ══════════════════════════════════════════════════════════════════════════════
#  CONFIG — edit these to customise behaviour
# ══════════════════════════════════════════════════════════════════════════════

CONFIG = {
    # Seed accounts — their followers are your target audience
    "seed_accounts": [
        "wanji.chenelle",
    ],

    # Hashtags to target
    "hashtags": [
        "kenyatech",
        "africatech",
        "techafrica",
        "coding",
        "programming",
        "aiafrica",
        "techkenya",
        "devkenya",
    ],

    # Follower count filter — skip too small or too big
    "min_followers": 500,
    "max_followers": 10000,

    # Max follows per day (stay safe)
    "max_follows_per_day": 25,

    # Max likes per day
    "max_likes_per_day": 60,

    # How many posts to like per user we follow
    "likes_per_user": 2,

    # Days before unfollowing non-followers
    "unfollow_after_days": 3,

    # Delays (seconds) between actions — humanlike
    "delay_between_follows" : (30, 70),
    "delay_between_likes"   : (8,  20),
    "delay_between_pages"   : (4,  10),
}

# ── File paths ─────────────────────────────────────────────────────────────
SESSION_FILE   = "ig_session.json"
FOLLOW_LOG     = "follow_log.json"       # tracks who we followed + when
PROCESSED_FILE = "processed_seeds.json"  # seeds/hashtags already scanned


# ══════════════════════════════════════════════════════════════════════════════
#  SESSION  (reuses hunter15 session file)
# ══════════════════════════════════════════════════════════════════════════════

WEB_HEADERS = {
    "User-Agent"      : "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept"          : "*/*",
    "Accept-Language" : "en-US,en;q=0.9",
    "Accept-Encoding" : "gzip, deflate, br",
    "X-IG-App-ID"     : "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Referer"         : "https://www.instagram.com/accounts/login/",
    "Origin"          : "https://www.instagram.com",
    "Connection"      : "keep-alive",
}

API_HEADERS = {
    "User-Agent"      : "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0.0.0 Mobile Safari/537.36",
    "Accept"          : "*/*",
    "Accept-Language" : "en-US,en;q=0.9",
    "X-IG-App-ID"     : "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Referer"         : "https://www.instagram.com/",
    "Origin"          : "https://www.instagram.com",
}


def load_session():
    if not os.path.exists(SESSION_FILE):
        return None
    with open(SESSION_FILE) as f:
        return json.load(f)


def save_session(data):
    with open(SESSION_FILE, "w") as f:
        json.dump(data, f, indent=2)


def restore_session(saved):
    s = requests.Session()
    s.headers.update(API_HEADERS)
    s.headers["X-CSRFToken"] = saved["csrftoken"]
    s.cookies.set("sessionid",  saved["sessionid"],  domain=".instagram.com")
    s.cookies.set("csrftoken",  saved["csrftoken"],   domain=".instagram.com")
    s.cookies.set("ds_user_id", saved["user_id"],     domain=".instagram.com")
    return s


def verify_session(session):
    try:
        r = session.get(
            "https://www.instagram.com/api/v1/accounts/current_user/?edit=true",
            timeout=10
        )
        return r.status_code == 200 and "user" in r.text
    except Exception:
        return False


def login_web(username, password):
    print(f"\n🔐  Logging in as @{username}...")
    s = requests.Session()
    s.headers.update(WEB_HEADERS)

    try:
        r    = s.get("https://www.instagram.com/accounts/login/", timeout=15)
        csrf = s.cookies.get("csrftoken", "")
        if not csrf:
            m    = re.search(r'"csrf_token":"([^"]+)"', r.text)
            csrf = m.group(1) if m else ""
        if not csrf:
            print("   ✘  Could not get CSRF token")
            return None
    except Exception as e:
        print(f"   ✘  {e}")
        return None

    time.sleep(random.uniform(2, 4))
    s.headers["X-CSRFToken"] = csrf

    payload = {
        "username"            : username,
        "enc_password"        : f"#PWD_INSTAGRAM_BROWSER:0:{int(time.time())}:{password}",
        "queryParams"         : "{}",
        "optIntoOneTap"       : "false",
        "stopDeletionNonce"   : "",
        "trustedDeviceRecords": "{}",
    }

    try:
        r = s.post(
            "https://www.instagram.com/api/v1/web/accounts/login/ajax/",
            data=payload, timeout=20,
        )
    except Exception as e:
        print(f"   ✘  {e}")
        return None

    if not r.text.strip():
        print("   ✘  Empty response — try turning off VPN.")
        return None

    try:
        data = r.json()
    except Exception:
        print(f"   ✘  Bad response: {r.text[:100]}")
        return None

    if data.get("checkpoint_url") or "checkpoint" in str(data):
        url = data.get("checkpoint_url", "")
        full = f"https://www.instagram.com{url}" if url.startswith("/") else url
        print(f"\n   🔒  Verification needed!")
        print(f"      Open: {full}")
        input("      Press Enter after completing... ")
        time.sleep(3)
        try:
            r    = s.post(
                "https://www.instagram.com/api/v1/web/accounts/login/ajax/",
                data=payload, timeout=20,
            )
            data = r.json()
        except Exception:
            pass

    if data.get("two_factor_required"):
        info       = data.get("two_factor_info", {})
        identifier = info.get("two_factor_identifier", "")
        code       = input("   Enter 2FA code: ").strip()
        r2   = s.post(
            "https://www.instagram.com/api/v1/web/accounts/login/ajax/two_factor/",
            data={"username": username, "verificationCode": code,
                  "two_factor_identifier": identifier, "queryParams": "{}"},
            timeout=20,
        )
        data = r2.json()

    if data.get("authenticated"):
        sessionid = s.cookies.get("sessionid", "")
        csrftoken = s.cookies.get("csrftoken", csrf)
        user_id   = data.get("userId", "")
        save_session({"username": username, "user_id": str(user_id),
                      "sessionid": sessionid, "csrftoken": csrftoken})
        s.headers.update(API_HEADERS)
        s.headers["X-CSRFToken"] = csrftoken
        print(f"   ✔  Logged in! user_id={user_id}")
        return s

    if data.get("authenticated") is False:
        print("   ✘  Wrong password.")
    else:
        print(f"   ✘  Login failed: {data.get('message','')}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  FOLLOW LOG  — tracks who we followed and when
# ══════════════════════════════════════════════════════════════════════════════

def load_follow_log():
    if not os.path.exists(FOLLOW_LOG):
        return {}
    with open(FOLLOW_LOG) as f:
        return json.load(f)


def save_follow_log(log):
    with open(FOLLOW_LOG, "w") as f:
        json.dump(log, f, indent=2)


def followed_today(log):
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(1 for v in log.values() if v.get("followed_at", "").startswith(today))


def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return {}
    with open(PROCESSED_FILE) as f:
        return json.load(f)


def save_processed(data):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ══════════════════════════════════════════════════════════════════════════════
#  INSTAGRAM API HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def api_get(session, url, retries=2):
    """GET with basic rate limit handling."""
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=15)
            if r.status_code == 429:
                wait = 60 * (attempt + 1)
                print(f"      ⚠  Rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            return r
        except Exception as e:
            if attempt == retries:
                return None
            time.sleep(10)
    return None


def get_user_info(session, username):
    """Get basic profile info for a username."""
    r = api_get(session,
        f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}")
    if not r or r.status_code != 200:
        return None
    try:
        user = r.json()["data"]["user"]
        return {
            "id"             : str(user["id"]),
            "username"       : user["username"],
            "followers"      : user["edge_followed_by"]["count"],
            "following"      : user["edge_follow"]["count"],
            "posts"          : user["edge_owner_to_timeline_media"]["count"],
            "is_private"     : user["is_private"],
            "is_business"    : user.get("is_business_account", False),
            "is_verified"    : user.get("is_verified", False),
            "full_name"      : user.get("full_name", ""),
        }
    except Exception:
        return None


def get_recent_posts(session, user_id, count=3):
    """Get recent post IDs for a user."""
    r = api_get(session,
        f"https://www.instagram.com/api/v1/feed/user/{user_id}/?count={count}")
    if not r or r.status_code != 200:
        return []
    try:
        items = r.json().get("items", [])
        return [str(item["id"]) for item in items[:count]]
    except Exception:
        return []


def like_post(session, media_id):
    """Like a post by media ID."""
    try:
        r = session.post(
            f"https://www.instagram.com/api/v1/media/{media_id}/like/",
            data={"media_id": media_id},
            timeout=15,
        )
        return r.status_code == 200
    except Exception:
        return False


def follow_user(session, user_id):
    """Follow a user by numeric ID."""
    try:
        r = session.post(
            f"https://www.instagram.com/api/v1/friendships/create/{user_id}/",
            data={"user_id": user_id},
            timeout=15,
        )
        return r.status_code == 200
    except Exception:
        return False


def unfollow_user(session, user_id):
    """Unfollow a user by numeric ID."""
    try:
        r = session.post(
            f"https://www.instagram.com/api/v1/friendships/destroy/{user_id}/",
            data={"user_id": user_id},
            timeout=15,
        )
        return r.status_code == 200
    except Exception:
        return False


def get_friendship_status(session, user_id):
    """Check if someone follows you back."""
    try:
        r = api_get(session,
            f"https://www.instagram.com/api/v1/friendships/show/{user_id}/")
        if not r or r.status_code != 200:
            return None
        data = r.json()
        return {
            "you_follow_them"  : data.get("following", False),
            "they_follow_you"  : data.get("followed_by", False),
        }
    except Exception:
        return None


def get_seed_followers(session, seed_username, max_users=200):
    """Fetch followers of a seed account."""
    print(f"\n   📥  Fetching followers of @{seed_username}...")

    # First get the seed account's user ID
    info = get_user_info(session, seed_username)
    if not info:
        print(f"   ✘  Could not find @{seed_username}")
        return []

    seed_id   = info["id"]
    followers = []
    next_page = None
    page      = 1

    while len(followers) < max_users:
        url = f"https://www.instagram.com/api/v1/friendships/{seed_id}/followers/?count=50"
        if next_page:
            url += f"&max_id={next_page}"

        r = api_get(session, url)
        if not r or r.status_code != 200:
            break

        try:
            data  = r.json()
            users = data.get("users", [])
        except Exception:
            break

        for user in users:
            followers.append({
                "id"        : str(user.get("pk", "")),
                "username"  : user.get("username", ""),
                "followers" : user.get("follower_count", 0),
                "is_private": user.get("is_private", False),
                "is_verified": user.get("is_verified", False),
            })

        print(f"      Page {page}: {len(users)} fetched "
              f"({len(followers)} total)")

        next_page = data.get("next_max_id")
        if not next_page or not users:
            break

        page += 1
        time.sleep(random.uniform(*CONFIG["delay_between_pages"]))

    return followers


def get_hashtag_posts(session, hashtag, count=50):
    """Fetch recent posts for a hashtag."""
    print(f"\n   #️⃣  Fetching posts for #{hashtag}...")

    # Get hashtag ID first
    r = api_get(session,
        f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={hashtag}")
    if not r or r.status_code != 200:
        return []

    try:
        data       = r.json()
        hashtag_id = data["data"]["hashtag"]["id"]
    except Exception:
        return []

    # Fetch recent posts
    r = api_get(session,
        f"https://www.instagram.com/api/v1/feed/tag/{hashtag_id}/?count={count}")
    if not r or r.status_code != 200:
        return []

    try:
        items = r.json().get("items", [])
        posts = []
        for item in items:
            user = item.get("user", {})
            posts.append({
                "media_id"       : str(item.get("id", "")),
                "user_id"        : str(user.get("pk", "")),
                "username"       : user.get("username", ""),
                "user_followers" : user.get("follower_count", 0),
                "is_verified"    : user.get("is_verified", False),
                "is_private"     : user.get("is_private", False),
            })
        return posts
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════════
#  QUALITY FILTER
# ══════════════════════════════════════════════════════════════════════════════

def is_quality_account(user, follow_log):
    """Returns (bool, reason) — True if worth following."""
    username  = user.get("username", "")
    followers = user.get("followers", user.get("user_followers", 0))

    if not username or not user.get("id", user.get("user_id", "")):
        return False, "missing data"
    if user.get("is_verified"):
        return False, "verified (big account)"
    if followers < CONFIG["min_followers"]:
        return False, f"too few followers ({followers})"
    if followers > CONFIG["max_followers"]:
        return False, f"too many followers ({followers})"
    if user.get("is_private"):
        return False, "private account"
    if username in follow_log:
        return False, "already followed"

    return True, "ok"


# ══════════════════════════════════════════════════════════════════════════════
#  CORE ACTIONS
# ══════════════════════════════════════════════════════════════════════════════

def follow_and_like(session, user, follow_log, likes_today_ref):
    """Follow a user and like their recent posts."""
    username = user.get("username", "")
    uid      = user.get("id") or user.get("user_id", "")

    # Follow
    ok = follow_user(session, uid)
    if ok:
        follow_log[username] = {
            "user_id"    : uid,
            "followed_at": datetime.now().isoformat(),
            "followed_back": None,
        }
        save_follow_log(follow_log)
        print(f"      ✔  Followed @{username}")
    else:
        print(f"      ✘  Failed to follow @{username}")
        return False

    time.sleep(random.uniform(5, 12))

    # Like recent posts
    liked = 0
    if likes_today_ref[0] < CONFIG["max_likes_per_day"]:
        posts = get_recent_posts(session, uid, CONFIG["likes_per_user"])
        for post_id in posts:
            if likes_today_ref[0] >= CONFIG["max_likes_per_day"]:
                break
            if like_post(session, post_id):
                liked += 1
                likes_today_ref[0] += 1
                time.sleep(random.uniform(*CONFIG["delay_between_likes"]))

    if liked:
        print(f"      ❤️   Liked {liked} post(s)")

    return True


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN GROWTH MODES
# ══════════════════════════════════════════════════════════════════════════════

def run_seed_follow(session, follow_log):
    """Follow quality accounts from seed account followers."""
    print(f"\n{'═'*52}")
    print(f"  🌱  SEED ACCOUNT GROWTH")
    print(f"{'═'*52}")

    follows_today = followed_today(follow_log)
    likes_today   = [0]   # mutable ref
    processed     = load_processed()

    if follows_today >= CONFIG["max_follows_per_day"]:
        print(f"  ⚠  Already hit daily follow limit ({CONFIG['max_follows_per_day']})")
        print(f"     Come back tomorrow!")
        return

    remaining = CONFIG["max_follows_per_day"] - follows_today
    print(f"  Can follow {remaining} more accounts today\n")

    for seed in CONFIG["seed_accounts"]:
        if follows_today >= CONFIG["max_follows_per_day"]:
            break

        followers = get_seed_followers(session, seed, max_users=300)
        if not followers:
            continue

        print(f"\n  🔍  Filtering {len(followers)} followers of @{seed}...")
        qualified = []
        for user in followers:
            ok, reason = is_quality_account(user, follow_log)
            if ok:
                qualified.append(user)

        print(f"  ✔  {len(qualified)} accounts passed the filter")
        random.shuffle(qualified)   # randomise order

        for user in qualified:
            if follows_today >= CONFIG["max_follows_per_day"]:
                print(f"\n  ✋  Daily limit reached ({CONFIG['max_follows_per_day']})")
                break

            ok = follow_and_like(session, user, follow_log, likes_today)
            if ok:
                follows_today += 1

            delay = random.uniform(*CONFIG["delay_between_follows"])
            print(f"      ⏳  Waiting {delay:.0f}s... "
                  f"({follows_today}/{CONFIG['max_follows_per_day']} today)")
            time.sleep(delay)

        # Mark seed as processed
        processed[seed] = datetime.now().isoformat()
        save_processed(processed)

    print(f"\n  ✅  Seed follow session complete — {follows_today} total follows today")


def run_hashtag_growth(session, follow_log):
    """Like posts and follow users via hashtags."""
    print(f"\n{'═'*52}")
    print(f"  #️⃣   HASHTAG GROWTH")
    print(f"{'═'*52}")

    follows_today = followed_today(follow_log)
    likes_today   = [0]

    if follows_today >= CONFIG["max_follows_per_day"]:
        print(f"  ⚠  Daily follow limit reached. Still liking posts...")

    for hashtag in CONFIG["hashtags"]:
        posts = get_hashtag_posts(session, hashtag, count=30)
        if not posts:
            continue

        print(f"\n  Found {len(posts)} posts for #{hashtag}")

        for post in posts:
            # Like the post regardless
            if likes_today[0] < CONFIG["max_likes_per_day"]:
                if like_post(session, post["media_id"]):
                    likes_today[0] += 1
                    print(f"      ❤️   Liked post by @{post['username']}")
                    time.sleep(random.uniform(*CONFIG["delay_between_likes"]))

            # Follow the poster if they qualify
            if follows_today < CONFIG["max_follows_per_day"]:
                ok, reason = is_quality_account(post, follow_log)
                if ok:
                    followed = follow_and_like(session, {
                        "id"      : post["user_id"],
                        "username": post["username"],
                        "followers": post["user_followers"],
                    }, follow_log, likes_today)
                    if followed:
                        follows_today += 1
                        delay = random.uniform(*CONFIG["delay_between_follows"])
                        print(f"      ⏳  Waiting {delay:.0f}s...")
                        time.sleep(delay)

        time.sleep(random.uniform(*CONFIG["delay_between_pages"]))

    print(f"\n  ✅  Hashtag session — {likes_today[0]} likes, {follows_today} follows today")


def run_unfollow_non_followers(session, follow_log):
    """Unfollow people who didn't follow back after X days."""
    print(f"\n{'═'*52}")
    print(f"  🔄  UNFOLLOW NON-FOLLOWERS")
    print(f"{'═'*52}")

    cutoff    = datetime.now() - timedelta(days=CONFIG["unfollow_after_days"])
    to_check  = []

    for username, data in follow_log.items():
        if data.get("followed_back") is not None:
            continue   # already resolved
        followed_at = datetime.fromisoformat(data.get("followed_at", datetime.now().isoformat()))
        if followed_at < cutoff:
            to_check.append((username, data))

    if not to_check:
        print(f"  ℹ️   No accounts ready to check yet")
        print(f"      (need {CONFIG['unfollow_after_days']} days after following)")
        return

    print(f"  Checking {len(to_check)} accounts followed {CONFIG['unfollow_after_days']}+ days ago...\n")

    unfollowed = followed_back = 0

    for username, data in to_check:
        uid    = data.get("user_id", "")
        status = get_friendship_status(session, uid)

        if not status:
            time.sleep(random.uniform(3, 7))
            continue

        if status["they_follow_you"]:
            follow_log[username]["followed_back"] = True
            followed_back += 1
            print(f"  ✅  @{username} follows you back — keeping")
        else:
            ok = unfollow_user(session, uid)
            if ok:
                follow_log[username]["followed_back"] = False
                unfollowed += 1
                print(f"  ❌  @{username} didn't follow back — unfollowed")
            time.sleep(random.uniform(20, 45))

        save_follow_log(follow_log)
        time.sleep(random.uniform(5, 12))

    print(f"\n  ✅  Done — {followed_back} follow back, {unfollowed} unfollowed")


def print_stats(follow_log):
    """Print a summary of growth activity."""
    total_followed  = len(follow_log)
    followed_back   = sum(1 for v in follow_log.values() if v.get("followed_back") is True)
    didnt_follow    = sum(1 for v in follow_log.values() if v.get("followed_back") is False)
    pending         = sum(1 for v in follow_log.values() if v.get("followed_back") is None)
    today           = datetime.now().strftime("%Y-%m-%d")
    followed_today_ = sum(1 for v in follow_log.values()
                          if v.get("followed_at","").startswith(today))

    rate = f"{followed_back/max(didnt_follow+followed_back,1)*100:.1f}%" \
           if (followed_back + didnt_follow) > 0 else "N/A"

    print(f"\n{'═'*52}")
    print(f"  📊  GROWTH STATS")
    print(f"{'═'*52}")
    print(f"  Total followed via script : {total_followed}")
    print(f"  Followed you back         : {followed_back}")
    print(f"  Didn't follow back        : {didnt_followed}")
    print(f"  Still pending (< 3 days)  : {pending}")
    print(f"  Follow-back rate          : {rate}")
    print(f"  Followed today            : {followed_today_}/{CONFIG['max_follows_per_day']}")
    print(f"{'═'*52}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════╗")
    print("║     geo_grow.py — @kuromirage            ║")
    print("║     Instagram Growth Manager             ║")
    print("╚══════════════════════════════════════════╝")
    print(f"""
  [1] 🌱  Follow seed account followers
  [2] #️⃣   Follow + like via hashtags
  [3] 🔄  Unfollow non-followers (3+ days old)
  [4] 📊  View growth stats
  [5] ⚙️   Run full session (1 + 2 + 3)
  [6] 🚪  Exit
""")

    if not REQUESTS_AVAILABLE:
        sys.exit("❌  Run: pip install requests")

    # ── Login ──────────────────────────────────────────────────────────────
    session = None
    saved   = load_session()

    if saved:
        print(f"✔  Found saved session for @{saved.get('username','?')}")
        session = restore_session(saved)
        print("   🔍  Verifying...", end=" ", flush=True)
        if verify_session(session):
            print("✔  Valid!")
        else:
            print("✘  Expired.")
            session = None

    if session is None:
        username = input("\n   Instagram username: ").strip()
        password = input("   Instagram password: ").strip()
        session  = login_web(username, password)
        if session is None:
            sys.exit("❌  Login failed.")

    follow_log = load_follow_log()
    choice     = input("\n  Choice [1-6]: ").strip()

    if choice == "1":
        run_seed_follow(session, follow_log)
    elif choice == "2":
        run_hashtag_growth(session, follow_log)
    elif choice == "3":
        run_unfollow_non_followers(session, follow_log)
    elif choice == "4":
        print_stats(follow_log)
    elif choice == "5":
        run_seed_follow(session, follow_log)
        time.sleep(random.uniform(30, 60))
        run_hashtag_growth(session, follow_log)
        time.sleep(random.uniform(30, 60))
        run_unfollow_non_followers(session, follow_log)
        print_stats(follow_log)
    elif choice == "6":
        print("   Bye! 👋")
    else:
        print("   Invalid choice.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⛔  Interrupted.")
