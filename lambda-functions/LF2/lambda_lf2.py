"""
LF2 - Suggestions queue worker.

Triggered every minute by EventBridge Scheduler. For each message in Q1:
  1. Get random restaurant IDs for the cuisine from OpenSearch
  2. Fetch full details from DynamoDB (yelp-restaurants)
  3. Email the suggestions via SES
  4. Delete the message (only after the email is sent)

Env vars:
  QUEUE_URL      SQS queue URL
  OS_ENDPOINT    https://search-....us-east-1.es.amazonaws.com
  OS_USER        OpenSearch master user
  OS_PASS        OpenSearch master password
  SENDER_EMAIL   SES-verified sender address
  TABLE_NAME     yelp-restaurants (default)
  NUM_SUGGESTIONS  3 (default)
"""
import base64
import json
import logging
import os
import urllib.request

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")
ses = boto3.client("ses")
table = boto3.resource("dynamodb").Table(os.environ.get("TABLE_NAME", "yelp-restaurants"))

QUEUE_URL = os.environ["QUEUE_URL"]
OS_ENDPOINT = os.environ["OS_ENDPOINT"].rstrip("/")
OS_AUTH = base64.b64encode(f"{os.environ['OS_USER']}:{os.environ['OS_PASS']}".encode()).decode()
SENDER = os.environ["SENDER_EMAIL"]
NUM_SUGGESTIONS = int(os.environ.get("NUM_SUGGESTIONS", "3"))


def get(msg, key):
    """Read a field whether LF1 sent it as 'Cuisine' or 'cuisine'."""
    return msg.get(key) or msg.get(key[0].lower() + key[1:])


def random_restaurant_ids(cuisine, n):
    """Ask OpenSearch for n random restaurant IDs of this cuisine."""
    query = {
        "size": n,
        "query": {
            "function_score": {
                "query": {"term": {"Cuisine": cuisine}},
                "random_score": {},
            }
        },
    }
    req = urllib.request.Request(
        f"{OS_ENDPOINT}/restaurants/_search",
        data=json.dumps(query).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {OS_AUTH}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        hits = json.loads(resp.read())["hits"]["hits"]
    return [h["_source"]["RestaurantID"] for h in hits]


def restaurant_details(ids):
    """Batch-fetch full records from DynamoDB, preserving the random order."""
    if not ids:
        return []
    resp = boto3.resource("dynamodb").batch_get_item(
        RequestItems={table.name: {"Keys": [{"BusinessID": i} for i in ids]}}
    )
    by_id = {item["BusinessID"]: item for item in resp["Responses"][table.name]}
    return [by_id[i] for i in ids if i in by_id]


def format_email(msg, restaurants):
    cuisine = get(msg, "Cuisine").title()
    people = get(msg, "NumberOfPeople")
    date = get(msg, "DiningDate")
    time = get(msg, "DiningTime")
    when = f"on {date} at {time}" if date else f"at {time}"

    if not restaurants:
        return f"Sorry, I couldn't find any {cuisine} restaurants right now. Please try another cuisine."

    lines = [f"Hello! Here are my {cuisine} restaurant suggestions for {people} people, {when}:", ""]
    for i, r in enumerate(restaurants, 1):
        rating = f" (rated {r['Rating']}, {r['NumberOfReviews']} reviews)" if "Rating" in r else ""
        lines.append(f"{i}. {r['Name']}, located at {r.get('Address', 'address unavailable')}{rating}")
    lines += ["", "Enjoy your meal!"]
    return "\n".join(lines)


def process(msg):
    cuisine = get(msg, "Cuisine").lower()
    ids = random_restaurant_ids(cuisine, NUM_SUGGESTIONS)
    restaurants = restaurant_details(ids)
    body = format_email(msg, restaurants)
    ses.send_email(
        Source=SENDER,
        Destination={"ToAddresses": [get(msg, "Email")]},
        Message={
            "Subject": {"Data": f"Your {cuisine.title()} restaurant suggestions"},
            "Body": {"Text": {"Data": body}},
        },
    )
    logger.info("Sent %d suggestions to %s", len(restaurants), get(msg, "Email"))


def lambda_handler(event, context):
    resp = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=5, WaitTimeSeconds=1)
    messages = resp.get("Messages", [])
    logger.info("Pulled %d messages", len(messages))

    processed = 0
    for m in messages:
        try:
            process(json.loads(m["Body"]))
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=m["ReceiptHandle"])
            processed += 1
        except Exception:
            # Leave the message in the queue; it becomes visible again and is retried
            logger.exception("Failed to process message: %s", m["Body"])

    return {"pulled": len(messages), "processed": processed}