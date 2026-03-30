import os
from dotenv import load_dotenv
from google import genai

# 1. Load the secret
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ ERROR: Python cannot find the GEMINI_API_KEY in your .env file.")
    exit()

print(f"✅ SUCCESS: Python found your key. It starts with: {api_key[:5]}")

# 2. Ping Google's Servers using the NEW SDK
print("Pinging Gemini 1.5 Pro...")
client = genai.Client(api_key=api_key)

try:
    response = client.models.generate_content(
        model='gemini-1.5-pro',
        contents="Reply with exactly these three words: API Connection Successful."
    )
    print(f"🤖 Gemini says: {response.text.strip()}")
except Exception as e:
    print(f"❌ API REJECTED THE KEY: {e}")