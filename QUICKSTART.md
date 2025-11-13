# Quick Start Guide

Get the Dining Macro Planner running in 5 minutes!

## Prerequisites

- Python 3.9+
- Google Gemini API key ([Get one here](https://ai.google.dev/))

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your API key
export GEMINI_API_KEY=your-api-key-here

# 3. Run automated setup
python setup.py
```

The setup script will:
- Initialize the SQLite database
- Load sample food data
- Generate embeddings for semantic search

## Start the Server

```bash
python run_server.py
```

The API will be available at `http://localhost:8000`

## Use the Frontend

Open `frontend/index.html` in your browser

Or serve it with:
```bash
cd frontend
python -m http.server 3000
```

Then visit `http://localhost:3000`

## Test the System

### 1. Set Preferences
- Enter your name (e.g., "john")
- Set macro targets (e.g., 40g protein, 150g carbs, 50g fat)
- Click "Save Preferences"

### 2. Get Recommendations
- Select dining hall: J2
- Select meal type: Lunch
- Click "Get AI Recommendations"
- Wait for Gemini to analyze foods and suggest combinations

### 3. Refine (Optional)
- Ask for adjustments: "Can you lower carbs to 120g?"
- The agent remembers context and refines suggestions

### 4. Browse Foods
- Click "View All Foods" to see what's available
- Note the food IDs and confidence scores

### 5. Submit Feedback
- If you measure actual macros, submit corrections
- This helps improve the system for everyone

## API Endpoints

Try these in your browser or with curl:

```bash
# Health check
curl http://localhost:8000/health

# Get foods for J2 Lunch
curl http://localhost:8000/foods/J2/Lunch

# API documentation
open http://localhost:8000/docs
```

## Common Issues

**"GEMINI_API_KEY not set"**
```bash
export GEMINI_API_KEY=your-key-here
```

**"No foods found"**
```bash
python scraper/load_data.py --sample
```

**"Database not found"**
```bash
python database/init_db.py
```

## Next Steps

1. **Scrape Real Data**: Update `scraper/selenium_scraper.py` with your dining hall URLs
2. **Deploy**: See README.md for production deployment guide
3. **Customize**: Modify config.py for your preferences

## Architecture

```
Frontend → API → RAG Retriever → Database
                     ↓
                Gemini Agent
```

The system uses RAG (Retrieval Augmented Generation) to ensure all recommendations are based on real, verified food data from the database, not hallucinated information.

## Learn More

- Full documentation: [README.md](README.md)
- API reference: `http://localhost:8000/docs`
- Architecture details: See README.md "System Architecture" section

---

**Ready to plan some meals!** 🍽️
