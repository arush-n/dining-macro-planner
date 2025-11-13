import os
from dotenv import load_dotenv

# Load .env from workspace root
load_dotenv()

key = os.getenv("GEMINI_API_KEY")
print("GEMINI_API_KEY:", key)
