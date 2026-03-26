import asyncio
import os

import httpx
import tweepy

from constants.stations import nearest_station


async def send_sms(alert: dict, station: dict):
    api_key = os.getenv("FAST2SMS_API_KEY", "")
    if not api_key:
        print("[SMS] No API key, skipping")
        return

    maps_link = f"https://maps.google.com/?q={alert['lat']},{alert['lng']}"
    message = (
        f"SAFESIGHT ALERT\n"
        f"Location: {alert['location_name']}\n"
        f"Camera: {alert['camera_id']}\n"
        f"Confidence: {int(alert['confidence'] * 100)}%\n"
        f"Nearest Station: {station['name']}\n"
        f"Navigate: {maps_link}"
    )

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "https://www.fast2sms.com/dev/bulkV2",
                headers={"authorization": api_key},
                params={
                    "variables_values": message,
                    "route": "q",
                    "numbers": station["phone"],
                },
            )
            print(f"[SMS] Fired to {station['name']}: {resp.status_code}")
    except Exception as exc:
        print(f"[SMS] Failed: {exc}")


def send_twitter(alert: dict, station: dict):
    keys = [
        os.getenv("TWITTER_API_KEY"),
        os.getenv("TWITTER_API_SECRET"),
        os.getenv("TWITTER_ACCESS_TOKEN"),
        os.getenv("TWITTER_ACCESS_SECRET"),
    ]
    if any(k is None or k == "replace_me" for k in keys):
        print("[TWITTER] Keys not set, skipping")
        return

    maps_link = f"https://maps.google.com/?q={alert['lat']},{alert['lng']}"
    tweet = (
        f"🚨 DISTRESS SIGNAL DETECTED\n"
        f"📍 {alert['location_name']} | Cam: {alert['camera_id']}\n"
        f"🚔 Alerting: {station['name']}\n"
        f"🎯 Confidence: {int(alert['confidence'] * 100)}%\n"
        f"🗺️ {maps_link}\n"
        f"@UhealthyCoder"
    )

    try:
        client = tweepy.Client(
            consumer_key=keys[0],
            consumer_secret=keys[1],
            access_token=keys[2],
            access_token_secret=keys[3],
        )
        client.create_tweet(text=tweet)
        print(f"[TWITTER] Posted — alerted {station['name']}")
    except Exception as exc:
        print(f"[TWITTER] Failed: {exc}")


async def notify_all(alert: dict):
    station = nearest_station(alert["lat"], alert["lng"])
    print(f"[NEAREST STATION] {station['name']} ({station['phone']})")
    await send_sms(alert, station)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_twitter, alert, station)
