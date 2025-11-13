"""List available Gemini models"""
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

genai.configure(api_key="AIzaSyCfJxOEZivlCHXWKUixFqVSNkkzUhTg65w")

print("Available Gemini models:")
print("=" * 70)
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f"- {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Supported Methods: {model.supported_generation_methods}")
        print()
