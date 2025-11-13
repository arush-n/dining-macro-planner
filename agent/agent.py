"""
Gemini Agent for Meal Planning
Uses function calling to interact with database for accurate meal suggestions
"""
import google.generativeai as genai
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any

sys.path.append(str(Path(__file__).parent.parent))
from config import GEMINI_API_KEY, AGENT_MODEL, MAX_TOKENS, TEMPERATURE, MACRO_TOLERANCE
from rag.rag_retriever import RAGRetriever
from agent.tools import DatabaseTools, TOOL_FUNCTIONS

class MealPlanningAgent:
    """
    Gemini-powered meal planning agent with function calling for database access
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

        # Create model with Python callable tools (Gemini auto-converts them)
        self.model = genai.GenerativeModel(
            model_name=AGENT_MODEL,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
            },
            tools=[
                self.db_tools.get_available_foods,
                self.db_tools.search_foods_by_macros,
                self.db_tools.get_food_by_name,
                self.db_tools.get_high_protein_foods,
                self.db_tools.get_user_preferences,
                self.db_tools.get_user_meal_history,
                self.db_tools.save_meal_plan,
                self.db_tools.get_foods_for_date,
                self.db_tools.create_weekly_plan,
                self.db_tools.scrape_dining_hall_now
            ]
        )

        self.retriever = RAGRetriever()
        self.conversation_history = []
        self.current_context = ""
        self.chat_session = None


    def create_system_prompt(self, user_id: str, dining_hall: str, meal_type: str) -> str:
        """
        Create system prompt for Gemini agent with function calling

        Args:
            user_id: User ID
            dining_hall: Dining hall name
            meal_type: Meal type

        Returns:
            System prompt string
        """
        return f"""You are an intelligent meal planning assistant that helps students achieve their macro targets using dining hall foods.

**YOUR CAPABILITIES:**
You have access to several tools/functions that let you query the database in real-time:
- get_available_foods: Get current foods available at dining halls from the database
- search_foods_by_macros: Find foods matching specific macro ranges
- get_food_by_name: Look up detailed nutrition info for specific foods
- get_high_protein_foods: Find high-protein options
- get_user_preferences: Get user's dietary preferences and macro targets
- get_user_meal_history: See what meals the user has eaten before
- save_meal_plan: Save a meal combination for the user
- get_foods_for_date: Get foods that were available on a specific date
- create_weekly_plan: Generate a complete weekly meal plan for the user
- scrape_dining_hall_now: Scrape fresh menu data directly from the dining hall website in real-time

**HOW TO USE TOOLS:**
1. When the user asks about TODAY'S meals or current menu, use scrape_dining_hall_now to get the freshest data directly from the dining hall website
2. For general queries or historical data, use get_available_foods to query the database
3. If they have specific macro requirements, use search_foods_by_macros to find suitable options
4. Use the actual data from tool calls to make suggestions - don't make up food items
5. Always verify nutritional information by calling the appropriate tools
6. When asked about historical data or specific dates, use get_foods_for_date
7. When asked to create a weekly plan, use create_weekly_plan to generate a structured plan

**CURRENT CONTEXT:**
- User ID: {user_id}
- Dining Hall: {dining_hall}
- Meal Type: {meal_type}
- Macro Tolerance: ±{MACRO_TOLERANCE}g

**SUGGESTION FORMAT:**
When providing meal suggestions, use this format:

**OPTION [N]: [Brief Description]**
Foods:
- [Food name] ([Xg protein, Xg carbs, Xg fat, Xcal])
- [Food name] ([Xg protein, Xg carbs, Xg fat, Xcal])

**Totals:** [X]g protein, [X]g carbs, [X]g fat, [X] calories

**Why this works:** [Brief explanation]

---

