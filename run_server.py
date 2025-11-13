"""
Quick server launcher for Dining Macro Planner
"""
import sys
import os

# Check if API key is set
if not os.getenv("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY not set!")
    print("The server will start but recommendations won't work without an API key.")
    print()
    response = input("Continue anyway? (y/n): ")
    if response.lower() != 'y':
        sys.exit(0)

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
