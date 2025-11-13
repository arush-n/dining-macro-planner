"""
Database Tools for Gemini Agent
Provides functions that the agent can call to query the database
"""
import sqlite3
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import date, datetime

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH


class DatabaseTools:
    """Tools for the agent to interact with the database"""

    def __init__(self):
        self.db_path = DATABASE_PATH

    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a query and return results as list of dicts"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results

    def get_available_foods(
        self,
        dining_hall: Optional[str] = None,
        meal_type: Optional[str] = None,
        limit: int = 50
    ) -> str:
        """
        Get available foods from the database

        Args:
            dining_hall: Filter by dining hall (J2, JCL, or Kins)
            meal_type: Filter by meal type (Breakfast, Lunch, or Dinner)
            limit: Maximum number of foods to return

        Returns:
            JSON string with food data
        """
        query = """
            SELECT id, name, dining_hall, meal_type,
                   protein, carbs, fats, calories,
                   confidence_score, scraped_date
            FROM foods
            WHERE 1=1
        """
        params = []

        if dining_hall:
            query += " AND dining_hall = ?"
            params.append(dining_hall)

        if meal_type:
            query += " AND meal_type = ?"
            params.append(meal_type)

        query += " ORDER BY confidence_score DESC, scraped_date DESC LIMIT ?"
        params.append(limit)

        results = self._execute_query(query, tuple(params))
        return json.dumps(results, indent=2)

    def search_foods_by_macros(
        self,
        min_protein: Optional[float] = None,
        max_protein: Optional[float] = None,
        min_carbs: Optional[float] = None,
        max_carbs: Optional[float] = None,
        min_fats: Optional[float] = None,
        max_fats: Optional[float] = None,
        dining_hall: Optional[str] = None,
        meal_type: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """
        Search for foods by macronutrient ranges

        Args:
            min_protein: Minimum protein in grams
            max_protein: Maximum protein in grams
            min_carbs: Minimum carbs in grams
            max_carbs: Maximum carbs in grams
            min_fats: Minimum fats in grams
            max_fats: Maximum fats in grams
            dining_hall: Filter by dining hall
            meal_type: Filter by meal type
            limit: Maximum number of results

        Returns:
            JSON string with matching foods
        """
        query = """
            SELECT id, name, dining_hall, meal_type,
                   protein, carbs, fats, calories,
                   confidence_score
            FROM foods
            WHERE 1=1
        """
        params = []

        if min_protein is not None:
            query += " AND protein >= ?"
            params.append(min_protein)
        if max_protein is not None:
            query += " AND protein <= ?"
            params.append(max_protein)
        if min_carbs is not None:
            query += " AND carbs >= ?"
            params.append(min_carbs)
        if max_carbs is not None:
            query += " AND carbs <= ?"
            params.append(max_carbs)
        if min_fats is not None:
            query += " AND fats >= ?"
            params.append(min_fats)
        if max_fats is not None:
            query += " AND fats <= ?"
            params.append(max_fats)
        if dining_hall:
            query += " AND dining_hall = ?"
            params.append(dining_hall)
        if meal_type:
            query += " AND meal_type = ?"
            params.append(meal_type)

        query += " ORDER BY confidence_score DESC LIMIT ?"
        params.append(limit)

        results = self._execute_query(query, tuple(params))
        return json.dumps(results, indent=2)

    def get_food_by_name(self, food_name: str) -> str:
        """
        Get detailed information about a specific food by name

        Args:
            food_name: Name of the food (partial match supported)

        Returns:
            JSON string with food details
        """
        query = """
            SELECT id, name, dining_hall, meal_type,
                   protein, carbs, fats, calories,
                   confidence_score, scraped_date,
                   times_selected
            FROM foods
            WHERE name LIKE ?
            ORDER BY confidence_score DESC
            LIMIT 5
        """
        results = self._execute_query(query, (f"%{food_name}%",))
        return json.dumps(results, indent=2)

    def get_high_protein_foods(
        self,
        dining_hall: Optional[str] = None,
        meal_type: Optional[str] = None,
        min_protein: float = 20.0,
        limit: int = 10
    ) -> str:
        """
        Get high-protein foods

        Args:
            dining_hall: Filter by dining hall
            meal_type: Filter by meal type
            min_protein: Minimum protein in grams
            limit: Maximum number of results

        Returns:
            JSON string with high-protein foods
        """
        query = """
            SELECT id, name, dining_hall, meal_type,
                   protein, carbs, fats, calories
            FROM foods
            WHERE protein >= ?
        """
        params = [min_protein]

        if dining_hall:
            query += " AND dining_hall = ?"
            params.append(dining_hall)
        if meal_type:
            query += " AND meal_type = ?"
            params.append(meal_type)

        query += " ORDER BY protein DESC LIMIT ?"
        params.append(limit)

        results = self._execute_query(query, tuple(params))
        return json.dumps(results, indent=2)

    def get_user_preferences(self, user_id: str) -> str:
        """
        Get user's dietary preferences and macro targets

        Args:
            user_id: User ID

        Returns:
            JSON string with user preferences
        """
        query = """
            SELECT user_id, target_protein, target_carbs, target_fats,
                   dietary_restrictions, avoided_foods, preferred_foods
            FROM user_preferences
            WHERE user_id = ?
        """
        results = self._execute_query(query, (user_id,))

        if results:
            return json.dumps(results[0], indent=2)
        else:
            return json.dumps({
                "user_id": user_id,
                "message": "No preferences found for this user"
            })

    def get_user_meal_history(
        self,
        user_id: str,
        limit: int = 10
    ) -> str:
        """
        Get user's recent meal history

        Args:
            user_id: User ID
            limit: Number of recent meals to return

        Returns:
            JSON string with meal history
        """
        query = """
            SELECT id, date, foods, total_protein, total_carbs,
                   total_fats, total_calories, user_satisfaction,
                   notes, timestamp
            FROM meal_combinations
            WHERE user_id = ?
            ORDER BY date DESC, timestamp DESC
            LIMIT ?
        """
        results = self._execute_query(query, (user_id, limit))
        return json.dumps(results, indent=2)

    def save_meal_plan(
        self,
        user_id: str,
        food_ids: List[int],
        notes: Optional[str] = None
    ) -> str:
        """
        Save a meal combination to the database

        Args:
            user_id: User ID
            food_ids: List of food IDs in the meal
            notes: Optional notes about the meal

        Returns:
            JSON string with save status
        """
        try:
            # Get food details to calculate totals
            placeholders = ','.join('?' * len(food_ids))
            query = f"""
                SELECT protein, carbs, fats, calories
                FROM foods
                WHERE id IN ({placeholders})
            """
            foods = self._execute_query(query, tuple(food_ids))

            if not foods:
                return json.dumps({"error": "No foods found with the given IDs"})

            # Calculate totals
            total_protein = sum(f['protein'] or 0 for f in foods)
            total_carbs = sum(f['carbs'] or 0 for f in foods)
            total_fats = sum(f['fats'] or 0 for f in foods)
            total_calories = sum(f['calories'] or 0 for f in foods)

            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO meal_combinations (
                    user_id, date, foods, total_protein, total_carbs,
                    total_fats, total_calories, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                str(date.today()),
                json.dumps(food_ids),
                total_protein,
                total_carbs,
                total_fats,
                total_calories,
                notes
            ))

            meal_id = cursor.lastrowid
            conn.commit()
            conn.close()

            return json.dumps({
                "success": True,
                "meal_id": meal_id,
                "total_protein": total_protein,
                "total_carbs": total_carbs,
                "total_fats": total_fats,
                "total_calories": total_calories
            })
        except Exception as e:
            return json.dumps({"error": str(e)})

    def get_foods_for_date(
        self,
        target_date: str,
        dining_hall: Optional[str] = None,
        meal_type: Optional[str] = None
    ) -> str:
        """
        Get foods that were available on a specific date

        Args:
            target_date: Date in YYYY-MM-DD format
            dining_hall: Filter by dining hall
            meal_type: Filter by meal type

        Returns:
            JSON string with foods available on that date
        """
        query = """
            SELECT id, name, dining_hall, meal_type,
                   protein, carbs, fats, calories,
                   confidence_score, scraped_date
            FROM foods
            WHERE DATE(scraped_date) = DATE(?)
        """
        params = [target_date]

        if dining_hall:
            query += " AND dining_hall = ?"
            params.append(dining_hall)

        if meal_type:
            query += " AND meal_type = ?"
            params.append(meal_type)

        query += " ORDER BY confidence_score DESC"

        results = self._execute_query(query, tuple(params))
        return json.dumps({
            "date": target_date,
            "dining_hall": dining_hall,
            "meal_type": meal_type,
            "count": len(results),
            "foods": results
        }, indent=2)

    def create_weekly_plan(
        self,
        user_id: str,
        dining_hall: str,
        meals_per_day: int = 3
    ) -> str:
        """
        Create a weekly meal plan suggestion for the user

        Args:
            user_id: User ID
            dining_hall: Dining hall to use
            meals_per_day: Number of meals per day (default: 3)

        Returns:
            JSON string with weekly meal plan structure
        """
        try:
            # Get user preferences
            prefs_query = """
                SELECT target_protein, target_carbs, target_fats
                FROM user_preferences
                WHERE user_id = ?
            """
            prefs = self._execute_query(prefs_query, (user_id,))

            if not prefs:
                return json.dumps({
                    "error": "User preferences not found. Please set your macro targets first."
                })

            target_protein = prefs[0]['target_protein']
            target_carbs = prefs[0]['target_carbs']
            target_fats = prefs[0]['target_fats']

            # Calculate per-meal targets
            per_meal_protein = target_protein // meals_per_day
            per_meal_carbs = target_carbs // meals_per_day
            per_meal_fats = target_fats // meals_per_day

            # Get available foods for the dining hall
            foods_query = """
                SELECT id, name, dining_hall, meal_type,
                       protein, carbs, fats, calories
                FROM foods
                WHERE dining_hall = ?
                ORDER BY confidence_score DESC
                LIMIT 100
            """
            available_foods = self._execute_query(foods_query, (dining_hall,))

            if not available_foods:
                return json.dumps({
                    "error": f"No foods found for dining hall: {dining_hall}"
                })

            # Create weekly plan structure
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            meal_types = ["Breakfast", "Lunch", "Dinner"][:meals_per_day]

            weekly_plan = {
                "user_id": user_id,
                "dining_hall": dining_hall,
                "daily_targets": {
                    "protein": target_protein,
                    "carbs": target_carbs,
                    "fats": target_fats
                },
                "per_meal_targets": {
                    "protein": per_meal_protein,
                    "carbs": per_meal_carbs,
                    "fats": per_meal_fats
                },
                "meals_per_day": meals_per_day,
                "plan": {}
            }

            # Create plan for each day
            for day in days:
                weekly_plan["plan"][day] = {
                    meal_type: {
                        "target_protein": per_meal_protein,
                        "target_carbs": per_meal_carbs,
                        "target_fats": per_meal_fats,
                        "suggested_foods": [
                            f["name"] for f in available_foods
                            if f["meal_type"] == meal_type
                        ][:5]  # Suggest top 5 foods for each meal type
                    }
                    for meal_type in meal_types
                }

            return json.dumps(weekly_plan, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)})


