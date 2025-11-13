"""
RAG Retrieval Layer
Retrieves relevant foods and context from database for Claude agent
"""
import sqlite3
import json
import numpy as np
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH, MAX_RETRIEVED_FOODS, VERIFIED_CONFIDENCE_THRESHOLD

class RAGRetriever:
    """Retrieves foods and context from database using various strategies"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def get_foods_by_macros(
        self,
        protein_range: Optional[Tuple[float, float]] = None,
        carbs_range: Optional[Tuple[float, float]] = None,
        fats_range: Optional[Tuple[float, float]] = None,
        dining_hall: Optional[str] = None,
        meal_type: Optional[str] = None,
        min_confidence: float = 0.0,
        limit: int = MAX_RETRIEVED_FOODS
    ) -> List[Dict]:
        """
        Retrieve foods matching macro ranges

        Args:
            protein_range: (min, max) grams of protein
            carbs_range: (min, max) grams of carbs
            fats_range: (min, max) grams of fats
            dining_hall: Filter by dining hall
            meal_type: Filter by meal type
            min_confidence: Minimum confidence score
            limit: Maximum number of results

        Returns:
            List of food dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM foods WHERE 1=1"
        params = []

        if protein_range:
            query += " AND protein BETWEEN ? AND ?"
            params.extend(protein_range)

        if carbs_range:
            query += " AND carbs BETWEEN ? AND ?"
            params.extend(carbs_range)

        if fats_range:
            query += " AND fats BETWEEN ? AND ?"
            params.extend(fats_range)

        if dining_hall:
            query += " AND dining_hall = ?"
            params.append(dining_hall)

        if meal_type:
            query += " AND meal_type = ?"
            params.append(meal_type)

        if min_confidence:
            query += " AND confidence_score >= ?"
            params.append(min_confidence)

        query += " ORDER BY confidence_score DESC, times_selected DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to dictionaries
        columns = [desc[0] for desc in cursor.description]
        foods = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return foods

    def get_all_available_foods(
        self,
        dining_hall: str,
        meal_type: str,
        include_corrections: bool = True
    ) -> List[Dict]:
        """
        Get all foods available for a specific dining hall and meal

        Args:
            dining_hall: Dining hall name
            meal_type: Meal type
            include_corrections: Whether to include correction history

        Returns:
            List of foods with optional correction data
        """
        foods = self.get_foods_by_macros(
            dining_hall=dining_hall,
            meal_type=meal_type,
            limit=1000  # Get all foods
        )

        if include_corrections:
            for food in foods:
                food['corrections'] = self.get_food_corrections(food['id'])

        return foods

    def get_food_corrections(self, food_id: int) -> List[Dict]:
        """
        Get all corrections for a specific food

        Args:
            food_id: Food ID

        Returns:
            List of correction dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM nutrition_corrections
            WHERE food_id = ?
            ORDER BY votes DESC, timestamp DESC
        """, (food_id,))

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        corrections = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return corrections

    def get_user_history(
        self,
        user_id: str,
        limit: int = 10,
        min_satisfaction: Optional[int] = None
    ) -> List[Dict]:
        """
        Get user's meal history

        Args:
            user_id: User ID
            limit: Maximum number of meals to retrieve
            min_satisfaction: Only return meals with satisfaction >= this

        Returns:
            List of meal combination dictionaries
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT * FROM meal_combinations
            WHERE user_id = ?
        """
        params = [user_id]

        if min_satisfaction is not None:
            query += " AND user_satisfaction >= ?"
            params.append(min_satisfaction)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        meals = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return meals

    def get_user_preferences(self, user_id: str) -> Optional[Dict]:
        """
        Get user's macro targets and preferences

        Args:
            user_id: User ID

        Returns:
            User preferences dictionary or None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM user_preferences WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()

        if row:
            columns = [desc[0] for desc in cursor.description]
            prefs = dict(zip(columns, row))

            # Parse JSON fields
            for field in ['dietary_restrictions', 'avoided_foods', 'preferred_foods']:
                if prefs.get(field):
                    try:
                        prefs[field] = json.loads(prefs[field])
                    except json.JSONDecodeError:
                        prefs[field] = []

            conn.close()
            return prefs

        conn.close()
        return None

    def get_similar_foods(
        self,
        food_name: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get foods similar to the given food name
        (Simple implementation - can be enhanced with embeddings)

        Args:
            food_name: Name of food to find similar foods to
            limit: Maximum number of results

        Returns:
            List of similar foods
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Simple similarity: foods with similar names
        cursor.execute("""
            SELECT * FROM foods
            WHERE name LIKE ?
            OR name LIKE ?
            ORDER BY confidence_score DESC
            LIMIT ?
        """, (f"%{food_name}%", f"%{food_name.split()[0]}%", limit))

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        foods = [dict(zip(columns, row)) for row in rows]

        conn.close()
        return foods

    def build_context_for_agent(
        self,
        user_id: str,
        dining_hall: str,
        meal_type: str,
        macro_targets: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Build comprehensive context string for Claude agent

        Args:
            user_id: User ID
            dining_hall: Dining hall name
            meal_type: Meal type
            macro_targets: Optional dict with protein, carbs, fats targets

        Returns:
            Formatted context string for agent prompt
        """
        # Get all available foods
        foods = self.get_all_available_foods(dining_hall, meal_type)

        # Get user preferences
        preferences = self.get_user_preferences(user_id)

        # Get user history
        history = self.get_user_history(user_id, limit=5, min_satisfaction=4)

        # Build context string
        context_parts = []

        # Section 1: Available foods
        context_parts.append(f"TODAY'S AVAILABLE FOODS AT {dining_hall} {meal_type.upper()}:\n")

        # Categorize foods by macro profile
        high_protein = [f for f in foods if f.get('protein', 0) and f['protein'] >= 20]
        high_carbs = [f for f in foods if f.get('carbs', 0) and f['carbs'] >= 30]
        high_fats = [f for f in foods if f.get('fats', 0) and f['fats'] >= 10]
        balanced = [f for f in foods if f not in high_protein + high_carbs + high_fats]

        if high_protein:
            context_parts.append("\nProteins (High-Confidence):")
            for food in sorted(high_protein, key=lambda x: x.get('confidence_score', 0), reverse=True)[:10]:
                corrections_note = ""
                if food.get('corrections'):
                    corrections_note = f" (corrected {len(food['corrections'])} times)"

                context_parts.append(
                    f"- {food['name']}: {food.get('protein', '?')}g protein, "
                    f"{food.get('carbs', '?')}g carbs, {food.get('fats', '?')}g fat, "
                    f"{food.get('calories', '?')} cal "
                    f"(confidence: {food.get('confidence_score', 0):.2f}){corrections_note}"
                )

        if high_carbs:
            context_parts.append("\nCarbs:")
            for food in sorted(high_carbs, key=lambda x: x.get('confidence_score', 0), reverse=True)[:10]:
                context_parts.append(
                    f"- {food['name']}: {food.get('protein', '?')}g protein, "
                    f"{food.get('carbs', '?')}g carbs, {food.get('fats', '?')}g fat"
                )

        if high_fats:
            context_parts.append("\nFats:")
            for food in sorted(high_fats, key=lambda x: x.get('confidence_score', 0), reverse=True)[:10]:
                context_parts.append(
                    f"- {food['name']}: {food.get('protein', '?')}g protein, "
                    f"{food.get('carbs', '?')}g carbs, {food.get('fats', '?')}g fat"
                )

        # Section 2: User targets and preferences
        if macro_targets or preferences:
            context_parts.append("\n\nYOUR PROFILE:")

        if macro_targets:
            context_parts.append(
                f"- Macro targets: {macro_targets.get('protein', '?')}g protein, "
                f"{macro_targets.get('carbs', '?')}g carbs, {macro_targets.get('fats', '?')}g fat"
            )
        elif preferences:
            context_parts.append(
                f"- Macro targets: {preferences.get('target_protein', '?')}g protein, "
                f"{preferences.get('target_carbs', '?')}g carbs, {preferences.get('target_fats', '?')}g fat"
            )

        if preferences:
            if preferences.get('dietary_restrictions'):
                context_parts.append(f"- Dietary restrictions: {', '.join(preferences['dietary_restrictions'])}")
            if preferences.get('preferred_foods'):
                context_parts.append(f"- Preferred foods: {', '.join(preferences['preferred_foods'])}")
            if preferences.get('avoided_foods'):
                context_parts.append(f"- Avoided foods: {', '.join(preferences['avoided_foods'])}")

        # Section 3: User history
        if history:
            context_parts.append("\n\nYOUR HISTORY:")
            for meal in history:
                food_ids = json.loads(meal['foods'])
                satisfaction = meal.get('user_satisfaction', 'N/A')
                context_parts.append(
                    f"- {meal['date']}: {len(food_ids)} foods, "
                    f"{meal['total_protein']:.1f}g protein, "
                    f"{meal['total_carbs']:.1f}g carbs, "
                    f"{meal['total_fats']:.1f}g fat "
                    f"(rated {satisfaction}/5)"
                )

        # Section 4: Recent corrections
        all_corrections = []
        for food in foods:
            if food.get('corrections'):
                for correction in food['corrections'][:1]:  # Only most recent
                    all_corrections.append((food['name'], correction))

        if all_corrections:
            context_parts.append("\n\nRECENT USER CORRECTIONS:")
            for food_name, correction in all_corrections[:5]:
                context_parts.append(
                    f"- {food_name}: Updated to {correction.get('corrected_protein', '?')}g protein "
                    f"({correction.get('votes', 1)} user(s) confirmed)"
                )

        return "\n".join(context_parts)


# Convenience functions
def get_foods_for_meal(dining_hall: str, meal_type: str) -> List[Dict]:
    """Get all foods for a specific meal"""
    retriever = RAGRetriever()
    return retriever.get_all_available_foods(dining_hall, meal_type)


def get_context_for_user(user_id: str, dining_hall: str, meal_type: str) -> str:
    """Get formatted context for a user"""
    retriever = RAGRetriever()
    return retriever.build_context_for_agent(user_id, dining_hall, meal_type)


if __name__ == "__main__":
    # Test the retriever
    retriever = RAGRetriever()

    print("Testing RAG Retriever\n")
    print("=" * 60)

    # Test 1: Get high protein foods
    print("\n1. High protein foods (20-40g):")
    foods = retriever.get_foods_by_macros(protein_range=(20, 40), limit=5)
    for food in foods:
        print(f"  - {food['name']}: {food['protein']}g protein")

    # Test 2: Build context
    print("\n2. Building context for user 'test_user':")
    context = retriever.build_context_for_agent(
        user_id="test_user",
        dining_hall="J2",
        meal_type="Lunch"
    )
    print(context)
