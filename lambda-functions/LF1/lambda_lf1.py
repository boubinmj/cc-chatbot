"""
LF1 - Lex V2 code hook for the Dining Concierge chatbot.

Handles:
  - GreetingIntent
  - ThankYouIntent
  - DiningSuggestionsIntent (validates slots, then pushes the request to SQS Q1)

Environment variables:
  QUEUE_URL  - URL of the SQS queue (Q1)

IAM: the Lambda execution role needs sqs:SendMessage on Q1.

Expected Lex slots on DiningSuggestionsIntent:
  Location, Cuisine, DiningDate, DiningTime, NumberOfPeople, Email
"""
import json
import os
import re
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs")
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/257656107916/DiningRequests"

NY_TZ = ZoneInfo("America/New_York")

VALID_LOCATIONS = {"manhattan", "new york", "nyc", "new york city", "ny"}
VALID_CUISINES = {"chinese", "italian", "japanese", "mexican", "indian", "thai", "french", "korean"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Order in which slots are validated / collected
SLOT_ORDER = ["Location", "Cuisine", "NumberOfPeople", "DiningDate", "DiningTime", "Email"]


# ---------------------------------------------------------------------------
# Lex V2 helpers
# ---------------------------------------------------------------------------
def get_slot(slots, name):
    slot = (slots or {}).get(name)
    if slot and slot.get("value"):
        return slot["value"].get("interpretedValue")
    return None


def elicit_slot(intent, slot_name, message, session_attrs):
    # Clear the invalid value so Lex re-prompts for it
    intent["slots"][slot_name] = None
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,
            "dialogAction": {"type": "ElicitSlot", "slotToElicit": slot_name},
            "intent": intent,
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


def delegate(intent, session_attrs):
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,
            "dialogAction": {"type": "Delegate"},
            "intent": intent,
        }
    }


def close(intent, session_attrs, message, state="Fulfilled"):
    intent["state"] = state
    return {
        "sessionState": {
            "sessionAttributes": session_attrs,
            "dialogAction": {"type": "Close"},
            "intent": intent,
        },
        "messages": [{"contentType": "PlainText", "content": message}],
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_slots(slots):
    """Return (slot_name, message) for the first invalid slot, or None if all OK."""
    location = get_slot(slots, "Location")
    if location and location.strip().lower() not in VALID_LOCATIONS:
        return "Location", (
            f"Sorry, I can't fulfill requests for {location}. "
            "Please enter a valid location (e.g. Manhattan)."
        )

    cuisine = get_slot(slots, "Cuisine")
    if cuisine and cuisine.strip().lower() not in VALID_CUISINES:
        options = ", ".join(sorted(c.title() for c in VALID_CUISINES))
        return "Cuisine", f"Sorry, I don't have suggestions for {cuisine}. Try one of: {options}."

    people = get_slot(slots, "NumberOfPeople")
    if people:
        try:
            n = int(float(people))
            if n < 1 or n > 20:
                raise ValueError
        except ValueError:
            return "NumberOfPeople", "Please enter a party size between 1 and 20."

    date_str = get_slot(slots, "DiningDate")
    if date_str:
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            if d < datetime.now(NY_TZ).date():
                return "DiningDate", "That date is in the past. What date would you like to dine?"
        except ValueError:
            return "DiningDate", "I didn't catch that date. What date would you like to dine?"

    time_str = get_slot(slots, "DiningTime")
    if time_str:
        try:
            t = datetime.strptime(time_str, "%H:%M").time()
            # If dining today, the time must still be in the future
            if date_str:
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                now = datetime.now(NY_TZ)
                if d == now.date() and t <= now.time().replace(tzinfo=None):
                    return "DiningTime", "That time has already passed today. What time would you like to dine?"
        except ValueError:
            return "DiningTime", "I didn't catch that time. What time would you like to dine?"

    email = get_slot(slots, "Email")
    if email and not EMAIL_RE.match(email.strip()):
        return "Email", "That doesn't look like a valid email address. Could you re-enter it?"

    return None


# ---------------------------------------------------------------------------
# Intent handlers
# ---------------------------------------------------------------------------
def handle_greeting(event, intent, session_attrs):
    return close(intent, session_attrs, "Hi there, how can I help?")


def handle_thank_you(event, intent, session_attrs):
    return close(intent, session_attrs, "You're welcome! Have a great meal.")


def handle_dining_suggestions(event, intent, session_attrs):
    slots = intent["slots"]
    source = event["invocationSource"]

    if source == "DialogCodeHook":
        problem = validate_slots(slots)
        if problem:
            slot_name, message = problem
            return elicit_slot(intent, slot_name, message, session_attrs)
        return delegate(intent, session_attrs)

    # FulfillmentCodeHook: all slots are filled and validated
    payload = {
        "Location": get_slot(slots, "Location"),
        "Cuisine": get_slot(slots, "Cuisine"),
        "NumberOfPeople": get_slot(slots, "NumberOfPeople"),
        "DiningDate": get_slot(slots, "DiningDate"),
        "DiningTime": get_slot(slots, "DiningTime"),
        "Email": get_slot(slots, "Email"),
    }
    logger.info("Sending to SQS: %s", json.dumps(payload))

    try:
        sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(payload))
    except Exception:
        logger.exception("Failed to send message to SQS")
        return close(
            intent,
            session_attrs,
            "Sorry, something went wrong submitting your request. Please try again in a moment.",
            state="Failed",
        )

    return close(
        intent,
        session_attrs,
        "You're all set! I'll email my restaurant suggestions to "
        f"{payload['Email']} shortly. Have a good day!",
    )


HANDLERS = {
    "GreetingIntent": handle_greeting,
    "ThankYouIntent": handle_thank_you,
    "DiningSuggestionsIntent": handle_dining_suggestions,
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    logger.info("Event: %s", json.dumps(event))

    intent = event["sessionState"]["intent"]
    session_attrs = event["sessionState"].get("sessionAttributes") or {}
    handler = HANDLERS.get(intent["name"])

    if handler is None:
        return close(
            intent, session_attrs,
            "Sorry, I didn't understand that. Can you try rephrasing?",
            state="Failed",
        )

    return handler(event, intent, session_attrs)