"""
Test JWT Authentication Flow
This simulates a real user journey
"""
import requests

BASE_URL = "http://127.0.0.1:8000/api/v1"

print("🧪 Testing JWT Authentication Flow\n")

# Step 1: Register a new user
print("1️⃣ Registering new user...")
register_response = requests.post(
    f"{BASE_URL}/user/registeration",
    json={
        "email": "sarah@example.com",
        "password": "secret123"
    }
)
print(f"   Status: {register_response.status_code}")
print(f"   Response: {register_response.json()}\n")

# Step 2: Login to get JWT token
print("2️⃣ Logging in...")
login_response = requests.post(
    f"{BASE_URL}/user/login",
    json={
        "email": "sarah@example.com",
        "password": "secret123"
    }
)
token_data = login_response.json()
token = token_data["access_token"]
print(f"   Status: {login_response.status_code}")
print(f"   Token (first 50 chars): {token[:50]}...\n")

# Step 3: Send message WITH JWT token
print("3️⃣ Sending message with JWT token...")
message_response = requests.post(
    f"{BASE_URL}/chat/message",
    json={
        "content": "Hello, testing JWT!",
        "session_id": None
    },
    headers={
        "Authorization": f"Bearer {token}"
    }
)
print(f"   Status: {message_response.status_code}")
chat_data = message_response.json()
print(f"   User message: {chat_data['user_message']['content']}")
print(f"   Bot reply: {chat_data['bot_response']['content']}\n")

# Step 4: Get chat sessions WITH JWT token
print("4️⃣ Getting chat sessions...")
sessions_response = requests.get(
    f"{BASE_URL}/chat/sessions",
    headers={
        "Authorization": f"Bearer {token}"
    }
)
print(f"   Status: {sessions_response.status_code}")
sessions = sessions_response.json()
print(f"   Total sessions: {len(sessions)}")
print(f"   Session title: {sessions["chat_sessions"][0]['title']}\n")

# Step 5: Try WITHOUT token (should fail)
print("5️⃣ Trying to send message WITHOUT token...")
no_token_response = requests.post(
    f"{BASE_URL}/chat/message",
    json={
        "content": "This should fail",
        "session_id": None
    }
)
print(f"   Status: {no_token_response.status_code}")
print(f"   Response: {no_token_response.json()}\n")

# Step 6: Try with INVALID token (should fail)
print("6️⃣ Trying with INVALID token...")
invalid_token_response = requests.post(
    f"{BASE_URL}/chat/message",
    json={
        "content": "This should also fail",
        "session_id": None
    },
    headers={
        "Authorization": "Bearer invalid-fake-token"
    }
)
print(f"   Status: {invalid_token_response.status_code}")
print(f"   Response: {invalid_token_response.json()}\n")

print("🎉 JWT Authentication test complete!")