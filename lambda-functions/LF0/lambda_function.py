"""
LF0 - API Gateway -> Lex V2.

Env vars:
  BOT_ID        - from the bot's overview page in Lex
  BOT_ALIAS_ID  - TSTALIASID for TestBotAlias
  LOCALE_ID     - en_US
"""
import json
import os

import boto3

lex = boto3.client("lexv2-runtime")


def lambda_handler(event, context):
    # Works with both proxy (body is a JSON string) and non-proxy integrations
    body = json.loads(event["body"]) if isinstance(event.get("body"), str) else event
    text = body["messages"][0]["unstructured"]["text"]
    session_id = body.get("sessionId", "default-user")

    resp = lex.recognize_text(
        botId=os.environ["BOT_ID"],
        botAliasId=os.environ["BOT_ALIAS_ID"],
        localeId=os.environ.get("LOCALE_ID", "en_US"),
        sessionId=session_id,
        text=text,
    )

    lex_msgs = resp.get("messages") or [{"content": "Sorry, I didn't catch that."}]
    result = {
        "messages": [
            {"type": "unstructured", "unstructured": {"text": m["content"]}}
            for m in lex_msgs
        ]
    }

    if "body" in event:  # proxy integration needs statusCode + CORS headers
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Content-Type": "application/json",
            },
            "body": json.dumps(result),
        }
    return result