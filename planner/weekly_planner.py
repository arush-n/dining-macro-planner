"""
Weekly Meal Planner
Comprehensive meal planning service with date support
"""
import sqlite3
import json
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional, Tuple
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH
from rag.optimized_search import get_search_engine


class WeeklyMealPlanner:
    """
    Service for creating and managing weekly meal plans
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        self.search_engine = get_search_engine()

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def create_weekly_plan(
        self,
        user_id: str,
        start_date: date,
        plan_name: Optional[str] = None
    ) -> int:
        """
        Create a new weekly meal plan

        Args:
            user_id: User ID
            start_date: Start date of the week (will be adjusted to Monday)
            plan_name: Optional name for the plan

        Returns:
            Plan ID
        """
        # Adjust to Monday of the week
        week_start = start_date - timedelta(days=start_date.weekday())
        week_end = week_start + timedelta(days=6)

        conn = self._get_connection()
        cursor = conn.cursor()

        # Check for existing active plan for this week
        cursor.execute("""
            SELECT id FROM weekly_meal_plans
            WHERE user_id = ?
            AND week_start_date = ?
            AND is_active = 1
        """, (user_id, week_start.isoformat()))

        existing = cursor.fetchone()
        if existing:
            conn.close()
            return existing[0]

        # Create new plan
        if not plan_name:
            plan_name = f"Week of {week_start.strftime('%B %d, %Y')}"

        cursor.execute("""
            INSERT INTO weekly_meal_plans (
                user_id, plan_name, week_start_date, week_end_date
            ) VALUES (?, ?, ?, ?)
        """, (user_id, plan_name, week_start.isoformat(), week_end.isoformat()))

        plan_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return plan_id

    def add_meal_to_plan(
        self,
        plan_id: int,
        meal_date: date,
        dining_hall: str,
        meal_type: str,
        food_ids: List[int],
        notes: Optional[str] = None
    ) -> int:
        """
        Add a meal to a weekly plan

        Args:
            plan_id: Weekly plan ID
            meal_date: Date of the meal
            dining_hall: Dining hall name
            meal_type: Meal type
            food_ids: List of food IDs
            notes: Optional notes

        Returns:
            Meal ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Calculate totals
        placeholders = ','.join(['?'] * len(food_ids))
        cursor.execute(f"""
            SELECT SUM(protein), SUM(carbs), SUM(fats), SUM(calories)
            FROM foods
            WHERE id IN ({placeholders})
        """, food_ids)

        totals = cursor.fetchone()

        # Insert meal
        cursor.execute("""
            INSERT INTO planned_meals (
                plan_id, meal_date, dining_hall, meal_type,
                foods, total_protein, total_carbs, total_fats, total_calories, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            meal_date.isoformat(),
            dining_hall,
            meal_type,
            json.dumps(food_ids),
            totals[0] or 0,
            totals[1] or 0,
            totals[2] or 0,
            totals[3] or 0,
            notes
        ))

        meal_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return meal_id

    def get_plan(self, plan_id: int) -> Optional[Dict]:
        """
        Get a weekly plan with all meals

        Args:
            plan_id: Plan ID

        Returns:
            Plan dictionary with meals
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Get plan details
        cursor.execute("""
            SELECT * FROM weekly_meal_plans WHERE id = ?
        """, (plan_id,))

        plan_row = cursor.fetchone()
        if not plan_row:
            conn.close()
            return None

        columns = [desc[0] for desc in cursor.description]
        plan = dict(zip(columns, plan_row))

        # Get all meals for this plan
        cursor.execute("""
            SELECT * FROM planned_meals
            WHERE plan_id = ?
            ORDER BY meal_date, meal_type
        """, (plan_id,))

        meal_rows = cursor.fetchall()
        meal_columns = [desc[0] for desc in cursor.description]
        meals = [dict(zip(meal_columns, row)) for row in meal_rows]

        # Parse food IDs
        for meal in meals:
            meal['food_ids'] = json.loads(meal['foods'])

        plan['meals'] = meals
        conn.close()

        return plan

    def get_user_plans(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[Dict]:
        """
        Get all plans for a user

        Args:
            user_id: User ID
            active_only: Only return active plans

        Returns:
            List of plans
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM weekly_meal_plans WHERE user_id = ?"
        params = [user_id]

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY week_start_date DESC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        plans = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return plans

    def suggest_weekly_plan(
        self,
        user_id: str,
        start_date: date,
        protein_target: float,
        carbs_target: float,
        fats_target: float,
        dining_hall: str = "Kins",
        meals_per_day: List[str] = None
    ) -> Dict:
        """
        Generate a suggested weekly meal plan

        Args:
            user_id: User ID
            start_date: Start date
            protein_target: Daily protein target
            carbs_target: Daily carbs target
            fats_target: Daily fats target
            dining_hall: Preferred dining hall
            meals_per_day: List of meal types to plan (default: all 3)

        Returns:
            Suggested plan dictionary
        """
        if meals_per_day is None:
            meals_per_day = ["Breakfast", "Lunch", "Dinner"]

        # Adjust targets per meal
        num_meals = len(meals_per_day)
        protein_per_meal = protein_target / num_meals
        carbs_per_meal = carbs_target / num_meals
        fats_per_meal = fats_target / num_meals

        # Adjust to Monday
        week_start = start_date - timedelta(days=start_date.weekday())

        suggestions = {
            "week_start": week_start.isoformat(),
            "week_end": (week_start + timedelta(days=6)).isoformat(),
            "daily_targets": {
                "protein": protein_target,
                "carbs": carbs_target,
                "fats": fats_target
            },
            "meals": []
        }

        # Generate suggestions for each day
        for day_offset in range(7):
            meal_date = week_start + timedelta(days=day_offset)

            for meal_type in meals_per_day:
                # Find combinations for this meal
                combos = self.search_engine.find_meal_combinations(
                    protein_target=protein_per_meal,
                    carbs_target=carbs_per_meal,
                    fats_target=fats_per_meal,
                    dining_hall=dining_hall,
                    meal_type=meal_type,
                    target_date=meal_date,
                    num_combinations=3,
                    max_items=5
                )

                if combos:
                    # Use the best combination
                    best_combo = combos[0]

                    suggestions["meals"].append({
                        "date": meal_date.isoformat(),
                        "day_name": meal_date.strftime("%A"),
                        "dining_hall": dining_hall,
                        "meal_type": meal_type,
                        "foods": best_combo['food_names'],
                        "food_ids": best_combo['food_ids'],
                        "totals": {
                            "protein": best_combo['total_protein'],
                            "carbs": best_combo['total_carbs'],
                            "fats": best_combo['total_fats'],
                            "calories": best_combo['total_calories']
                        },
                        "score": best_combo['score']
                    })

        return suggestions

    def save_suggested_plan(
        self,
        user_id: str,
        suggestions: Dict,
        plan_name: Optional[str] = None
    ) -> int:
        """
        Save a suggested plan to database

        Args:
            user_id: User ID
            suggestions: Suggestions from suggest_weekly_plan
            plan_name: Optional plan name

        Returns:
            Plan ID
        """
        start_date = datetime.fromisoformat(suggestions['week_start']).date()
        plan_id = self.create_weekly_plan(user_id, start_date, plan_name)

        for meal in suggestions['meals']:
            self.add_meal_to_plan(
                plan_id=plan_id,
                meal_date=datetime.fromisoformat(meal['date']).date(),
                dining_hall=meal['dining_hall'],
                meal_type=meal['meal_type'],
                food_ids=meal['food_ids']
            )

        return plan_id

    def get_plan_summary(self, plan_id: int) -> Dict:
        """
        Get summary statistics for a plan

        Args:
            plan_id: Plan ID

        Returns:
            Summary dictionary
        """
        plan = self.get_plan(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        summary = {
            "plan_id": plan_id,
            "plan_name": plan['plan_name'],
            "week": f"{plan['week_start_date']} to {plan['week_end_date']}",
            "total_meals": len(plan['meals']),
            "avg_daily_macros": {
                "protein": 0,
                "carbs": 0,
                "fats": 0,
                "calories": 0
            },
            "meals_by_type": {
                "Breakfast": 0,
                "Lunch": 0,
                "Dinner": 0
            }
        }

        # Calculate averages
        total_protein = sum(m['total_protein'] for m in plan['meals'])
        total_carbs = sum(m['total_carbs'] for m in plan['meals'])
        total_fats = sum(m['total_fats'] for m in plan['meals'])
        total_calories = sum(m['total_calories'] for m in plan['meals'])

        # Count meals by type
        for meal in plan['meals']:
            summary['meals_by_type'][meal['meal_type']] += 1

        # Calculate daily averages (7 days)
        summary['avg_daily_macros'] = {
            "protein": round(total_protein / 7, 1),
            "carbs": round(total_carbs / 7, 1),
            "fats": round(total_fats / 7, 1),
            "calories": round(total_calories / 7, 1)
        }

        return summary


def create_plan_for_week(
    user_id: str,
    start_date: date,
    protein_target: float,
    carbs_target: float,
    fats_target: float,
    dining_hall: str = "Kins"
) -> int:
    """
    Convenience function to create and save a weekly plan

    Args:
        user_id: User ID
        start_date: Week start date
        protein_target: Daily protein target
        carbs_target: Daily carbs target
        fats_target: Daily fats target
        dining_hall: Preferred dining hall

    Returns:
        Plan ID
    """
    planner = WeeklyMealPlanner()

    # Generate suggestions
    suggestions = planner.suggest_weekly_plan(
        user_id=user_id,
        start_date=start_date,
        protein_target=protein_target,
        carbs_target=carbs_target,
        fats_target=fats_target,
        dining_hall=dining_hall
    )

    # Save plan
    plan_id = planner.save_suggested_plan(user_id, suggestions)

    print(f"\nWeekly plan created successfully!")
    print(f"Plan ID: {plan_id}")
    print(f"Week: {suggestions['week_start']} to {suggestions['week_end']}")
    print(f"Total meals planned: {len(suggestions['meals'])}")

    return plan_id


if __name__ == "__main__":
    # Test the weekly planner
    print("Testing Weekly Meal Planner\n")
    print("=" * 70)

    planner = WeeklyMealPlanner()

    # Test 1: Create a plan
    print("\n1. Creating weekly plan...")
    plan_id = create_plan_for_week(
        user_id="test_user",
        start_date=date.today(),
        protein_target=150,
        carbs_target=300,
        fats_target=80,
        dining_hall="Kins"
    )

    # Test 2: Get plan summary
    print("\n2. Getting plan summary...")
    summary = planner.get_plan_summary(plan_id)
    print(json.dumps(summary, indent=2))

    # Test 3: Get full plan
    print("\n3. Getting full plan...")
    plan = planner.get_plan(plan_id)
    print(f"Plan: {plan['plan_name']}")
    print(f"Meals: {len(plan['meals'])}")
    for meal in plan['meals'][:3]:  # Show first 3
        print(f"  - {meal['meal_date']} {meal['meal_type']}: "
              f"{meal['total_protein']:.1f}g protein, "
              f"{meal['total_carbs']:.1f}g carbs, "
              f"{meal['total_fats']:.1f}g fat")
