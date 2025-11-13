"""
Simplified Gemini Agent for Meal Planning
Uses database tools to provide accurate meal suggestions
"""
import google.generativeai as genai
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

sys.path.append(str(Path(__file__).parent.parent))
from config import GEMINI_API_KEY, AGENT_MODEL, MAX_TOKENS, TEMPERATURE, MACRO_TOLERANCE
from agent.tools import DatabaseTools

class MealPlanningAgent:
    """
    Gemini-powered meal planning agent that queries database for accurate suggestions
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the agent

        Args:
            api_key: Google Gemini API key (optional, uses env var if not provided)
        """
        genai.configure(api_key=api_key or GEMINI_API_KEY)

        # Initialize database tools
        self.db_tools = DatabaseTools()

        # Create model without tools (simpler approach)
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
        """
        Create system prompt with real-time database data

        Args:
            user_id: User ID
            dining_hall: Dining hall name
            meal_type: Meal type
            available_foods: JSON string of available foods from database

        Returns:
            System prompt string
        """
        return f"""You are an intelligent meal planning assistant that helps students achieve their macro targets.

**CURRENT CONTEXT:**
- User ID: {user_id}
- Dining Hall: {dining_hall}
- Meal Type: {meal_type}
- Macro Tolerance: ±{MACRO_TOLERANCE}g

**AVAILABLE FOODS (from real-time database):**
{available_foods}

**YOUR TASK:**
Use ONLY the foods listed above to create meal suggestions. These are the actual foods available right now in the database.

**IMPORTANT RULES:**
1. ONLY suggest foods from the list above - never make up food items
2. Use the exact nutritional values provided in the database
3. Calculate precise macro totals for each suggestion
4. Provide 3-4 diverse meal options
5. Explain why each option fits the user's needs

**SUGGESTION FORMAT:**
For each option, use this format:

**OPTION [N]: [Brief Description]**
Foods:
- [Food name] (ID: [id]) - [Xg protein, Xg carbs, Xg fat, Xcal]
- [Food name] (ID: [id]) - [Xg protein, Xg carbs, Xg fat, Xcal]

**Totals:** [X]g protein, [X]g carbs, [X]g fat, [X] calories

**Why this works:** [Brief explanation]

---

After providing all options, ask if they want adjustments or have questions.
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
        """
        Have a conversation with the agent

        Args:
            user_id: User ID
            user_message: User's message
            dining_hall: Dining hall name
            meal_type: Meal type
            macro_targets: Optional macro targets (protein, carbs, fats)
            reset_conversation: Whether to reset conversation history

        Returns:
            Agent's response
        """
        # Reset conversation if requested
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
        print(f"[DB RESULT] Retrieved {len(json.loads(available_foods_json))} foods")

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
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Call Gemini
        response = self.chat_session.send_message(full_message)

        # Extract response text
        try:
            assistant_message = response.text
        except ValueError:
            # If response has multiple parts, concatenate them
            assistant_message = "".join(
                part.text for part in response.parts
                if hasattr(part, 'text') and part.text
            )

        # Add to history
        self.conversation_history.append({
            "role": "model",
            "content": assistant_message
        })

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
        """
        Get meal suggestions for a user

        Args:
            user_id: User ID
            dining_hall: Dining hall name
            meal_type: Meal type
            protein_target: Target protein in grams
            carbs_target: Target carbs in grams
            fats_target: Target fats in grams

        Returns:
            Agent's meal suggestions
        """
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

Please suggest 3-4 meal combinations that hit these targets using only the foods available."""

        return self.chat(
            user_id=user_id,
            user_message=user_message,
            dining_hall=dining_hall,
            meal_type=meal_type,
            macro_targets=macro_targets,
            reset_conversation=True
        )

    def reset(self):
        """Reset conversation history"""
        self.conversation_history = []
        self.chat_session = None


def demo_agent():
    """Demo the agent with sample interactions"""
    print("=" * 70)
    print("DINING MACRO PLANNER - AGENT DEMO")
    print("=" * 70)

    agent = MealPlanningAgent()

    user_id = "demo_user"
    dining_hall = "J2"
    meal_type = "Lunch"

    print("\n[USER REQUEST]")
    print("Get meal suggestions for lunch at J2")
    print("Targets: 40g protein, 150g carbs, 50g fat\n")

    response = agent.suggest_meals(
        user_id=user_id,
        dining_hall=dining_hall,
        meal_type=meal_type,
        protein_target=40,
        carbs_target=150,
        fats_target=50
    )

    print("[AGENT RESPONSE]")
    print(response)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import os

    if not os.getenv("GEMINI_API_KEY") and not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable not set")
        sys.exit(1)

    demo_agent()
