"""
Simplified Gemini Agent for Meal Planning
Uses database tools to provide accurate meal suggestions
"""
import google.generativeai as genai
import json
import sys
from pathlib import Path
from typing import Dict, Optional

sys.path.append(str(Path(__file__).parent))
from config import GEMINI_API_KEY, AGENT_MODEL, MAX_TOKENS, TEMPERATURE, MACRO_TOLERANCE
from agent.tools import DatabaseTools

class MealPlanningAgent:
    """
    Gemini-powered meal planning agent that queries database for accurate suggestions
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the agent"""
        genai.configure(api_key=api_key or GEMINI_API_KEY)

        # Initialize database tools
        self.db_tools = DatabaseTools()

        # Create model
        self.model = genai.GenerativeModel(
            model_name=AGENT_MODEL,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
            }
        )

        self.conversation_history = []
        self.chat_session = None

    def create_system_prompt(self, user_id: str, dining_hall: str, meal_type: str, available_foods: str) -> str:
        """Create system prompt with real-time database data"""
        # Keep it concise to avoid token limits
        return f"""You are a meal planner for {dining_hall} - {meal_type}.

Available foods:
{available_foods}

ONLY use foods from the list above. Suggest 2-3 meal combinations with exact macros.

Format each option as:
**OPTION [N]:**
- Food 1 (ID) - Xg protein, Xg carbs, Xg fat
- Food 2 (ID) - Xg protein, Xg carbs, Xg fat
**Totals:** Xg protein, Xg carbs, Xg fat, X cal
**Why:** Brief reason
"""

    def chat(
        self,
        user_id: str,
        user_message: str,
        dining_hall: str,
        meal_type: str,
        macro_targets: Optional[Dict[str, int]] = None,
        reset_conversation: bool = False
    ) -> str:
        """Have a conversation with the agent"""
        if reset_conversation:
            self.conversation_history = []
            self.chat_session = None

        # Query database for available foods
        print(f"[DB QUERY] Getting available foods for {dining_hall} - {meal_type}...")
        available_foods_json = self.db_tools.get_available_foods(
            dining_hall=dining_hall,
            meal_type=meal_type,
            limit=50
        )
        foods_list = json.loads(available_foods_json)
        print(f"[DB RESULT] Retrieved {len(foods_list)} foods")

        # Create system prompt with real data
        system_prompt = self.create_system_prompt(
            user_id, dining_hall, meal_type, available_foods_json
        )

        # Initialize chat session if needed
        if self.chat_session is None:
            self.chat_session = self.model.start_chat(history=[])

        # Prepare the message
        if not self.conversation_history:
            macro_info = ""
            if macro_targets:
                macro_info = f"\n\nUser's macro targets: {macro_targets['protein']}g protein, {macro_targets['carbs']}g carbs, {macro_targets['fats']}g fats"
            full_message = f"{system_prompt}{macro_info}\n\nUser: {user_message}"
        else:
            full_message = user_message

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})

        # Call Gemini
        print("[GEMINI] Generating response...")
        response = self.chat_session.send_message(full_message)

        # Extract response text
        try:
            assistant_message = response.text
        except (ValueError, AttributeError):
            # Try to extract from candidates
            try:
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    print(f"[DEBUG] Candidate: {candidate}")
                    print(f"[DEBUG] Candidate finish_reason: {candidate.finish_reason if hasattr(candidate, 'finish_reason') else 'N/A'}")
                    print(f"[DEBUG] Candidate safety_ratings: {candidate.safety_ratings if hasattr(candidate, 'safety_ratings') else 'N/A'}")

                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        print(f"[DEBUG] Content parts count: {len(candidate.content.parts)}")
                        parts_text = []
                        for i, part in enumerate(candidate.content.parts):
                            print(f"[DEBUG] Part {i}: {part}")
                            if hasattr(part, 'text'):
                                parts_text.append(part.text)
                        assistant_message = "".join(parts_text)
                        print(f"[INFO] Extracted {len(assistant_message)} chars")
                    else:
                        assistant_message = "Sorry, unable to extract response."
                else:
                    assistant_message = "Sorry, no response generated."
            except Exception as e:
                print(f"[ERROR] Could not extract text: {e}")
                import traceback
                traceback.print_exc()
                assistant_message = "Sorry, I encountered an error."

        # Add to history
        self.conversation_history.append({"role": "model", "content": assistant_message})

        return assistant_message

    def suggest_meals(
        self,
        user_id: str,
        dining_hall: str,
        meal_type: str,
        protein_target: int,
        carbs_target: int,
        fats_target: int
    ) -> str:
        """Get meal suggestions for a user"""
        macro_targets = {
            "protein": protein_target,
            "carbs": carbs_target,
            "fats": fats_target
        }

        user_message = f"""I need meal suggestions for {meal_type} at {dining_hall}.

My macro targets are:
- Protein: {protein_target}g
- Carbs: {carbs_target}g
- Fats: {fats_target}g

Please suggest meal combinations that hit these targets using only the foods available."""

        return self.chat(
            user_id=user_id,
            user_message=user_message,
            dining_hall=dining_hall,
            meal_type=meal_type,
            macro_targets=macro_targets,
            reset_conversation=True
        )


def demo_agent():
    """Demo the agent"""
    print("=" * 70)
    print("DINING MACRO PLANNER - AGENT DEMO WITH DATABASE TOOLS")
    print("=" * 70)

    agent = MealPlanningAgent()

    print("\n[USER REQUEST]")
    print("Get meal suggestions for lunch at J2")
    print("Targets: 40g protein, 100g carbs, 20g fat\n")

    response = agent.suggest_meals(
        user_id="demo_user",
        dining_hall="J2",
        meal_type="Lunch",
        protein_target=40,
        carbs_target=100,
        fats_target=20
    )

    print("\n[AGENT RESPONSE]")
    print(response)
    print("\n" + "=" * 70)


if __name__ == "__main__":
    demo_agent()
