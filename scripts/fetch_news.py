# scripts/fetch_news.py
import os
import re
import json
import time
import requests
from collections import Counter
from datetime import datetime, timezone

BASE_URL = "https://newsdata.io/api/1/latest"

# Dropdown options from your index.html
CATEGORIES = ["all", "world", "politics", "business", "technology", "environment"]
N_VALUES = [20, 40, 60, 100]

# -----------------------------
# Fetch headlines (with gentle backoff)
# -----------------------------
def _request_with_backoff(params: dict, max_retries: int = 3):
    delay = 1.0
    last_exc = None
    for _ in range(max_retries + 1):
        try:
            r = requests.get(BASE_URL, params=params, timeout=30)
            if r.status_code == 429:
                time.sleep(delay)
                delay *= 2
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last_exc = e
            time.sleep(delay)
            delay *= 2
    raise last_exc

def fetch_top_n(api_key: str, n: int = 100, language: str = "en", max_calls: int = 4, category: str | None = None):
    items = []
    page_token = None

    for _ in range(max_calls):
        params = {"apikey": api_key, "language": language}

        # NewsData expects category only when not "all"
        if category:
            params["category"] = category

        if page_token:
            params["page"] = page_token

        data = _request_with_backoff(params, max_retries=2)
        if data.get("status") != "success":
            raise RuntimeError(str(data))

        items.extend(data.get("results") or [])

        if len(items) >= n:
            break

        page_token = data.get("nextPage")
        if not page_token:
            break

    return items[:n]

# -----------------------------
# Text utilities (clustering)
# -----------------------------
STOP = set("""
a an the and or but if then than so to of in on for with from by at as is are was were be been being
this that these those it its into over under about across after before during between also not no
can could would should may might will just more most much very per via
""".split())

SPORTS = set("""
nba nfl nhl mlb match game games season playoff all-star dunk overtime quarter finals championship
wrestle wrestling division scoreboard wildcats lakers nascar daytona
""".split())

LIFESTYLE_LOCAL = set("""
wedding weddings horoscope crossword recipe recipes dining travel scenic waterfall park
town county local citizen newsletter obituaries health scores
""".split())

FINANCE_TICKER = set("""
nyse nasdaq etf stock stocks shares bond bonds yield earnings ticker short interest price target
""".split())

def normalize(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text: str):
    return [
        w for w in normalize(text).split()
        if w not in STOP and len(w) > 2 and not w.isdigit()
    ]

def is_low_signal(title: str, desc: str) -> bool:
    ws = set(tokenize((title or "") + " " + (desc or "")))
    if len(ws & SPORTS) >= 2:
        return True
    if len(ws & LIFESTYLE_LOCAL) >= 2:
        return True
    if len(ws & FINANCE_TICKER) >= 3:
        return True
    return False

def jaccard(a, b):
    A, B = set(a), set(b)
    if not A or not B:
        return 0.0
    return len(A & B) / (len(A | B) or 1)

def cluster_titles(rows, sim_threshold=0.33):
    clusters = []
    for r in rows:
        title = (r.get("title") or "").strip()
        if not title:
            continue
        tks = tokenize(title)
        if not tks:
            continue

        best_i = None
        best_sim = 0.0
        for i, c in enumerate(clusters):
            centroid = [w for w, _ in c["tok_counts"].most_common(25)]
            sim = jaccard(tks, centroid)
            if sim > best_sim:
                best_sim, best_i = sim, i

        if best_i is not None and best_sim >= sim_threshold:
            clusters[best_i]["rows"].append(r)
            clusters[best_i]["tok_counts"].update(tks)
        else:
            clusters.append({"rows":[r], "tok_counts":Counter(tks)})

    clusters.sort(key=lambda c: len(c["rows"]), reverse=True)
    return clusters

