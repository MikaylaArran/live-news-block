import os, json
import requests
from datetime import datetime, timedelta, timezone

ACLED_EMAIL = os.environ["ACLED_EMAIL"]
ACLED_PASSWORD = os.environ["ACLED_PASSWORD"]

# Your 10 countries (you can edit this list)
COUNTRIES = [
    "Yemen","Sudan","Syria","Afghanistan","Israel",
    "Ukraine","Russia","Iran","Venezuela","South Africa"
]

def get_token():
    # OAuth password grant (per ACLED docs)
    url = "https://acleddata.com/oauth/token"
    data = {
        "username": ACLED_EMAIL,
        "password": ACLED_PASSWORD,
        "grant_type": "password",
        "client_id": "acled"
    }
    r = requests.post(url, data=data, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_events(token, start_date, end_date):
    # ACLED endpoint
    url = "https://acleddata.com/api/acled/read"
    params = {
        "limit": 5000,
        "country": "|".join(COUNTRIES),
        "event_date": f"{start_date}|{end_date}",
        "event_date_where": "BETWEEN",
    }
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers, timeout=60)
    r.raise_for_status()
    return r.json().get("data", [])

def compute_scores(rows):
    # Build per-country stats
    stats = {c: {"U":0,"C":0,"S":0,"I":0} for c in COUNTRIES}

    for ev in rows:
        c = ev.get("country")
        if c not in stats:
            continue

        disorder = (ev.get("disorder_type") or "").lower()
        fatalities = ev.get("fatalities") or 0

        # Simple breakdown (you can refine later)
        if "demonstration" in disorder:
            stats[c]["U"] += 1
        elif "strategic development" in disorder:
            stats[c]["S"] += 1
        elif "political violence" in disorder:
            stats[c]["C"] += 1

        # Intensity = fatalities (cap later via scoring)
        try:
            stats[c]["I"] += int(float(fatalities))
        except:
            pass

    # Convert to your JSON format + a 0–100 score
    out = []
    for c, d in stats.items():
        # Scoring: tune as you like
        score = (d["C"] * 4) + (d["U"] * 2) + (d["S"] * 1) + (d["I"] * 0.5)
        score = max(0, min(100, round(score)))

        out.append({
            "country": c,
            "score": score,
            "U": d["U"],
            "C": d["C"],
            "S": d["S"],
            "I": d["I"],
        })

    # Sort highest first
    out.sort(key=lambda x: x["score"], reverse=True)
    return out

def main():
    # Last 7 days window
    end = datetime.now(timezone.utc).date()
    start = (datetime.now(timezone.utc) - timedelta(days=7)).date()

    token = get_token()
    events = fetch_events(token, start.isoformat(), end.isoformat())
    scores = compute_scores(events)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "window_days": 7,
        "countries": scores
    }

    os.makedirs("data", exist_ok=True)
    with open("data/instability.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote data/instability.json with {len(scores)} countries from {len(events)} events.")

if __name__ == "__main__":
    main()
