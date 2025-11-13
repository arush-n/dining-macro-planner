"""
Optimized Food Search Engine
Fast, accurate food retrieval with caching and smart algorithms
"""
import sqlite3
import json
from datetime import date, datetime, timedelta
from typing import List, Dict, Tuple, Optional
from functools import lru_cache
from collections import defaultdict
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH, MAX_RETRIEVED_FOODS, MACRO_TOLERANCE


class OptimizedFoodSearch:
    """
    High-performance food search engine with multiple optimization strategies
    """

    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._cache_timestamps = {}

    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self._cache_timestamps:
            return False

        age = (datetime.now() - self._cache_timestamps[cache_key]).total_seconds()
        return age < self._cache_ttl

    def _get_cached(self, cache_key: str):
        """Get cached result if valid"""
        if self._is_cache_valid(cache_key):
            return self._cache.get(cache_key)
        return None

    def _set_cache(self, cache_key: str, value):
        """Set cache entry with timestamp"""
        self._cache[cache_key] = value
        self._cache_timestamps[cache_key] = datetime.now()

    def clear_cache(self):
        """Clear all cache"""
        self._cache.clear()
        self._cache_timestamps.clear()

    def search_by_macros(
        self,
        protein_target: Optional[float] = None,
        carbs_target: Optional[float] = None,
        fats_target: Optional[float] = None,
        dining_hall: Optional[str] = None,
        meal_type: Optional[str] = None,
        target_date: Optional[date] = None,
        tolerance: int = MACRO_TOLERANCE,
        min_confidence: float = 0.3,
        limit: int = MAX_RETRIEVED_FOODS
    ) -> List[Dict]:
        """
        Smart macro-based search with scoring algorithm

        Args:
            protein_target: Target protein in grams
            carbs_target: Target carbs in grams
            fats_target: Target fats in grams
            dining_hall: Filter by dining hall
            meal_type: Filter by meal type
            target_date: Filter by foods available on this date
            tolerance: Tolerance for macro matching (±grams)
            min_confidence: Minimum confidence score
            limit: Maximum results

        Returns:
            List of foods sorted by relevance score
        """
        # Build cache key
        cache_key = f"search_{protein_target}_{carbs_target}_{fats_target}_{dining_hall}_{meal_type}_{target_date}_{tolerance}"

        # Check cache
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        conn = self._get_connection()
        cursor = conn.cursor()

        # Build optimized query
        query = """
            SELECT
                f.*,
                f.confidence_score * (1 + f.times_selected * 0.01) as relevance_base
            FROM foods f
            WHERE 1=1
        """
        params = []

        # Filter by dining hall and meal type
        if dining_hall:
            query += " AND f.dining_hall = ?"
            params.append(dining_hall)

        if meal_type:
            query += " AND f.meal_type = ?"
            params.append(meal_type)

        # Filter by date (foods scraped recently or on target date)
        if target_date:
            query += " AND f.scraped_date >= ?"
            params.append((target_date - timedelta(days=7)).isoformat())

        # Filter by confidence
        query += " AND f.confidence_score >= ?"
        params.append(min_confidence)

        # Add macro range filters for performance
        if protein_target is not None:
            query += " AND f.protein BETWEEN ? AND ?"
            params.extend([
                max(0, protein_target - tolerance * 2),
                protein_target + tolerance * 2
            ])

        if carbs_target is not None:
            query += " AND f.carbs BETWEEN ? AND ?"
            params.extend([
                max(0, carbs_target - tolerance * 2),
                carbs_target + tolerance * 2
            ])

        if fats_target is not None:
            query += " AND f.fats BETWEEN ? AND ?"
            params.extend([
                max(0, fats_target - tolerance * 2),
                fats_target + tolerance * 2
            ])

        cursor.execute(query, params)
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        # Convert to dictionaries
        foods = []
        for row in rows:
            food = dict(zip(columns, row))

            # Calculate relevance score
            score = self._calculate_relevance_score(
                food,
                protein_target,
                carbs_target,
                fats_target,
                tolerance
            )
            food['relevance_score'] = score
            foods.append(food)

        conn.close()

        # Sort by relevance score
        foods.sort(key=lambda x: x['relevance_score'], reverse=True)

        # Limit results
        result = foods[:limit]

        # Cache result
        self._set_cache(cache_key, result)

        return result

    def _calculate_relevance_score(
        self,
        food: Dict,
        protein_target: Optional[float],
        carbs_target: Optional[float],
        fats_target: Optional[float],
        tolerance: int
    ) -> float:
        """
        Calculate relevance score for a food item

        Scoring factors:
        - Macro fit (how close to targets)
        - Confidence score
        - Popularity (times selected)
        - Recent updates
        """
        score = 0.0

        # Base score from confidence and popularity
        confidence = food.get('confidence_score', 0.5)
        times_selected = food.get('times_selected', 0)
        score += confidence * 40  # Max 40 points from confidence
        score += min(times_selected * 0.5, 20)  # Max 20 points from popularity

        # Macro fit score
        macro_fit = 0.0
        macro_count = 0

        if protein_target is not None and food.get('protein') is not None:
            diff = abs(food['protein'] - protein_target)
            if diff <= tolerance:
                macro_fit += (tolerance - diff) / tolerance * 15
            macro_count += 1

        if carbs_target is not None and food.get('carbs') is not None:
            diff = abs(food['carbs'] - carbs_target)
            if diff <= tolerance:
                macro_fit += (tolerance - diff) / tolerance * 15
            macro_count += 1

        if fats_target is not None and food.get('fats') is not None:
            diff = abs(food['fats'] - fats_target)
            if diff <= tolerance:
                macro_fit += (tolerance - diff) / tolerance * 10
            macro_count += 1

        if macro_count > 0:
            score += macro_fit

        # Bonus for recent scrapes
        if food.get('scraped_date'):
            try:
                scraped = datetime.fromisoformat(food['scraped_date']).date()
                days_old = (date.today() - scraped).days
                if days_old <= 7:
                    score += (7 - days_old) * 1  # Max 7 points for freshness
            except:
                pass

        return score

    def find_meal_combinations(
        self,
        protein_target: float,
        carbs_target: float,
        fats_target: float,
        dining_hall: str,
        meal_type: str,
        target_date: Optional[date] = None,
        max_items: int = 5,
        num_combinations: int = 5,
        tolerance: int = MACRO_TOLERANCE
    ) -> List[Dict]:
        """
        Find optimal meal combinations that hit macro targets

        Uses a greedy algorithm with backtracking for fast results

        Args:
            protein_target: Target protein
            carbs_target: Target carbs
            fats_target: Target fats
            dining_hall: Dining hall
            meal_type: Meal type
            target_date: Target date
            max_items: Maximum items per combination
            num_combinations: Number of combinations to return
            tolerance: Macro tolerance

        Returns:
            List of meal combination dictionaries
        """
        # Get all available foods
        cache_key = f"foods_{dining_hall}_{meal_type}_{target_date}"
        cached_foods = self._get_cached(cache_key)

        if cached_foods is None:
            conn = self._get_connection()
            cursor = conn.cursor()

            query = "SELECT * FROM foods WHERE dining_hall = ? AND meal_type = ?"
            params = [dining_hall, meal_type]

            if target_date:
                query += " AND scraped_date >= ?"
                params.append((target_date - timedelta(days=7)).isoformat())

            query += " ORDER BY confidence_score DESC, times_selected DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            cached_foods = [dict(zip(columns, row)) for row in rows]
            conn.close()

            self._set_cache(cache_key, cached_foods)

        # Greedy algorithm to find combinations
        combinations = []

        # Sort foods by macro density for efficient search
        high_protein = [f for f in cached_foods if f.get('protein', 0) >= 15]
        high_carbs = [f for f in cached_foods if f.get('carbs', 0) >= 25]
        balanced = [f for f in cached_foods if f not in high_protein + high_carbs]

        # Try different starting points
        for _ in range(num_combinations * 3):  # More attempts than needed
            combo = self._build_combination(
                high_protein, high_carbs, balanced,
                protein_target, carbs_target, fats_target,
                max_items, tolerance
            )

            if combo and combo not in combinations:
                combinations.append(combo)

            if len(combinations) >= num_combinations:
                break

        return combinations[:num_combinations]

    def _build_combination(
        self,
        high_protein: List[Dict],
        high_carbs: List[Dict],
        balanced: List[Dict],
        protein_target: float,
        carbs_target: float,
        fats_target: float,
        max_items: int,
        tolerance: int
    ) -> Optional[Dict]:
        """Build a single meal combination using greedy selection"""
        import random

        selected = []
        totals = {'protein': 0.0, 'carbs': 0.0, 'fats': 0.0, 'calories': 0.0}

        # Determine needed macros
        protein_gap = protein_target
        carbs_gap = carbs_target
        fats_gap = fats_target

        # Add random variation to avoid identical combinations
        pools = [high_protein, high_carbs, balanced]
        random.shuffle(pools)

        for pool in pools:
            if len(selected) >= max_items:
                break

            pool_copy = pool.copy()
            random.shuffle(pool_copy)

            for food in pool_copy[:10]:  # Only consider top 10 from each pool
                if len(selected) >= max_items:
                    break

                # Check if adding this food helps
                if food in selected:
                    continue

                new_protein = totals['protein'] + food.get('protein', 0)
                new_carbs = totals['carbs'] + food.get('carbs', 0)
                new_fats = totals['fats'] + food.get('fats', 0)

                # Don't overshoot too much
                if (new_protein > protein_target + tolerance * 2 or
                    new_carbs > carbs_target + tolerance * 2 or
                    new_fats > fats_target + tolerance * 2):
                    continue

                # Add if it reduces the gap
                selected.append(food)
                totals['protein'] = new_protein
                totals['carbs'] = new_carbs
                totals['fats'] = new_fats
                totals['calories'] += food.get('calories', 0)

                protein_gap = abs(protein_target - totals['protein'])
                carbs_gap = abs(carbs_target - totals['carbs'])
                fats_gap = abs(fats_target - totals['fats'])

                # If we hit targets, stop
                if (protein_gap <= tolerance and
                    carbs_gap <= tolerance and
                    fats_gap <= tolerance):
                    break

        # Check if combination is good enough
        if (abs(protein_target - totals['protein']) <= tolerance * 1.5 and
            abs(carbs_target - totals['carbs']) <= tolerance * 1.5 and
            abs(fats_target - totals['fats']) <= tolerance * 1.5):

            return {
                'foods': selected,
                'food_ids': [f['id'] for f in selected],
                'food_names': [f['name'] for f in selected],
                'total_protein': totals['protein'],
                'total_carbs': totals['carbs'],
                'total_fats': totals['fats'],
                'total_calories': totals['calories'],
                'protein_diff': abs(protein_target - totals['protein']),
                'carbs_diff': abs(carbs_target - totals['carbs']),
                'fats_diff': abs(fats_target - totals['fats']),
                'score': self._score_combination(totals, protein_target, carbs_target, fats_target)
            }

        return None

    def _score_combination(
        self,
        totals: Dict,
        protein_target: float,
        carbs_target: float,
        fats_target: float
    ) -> float:
        """Score how well a combination matches targets"""
        protein_diff = abs(protein_target - totals['protein'])
        carbs_diff = abs(carbs_target - totals['carbs'])
        fats_diff = abs(fats_target - totals['fats'])

        # Lower difference = higher score
        score = 100 - (protein_diff + carbs_diff + fats_diff) / 3
        return max(0, score)

    def get_foods_for_date(
        self,
        dining_hall: str,
        meal_type: str,
        target_date: date
    ) -> List[Dict]:
        """
        Get foods available for a specific date

        Args:
            dining_hall: Dining hall name
            meal_type: Meal type
            target_date: Target date

        Returns:
            List of available foods
        """
        cache_key = f"date_{dining_hall}_{meal_type}_{target_date}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        conn = self._get_connection()
        cursor = conn.cursor()

        # Get foods scraped within 7 days of target date
        cursor.execute("""
            SELECT * FROM foods
            WHERE dining_hall = ?
            AND meal_type = ?
            AND scraped_date >= ?
            AND scraped_date <= ?
            ORDER BY confidence_score DESC, scraped_date DESC
        """, (
            dining_hall,
            meal_type,
            (target_date - timedelta(days=7)).isoformat(),
            (target_date + timedelta(days=1)).isoformat()
        ))

        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        foods = [dict(zip(columns, row)) for row in rows]
        conn.close()

        self._set_cache(cache_key, foods)
        return foods


