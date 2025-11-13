# Testing Guide

Complete guide to run and test the Dining Macro Planner locally.

---

## Quick Start (Easiest Way)

### Option 1: Auto Start Everything

```bash
python start_all.py
```

This single command will:
- Check all requirements
- Start the API server (port 8000)
- Start the frontend server (port 3000)
- Open both servers automatically

Then open your browser to: **http://localhost:3000**

---

## Manual Setup (Step by Step)

### Step 1: Initialize Database

```bash
# Create database and tables
python database/init_db.py

# Load sample data
python scraper/load_data.py --sample
```

You should see:
```
✓ Database initialized successfully
✓ Loaded 10 sample foods
```

### Step 2: Generate Embeddings (Optional)

```bash
python rag/generate_embeddings.py
```

### Step 3: Set API Key

```bash
# Windows (Command Prompt)
set GEMINI_API_KEY=your-api-key-here

# Windows (PowerShell)
$env:GEMINI_API_KEY="your-api-key-here"

# Linux/Mac
export GEMINI_API_KEY=your-api-key-here
```

Or create a `.env` file:
```
GEMINI_API_KEY=your-api-key-here
```

### Step 4: Start API Server

```bash
python run_server.py
```

You should see:
```
Starting Dining Macro Planner API server...
API will be available at: http://localhost:8000
```

**Keep this terminal open!**

### Step 5: Test API Connection

Open a **new terminal** and run:

```bash
python test_connection.py
```

You should see:
```
Testing: Health Check... ✓ PASSED
Testing: Root Endpoint... ✓ PASSED
Testing: Get Foods (J2 Lunch)... ✓ PASSED

Results: 3 passed, 0 failed
✓ All tests passed! API is ready.
```

### Step 6: Start Frontend Server

In the **same terminal** as test:

```bash
python start_frontend.py
```

You should see:
```
🌐 Frontend running at: http://localhost:3000
📝 Open your browser and go to: http://localhost:3000
```

### Step 7: Open Browser

Go to: **http://localhost:3000**

---

## Testing the Frontend

### Test 1: Load Foods

1. Enter your name in the header (e.g., "John")
2. Select dining hall: "J2"
3. Select meal type: "Lunch"
4. Click **"Load Available Foods"**

**Expected Result:**
- Table fills with 10 sample foods
- Foods show: Chicken, Rice, Beans, etc.
- Each food has macros and confidence score

### Test 2: Auto-Match Algorithm

1. Set macro targets:
   - Protein: 40g
   - Carbs: 150g
   - Fats: 50g
2. Click **"Auto-Match Foods"**

**Expected Result:**
- Foods automatically selected
- Progress bars update
- Selection summary shows foods
- Totals approximately match targets

### Test 3: Manual Selection

1. Click "Load Available Foods"
2. Click **"Add"** button on any food in the table
3. Watch the progress bars update in real-time

**Expected Result:**
- Food appears in "Your Selection" panel
- Progress bars animate
- Macros update
- "Add" button becomes disabled

### Test 4: AI Chat

1. Enter your name if not already entered
2. Click quick action button: **"Hit My Targets"**
3. Or type a custom message: "Suggest a high-protein lunch"
4. Click send (paper plane icon)

**Expected Result:**
- Your message appears in chat
- Typing indicator shows
- AI responds with meal suggestions
- Suggestions panel updates

### Test 5: Save Meal

1. Select some foods (manually or auto-match)
2. Click **"Save This Meal"**
3. Rate with stars (1-5)
4. Add optional notes
5. Click **"Save Meal"**

**Expected Result:**
- Modal appears
- Can rate and add notes
- "Meal saved successfully!" toast appears
- Modal closes

---

## Troubleshooting

### Problem: "Cannot connect to API"

**Solution:**
```bash
# Make sure API server is running
python run_server.py

# In another terminal, test connection
python test_connection.py
```

### Problem: "No foods found"

**Solution:**
```bash
# Load sample data
python scraper/load_data.py --sample

# Verify database
python -c "import sqlite3; print(sqlite3.connect('database/dining_planner.db').execute('SELECT COUNT(*) FROM foods').fetchone())"
```

### Problem: "GEMINI_API_KEY not set"

**Solution:**
```bash
# Set the environment variable
export GEMINI_API_KEY=your-key-here

# Or create .env file in project root
echo "GEMINI_API_KEY=your-key-here" > .env
```

### Problem: "Port already in use"

**Solution:**
```bash
# Find what's using port 8000 (API)
# Windows:
netstat -ano | findstr :8000

# Linux/Mac:
lsof -i :8000

# Kill the process or change port in run_server.py
```

### Problem: Frontend looks broken (no styles)

**Solution:**
- Make sure you're accessing: `http://localhost:3000` (not file://)
- Check browser console for errors (F12)
- Verify Font Awesome CDN is loading

---

## API Endpoints Reference

Test these in your browser or with curl:

### Health Check
```
GET http://localhost:8000/health
```

### Get Foods
```
GET http://localhost:8000/foods/J2/Lunch
GET http://localhost:8000/foods/JCL/Breakfast
GET http://localhost:8000/foods/Kins/Dinner
```

### API Documentation
```
http://localhost:8000/docs
```

Interactive Swagger UI with all endpoints

---

## Browser Console Testing

Open browser console (F12) and test JavaScript:

```javascript
// Test state
console.log(state);

// Test API call
apiRequest('/health').then(console.log);

// Test food loading
loadAvailableFoods();

// Test auto-match
autoMatchFoods();
```

---

## Performance Testing

### Load Test

```bash
# Install Apache Bench (if needed)
# Then test API
ab -n 100 -c 10 http://localhost:8000/health
```

### Database Query Test

```python
python -c "
from rag.rag_retriever import RAGRetriever
import time

retriever = RAGRetriever()
start = time.time()
foods = retriever.get_all_available_foods('J2', 'Lunch')
print(f'Query time: {time.time() - start:.3f}s')
print(f'Foods found: {len(foods)}')
"
```

---

## Expected Behavior

### Loading Foods
- Should take < 1 second
- Shows toast notification
- Table updates smoothly

### Auto-Match Algorithm
- Should complete < 0.5 seconds
- Finds 3-8 foods typically
- Matches within ±10g tolerance

### AI Chat
- Response time: 2-5 seconds (depends on Gemini API)
- Shows typing indicator
- Formats response nicely

### Progress Bars
- Update in real-time
- Smooth animations
- Color-coded (red/orange/blue)

---

## Success Criteria

✓ Database has 10+ foods
✓ API responds to all endpoints
✓ Frontend loads without errors
✓ Foods table displays correctly
✓ Auto-match finds combinations
✓ Progress bars update smoothly
✓ Chat sends/receives messages
✓ Can save meals to database

---

## Next Steps

Once everything works:

1. **Add Real Data**: Customize scraper for your dining hall
2. **Deploy**: See README.md for production deployment
3. **Customize**: Modify macro targets, tolerance, etc.

---

**Need Help?**
- Check browser console (F12) for errors
- Check terminal for API logs
- Run `python test_connection.py`
- Verify database: `python scraper/load_data.py --sample`
