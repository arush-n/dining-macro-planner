"""
FastAPI Backend for Dining Macro Planner
Provides REST API endpoints for the meal planning system
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import sqlite3
import json
from datetime import date, datetime
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH, DINING_HALLS, MEAL_TYPES
from agent.agent import MealPlanningAgent
from rag.rag_retriever import RAGRetriever
from scraper.scrape_service import get_scraping_service

# Initialize FastAPI app
app = FastAPI(
    title="Dining Macro Planner API",
    description="RAG + Agent powered meal planning system with web scraping",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agent, retriever, and scraping service
agent = MealPlanningAgent()
retriever = RAGRetriever()
scraping_service = get_scraping_service()

# Pydantic models for requests/responses
class UserPreferences(BaseModel):
    target_protein: int
    target_carbs: int
    target_fats: int
    dietary_restrictions: Optional[List[str]] = []
    avoided_foods: Optional[List[str]] = []
    preferred_foods: Optional[List[str]] = []

class RecommendationRequest(BaseModel):
    user_id: str
    dining_hall: str
    meal_type: str
    protein_target: Optional[int] = None
    carbs_target: Optional[int] = None
    fats_target: Optional[int] = None

class MealSelection(BaseModel):
    user_id: str
    food_ids: List[int]
    total_protein: float
    total_carbs: float
    total_fats: float
    total_calories: float

class FoodCorrection(BaseModel):
    corrected_by_user: str
    corrected_protein: Optional[float] = None
    corrected_carbs: Optional[float] = None
    corrected_fats: Optional[float] = None
    corrected_calories: Optional[float] = None
    reason: Optional[str] = None

class MealRating(BaseModel):
    meal_id: int
    rating: int  # 1-5
    notes: Optional[str] = None

class RefinementRequest(BaseModel):
    user_id: str
    dining_hall: str
    meal_type: str
    message: str


# Database helper
def get_db():
    """Get database connection"""
    return sqlite3.connect(DATABASE_PATH)


# ENDPOINTS

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Dining Macro Planner API - Complete Meal Planning System",
        "version": "2.0.0",
        "features": [
            "AI-Powered Meal Recommendations",
            "Web Scraping from Dining Halls",
            "Weekly Meal Planning",
            "Nutrition Tracking",
            "User Preferences & History"
        ],
        "endpoints": {
            "user": {
                "preferences": "/user/{user_id}/preferences",
                "summary": "/user/{user_id}/summary"
            },
            "meal_planning": {
                "recommendations": "/recommendations",
                "refine": "/refine",
                "select": "/select",
                "rate_meal": "/rate-meal"
            },
            "foods": {
                "get_foods": "/foods/{dining_hall}/{meal_type}",
                "feedback": "/feedback/food/{food_id}"
            },
            "scraping": {
                "scrape_dining_hall": "/scrape/dining-hall/{dining_hall}",
                "scrape_specific_meal": "/scrape/meal",
                "refresh_all": "/scrape/refresh",
                "scrape_status": "/scrape/status"
            },
            "health": "/health"
        },
        "dining_halls": DINING_HALLS,
        "meal_types": MEAL_TYPES
    }


@app.post("/user/{user_id}/preferences")
async def set_preferences(user_id: str, preferences: UserPreferences):
    """Set or update user preferences"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Check if user exists
        cursor.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
        exists = cursor.fetchone()

        # Convert lists to JSON
        dietary_restrictions_json = json.dumps(preferences.dietary_restrictions)
        avoided_foods_json = json.dumps(preferences.avoided_foods)
        preferred_foods_json = json.dumps(preferences.preferred_foods)

        if exists:
            cursor.execute("""
                UPDATE user_preferences SET
                    target_protein = ?,
                    target_carbs = ?,
                    target_fats = ?,
                    dietary_restrictions = ?,
                    avoided_foods = ?,
                    preferred_foods = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE user_id = ?
            """, (
                preferences.target_protein,
                preferences.target_carbs,
                preferences.target_fats,
                dietary_restrictions_json,
                avoided_foods_json,
                preferred_foods_json,
                user_id
            ))
        else:
            cursor.execute("""
                INSERT INTO user_preferences (
                    user_id, target_protein, target_carbs, target_fats,
                    dietary_restrictions, avoided_foods, preferred_foods
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                preferences.target_protein,
                preferences.target_carbs,
                preferences.target_fats,
                dietary_restrictions_json,
                avoided_foods_json,
                preferred_foods_json
            ))

        conn.commit()
        return {"status": "success", "message": "Preferences saved", "user_id": user_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/user/{user_id}/preferences")
async def get_preferences(user_id: str):
    """Get user preferences"""
    prefs = retriever.get_user_preferences(user_id)
    if not prefs:
        raise HTTPException(status_code=404, detail="User preferences not found")
    return prefs


@app.post("/recommendations")
async def get_recommendations(request: RecommendationRequest):
    """Get meal recommendations from Claude agent"""

    # Validate inputs
    if request.dining_hall not in DINING_HALLS:
        raise HTTPException(status_code=400, detail=f"Invalid dining hall. Must be one of: {DINING_HALLS}")

    if request.meal_type not in MEAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid meal type. Must be one of: {MEAL_TYPES}")

    try:
        # Get macro targets from request or user preferences
        if request.protein_target and request.carbs_target and request.fats_target:
            protein = request.protein_target
            carbs = request.carbs_target
            fats = request.fats_target
        else:
            # Get from user preferences
            prefs = retriever.get_user_preferences(request.user_id)
            if not prefs:
                raise HTTPException(
                    status_code=400,
                    detail="No macro targets provided and no user preferences found. Please set preferences first."
                )
            protein = prefs['target_protein']
            carbs = prefs['target_carbs']
            fats = prefs['target_fats']

        # Get recommendations from agent
        response = agent.suggest_meals(
            user_id=request.user_id,
            dining_hall=request.dining_hall,
            meal_type=request.meal_type,
            protein_target=protein,
            carbs_target=carbs,
            fats_target=fats
        )

        return {
            "status": "success",
            "user_id": request.user_id,
            "dining_hall": request.dining_hall,
            "meal_type": request.meal_type,
            "targets": {
                "protein": protein,
                "carbs": carbs,
                "fats": fats
            },
            "recommendations": response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/refine")
async def refine_recommendations(request: RefinementRequest):
    """Refine recommendations based on user feedback"""
    try:
        response = agent.refine_suggestion(
            user_message=request.message,
            user_id=request.user_id,
            dining_hall=request.dining_hall,
            meal_type=request.meal_type
        )

        return {
            "status": "success",
            "refined_recommendations": response
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/select")
async def select_meal(selection: MealSelection):
    """Record user's meal selection"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Store meal combination
        cursor.execute("""
            INSERT INTO meal_combinations (
                user_id, date, foods,
                total_protein, total_carbs, total_fats, total_calories
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            selection.user_id,
            str(date.today()),
            json.dumps(selection.food_ids),
            selection.total_protein,
            selection.total_carbs,
            selection.total_fats,
            selection.total_calories
        ))

        meal_id = cursor.lastrowid

        # Increment times_selected for each food
        for food_id in selection.food_ids:
            cursor.execute("""
                UPDATE foods
                SET times_selected = times_selected + 1
                WHERE id = ?
            """, (food_id,))

        conn.commit()

        return {
            "status": "success",
            "message": "Meal selection recorded",
            "meal_id": meal_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/feedback/food/{food_id}")
async def submit_food_correction(food_id: int, correction: FoodCorrection):
    """Submit correction for food nutrition data"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Check if food exists
        cursor.execute("SELECT id FROM foods WHERE id = ?", (food_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Food not found")

        # Insert correction
        cursor.execute("""
            INSERT INTO nutrition_corrections (
                food_id, corrected_protein, corrected_carbs, corrected_fats,
                corrected_calories, corrected_by_user, reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            food_id,
            correction.corrected_protein,
            correction.corrected_carbs,
            correction.corrected_fats,
            correction.corrected_calories,
            correction.corrected_by_user,
            correction.reason
        ))

        conn.commit()

        return {
            "status": "success",
            "message": "Correction submitted",
            "food_id": food_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.post("/rate-meal")
async def rate_meal(rating: MealRating):
    """Rate a meal combination"""
    if rating.rating < 1 or rating.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE meal_combinations
            SET user_satisfaction = ?, notes = ?
            WHERE id = ?
        """, (rating.rating, rating.notes, rating.meal_id))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Meal not found")

        conn.commit()

        return {
            "status": "success",
            "message": "Rating recorded",
            "meal_id": rating.meal_id,
            "rating": rating.rating
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/foods/{dining_hall}/{meal_type}")
async def get_foods(dining_hall: str, meal_type: str):
    """Get all available foods for a dining hall and meal type"""
    if dining_hall not in DINING_HALLS:
        raise HTTPException(status_code=400, detail=f"Invalid dining hall. Must be one of: {DINING_HALLS}")

    if meal_type not in MEAL_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid meal type. Must be one of: {MEAL_TYPES}")

    foods = retriever.get_all_available_foods(dining_hall, meal_type, include_corrections=True)

    return {
        "dining_hall": dining_hall,
        "meal_type": meal_type,
        "count": len(foods),
        "foods": foods
    }


@app.get("/user/{user_id}/summary")
async def get_user_summary(user_id: str, days: int = 7):
    """Get summary of user's meals and progress"""
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Get user preferences
        prefs = retriever.get_user_preferences(user_id)

        # Get recent meals
        history = retriever.get_user_history(user_id, limit=days * 3)  # Assume 3 meals/day

        # Calculate averages
        if history:
            avg_protein = sum(m['total_protein'] for m in history) / len(history)
            avg_carbs = sum(m['total_carbs'] for m in history) / len(history)
            avg_fats = sum(m['total_fats'] for m in history) / len(history)
            avg_satisfaction = sum(
                m['user_satisfaction'] for m in history if m['user_satisfaction']
            ) / len([m for m in history if m['user_satisfaction']]) if any(m['user_satisfaction'] for m in history) else None
        else:
            avg_protein = avg_carbs = avg_fats = avg_satisfaction = None

        return {
            "user_id": user_id,
            "preferences": prefs,
            "recent_meals": history,
            "averages": {
                "protein": round(avg_protein, 1) if avg_protein else None,
                "carbs": round(avg_carbs, 1) if avg_carbs else None,
                "fats": round(avg_fats, 1) if avg_fats else None,
                "satisfaction": round(avg_satisfaction, 1) if avg_satisfaction else None
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# ============================================================================
# SCRAPING ENDPOINTS
# ============================================================================

class ScrapeRequest(BaseModel):
    """Request model for scraping operations"""
    dining_hall: Optional[str] = None
    meal_type: Optional[str] = None
    target_date: Optional[str] = None  # YYYY-MM-DD format


@app.post("/scrape/dining-hall/{dining_hall}")
async def scrape_dining_hall(dining_hall: str, target_date: Optional[str] = None):
    """
    Scrape all meals for a specific dining hall

    Args:
        dining_hall: Dining hall name (J2, JCL, or Kins)
        target_date: Optional date in YYYY-MM-DD format

    Returns:
        Scrape results including all foods found
    """
    if dining_hall not in DINING_HALLS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dining hall. Must be one of: {', '.join(DINING_HALLS)}"
        )

    # Parse date if provided
    date_obj = None
    if target_date:
        try:
            date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    result = scraping_service.scrape_dining_hall(dining_hall, date_obj, save_to_db=True)

    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])

    return result


@app.post("/scrape/meal")
async def scrape_specific_meal(request: ScrapeRequest):
    """
    Scrape a specific meal

    Args:
        request: Scrape request with dining hall, meal type, and optional date

    Returns:
        Scrape results for the specific meal
    """
    if not request.dining_hall or not request.meal_type:
        raise HTTPException(
            status_code=400,
            detail="dining_hall and meal_type are required"
        )

    if request.dining_hall not in DINING_HALLS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid dining hall. Must be one of: {', '.join(DINING_HALLS)}"
        )

    if request.meal_type not in MEAL_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid meal type. Must be one of: {', '.join(MEAL_TYPES)}"
        )

    # Parse date if provided
    date_obj = None
    if request.target_date:
        try:
            date_obj = datetime.strptime(request.target_date, "%Y-%m--%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    result = scraping_service.scrape_specific_meal(
        request.dining_hall,
        request.meal_type,
        date_obj,
        save_to_db=True
    )

    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])

    return result


@app.post("/scrape/refresh")
async def refresh_all_data():
    """
    Refresh all dining hall data
    Scrapes all dining halls and all meals

    Returns:
        Complete refresh results
    """
    result = scraping_service.refresh_all_data()

    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])

    return result


@app.get("/scrape/status")
async def get_scrape_status():
    """
    Get current scraping status

    Returns:
        Statistics about scraped data in the database
    """
    result = scraping_service.get_scrape_status()

    if result['status'] == 'error':
        raise HTTPException(status_code=500, detail=result['message'])

    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
