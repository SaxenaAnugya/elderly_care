# Backend API Server Setup

## Overview

The backend API server (`backend/api_server.py`) provides REST endpoints for the Next.js frontend to interact with the Loneliness Companion.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the API Server

```bash
python backend/api_server.py
```

Or using uvicorn directly:

```bash
uvicorn backend.api_server:app --host 0.0.0.0 --port 8000 --reload
```

The server will start on `http://localhost:8000`

### 3. Verify It's Running

Visit `http://localhost:8000/health` in your browser or:

```bash
curl http://localhost:8000/health
```

You should see:
```json
{"status": "ok", "timestamp": "2024-..."}
```

## API Endpoints

### Health Check
- `GET /health` - Check if server is running

### Voice
- `POST /voice/start` - Start a voice session
- `POST /voice/stop/{session_id}` - Stop a voice session
- `POST /voice/message/{session_id}` - Send audio message
- `GET /voice/status/{session_id}` - Get voice status

### Conversations
- `GET /conversations?limit=10` - Get conversation history
- `POST /conversations` - Save a conversation

### Medications
- `GET /medications` - Get all medications
- `POST /medications` - Add medication
- `PATCH /medications/{id}` - Update medication
- `DELETE /medications/{id}` - Delete medication
- `GET /medications/due` - Get medications due now

### Word of Day
- `GET /word-of-day` - Get current word of the day

### Settings
- `GET /settings` - Get current settings
- `PATCH /settings` - Update settings

## CORS Configuration

The server is configured to allow requests from:
- `http://localhost:3000` (Next.js default)
- `http://127.0.0.1:3000`

To add more origins, edit `backend/api_server.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://your-frontend-url.com"
    ],
    ...
)
```

## Environment Variables

Make sure your `.env` file has:
```env
MURF_API_KEY=your_key
DEEPGRAM_API_KEY=your_key
GROQ_API_KEY=your_key  # Optional
LLM_PROVIDER=groq      # Optional
```

## Frontend Configuration

In your frontend `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running Both Frontend and Backend

### Terminal 1 - Backend
```bash
python backend/api_server.py
```

### Terminal 2 - Frontend
```bash
cd frontend
npm run dev
```

Then visit `http://localhost:3000` - the frontend should now connect to the backend!

## Troubleshooting

### "Not connected to server" in Frontend

1. **Check backend is running**:
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check API URL in frontend**:
   - Verify `.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8000`
   - Restart Next.js dev server after changing env vars

3. **Check CORS**:
   - Make sure frontend URL is in CORS allowed origins
   - Check browser console for CORS errors

4. **Check ports**:
   - Backend should be on port 8000
   - Frontend should be on port 3000
   - Make sure ports aren't blocked by firewall

### Backend Won't Start

1. **Check dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Check API keys**:
   - Make sure `.env` file exists with required keys
   - Check logs for missing key errors

3. **Check port availability**:
   - Make sure port 8000 is not in use
   - Change port in `backend/api_server.py` if needed

### API Errors

1. **Check logs**: The server logs errors to console
2. **Check database**: Make sure SQLite database can be created
3. **Check companion initialization**: Errors during startup are logged

## Production Deployment

For production:

1. **Use production ASGI server**:
   ```bash
   uvicorn backend.api_server:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Set up reverse proxy** (nginx, etc.)

3. **Configure CORS** for your production domain

4. **Use environment variables** for all secrets

5. **Set up SSL/HTTPS** for secure connections

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

These provide interactive API documentation.