TOPIC_LEXICON = {
    "Geopolitics & security": ["war","military","nuclear","sanctions","border","defense","attack","navy"],
    "Elections & governance": ["election","vote","parliament","government","president","minister","court","policy"],
    "Economy & markets": ["inflation","gdp","economy","bank","interest","rate","currency","trade","jobs","markets"],
    "Tech & AI": ["ai","artificial","chip","cyber","data","software","platform"],
    "Climate & disasters": ["climate","flood","storm","drought","wildfire","earthquake"],
    "Public safety & crime": ["police","arrest","trial","fraud","shooting","crime"]
}

def label_cluster(cluster):
    counts = cluster["tok_counts"]
    best_topic = None
    best_score = 0
    for topic, words in TOPIC_LEXICON.items():
        score = sum(counts.get(w, 0) for w in words)
        if score > best_score:
            best_score = score
            best_topic = topic
    return best_topic or "Other"

def representative_title(cluster):
    counts = cluster["tok_counts"]
    def score(t):
        return sum(counts.get(w, 0) for w in tokenize(t))
    rows = cluster["rows"]
    rows_sorted = sorted(rows, key=lambda r: (-score(r.get("title","")), len(r.get("title","") or "")))
    return (rows_sorted[0].get("title","") or "").strip()

def build_clean_paragraph(rows):
    if not rows:
        return "No headlines were available to summarize."

    filtered = [r for r in rows if not is_low_signal(r.get("title",""), r.get("description",""))]
    corpus = filtered if len(filtered) >= 40 else rows

    clusters = cluster_titles(corpus)
    if not clusters:
        return "Insufficient signal to produce a coherent summary."

    for c in clusters:
        c["topic"] = label_cluster(c)

    chosen = []
    seen = set()
    for c in clusters:
        if c["topic"] not in seen:
            chosen.append(c)
            seen.add(c["topic"])
        if len(chosen) == 3:
            break
    if len(chosen) < 3:
        chosen = clusters[:3]

    lines = []
    for c in chosen:
        rep = representative_title(c)
        if rep:
            lines.append(f"{c['topic']}: {rep}")

    while len(lines) < 3:
        lines.append("Other: Additional headlines are mixed and do not cluster cleanly.")

    return (
        "The current headlines point to several parallel developments. "
        f"{lines[0]}. {lines[1]}. {lines[2]}. "
        "Taken together, the feed reflects a dispersed news cycle rather than a single dominant global event."
    )

# -----------------------------
# Write JSON (for index.html)
# -----------------------------
def write_payload(path: str, language: str, category_label: str, n: int, results: list):
    articles = []
    for a in results[:10]:
        articles.append({
            "title": a.get("title", "Untitled"),
            "link": a.get("link", "") or a.get("url", ""),
            "source": a.get("source_id", "") or a.get("source", ""),
            "pubDate": a.get("pubDate", "") or a.get("published_at", "") or a.get("publishedAt", "")
        })

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "language": language,
        "category": category_label,
        "n": n,
        "summary": build_clean_paragraph(results),
        "articles": articles
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def main():
    api_key = os.getenv("NEWSDATA_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing NEWSDATA_API_KEY")

    language = (os.getenv("NEWS_LANGUAGE", "en") or "en").strip()

    os.makedirs("data", exist_ok=True)

    # Generate all category + N combos for your dropdown
    written = 0
    for cat in CATEGORIES:
        cat_param = None if cat == "all" else cat

        for n in N_VALUES:
            results = fetch_top_n(api_key, n=n, language=language, category=cat_param)
            out_path = f"data/top_news_{cat}_{n}.json"
            write_payload(out_path, language, cat, n, results)
            written += 1
            print(f"✅ Wrote {out_path}")

    # Also write a fallback file (optional) so older code still works
    # Default: all_60
    default_path = "data/top_news.json"
    with open(f"data/top_news_all_60.json", "r", encoding="utf-8") as src:
        default_payload = json.load(src)
    with open(default_path, "w", encoding="utf-8") as dst:
        json.dump(default_payload, dst, ensure_ascii=False, indent=2)
    print("✅ Wrote data/top_news.json (alias of top_news_all_60.json)")

    print(f"✅ Done. Generated {written} files.")

if __name__ == "__main__":
    main()
