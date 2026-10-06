"""
Scrape Manhattan restaurants from the Yelp Fusion API and save them to JSON files.
(No AWS needed.)

Setup:
    pip install requests python-dotenv
    Put YELP-API-KEY (or YELP_API_KEY) in a .env file next to this script.

Run:
    python scrape_yelp.py

Outputs:
    - restaurants.json         full records (for DynamoDB "yelp-restaurants")
    - restaurants_backup.json  RestaurantID + Cuisine only (for OpenSearch)
"""
import json
import os
import time
from datetime import datetime, timezone

import requests

try:
    from dotenv import load_dotenv  # pip install python-dotenv
    load_dotenv()
except ImportError:
    pass  # fall back to variables already in the environment


def get_env(*names):
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    raise SystemExit(f"Missing environment variable (tried: {', '.join(names)})")


# Accepts either YELP-API-KEY or YELP_API_KEY.
YELP_API_KEY = get_env("YELP-API-KEY", "YELP_API_KEY")

CUISINES = ["chinese", "italian", "japanese", "mexican", "indian"]
LOCATION = "Manhattan, NY"

SEARCH_URL = "https://api.yelp.com/v3/businesses/search"
PAGE_SIZE = 50
# Yelp caps how deep you can page (offset + limit); 240 is the conservative figure.
MAX_DEPTH = 240

HEADERS = {"Authorization": f"Bearer {YELP_API_KEY}"}


def fetch_cuisine(cuisine):
    """Yield raw Yelp business dicts for one cuisine, paging until exhausted."""
    offset = 0
    while offset < MAX_DEPTH:
        limit = min(PAGE_SIZE, MAX_DEPTH - offset)
        params = {
            "term": f"{cuisine} restaurants",
            "location": LOCATION,
            "limit": limit,
            "offset": offset,
        }
        resp = requests.get(SEARCH_URL, headers=HEADERS, params=params, timeout=15)
        if resp.status_code != 200:
            print(f"  [{cuisine}] stopped at offset {offset}: {resp.status_code} {resp.text[:150]}")
            return
        businesses = resp.json().get("businesses", [])
        if not businesses:
            return
        for b in businesses:
            yield b
        offset += len(businesses)
        time.sleep(0.3)  # be polite


def to_item(biz, cuisine):
    loc = biz.get("location", {}) or {}
    coords = biz.get("coordinates", {}) or {}
    item = {
        "BusinessID": biz["id"],
        "Name": biz.get("name"),
        "Address": ", ".join(loc.get("display_address", [])) or None,
        "Coordinates": {
            "Latitude": coords.get("latitude"),
            "Longitude": coords.get("longitude"),
        },
        "NumberOfReviews": biz.get("review_count"),
        "Rating": biz.get("rating"),
        "ZipCode": loc.get("zip_code"),
        "Cuisine": cuisine,
        "insertedAtTimestamp": datetime.now(timezone.utc).isoformat(),
    }
    item["Coordinates"] = {k: v for k, v in item["Coordinates"].items() if v is not None}
    return {k: v for k, v in item.items() if v is not None}


def main():
    seen = {}  # BusinessID -> item (dedupe across all cuisines)

    for cuisine in CUISINES:
        print(f"Fetching {cuisine}...")
        added = 0
        for biz in fetch_cuisine(cuisine):
            if biz["id"] in seen:
                continue
            seen[biz["id"]] = to_item(biz, cuisine)
            added += 1
        print(f"  {added} new unique restaurants for {cuisine}")

    restaurants = list(seen.values())
    print(f"\nTotal unique restaurants: {len(restaurants)}")

    with open("restaurants.json", "w") as f:
        json.dump(restaurants, f, indent=2)
    print("Wrote restaurants.json")

    # Slim version for the OpenSearch step (RestaurantID + Cuisine only)
    with open("restaurants_backup.json", "w") as f:
        json.dump(
            [{"RestaurantID": r["BusinessID"], "Cuisine": r["Cuisine"]} for r in restaurants],
            f,
            indent=2,
        )
    print("Wrote restaurants_backup.json")


if __name__ == "__main__":
    main()