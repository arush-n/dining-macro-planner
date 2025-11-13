"""
Setup Verification Script
Checks if everything is configured correctly before starting
"""
import os
import sys
from pathlib import Path
import sqlite3

def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        return False, f"Python 3.9+ required (you have {version.major}.{version.minor})"
    return True, f"Python {version.major}.{version.minor}.{version.micro} ✓"

def check_dependencies():
    """Check if required packages are installed"""
    required = [
        'fastapi',
        'uvicorn',
        'google.generativeai',
        'sklearn',
        'numpy',
        'requests',
        'beautifulsoup4'
    ]

    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        return False, f"Missing packages: {', '.join(missing)}"
    return True, "All dependencies installed"

def check_database():
    """Check if database exists and has data"""
    db_path = Path(__file__).parent / "database" / "dining_planner.db"

    if not db_path.exists():
        return False, "Database not found. Run: python database/init_db.py"

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['foods', 'meal_combinations', 'user_preferences', 'nutrition_corrections', 'food_embeddings']

        missing_tables = [t for t in required_tables if t not in tables]
        if missing_tables:
            conn.close()
            return False, f"Missing tables: {', '.join(missing_tables)}"

        # Check if foods table has data
        cursor.execute("SELECT COUNT(*) FROM foods")
        count = cursor.fetchone()[0]

        conn.close()

        if count == 0:
            return False, "No foods in database. Run: python scraper/load_data.py --sample"

        return True, f"Database ready ({count} foods)"

    except Exception as e:
        return False, f"Database error: {str(e)}"

def check_api_key():
    """Check if Gemini API key is set"""
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return False, "Not set (AI chat won't work)"

    if len(api_key) < 20:
        return False, "API key seems invalid (too short)"

    return True, "API key configured"

def check_directories():
    """Check if all required directories exist"""
    base_dir = Path(__file__).parent
    required_dirs = [
        'database',
        'scraper',
        'rag',
        'agent',
        'api',
        'frontend',
        'frontend/static'
    ]

    missing = []
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        if not dir_path.exists():
            missing.append(dir_name)

    if missing:
        return False, f"Missing directories: {', '.join(missing)}"
    return True, "All directories present"

def check_frontend_files():
    """Check if frontend files exist"""
    base_dir = Path(__file__).parent
    required_files = [
        'frontend/index.html',
        'frontend/static/style.css',
        'frontend/static/script.js'
    ]

    missing = []
    for file_name in required_files:
        file_path = base_dir / file_name
        if not file_path.exists():
            missing.append(file_name)

    if missing:
        return False, f"Missing files: {', '.join(missing)}"
    return True, "All frontend files present"

def main():
    """Run all checks"""
    print("=" * 70)
    print("SETUP VERIFICATION")
    print("=" * 70)
    print()
    sys.stdout.flush()

    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Directories", check_directories),
        ("Frontend Files", check_frontend_files),
        ("Database", check_database),
        ("Gemini API Key", check_api_key),
    ]

    passed = 0
    failed = 0
    warnings = 0

    for check_name, check_func in checks:
        print(f"Checking {check_name}...", end=" ", flush=True)
        try:
            success, message = check_func()

            if success:
                print(f"✓ {message}")
                passed += 1
            else:
                if check_name == "Gemini API Key":
                    print(f"⚠ {message}")
                    warnings += 1
                else:
                    print(f"✗ {message}")
                    failed += 1
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            failed += 1

        sys.stdout.flush()

    print()
    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed, {warnings} warnings")
    print("=" * 70)
    print()
    sys.stdout.flush()

    if failed > 0:
        print("❌ Setup incomplete. Please fix the errors above.")
        print()
        print("Quick fixes:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Initialize database: python database/init_db.py")
        print("  3. Load sample data: python scraper/load_data.py --sample")
        print()
        sys.stdout.flush()
        return False

    if warnings > 0:
        print("⚠️  Setup mostly complete, but with warnings:")
        print("   - AI chat won't work without GEMINI_API_KEY")
        print("   - Other features (calculator, manual selection) will work")
        print()
        print("To set API key:")
        print("  Windows: set GEMINI_API_KEY=your-key-here")
        print("  Linux/Mac: export GEMINI_API_KEY=your-key-here")
        print()
        sys.stdout.flush()

    print("✓ System ready to start!")
    print()
    print("Start with:")
    print("  python start_all.py")
    print("  OR")
    print("  python run_server.py  (in one terminal)")
    print("  python start_frontend.py  (in another terminal)")
    print()
    sys.stdout.flush()

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