**IMPORTANT:**
- ALWAYS use tools to get real data from the database
- NEVER suggest foods you haven't verified exist through tool calls
- Calculate exact macro totals from the actual food data
- Provide 3-4 diverse options when possible
"""

    def chat(
        self,
        user_id: str,
        user_message: str,
        dining_hall: str,
        meal_type: str,
        macro_targets: Optional[Dict[str, int]] = None,
        reset_conversation: bool = False,
        max_tool_iterations: int = 5
    ) -> str:
        """
        Have a conversation with the agent using function calling

        Args:
            user_id: User ID
            user_message: User's message
            dining_hall: Dining hall name
            meal_type: Meal type
            macro_targets: Optional macro targets (protein, carbs, fats)
            reset_conversation: Whether to reset conversation history
            max_tool_iterations: Maximum number of tool calling iterations

        Returns:
            Agent's response
        """
        # Reset conversation if requested
        if reset_conversation:
            self.conversation_history = []
            self.chat_session = None

        # Create system prompt
        system_prompt = self.create_system_prompt(user_id, dining_hall, meal_type)

        # Initialize chat session if needed
        if self.chat_session is None:
            # Try to enable automatic function calling if supported
            try:
                self.chat_session = self.model.start_chat(history=[], enable_automatic_function_calling=True)
            except TypeError:
                # Fallback if automatic function calling not supported
                self.chat_session = self.model.start_chat(history=[])

        # Prepare the message with system context and macro targets for first message
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

        # Agentic loop: Allow model to call functions iteratively
        iterations = 0
        while iterations < max_tool_iterations:
            iterations += 1

            # Call Gemini
            response = self.chat_session.send_message(full_message)

            # Check if the model wants to call functions
            function_calls = []
            for part in response.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)

            # If no function calls, we have the final response
            if not function_calls:
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

            # Log function calls for debugging
            for function_call in function_calls:
                function_name = function_call.name
                function_args = dict(function_call.args)
                print(f"[TOOL CALL] {function_name}({json.dumps(function_args, indent=2)})")

            # With automatic function calling disabled, we would need to handle this manually
            # But for now, let's just note that functions were called
            # The results should be in the response already if automatic calling is enabled

        # If we hit max iterations, return a message
        return "I've made several attempts to gather information, but I'm having trouble completing this request. Please try rephrasing your question or simplifying your requirements."

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

Please suggest 3-4 meal combinations that hit these targets using only the foods available today."""

        return self.chat(
            user_id=user_id,
            user_message=user_message,
            dining_hall=dining_hall,
            meal_type=meal_type,
            macro_targets=macro_targets,
            reset_conversation=True
        )

    def refine_suggestion(
        self,
        user_message: str,
        user_id: str,
        dining_hall: str,
        meal_type: str
    ) -> str:
        """
        Refine previous suggestions based on user feedback

        Args:
            user_message: User's refinement request
            user_id: User ID
            dining_hall: Dining hall name
            meal_type: Meal type

        Returns:
            Agent's refined suggestions
        """
        return self.chat(
            user_id=user_id,
            user_message=user_message,
            dining_hall=dining_hall,
            meal_type=meal_type,
            reset_conversation=False
        )

    def reset(self):
        """Reset conversation history"""
        self.conversation_history = []
        self.current_context = ""
        self.chat_session = None


def demo_agent():
    """
    Demo the agent with sample interactions
    """
    print("=" * 70)
    print("DINING MACRO PLANNER - AGENT DEMO")
    print("=" * 70)

    agent = MealPlanningAgent()

    # Simulate a user interaction
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

    print("\n" + "-" * 70)
    print("\n[USER FOLLOW-UP]")
    print("Can you lower the carbs to around 120g?\n")

    response = agent.refine_suggestion(
        user_message="Can you lower the carbs to around 120g?",
        user_id=user_id,
        dining_hall=dining_hall,
        meal_type=meal_type
    )

    print("[AGENT RESPONSE]")
    print(response)

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import os

    if not os.getenv("GEMINI_API_KEY") and not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable not set")
        print("Please set it with: export GEMINI_API_KEY='your-key-here'")
        sys.exit(1)

    demo_agent()