# Tool function declarations for Gemini
TOOL_FUNCTIONS = {
    "get_available_foods": {
        "name": "get_available_foods",
        "description": "Get available foods from the dining halls. Use this to see what foods are currently available.",
        "parameters": {
            "type": "object",
            "properties": {
                "dining_hall": {
                    "type": "string",
                    "description": "The dining hall to filter by (J2, JCL, or Kins)",
                    "enum": ["J2", "JCL", "Kins"]
                },
                "meal_type": {
                    "type": "string",
                    "description": "The meal type to filter by (Breakfast, Lunch, or Dinner)",
                    "enum": ["Breakfast", "Lunch", "Dinner"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of foods to return (default: 50)",
                    "default": 50
                }
            }
        }
    },
    "search_foods_by_macros": {
        "name": "search_foods_by_macros",
        "description": "Search for foods that match specific macronutrient criteria. Use this when the user has specific protein, carb, or fat requirements.",
        "parameters": {
            "type": "object",
            "properties": {
                "min_protein": {
                    "type": "number",
                    "description": "Minimum protein in grams"
                },
                "max_protein": {
                    "type": "number",
                    "description": "Maximum protein in grams"
                },
                "min_carbs": {
                    "type": "number",
                    "description": "Minimum carbs in grams"
                },
                "max_carbs": {
                    "type": "number",
                    "description": "Maximum carbs in grams"
                },
                "min_fats": {
                    "type": "number",
                    "description": "Minimum fats in grams"
                },
                "max_fats": {
                    "type": "number",
                    "description": "Maximum fats in grams"
                },
                "dining_hall": {
                    "type": "string",
                    "description": "Filter by dining hall",
                    "enum": ["J2", "JCL", "Kins"]
                },
                "meal_type": {
                    "type": "string",
                    "description": "Filter by meal type",
                    "enum": ["Breakfast", "Lunch", "Dinner"]
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 20
                }
            }
        }
    },
    "get_food_by_name": {
        "name": "get_food_by_name",
        "description": "Get detailed nutritional information about a specific food by searching for its name. Partial matches are supported.",
        "parameters": {
            "type": "object",
            "properties": {
                "food_name": {
                    "type": "string",
                    "description": "The name of the food to search for"
                }
            },
            "required": ["food_name"]
        }
    },
    "get_high_protein_foods": {
        "name": "get_high_protein_foods",
        "description": "Get foods that are high in protein. Use this when the user wants high-protein options.",
        "parameters": {
            "type": "object",
            "properties": {
                "dining_hall": {
                    "type": "string",
                    "description": "Filter by dining hall",
                    "enum": ["J2", "JCL", "Kins"]
                },
                "meal_type": {
                    "type": "string",
                    "description": "Filter by meal type",
                    "enum": ["Breakfast", "Lunch", "Dinner"]
                },
                "min_protein": {
                    "type": "number",
                    "description": "Minimum protein in grams (default: 20)",
                    "default": 20.0
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 10
                }
            }
        }
    },
    "get_user_preferences": {
        "name": "get_user_preferences",
        "description": "Get the user's dietary preferences and macro targets",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's ID"
                }
            },
            "required": ["user_id"]
        }
    },
    "get_user_meal_history": {
        "name": "get_user_meal_history",
        "description": "Get the user's recent meal history to understand their preferences and patterns",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's ID"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of recent meals to return",
                    "default": 10
                }
            },
            "required": ["user_id"]
        }
    },
    "save_meal_plan": {
        "name": "save_meal_plan",
        "description": "Save a meal plan/combination to the database for the user",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's ID"
                },
                "food_ids": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "List of food IDs that make up the meal"
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about the meal plan"
                }
            },
            "required": ["user_id", "food_ids"]
        }
    },
    "get_foods_for_date": {
        "name": "get_foods_for_date",
        "description": "Get foods that were available on a specific date. Use this when the user asks about what was available on a particular day.",
        "parameters": {
            "type": "object",
            "properties": {
                "target_date": {
                    "type": "string",
                    "description": "The date in YYYY-MM-DD format (e.g., '2024-01-15')"
                },
                "dining_hall": {
                    "type": "string",
                    "description": "Filter by dining hall",
                    "enum": ["J2", "JCL", "Kins"]
                },
                "meal_type": {
                    "type": "string",
                    "description": "Filter by meal type",
                    "enum": ["Breakfast", "Lunch", "Dinner"]
                }
            },
            "required": ["target_date"]
        }
    },
    "create_weekly_plan": {
        "name": "create_weekly_plan",
        "description": "Create a weekly meal plan for the user with suggested foods for each day and meal. Use this when the user asks for a weekly plan or wants to plan ahead for the week.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {
                    "type": "string",
                    "description": "The user's ID"
                },
                "dining_hall": {
                    "type": "string",
                    "description": "The dining hall to use for the plan",
                    "enum": ["J2", "JCL", "Kins"]
                },
                "meals_per_day": {
                    "type": "integer",
                    "description": "Number of meals per day (default: 3)",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 5
                }
            },
            "required": ["user_id", "dining_hall"]
        }
    }
}
