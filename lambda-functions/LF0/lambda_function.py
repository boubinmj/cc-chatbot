"""
Lambda Function LF0: Chatbot Chat Operation Handler

This Lambda function handles the POST /v1/chatbot endpoint and returns
a boilerplate response. It follows the request/response model specified
in the Swagger API specification.

Request schema (BotRequest):
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "id": "string",
        "text": "string",
        "timestamp": "datetime"
      }
    }
  ]
}

Response schema (BotResponse):
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "id": "string",
        "text": "string",
        "timestamp": "datetime"
      }
    }
  ]
}
"""

import json
import uuid
from datetime import datetime


def lambda_handler(event, context):
    """
    Lambda handler for the chatbot API endpoint.
    
    Args:
        event: API Gateway Lambda proxy integration event
        context: Lambda context object
    
    Returns:
        API Gateway Lambda proxy integration response with statusCode, headers, and body
    """
    
    # Set CORS headers to allow cross-origin requests from the frontend
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Content-Type": "application/json"
    }
    
    # Handle OPTIONS pre-flight request for CORS
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({})
        }
    
    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        # Validate that the request contains the messages array
        if 'messages' not in body:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'code': 400,
                    'message': 'Invalid request: "messages" field is required'
                })
            }
        
        if not isinstance(body['messages'], list):
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'code': 400,
                    'message': 'Invalid request: "messages" must be an array'
                })
            }
        
        # Generate a boilerplate response message for each incoming message
        response_messages = []
        for incoming_message in body['messages']:
            response_message = {
                'type': 'unstructured',
                'unstructured': {
                    'id': str(uuid.uuid4()),
                    'text': 'I\'m still under development. Please come back later.',
                    'timestamp': datetime.utcnow().isoformat() + 'Z'
                }
            }
            response_messages.append(response_message)
        
        # Return the BotResponse
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'messages': response_messages
            })
        }
    
    except json.JSONDecodeError as e:
        # Handle invalid JSON in request body
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'code': 400,
                'message': f'Invalid JSON in request body: {str(e)}'
            })
        }
    except Exception as e:
        # Handle unexpected errors
        print(f'Unexpected error: {str(e)}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'code': 500,
                'message': 'Internal server error'
            })
        }