# Singleton instance for reuse
_search_engine = None

def get_search_engine() -> OptimizedFoodSearch:
    """Get or create singleton search engine instance"""
    global _search_engine
    if _search_engine is None:
        _search_engine = OptimizedFoodSearch()
    return _search_engine


if __name__ == "__main__":
    # Test the search engine
    engine = OptimizedFoodSearch()

    print("Testing Optimized Food Search Engine\n")
    print("=" * 70)

    # Test 1: Macro search
    print("\n1. Searching for high protein foods:")
    results = engine.search_by_macros(
        protein_target=30,
        dining_hall="Kins",
        meal_type="Lunch",
        limit=5
    )
    for food in results:
        print(f"  - {food['name']}: {food['protein']}g protein (score: {food['relevance_score']:.1f})")

    # Test 2: Find meal combinations
    print("\n2. Finding meal combinations for 40g protein, 150g carbs, 50g fat:")
    combos = engine.find_meal_combinations(
        protein_target=40,
        carbs_target=150,
        fats_target=50,
        dining_hall="Kins",
        meal_type="Lunch",
        num_combinations=3
    )

    for i, combo in enumerate(combos, 1):
        print(f"\n  Combination {i} (Score: {combo['score']:.1f}):")
        for food in combo['foods']:
            print(f"    - {food['name']}")
        print(f"    Totals: {combo['total_protein']:.1f}g protein, "
              f"{combo['total_carbs']:.1f}g carbs, {combo['total_fats']:.1f}g fat")
