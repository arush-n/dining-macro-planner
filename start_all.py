"""
Start All Servers - One command to run everything
Starts both the API backend and frontend server
"""
import subprocess
import sys
import os
import time
from pathlib import Path

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Running setup verification...\n")

    # Run the comprehensive check (let it print directly)
    result = subprocess.run([sys.executable, "check_setup.py"])

    if result.returncode != 0:
        print("\nPlease fix the errors above before starting.")
        sys.exit(1)

    print("\n✓ Ready to start!\n")
    time.sleep(1)

def start_servers():
    """Start both API and frontend servers"""
    print("=" * 70)
    print("DINING MACRO PLANNER - STARTING ALL SERVERS")
    print("=" * 70)
    print()

    # Start API server
    print("🚀 Starting API server on port 8000...")
    api_process = subprocess.Popen(
        [sys.executable, "run_server.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Wait a moment for API to start
    time.sleep(2)

    # Start frontend server
    print("🌐 Starting frontend server on port 3000...")
    frontend_process = subprocess.Popen(
        [sys.executable, "start_frontend.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    time.sleep(1)

    print()
    print("=" * 70)
    print("✓ ALL SERVERS RUNNING")
    print("=" * 70)
    print()
    print("📍 API Backend:  http://localhost:8000")
    print("   API Docs:     http://localhost:8000/docs")
    print()
    print("📍 Frontend:     http://localhost:3000")
    print()
    print("=" * 70)
    print()
    print("🎯 OPEN YOUR BROWSER TO: http://localhost:3000")
    print()
    print("Press Ctrl+C to stop all servers")
    print("=" * 70)
    print()

    try:
        # Keep running and show output
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping servers...")
        api_process.terminate()
        frontend_process.terminate()
        print("👋 All servers stopped")

if __name__ == "__main__":
    check_requirements()
    start_servers()
