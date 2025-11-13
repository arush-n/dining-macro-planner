"""
Setup script for Dining Macro Planner
Automates initial setup process
"""
import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is 3.9+"""
    if sys.version_info < (3, 9):
        print("ERROR: Python 3.9 or higher is required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print("✓ Python version OK")

def check_api_key():
    """Check if Gemini API key is set"""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your-gemini-api-key-here":
        print("⚠ WARNING: GEMINI_API_KEY not set or using placeholder")
        print("  Please set your API key:")
        print("  - Create a .env file (copy from .env.example)")
        print("  - Or: export GEMINI_API_KEY=your-key-here")
        return False
    print("✓ Gemini API key configured")
    return True

def init_database():
    """Initialize the database"""
    print("\nInitializing database...")
    from database.init_db import init_database
    try:
        init_database()
        print("✓ Database initialized")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def load_sample_data():
    """Load sample data"""
    print("\nLoading sample data...")
    from scraper.load_data import load_sample_data
    try:
        count = load_sample_data()
        print(f"✓ Loaded {count} sample foods")
        return True
    except Exception as e:
        print(f"✗ Failed to load sample data: {e}")
        return False

def generate_embeddings():
    """Generate food embeddings"""
    print("\nGenerating embeddings...")
    from rag.generate_embeddings import generate_embeddings
    try:
        generate_embeddings()
        print("✓ Embeddings generated")
        return True
    except Exception as e:
        print(f"✗ Failed to generate embeddings: {e}")
        return False

def main():
    """Main setup function"""
    print("=" * 70)
    print("DINING MACRO PLANNER - SETUP")
    print("=" * 70)
    print()

    # Check requirements
    check_python_version()
    has_api_key = check_api_key()
    
    print()
    
    # Initialize components
    success = []
    success.append(init_database())
    success.append(load_sample_data())
    success.append(generate_embeddings())
    
    print()
    print("=" * 70)
    
    if all(success):
        print("✓ SETUP COMPLETE!")
        print()
        print("Next steps:")
        print("1. Start the API server:")
        print("   python api/main.py")
        print()
        print("2. Open frontend/index.html in your browser")
        print()
        if not has_api_key:
            print("NOTE: Set GEMINI_API_KEY before getting recommendations")
    else:
        print("✗ SETUP INCOMPLETE")
        print("Please fix errors above and run setup again")
    
    print("=" * 70)

if __name__ == "__main__":
    main()
