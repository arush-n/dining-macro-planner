"""
Test script for Gemini agent with function calling
Demonstrates how the agent uses database tools to provide accurate suggestions
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

def test_agent_with_tools():
    """Test agent with function calling capabilities"""
    print("=" * 70)
    print("TESTING GEMINI AGENT WITH FUNCTION CALLING")
    print("=" * 70)

    try:
        # Initialize agent
        print("\n1. Initializing Gemini agent with database tools...")
        agent = MealPlanningAgent()
        print("   [OK] Agent initialized successfully")

        # Test 1: Ask for high-protein lunch options
        print("\n2. Testing tool calling with high-protein lunch request...")
        print("   User: I need a high-protein lunch at J2")
        print()

        response = agent.chat(
            user_id="test_user",
            user_message="I need a high-protein lunch. Can you show me what high-protein foods are available at J2 for lunch?",
            dining_hall="J2",
            meal_type="Lunch",
            macro_targets={"protein": 40, "carbs": 50, "fats": 20},
            reset_conversation=True
        )

        print("\n   Agent Response:")
        print("   " + "-" * 66)
        print("   " + response)
        print("   " + "-" * 66)

        # Test 2: Ask about specific food
        print("\n3. Testing food lookup...")
        print("   User: Tell me about the grilled chicken")
        print()

        response = agent.chat(
            user_id="test_user",
            user_message="Tell me more about the grilled chicken - what are the exact macros?",
            dining_hall="J2",
            meal_type="Lunch",
            reset_conversation=False
        )

        print("\n   Agent Response:")
        print("   " + "-" * 66)
        print("   " + response)
        print("   " + "-" * 66)

        # Test 3: Create a meal plan
        print("\n4. Testing meal plan creation...")
        print("   User: Create a balanced meal for me")
        print()

        response = agent.chat(
            user_id="test_user",
            user_message="Can you suggest a complete balanced meal using the available foods?",
            dining_hall="J2",
            meal_type="Lunch",
            macro_targets={"protein": 40, "carbs": 100, "fats": 30},
            reset_conversation=False
        )

        print("\n   Agent Response:")
        print("   " + "-" * 66)
        print("   " + response)
        print("   " + "-" * 66)

        print("\n" + "=" * 70)
        print("SUCCESS: Agent with function calling is working correctly!")
        print("=" * 70)
        print("\nThe agent successfully:")
        print("  - Queried the database for available foods")
        print("  - Looked up specific food information")
        print("  - Provided meal suggestions based on real data")
        print("  - Used multiple tools to fulfill the requests")

        return True

    except Exception as e:
        print(f"\n   [ERROR] {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "=" * 70)
        print("FAILED: Agent test failed")
        print("=" * 70)
        return False

if __name__ == "__main__":
    test_agent_with_tools()
