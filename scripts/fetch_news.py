import os, json
import requests
from datetime import datetime, timezone

API_KEY = os.environ["pub_01fca8530e7644058c7b3cc72d9b6d75"]
URL = f"https://newsdata.io/api/1/latest?apikey={API_KEY}&language=en"

def main():
    r = requests.get(URL, timeout=30)
    r.raise_for_status()
    data = r.json()

    if data.get("status") != "success":
        raise SystemExit(f"API error: {data}")

    results = (data.get("results") or [])[:10]
    articles = [{
        "title": a.get("title") or "Untitled",
        "link": a.get("link") or "",
        "source": a.get("source_id") or "",
        "pubDate": a.get("pubDate") or ""
    } for a in results]

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "articles": articles
    }

    os.makedirs("data", exist_ok=True)
    with open("data/top_news.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("Wrote data/top_news.json")

if __name__ == "__main__":
    main()
