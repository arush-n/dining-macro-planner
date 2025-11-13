"""
Database initialization script
Creates all tables for the Dining Macro Planner
"""
import sqlite3
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH

def init_database():
    """Initialize the database with all required tables"""

    # Create database directory if it doesn't exist
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Table 1: foods
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS foods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        dining_hall TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        protein REAL,
        carbs REAL,
        fats REAL,
        calories REAL,
        confidence_score REAL DEFAULT 0.5,
        scraped_date DATE NOT NULL,
        last_verified DATE,
        times_selected INTEGER DEFAULT 0,
        CHECK (dining_hall IN ('J2', 'JCL', 'Kins')),
        CHECK (meal_type IN ('Breakfast', 'Lunch', 'Dinner')),
        CHECK (confidence_score BETWEEN 0 AND 1)
    )
    """)

    # Table 2: meal_combinations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meal_combinations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        date DATE NOT NULL,
        foods TEXT NOT NULL,  -- JSON array of food_ids
        total_protein REAL NOT NULL,
        total_carbs REAL NOT NULL,
        total_fats REAL NOT NULL,
        total_calories REAL NOT NULL,
        user_satisfaction INTEGER,  -- 1-5 rating
        notes TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        CHECK (user_satisfaction IS NULL OR user_satisfaction BETWEEN 1 AND 5)
    )
    """)

    # Table 3: nutrition_corrections
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nutrition_corrections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER NOT NULL,
        corrected_protein REAL,
        corrected_carbs REAL,
        corrected_fats REAL,
        corrected_calories REAL,
        corrected_by_user TEXT NOT NULL,
        reason TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        votes INTEGER DEFAULT 1,
        FOREIGN KEY (food_id) REFERENCES foods(id)
    )
    """)

    # Table 4: user_preferences
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id TEXT PRIMARY KEY,
        target_protein INTEGER NOT NULL,
        target_carbs INTEGER NOT NULL,
        target_fats INTEGER NOT NULL,
        dietary_restrictions TEXT,  -- JSON array
        avoided_foods TEXT,  -- JSON array
        preferred_foods TEXT,  -- JSON array
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Table 5: food_embeddings
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        food_id INTEGER NOT NULL UNIQUE,
        embedding BLOB NOT NULL,  -- Serialized vector
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (food_id) REFERENCES foods(id)
    )
    """)

    # Table 6: weekly_meal_plans
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weekly_meal_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        plan_name TEXT,
        week_start_date DATE NOT NULL,
        week_end_date DATE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )
    """)

    # Table 7: planned_meals
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS planned_meals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        meal_date DATE NOT NULL,
        dining_hall TEXT NOT NULL,
        meal_type TEXT NOT NULL,
        foods TEXT NOT NULL,  -- JSON array of food_ids
        total_protein REAL NOT NULL,
        total_carbs REAL NOT NULL,
        total_fats REAL NOT NULL,
        total_calories REAL NOT NULL,
        notes TEXT,
        was_eaten BOOLEAN DEFAULT 0,
        actual_satisfaction INTEGER,  -- 1-5 rating if eaten
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        CHECK (dining_hall IN ('J2', 'JCL', 'Kins')),
        CHECK (meal_type IN ('Breakfast', 'Lunch', 'Dinner')),
        CHECK (actual_satisfaction IS NULL OR actual_satisfaction BETWEEN 1 AND 5),
        FOREIGN KEY (plan_id) REFERENCES weekly_meal_plans(id)
    )
    """)

    # Create indexes for faster queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_dining_hall ON foods(dining_hall)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_meal_type ON foods(meal_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_protein ON foods(protein)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_confidence ON foods(confidence_score)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_foods_scraped_date ON foods(scraped_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_meal_combinations_user ON meal_combinations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_meal_combinations_date ON meal_combinations(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_corrections_food ON nutrition_corrections(food_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weekly_plans_user ON weekly_meal_plans(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_weekly_plans_dates ON weekly_meal_plans(week_start_date, week_end_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planned_meals_plan ON planned_meals(plan_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_planned_meals_date ON planned_meals(meal_date)")

    conn.commit()
    conn.close()

    print(f"[OK] Database initialized successfully at {DATABASE_PATH}")
    print("[OK] All tables created")
    print("[OK] Indexes created")

if __name__ == "__main__":
    init_database()
