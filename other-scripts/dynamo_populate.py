import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
 
import boto3
 
table = boto3.resource("dynamodb", region_name="us-east-1").Table("yelp-restaurants")
 
with open(sys.argv[1]) as f:
    restaurants = json.load(f, parse_float=Decimal)  # DynamoDB rejects Python floats
 
with table.batch_writer(overwrite_by_pkeys=["BusinessID"]) as batch:
    for r in restaurants:
        r["insertedAtTimestamp"] = datetime.now(timezone.utc).isoformat()
        batch.put_item(Item=r)
 
print(f"Loaded {len(restaurants)} items (duplicates by BusinessID overwrite each other)")
