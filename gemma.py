import openai
import os
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY")
)

print("Testing Gemma2 9B...")
try:
    r = client.chat.completions.create(
        model="gemma2-9b-it",
        messages=[{"role": "user", "content": "Reply with valid JSON only: {\"test\": \"ok\"}"}],
        response_format={"type": "json_object"}
    )
    print("SUCCESS:", r.choices[0].message.content)
except Exception as e:
    print("FAILED with json_object format:", e)

print("\nTesting without response_format...")
try:
    r = client.chat.completions.create(
        model="gemma2-9b-it",
        messages=[{"role": "user", "content": "Reply with valid JSON only, no extra text: {\"test\": \"ok\"}"}],
    )
    print("SUCCESS:", r.choices[0].message.content)
except Exception as e:
    print("FAILED without format too:", e)