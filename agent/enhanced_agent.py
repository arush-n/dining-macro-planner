"""
Enhanced Gemini Agent with Function Calling
Integrates optimized search and weekly planning tools
"""
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool
import sys
import json
from pathlib import Path
from datetime import date, datetime
from typing import List, Dict, Optional

sys.path.append(str(Path(__file__).parent.parent))
from config import GEMINI_API_KEY, AGENT_MODEL, MAX_TOKENS, TEMPERATURE
from agent.tools import DatabaseTools, TOOL_FUNCTIONS
from rag.optimized_search import get_search_engine
from planner.weekly_planner import WeeklyMealPlanner


class EnhancedMealPlanningAgent:
    """
    Advanced meal planning agent with function calling and weekly planning
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the enhanced agent"""
        genai.configure(api_key=api_key or GEMINI_API_KEY)

        # Initialize tools
        self.db_tools = DatabaseTools()
        self.search_engine = get_search_engine()
        self.weekly_planner = WeeklyMealPlanner()

        # Create function declarations for Gemini
        self.functions = self._create_function_declarations()

        # Create Gemini tool
        self.tool = Tool(function_declarations=list(self.functions.values()))

        # Initialize model with tools
        self.model = genai.GenerativeModel(
            model_name=AGENT_MODEL,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
            },
            tools=[self.tool]
        )

        self.chat_session = None
        self.conversation_history = []

    def _create_function_declarations(self) -> Dict[str, FunctionDeclaration]:
        """Create Gemini function declarations from tools"""
        functions = {}

        # Convert tool definitions to Gemini format
        for tool_name, tool_spec in TOOL_FUNCTIONS.items():
            functions[tool_name] = FunctionDeclaration(
                name=tool_spec["name"],
                description=tool_spec["description"],
                parameters=tool_spec["parameters"]
            )

        # Add weekly planning functions
        functions["create_weekly_plan"] = FunctionDeclaration(
            name="create_weekly_plan",
            description="Create a weekly meal plan with suggested meals for all days",
            parameters={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "protein_target": {
                        "type": "number",
                        "description": "Daily protein target in grams"
                    },
                    "carbs_target": {
                        "type": "number",
                        "description": "Daily carbs target in grams"
                    },
                    "fats_target": {
                        "type": "number",
                        "description": "Daily fats target in grams"
                    },
                    "dining_hall": {
                        "type": "string",
                        "enum": ["J2", "JCL", "Kins"],
                        "description": "Preferred dining hall"
                    }
                },
                "required": ["user_id", "start_date", "protein_target", "carbs_target", "fats_target"]
            }
        )

        functions["get_weekly_plan"] = FunctionDeclaration(
            name="get_weekly_plan",
            description="Get details of a weekly meal plan",
            parameters={
                "type": "object",
                "properties": {
                    "plan_id": {
                        "type": "integer",
                        "description": "Plan ID"
                    }
                },
                "required": ["plan_id"]
            }
        )

        return functions

    def _execute_function(self, function_name: str, args: Dict) -> str:
        """Execute a function call"""
        try:
            # Database tools
            if function_name == "get_available_foods":
                return self.db_tools.get_available_foods(**args)
            elif function_name == "search_foods_by_macros":
                return self.db_tools.search_foods_by_macros(**args)
            elif function_name == "get_food_by_name":
                return self.db_tools.get_food_by_name(**args)
            elif function_name == "get_high_protein_foods":
                return self.db_tools.get_high_protein_foods(**args)
            elif function_name == "get_user_preferences":
                return self.db_tools.get_user_preferences(**args)
            elif function_name == "get_user_meal_history":
                return self.db_tools.get_user_meal_history(**args)
            elif function_name == "save_meal_plan":
                return self.db_tools.save_meal_plan(**args)

            # Weekly planning tools
            elif function_name == "create_weekly_plan":
                start_date = datetime.fromisoformat(args['start_date']).date()
                suggestions = self.weekly_planner.suggest_weekly_plan(
                    user_id=args['user_id'],
                    start_date=start_date,
                    protein_target=args['protein_target'],
                    carbs_target=args['carbs_target'],
                    fats_target=args['fats_target'],
                    dining_hall=args.get('dining_hall', 'Kins')
                )
                plan_id = self.weekly_planner.save_suggested_plan(
                    args['user_id'],
                    suggestions
                )
                return json.dumps({
                    "plan_id": plan_id,
                    "summary": self.weekly_planner.get_plan_summary(plan_id)
                }, indent=2)

            elif function_name == "get_weekly_plan":
                plan = self.weekly_planner.get_plan(args['plan_id'])
                if plan:
                    return json.dumps(plan, indent=2, default=str)
                return json.dumps({"error": "Plan not found"})

            else:
                return json.dumps({"error": f"Unknown function: {function_name}"})

        except Exception as e:
            return json.dumps({"error": str(e)})

    def chat(
        self,
        user_message: str,
        user_id: str = "default_user",
        reset_conversation: bool = False
    ) -> str:
        """
        Chat with the agent

        Args:
            user_message: User's message
            user_id: User ID
            reset_conversation: Whether to reset the conversation

        Returns:
            Agent's response
        """
        if reset_conversation or self.chat_session is None:
            self.chat_session = self.model.start_chat(history=[])
            self.conversation_history = []

        # Send message
        response = self.chat_session.send_message(user_message)

        # Check if model wants to call functions
        while response.candidates[0].content.parts:
            part = response.candidates[0].content.parts[0]

            # If there's a function call, execute it
            if hasattr(part, 'function_call') and part.function_call:
                function_call = part.function_call
                function_name = function_call.name
                function_args = dict(function_call.args)

                print(f"[Function Call] {function_name}({json.dumps(function_args, indent=2)})")

                # Execute function
                result = self._execute_function(function_name, function_args)

                print(f"[Function Result] {result[:200]}...")  # Print first 200 chars

                # Send function response back to model
                response = self.chat_session.send_message(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={"result": result}
                        )
                    )
                )
            else:
                # No more function calls, break
                break

        # Extract final text response
        final_response = response.text
        return final_response

    def create_weekly_plan_interactive(
        self,
        user_id: str,
        protein_target: float,
        carbs_target: float,
        fats_target: float,
        start_date: Optional[date] = None,
        dining_hall: str = "Kins"
    ) -> str:
        """
        Create a weekly plan and return a natural language summary

        Args:
            user_id: User ID
            protein_target: Daily protein target
            carbs_target: Daily carbs target
            fats_target: Daily fats target
            start_date: Start date (defaults to today)
            dining_hall: Preferred dining hall

        Returns:
            Natural language plan summary
        """
        if start_date is None:
            start_date = date.today()

        # Create plan
        suggestions = self.weekly_planner.suggest_weekly_plan(
            user_id=user_id,
            start_date=start_date,
            protein_target=protein_target,
            carbs_target=carbs_target,
            fats_target=fats_target,
            dining_hall=dining_hall
        )

        plan_id = self.weekly_planner.save_suggested_plan(user_id, suggestions)
        summary = self.weekly_planner.get_plan_summary(plan_id)

        # Ask agent to summarize
        prompt = f"""I've created a weekly meal plan. Here's the summary:

{json.dumps(summary, indent=2)}

Please provide a friendly, natural language summary of this meal plan for the user. Include:
1. The week covered
2. Total meals planned
3. Average daily macros
4. A brief encouraging message

Keep it concise and friendly."""

        return self.chat(prompt, user_id, reset_conversation=True)


def demo_enhanced_agent():
    """Demo the enhanced agent"""
    print("=" * 70)
    print("ENHANCED MEAL PLANNING AGENT DEMO")
    print("=" * 70)

    agent = EnhancedMealPlanningAgent()

    # Demo 1: Simple food search
    print("\n[USER] Show me high protein foods for lunch at Kins")
    response = agent.chat(
        "Show me high protein foods for lunch at Kins",
        user_id="demo_user"
    )
    print(f"[AGENT] {response}")

    # Demo 2: Create weekly plan
    print("\n" + "-" * 70)
    print("\n[USER] Create a weekly meal plan")
    response = agent.create_weekly_plan_interactive(
        user_id="demo_user",
        protein_target=150,
        carbs_target=300,
        fats_target=80,
        dining_hall="Kins"
    )
    print(f"[AGENT] {response}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    import os

    if not os.getenv("GEMINI_API_KEY") and not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY not set")
        sys.exit(1)

    demo_enhanced_agent()
