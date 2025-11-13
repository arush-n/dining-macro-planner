"""
Load scraped food data into SQLite database
"""
import sqlite3
import json
import sys
from pathlib import Path
from datetime import date

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH

def load_foods_to_db(foods_data):
    """
    Load list of food dictionaries into the database

    Args:
        foods_data: List of food dictionaries from scraper

    Returns:
        Number of foods inserted
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    inserted_count = 0
    updated_count = 0
    skipped_count = 0

    for food in foods_data:
        try:
            # Check if food already exists
            cursor.execute(
                "SELECT id, confidence_score FROM foods WHERE name = ?",
                (food['name'],)
            )
            existing = cursor.fetchone()

            if existing:
                # Update existing food if scraped today
                food_id, old_confidence = existing

                cursor.execute("""
                    UPDATE foods SET
                        dining_hall = ?,
                        meal_type = ?,
                        protein = ?,
                        carbs = ?,
                        fats = ?,
                        calories = ?,
                        scraped_date = ?
                    WHERE id = ?
                """, (
                    food['dining_hall'],
                    food['meal_type'],
                    food.get('protein'),
                    food.get('carbs'),
                    food.get('fats'),
                    food.get('calories'),
                    food['scraped_date'],
                    food_id
                ))
                updated_count += 1
                print(f"  [UPDATED] {food['name']}")

            else:
                # Insert new food
                cursor.execute("""
                    INSERT INTO foods (
                        name, dining_hall, meal_type,
                        protein, carbs, fats, calories,
                        confidence_score, scraped_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    food['name'],
                    food['dining_hall'],
                    food['meal_type'],
                    food.get('protein'),
                    food.get('carbs'),
                    food.get('fats'),
                    food.get('calories'),
                    food.get('confidence_score', 0.5),
                    food['scraped_date']
                ))
                inserted_count += 1
                print(f"  [OK] Inserted: {food['name']}")

        except sqlite3.IntegrityError as e:
            skipped_count += 1
            print(f"  [SKIP] Skipped (integrity error): {food['name']}")
        except Exception as e:
            skipped_count += 1
            print(f"  [ERROR] Error with {food.get('name', 'unknown')}: {e}")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"LOAD SUMMARY:")
    print(f"  Inserted: {inserted_count}")
    print(f"  Updated:  {updated_count}")
    print(f"  Skipped:  {skipped_count}")
    print(f"  Total:    {len(foods_data)}")
    print("=" * 60)

    return inserted_count


def load_from_json(json_file_path):
    """
    Load foods from a JSON file into the database

    Args:
        json_file_path: Path to JSON file with food data
    """
    with open(json_file_path, 'r') as f:
        foods_data = json.load(f)

    print(f"Loading {len(foods_data)} foods from {json_file_path}")
    return load_foods_to_db(foods_data)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load food data into database")
    parser.add_argument("--json", type=str, help="Path to JSON file with food data")
    parser.add_argument("--sample", action="store_true", help="Load sample data for testing")

    args = parser.parse_args()

    if args.json:
        load_from_json(args.json)
    else:
        # Default: try to load from scraped_foods.json
        json_path = Path(__file__).parent / "scraped_foods.json"
        if json_path.exists():
            load_from_json(json_path)
        else:
            print("No JSON file found. Use --sample to load sample data or --json to specify a file.")
