"""
Configuration file for Dining Macro Planner
"""
import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).parent
DATABASE_PATH = BASE_DIR / "database" / "dining_planner.db"

# Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCfJxOEZivlCHXWKUixFqVSNkkzUhTg65w")

# Dining halls
DINING_HALLS = ["J2", "JCL", "Kins"]
MEAL_TYPES = ["Breakfast", "Lunch", "Dinner"]

# RAG Settings
EMBEDDING_MODEL = "claude-3-5-sonnet-20241022"  # Using Claude for embeddings via text
SIMILARITY_THRESHOLD = 0.7
MAX_RETRIEVED_FOODS = 50

# Agent Settings
AGENT_MODEL = "gemini-2.5-flash"  # Fast and efficient. Use "gemini-2.5-pro" for higher quality
MAX_TOKENS = 8000  # Increased to allow for longer system prompts and responses
TEMPERATURE = 0.7

# Macro tolerance (±grams)
MACRO_TOLERANCE = 5

# Default confidence score for scraped foods
DEFAULT_CONFIDENCE = 0.5
VERIFIED_CONFIDENCE_THRESHOLD = 0.8

# Crowdsource validation
MIN_VOTES_FOR_UPDATE = 3
