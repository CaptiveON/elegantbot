from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.crud import crud_user, crud_chat
from app.services.chat_service import chat_service
from app.schema import MessageCreate

print("🧪 Testing Complete Chat Flow\n")

# Get database session
db = SessionLocal()

# Step 1: Create a user
print("1️⃣ Creating anonymous user...")
user = crud_user.create_anonymous_user(db)
print(f"   ✅ User created: {user.id}\n")

# Step 2: Send first message
print("2️⃣ Sending first message: 'Hello'")
message1 = MessageCreate(content="Hello", session_id=None)
response1 = chat_service.process_message(db, user.id, message1)
print(f"   ✅ Session created: {response1.session_id}")
print(f"   ✅ User message: {response1.user_message.content}")
print(f"   ✅ Bot reply: {response1.bot_response.content}\n")

# Step 3: Send second message in same session
print("3️⃣ Sending second message: 'How are you?'")
message2 = MessageCreate(content="How are you?", session_id=response1.session_id)
response2 = chat_service.process_message(db, user.id, message2)
print(f"   ✅ Same session: {response2.session_id}")
print(f"   ✅ User message: {response2.user_message.content}")
print(f"   ✅ Bot reply: {response2.bot_response.content}\n")

# Step 4: Get chat history
print("4️⃣ Getting chat history...")
history = chat_service.get_chat_history(db, response1.session_id)
print(f"   ✅ Total messages: {len(history.messages)}")
for i, msg in enumerate(history.messages, 1):
    print(f"   {i}. [{msg.role}]: {msg.content}")
print()

# Step 5: Get all user sessions
print("5️⃣ Getting all user sessions...")
sessions = crud_chat.get_user_sessions(db, user.id)
print(f"   ✅ Total sessions: {len(sessions)}")
for i, session in enumerate(sessions, 1):
    print(f"   {i}. {session.title}")
print()

print("🎉 Complete flow test PASSED!\n")

db.close()