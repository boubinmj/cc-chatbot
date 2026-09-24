"""
Unit tests for Lambda Function LF0 (Chatbot Chat Operation Handler)

This test suite validates:
1. Successful message handling with boilerplate response
2. CORS header presence in all responses
3. OPTIONS pre-flight request handling
4. Error handling for malformed requests
5. Error handling for missing required fields
"""

import json
import pytest
from lambda_function import lambda_handler


class TestLambdaChatbotFunction:
    """Test suite for LF0 Lambda function"""
    
    def test_valid_bot_request(self):
        """Test successful processing of a valid BotRequest"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'messages': [
                    {
                        'type': 'unstructured',
                        'unstructured': {
                            'id': 'msg-001',
                            'text': 'Hello, how are you?',
                            'timestamp': '2026-09-23T10:00:00Z'
                        }
                    }
                ]
            })
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        # Verify status code
        assert response['statusCode'] == 200
        
        # Verify CORS headers
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
        assert 'Access-Control-Allow-Headers' in response['headers']
        assert 'Access-Control-Allow-Methods' in response['headers']
        
        # Verify response body structure
        body = json.loads(response['body'])
        assert 'messages' in body
        assert isinstance(body['messages'], list)
        assert len(body['messages']) == 1
        
        # Verify response message structure
        response_msg = body['messages'][0]
        assert response_msg['type'] == 'unstructured'
        assert 'unstructured' in response_msg
        assert 'id' in response_msg['unstructured']
        assert 'text' in response_msg['unstructured']
        assert 'timestamp' in response_msg['unstructured']
        
        # Verify boilerplate response text
        assert response_msg['unstructured']['text'] == 'I\'m still under development. Please come back later.'
    
    def test_multiple_messages(self):
        """Test handling multiple messages in a single request"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'messages': [
                    {
                        'type': 'unstructured',
                        'unstructured': {
                            'id': 'msg-001',
                            'text': 'First message',
                            'timestamp': '2026-09-23T10:00:00Z'
                        }
                    },
                    {
                        'type': 'unstructured',
                        'unstructured': {
                            'id': 'msg-002',
                            'text': 'Second message',
                            'timestamp': '2026-09-23T10:01:00Z'
                        }
                    }
                ]
            })
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['messages']) == 2
    
    def test_options_preflight_request(self):
        """Test handling of CORS OPTIONS pre-flight request"""
        event = {
            'httpMethod': 'OPTIONS'
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 200
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Methods'] == 'POST, OPTIONS'
    
    def test_missing_messages_field(self):
        """Test error handling when messages field is missing"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({})
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['code'] == 400
        assert 'messages' in body['message'].lower()
    
    def test_invalid_messages_type(self):
        """Test error handling when messages is not an array"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'messages': 'not an array'
            })
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['code'] == 400
    
    def test_malformed_json(self):
        """Test error handling for malformed JSON in request body"""
        event = {
            'httpMethod': 'POST',
            'body': 'not valid json'
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert body['code'] == 400
    
    def test_cors_headers_on_error(self):
        """Test that CORS headers are included in error responses"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({})
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        # Even on error, CORS headers should be present
        assert 'Access-Control-Allow-Origin' in response['headers']
        assert response['headers']['Access-Control-Allow-Origin'] == '*'
    
    def test_empty_messages_array(self):
        """Test handling of empty messages array"""
        event = {
            'httpMethod': 'POST',
            'body': json.dumps({
                'messages': []
            })
        }
        context = {}
        
        response = lambda_handler(event, context)
        
        # Empty messages array should be valid (returns 0 responses)
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert len(body['messages']) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
