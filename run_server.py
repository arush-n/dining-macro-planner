"""
Quick server launcher for Dining Macro Planner
"""
import sys
import os

# Check if API key is set (just warn, don't block)
if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY not set!")
    print("AI chat won't work, but other features will work fine.")
    print()

print("Starting Dining Macro Planner API server...")
print("API will be available at: http://localhost:8000")
print("API Documentation: http://localhost:8000/docs")
print()
print("To access the frontend:")
print("  Option 1: Open frontend/index.html in your browser")
print("  Option 2: Run 'python -m http.server 3000' in the frontend directory")
print()
print("Press Ctrl+C to stop the server")
print()

# Start the server
import uvicorn
from api.main import app

uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
