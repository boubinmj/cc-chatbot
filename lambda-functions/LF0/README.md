# Lambda Function LF0 - Chatbot Chat Operation

This is the implementation of Lambda Function (LF0) that handles the chat operation for the AI Customer Service Chatbot application.

## Overview

**Endpoint**: `POST /v1/chatbot`  
**Purpose**: Processes user messages and returns chatbot responses  
**Status**: Boilerplate implementation (returns placeholder response)

## API Specification

### Request (BotRequest)
```json
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "id": "string",
        "text": "string",
        "timestamp": "datetime (ISO 8601)"
      }
    }
  ]
}
```

### Response (BotResponse)
```json
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "id": "string",
        "text": "string",
        "timestamp": "datetime (ISO 8601)"
      }
    }
  ]
}
```

### Error Response
```json
{
  "code": 400,
  "message": "Error description"
}
```

## Features

✅ **Request/Response Validation**: Validates incoming requests against the BotRequest schema  
✅ **CORS Support**: Includes proper CORS headers for cross-origin requests from frontend  
✅ **OPTIONS Handling**: Handles CORS pre-flight requests correctly  
✅ **Error Handling**: Returns appropriate HTTP status codes and error messages:
  - `400`: Malformed JSON or missing required fields
  - `500`: Unexpected server errors  
✅ **Boilerplate Response**: Returns "I'm still under development. Please come back later." for any message  
✅ **Unique Message IDs**: Generates UUIDs for each response message  
✅ **ISO 8601 Timestamps**: Timestamps in UTC with 'Z' suffix  

## Files

- **lambda_function.py**: Main Lambda handler function
- **requirements.txt**: Python dependencies (empty - uses stdlib only)
- **test_lambda_function.py**: Comprehensive unit tests
- **README.md**: This documentation

## Dependencies

No external dependencies required. Uses only Python standard library:
- `json`: JSON serialization/deserialization
- `uuid`: Unique identifier generation
- `datetime`: Timestamp generation

## Deployment to AWS Lambda

### 1. Package the Function
```bash
cd lambda-functions/LF0
zip -r lambda_function.zip lambda_function.py
```

### 2. Create Lambda Function (AWS Console or CLI)
```bash
aws lambda create-function \
  --function-name LF0 \
  --runtime python3.11 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip
```

### 3. Create API Gateway Integration
1. In AWS API Gateway console, create a new resource: `/chatbot`
2. Create a POST method on the `/chatbot` resource
3. Integration type: Lambda Function
4. Lambda function: `LF0`
5. **Enable CORS**:
   - Actions → Enable CORS and replace CORS headers
   - Access-Control-Allow-Headers: Add `Content-Type, Authorization`
   - Click "Enable CORS and replace existing CORS headers"

### 4. Deploy the API
1. Actions → Deploy API
2. Select/create deployment stage (e.g., `v1`)
3. Note the Invoke URL

## Testing

### Local Testing

Run the test suite:
```bash
cd lambda-functions/LF0
pytest test_lambda_function.py -v
```

Or with pytest installed:
```bash
pip install pytest
pytest test_lambda_function.py -v
```

### Sample Requests

#### Sample cURL Request
```bash
curl -X POST https://your-api-gateway-url/v1/chatbot \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "type": "unstructured",
        "unstructured": {
          "id": "msg-001",
          "text": "Hello, how are you?",
          "timestamp": "2026-09-23T10:00:00Z"
        }
      }
    ]
  }'
```

#### Sample Response
```json
{
  "messages": [
    {
      "type": "unstructured",
      "unstructured": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "text": "I'm still under development. Please come back later.",
        "timestamp": "2026-09-23T10:05:42.123456Z"
      }
    }
  ]
}
```

### CORS Pre-flight Request
```bash
curl -X OPTIONS https://your-api-gateway-url/v1/chatbot \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type"
```

Response headers should include:
```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization, X-Amz-Date, X-Api-Key, X-Amz-Security-Token
```

## Frontend Integration

The generated API Gateway SDK (`frontend/assets/js/sdk/apigClient.js`) will automatically:
1. Handle CORS pre-flight requests
2. Sign requests with AWS Signature V4
3. Invoke the LF0 Lambda function through API Gateway

See [frontend documentation](../../frontend/README.md) for how to use the generated SDK.

## Future Enhancements

Once the boilerplate phase is complete, the following can be implemented:

1. **NLP Backend Integration**: Connect to Lex, Luis, or custom NLP service
2. **Session Management**: Track conversation history
3. **User Profile Integration**: Access user data for personalized responses
4. **Database Integration**: Store conversation logs
5. **Authentication**: Implement proper authorization checks
6. **Logging**: Enhanced CloudWatch logging for debugging

## Troubleshooting

### CORS Errors in Frontend
- Ensure API Gateway has CORS enabled
- Check that response includes `Access-Control-Allow-Origin` header
- Verify pre-flight OPTIONS request returns 200 status

### 403 Unauthorized
- Check Lambda execution role has API Gateway invoke permissions
- Verify API Gateway resource policy

### 400 Bad Request
- Validate request body matches BotRequest schema
- Check Content-Type header is `application/json`
- Verify messages array is present and contains valid objects

### Timeout Errors
- Increase Lambda timeout (default 3 seconds)
- Check for network issues to external services (if added later)

## Notes

- The current implementation returns the same boilerplate response for any input
- Message IDs are randomly generated UUIDs
- Timestamps are in UTC (ISO 8601 format with 'Z' suffix)
- CORS is permissive (`*`) for development; restrict to specific domain in production
- All responses include proper CORS headers for frontend compatibility
