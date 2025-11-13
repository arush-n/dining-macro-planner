# Running Locally - Quick Guide

## 🚀 Fastest Way to Start

### Windows:
```cmd
start.bat
```

### Linux/Mac:
```bash
./start.sh
```

Then open: **http://localhost:3000**

---

## Alternative: Python Command

```bash
python start_all.py
```

This will:
1. Check your database is initialized
2. Start API server on port 8000
3. Start frontend server on port 3000
4. Show you the URLs to open

---

## First Time Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python database/init_db.py
python scraper/load_data.py --sample
```

### 3. Set API Key (for AI chat)
```bash
# Windows
set GEMINI_API_KEY=your-key-here

# Linux/Mac
export GEMINI_API_KEY=your-key-here
```

### 4. Start Servers
```bash
python start_all.py
```

---

## Manual Start (Advanced)

### Terminal 1: API Server
```bash
python run_server.py
```
Runs on: http://localhost:8000

### Terminal 2: Frontend Server
```bash
python start_frontend.py
```
Runs on: http://localhost:3000

---

## Verify Everything Works

```bash
python test_connection.py
```

Should show:
```
Testing: Health Check... ✓ PASSED
Testing: Root Endpoint... ✓ PASSED
Testing: Get Foods (J2 Lunch)... ✓ PASSED
```

---

## What You'll See

### API Server (Port 8000)
- FastAPI backend
- Handles all data requests
- API docs at: http://localhost:8000/docs

### Frontend Server (Port 3000)
- Serves HTML/CSS/JavaScript
- Modern split-panel interface
- Calculator + AI Chat

---

## Using the App

1. **Enter your name** in the top header
2. **Select dining hall** (J2, JCL, or Kins)
3. **Select meal type** (Breakfast, Lunch, Dinner)
4. **Set macro targets** (protein, carbs, fats)

Then choose:

### Option A: Auto-Match
- Click "Auto-Match Foods"
- Algorithm finds optimal combination
- Foods auto-selected

### Option B: Browse Table
- Click "Load Available Foods"
- Browse the table
- Click "Add" on foods you want

### Option C: AI Chat
- Ask the AI assistant
- Get personalized suggestions
- Use quick action buttons

---

## Troubleshooting

### "Cannot connect to API"
- Make sure `python run_server.py` is running
- Check http://localhost:8000/health works

### "No foods found"
- Run: `python scraper/load_data.py --sample`
- Verify database exists

### "GEMINI_API_KEY not set"
- AI chat won't work without it
- Calculator and manual selection still work
- Set the environment variable

---

## Ports

- **API**: 8000
- **Frontend**: 3000

Change these in:
- API: `run_server.py`
- Frontend: `start_frontend.py`

---

## Stopping Servers

Press **Ctrl+C** in the terminal

Or if using `start_all.py`, it will stop both servers together.

---

## Next Steps

See [TESTING.md](TESTING.md) for detailed testing guide.
