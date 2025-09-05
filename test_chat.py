#!/usr/bin/env python3
import requests
import json

# JWT token from final test user with completely new agent
jwt_token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InBCMHFmdEVVVHFuRkxoaUUiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3B0Y3BlbWZva3dqZ3BqZ21iZ29qLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiI2YmJlNmY3Zi0wNWMyLTRiNjctOTdmYy0yZTBlMDc0N2I4MDEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU3MDA3NTU0LCJpYXQiOjE3NTcwMDM5NTQsImVtYWlsIjoiZmluYWwtdGVzdEBleGFtcGxlLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWxfdmVyaWZpZWQiOnRydWV9LCJyb2xlIjoiYXV0aGVudGljYXRlZCIsImFhbCI6ImFhbDEiLCJhbXIiOlt7Im1ldGhvZCI6InBhc3N3b3JkIiwidGltZXN0YW1wIjoxNzU3MDAzOTU0fV0sInNlc3Npb25faWQiOiJiZTBhMWE5YS1lNzAwLTQ4ZTAtOThkMi0zNDg0NjgxZGU0ZjUiLCJpc19hbm9ueW1vdXMiOmZhbHNlfQ.WAVe52VaA3Uff_0oAysHU0tRedmlSaotPzyprZT-d6g"

# Test chat message
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {jwt_token}"
}

message_data = {
    "content": "Hello! Can you introduce yourself and tell me what AI model you are using?"
}

print("=== TESTING CHAT FUNCTIONALITY ===")
print(f"Sending message: {message_data['content']}")

try:
    response = requests.post(
        "http://localhost:8000/api/v1/chat/message",
        headers=headers,
        json=message_data,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        print("=== CHAT SUCCESS ===")
        print(f"Agent Response: {data.get('agent_response', 'No response')}")
        print(f"Usage Stats: {data.get('usage_stats', 'No usage stats')}")
    else:
        print("=== CHAT FAILED ===")
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Error: {e}")