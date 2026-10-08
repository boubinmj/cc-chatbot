"""
Create the "restaurants" index in OpenSearch and load RestaurantID + Cuisine.

Usage:
    export OS_ENDPOINT=https://search-xxxx.us-east-1.es.amazonaws.com
    export OS_USER=your-master-user
    export OS_PASS=your-master-password
    python opensearch_populate.py restaurants.json
"""
import json
import os
import sys

import requests

ENDPOINT = os.environ["OS_ENDPOINT"].rstrip("/")
AUTH = (os.environ["OS_USER"], os.environ["OS_PWD"])
INDEX = "restaurants"

# Create the index (ignore "already exists")
mapping = {
    "mappings": {
        "properties": {
            "RestaurantID": {"type": "keyword"},
            "Cuisine": {"type": "keyword"},
            "type": {"type": "keyword"},  # stands in for the removed "Restaurant" mapping type
        }
    }
}
r = requests.put(f"{ENDPOINT}/{INDEX}", auth=AUTH, json=mapping)
if r.status_code not in (200, 400):
    sys.exit(f"Index creation failed: {r.status_code} {r.text}")

with open(sys.argv[1]) as f:
    restaurants = json.load(f)

# Dedupe by BusinessID so OpenSearch matches DynamoDB
unique = {r["BusinessID"]: r for r in restaurants}.values()

# Bulk load; using BusinessID as the doc _id makes reruns overwrite instead of duplicate
lines = []
for rest in unique:
    lines.append(json.dumps({"index": {"_index": INDEX, "_id": rest["BusinessID"]}}))
    lines.append(json.dumps({
        "RestaurantID": rest["BusinessID"],
        "Cuisine": rest["Cuisine"].lower(),
        "type": "Restaurant",
    }))

r = requests.post(
    f"{ENDPOINT}/_bulk",
    auth=AUTH,
    data="\n".join(lines) + "\n",
    headers={"Content-Type": "application/x-ndjson"},
)
r.raise_for_status()
if r.json().get("errors"):
    sys.exit("Some documents failed; check the response:\n" + r.text[:2000])

requests.post(f"{ENDPOINT}/{INDEX}/_refresh", auth=AUTH)
count = requests.get(f"{ENDPOINT}/{INDEX}/_count", auth=AUTH).json()["count"]
print(f"Loaded. {INDEX} now has {count} documents.")