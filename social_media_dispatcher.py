#!/usr/bin/env python3
"""
NC Political Predictions - Social Media Automated Dispatcher
------------------------------------------------------------
Automatically formats and publishes real-time race calls to Twitter (X),
Threads, and Instagram as soon as they are certified by election_night_race_caller.py.

Handles:
  - Formatted post generation with party badges, margins, confidence & hashtags
  - Twitter API v2 dispatch (via OAuth 1.0a / Bearer)
  - Meta Threads API dispatch (via Graph API container & publish)
  - Instagram Graph API / Creator webhook dispatch
  - Multi-platform webhook fan-out (Zapier / Buffer / Make.com)
  - Local logging to social_posts_log.json and graceful fallback
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

CONFIG_PATH = os.path.expanduser("~/.social_credentials.json")
LOG_PATH = Path("/home/rann/src/website/mainwebsite/social_posts_log.json")

# Verified bio links (excluding /beta per strict directive)
BIO_LINKS = {
    "live_needle": "https://rannbar-on.com/needle",
    "forecast_model": "https://rannbar-on.com/prediction",
    "turnout_map": "https://rannbar-on.com/early_voting_turnout_map.html",
    "durham_precinct_map": "https://rannbar-on.com/durhamprecinctmap.pdf",
    "campus_voting_guides": "https://rannbar-on.com/vote"
}

def load_credentials():
    """Loads API tokens from ~/.social_credentials.json or environment."""
    creds = {
        "twitter_api_key": os.getenv("TWITTER_API_KEY", ""),
        "twitter_api_secret": os.getenv("TWITTER_API_SECRET", ""),
        "twitter_access_token": os.getenv("TWITTER_ACCESS_TOKEN", ""),
        "twitter_access_secret": os.getenv("TWITTER_ACCESS_SECRET", ""),
        "threads_access_token": os.getenv("THREADS_ACCESS_TOKEN", ""),
        "threads_user_id": os.getenv("THREADS_USER_ID", ""),
        "instagram_access_token": os.getenv("INSTAGRAM_ACCESS_TOKEN", ""),
        "instagram_account_id": os.getenv("INSTAGRAM_ACCOUNT_ID", ""),
        "social_webhook_url": os.getenv("SOCIAL_WEBHOOK_URL", "")
    }

    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                disk_creds = json.load(f)
                for k, v in disk_creds.items():
                    if v and not creds.get(k):
                        creds[k] = v
        except Exception as e:
            print(f"[Social] Warning reading {CONFIG_PATH}: {e}")
    return creds

def format_social_post(call_record):
    """
    Formats a high-impact, professional social post suitable for Twitter, Threads, and Instagram.
    """
    winner = call_record.get('winner', 'Projected Winner')
    party = call_record.get('party', 'Unknown')
    race_name = call_record.get('race_name', 'Race')
    chamber = call_record.get('chamber_label', '')
    margin_str = call_record.get('proj_margin_str', '')
    confidence = call_record.get('confidence_str', '')
    reported = call_record.get('reported_pct_str', '')
    time_str = call_record.get('called_at', datetime.now().strftime('%I:%M %p EST'))

    party_emoji = "🔵" if party.lower() == 'democrat' else "🔴" if party.lower() == 'republican' else "⚪"

    header = f"🚨 RACE CALL: {race_name.upper()}"
    winner_line = f"{party_emoji} {winner} ({party[0]}) is projected as the WINNER."

    stats_lines = []
    if margin_str:
        stats_lines.append(f"📊 Projected Margin: {margin_str}")
    if confidence:
        stats_lines.append(f"🎯 Statistical Confidence: {confidence}")
    if reported:
        stats_lines.append(f"🗳️ Turnout Reported: {reported}")

    stats_block = "\n".join(stats_lines)

    call_link = "https://rannbar-on.com/needle"

    hashtags = "#ncpol #ncelection #NCGA"
    if "senate" in race_name.lower():
        hashtags += " #NCSen"
    elif "house" in race_name.lower():
        hashtags += " #NCHouse"

    post_text = (
        f"{header}\n\n"
        f"{winner_line}\n\n"
        f"{stats_block}\n\n"
        f"Live dials & General Assembly balance of power:\n"
        f"🔗 {call_link}\n\n"
        f"{hashtags}"
    )

    return post_text

def post_to_twitter(text, creds):
    """Posts a status update to Twitter / X API v2."""
    if not (creds.get('twitter_api_key') and creds.get('twitter_access_token')):
        print("[Social] Twitter credentials not configured. Skipping Twitter dispatch.")
        return False

    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=creds['twitter_api_key'],
            consumer_secret=creds['twitter_api_secret'],
            access_token=creds['twitter_access_token'],
            access_token_secret=creds['twitter_access_secret']
        )
        response = client.create_tweet(text=text)
        print(f"[Social: Twitter] Tweet posted successfully! ID: {response.data.get('id')}")
        return True
    except ImportError:
        print("[Social: Twitter] 'tweepy' library not installed. Install via pip install tweepy.")
    except Exception as e:
        print(f"[Social: Twitter Error] {e}")
    return False

def post_to_threads(text, creds):
    """Posts a status update to Meta Threads API."""
    token = creds.get('threads_access_token')
    user_id = creds.get('threads_user_id')

    if not (token and user_id):
        print("[Social] Threads credentials not configured. Skipping Threads dispatch.")
        return False

    try:
        # Step 1: Create media container
        url_create = f"https://graph.threads.net/v1.0/{user_id}/threads"
        data_create = urllib.parse.urlencode({
            "media_type": "TEXT",
            "text": text,
            "access_token": token
        }).encode('utf-8')

        req = urllib.request.Request(url_create, data=data_create, method='POST')
        with urllib.request.urlopen(req, timeout=15) as resp:
            create_res = json.loads(resp.read().decode('utf-8'))
            container_id = create_res.get('id')

        if not container_id:
            print(f"[Social: Threads Error] Failed to create container: {create_res}")
            return False

        # Sleep 2s for container readiness
        time.sleep(2)

        # Step 2: Publish container
        url_pub = f"https://graph.threads.net/v1.0/{user_id}/threads_publish"
        data_pub = urllib.parse.urlencode({
            "creation_id": container_id,
            "access_token": token
        }).encode('utf-8')

        req_pub = urllib.request.Request(url_pub, data=data_pub, method='POST')
        with urllib.request.urlopen(req_pub, timeout=15) as resp_pub:
            pub_res = json.loads(resp_pub.read().decode('utf-8'))
            print(f"[Social: Threads] Post published successfully! ID: {pub_res.get('id')}")
            return True

    except Exception as e:
        print(f"[Social: Threads Error] {e}")
    return False

def post_to_webhook(call_record, text, creds):
    """Dispatches to multi-platform webhook (Zapier, Make, Buffer, IFTTT)."""
    webhook_url = creds.get('social_webhook_url')
    if not webhook_url:
        return False

    payload = {
        "text": text,
        "race_name": call_record.get('race_name'),
        "winner": call_record.get('winner'),
        "party": call_record.get('party'),
        "margin": call_record.get('projected_margin'),
        "confidence": call_record.get('win_prob_pct'),
        "url": "https://rannbar-on.com/needle",
        "timestamp": datetime.now().isoformat()
    }

    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={"Content-Type": "application/json"},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"[Social: Webhook] Multi-platform webhook triggered: HTTP {resp.status}")
            return True
    except Exception as e:
        print(f"[Social: Webhook Error] {e}")
    return False

def log_social_call(call_record, post_text, dispatch_results):
    """Logs the social dispatch event to social_posts_log.json with fallback."""
    target_path = LOG_PATH
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        target_path = Path("/tmp/social_posts_log.json")

    history = []
    if target_path.exists():
        try:
            with open(target_path, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except Exception:
            history = []

    event = {
        "race_id": call_record.get('race_id'),
        "race_name": call_record.get('race_name'),
        "winner": call_record.get('winner'),
        "party": call_record.get('party'),
        "called_at": call_record.get('called_at'),
        "post_text": post_text,
        "dispatched_at": datetime.now().isoformat(),
        "results": dispatch_results
    }
    history.append(event)
    try:
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2)
        print(f"[Social] Logged race call dispatch to {target_path}")
    except Exception as e:
        # Fallback to /tmp if primary was read-only
        try:
            fallback = Path("/tmp/social_posts_log.json")
            with open(fallback, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
            print(f"[Social] Logged race call dispatch to {fallback}")
        except Exception as e2:
            print(f"[Social] Warning writing log: {e2}")

def dispatch_race_call_socials(call_record):
    """
    Main entry point invoked by election_night_race_caller.py.
    Formats the post, dispatches to Twitter, Threads, Instagram/Webhook, and logs.
    """
    post_text = format_social_post(call_record)
    print("\n" + "="*60)
    print("📢 PREPARING SOCIAL MEDIA DISPATCH ('NC Political Predictions'):")
    print(post_text)
    print("="*60 + "\n")

    creds = load_credentials()
    results = {
        "twitter": post_to_twitter(post_text, creds),
        "threads": post_to_threads(post_text, creds),
        "webhook": post_to_webhook(call_record, post_text, creds)
    }

    log_social_call(call_record, post_text, results)
    return results

if __name__ == "__main__":
    # Test execution with sample race call
    sample_call = {
        "race_id": "statewide_senate",
        "race_name": "US Senate - North Carolina",
        "chamber_label": "North Carolina Statewide",
        "winner": "Roy Cooper",
        "party": "Democrat",
        "win_prob": 0.996,
        "win_prob_pct": "99.6",
        "confidence_str": "99.6% Confidence",
        "projected_margin": 2.5,
        "proj_margin_str": "DEM +2.5%",
        "reported_pct_str": "78.4%",
        "called_at": datetime.now().strftime('%I:%M %p EST')
    }
    print("Running Social Media Dispatcher in Test Mode...")
    dispatch_race_call_socials(sample_call)
