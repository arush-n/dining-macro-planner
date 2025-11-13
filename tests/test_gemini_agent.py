"""
Quick test script for Gemini agent integration
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv()

# Set up paths
sys.path.append(str(Path(__file__).parent))

from agent.agent import MealPlanningAgent

def test_basic_agent():
    """Test basic agent functionality"""
    print("=" * 70)
    print("TESTING GEMINI AGENT INTEGRATION")
    print("=" * 70)

    try:
        # Initialize agent
        print("\n1. Initializing Gemini agent...")
        agent = MealPlanningAgent()
        print("   [OK] Agent initialized successfully")

        # Test simple conversation
        print("\n2. Testing basic conversation...")
        response = agent.chat(
            user_id="test_user",
            user_message="Hello! Can you help me plan a high-protein lunch?",
            dining_hall="J2",
            meal_type="Lunch",
            reset_conversation=True
        )

        print("\n   Agent Response:")
        print("   " + "-" * 66)
        print("   " + response[:200] + "...")  # Print first 200 chars
        print("   " + "-" * 66)
        print("   [OK] Conversation test successful")

        print("\n" + "=" * 70)
        print("SUCCESS: Gemini agent is working correctly!")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n   [ERROR] {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("FAILED: Gemini agent test failed")
        print("=" * 70)
        return False

if __name__ == "__main__":
    test_basic_agent()
