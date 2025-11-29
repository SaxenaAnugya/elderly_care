# API Integration Troubleshooting Guide

## What I Fixed

### 1. **Better Error Handling**
- Added error interceptors in API client
- Console logging for all API calls
- Detailed error messages displayed to user
- Fallback responses when LLM fails

### 2. **Fixed Voice Interface Bug**
- Fixed `sessionId` timing issue (was using before set)
- Added proper error states
- Added loading indicators
- Better audio playback error handling

### 3. **Added LLM Test Endpoint**
- New `/test/llm` endpoint to verify Groq integration
- Test component in frontend ("Test LLM" tab)
- Shows detailed response/error information

### 4. **Improved Backend Logging**
- Detailed logs for each step of voice processing
- Error logging with stack traces
- Fallback responses when APIs fail

## How to Test

### Step 1: Test LLM Integration First

1. **Start backend**:
   ```bash
   python backend/api_server.py
   ```

2. **Start frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open browser**: http://localhost:3000

4. **Click "Test LLM" tab**

5. **Enter a test message** (e.g., "Hello, how are you?")

6. **Click "Test LLM" button**

7. **Check the response**:
   - ✅ **Success**: You'll see the LLM response
   - ❌ **Error**: Check the error message

### Step 2: Check Browser Console

Open browser DevTools (F12) and check Console tab:
- Look for `[API]` logs showing requests/responses
- Look for `[Voice]` logs showing voice processing
- Check for any red error messages

### Step 3: Check Backend Logs

In the terminal running `backend/api_server.py`, you should see:
```
INFO: Started voice session: <session_id>
INFO: Received audio: <size> bytes
INFO: Transcript: <text>
INFO: Generated response: <response>
```

## Common Issues & Fixes

### Issue: "No response from server"
**Fix**: 
- Check backend is running: `curl http://localhost:8000/health`
- Check `NEXT_PUBLIC_API_URL` in frontend `.env.local`
- Restart frontend after changing env vars

### Issue: "GROQ_API_KEY not found"
**Fix**:
- Add `GROQ_API_KEY=your_key` to `.env` file
- Add `LLM_PROVIDER=groq` to `.env` file
- Restart backend server

### Issue: "LLM returned empty response"
**Fix**:
- Check Groq API key is valid
- Check Groq account has credits
- Check internet connection
- Try the Test LLM tab to see detailed error

### Issue: "Deepgram API key not configured"
**Fix**:
- Add `DEEPGRAM_API_KEY=your_key` to `.env` file
- Restart backend server

### Issue: "Murf API key not configured"
**Fix**:
- Add `MURF_API_KEY=your_key` to `.env` file
- Voice will still work, just won't have TTS audio
- Browser TTS will be used as fallback

## Testing Checklist

- [ ] Backend starts without errors
- [ ] Frontend connects (no "Not connected" message)
- [ ] Test LLM tab works and shows response
- [ ] Voice interface can start session
- [ ] Voice interface shows transcript
- [ ] Voice interface shows AI response
- [ ] Browser console shows API logs
- [ ] Backend logs show processing steps

## Debug Mode

### Enable Detailed Logging

In `backend/api_server.py`, the logging is already set to INFO level. To see more:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Frontend Console Logs

All API calls are logged with `[API]` prefix:
- `[API] POST /voice/start` - Starting voice session
- `[API] POST /voice/message/...` - Sending audio
- `[API] Response: 200 {...}` - Successful response
- `[API] Response error: ...` - Error response

## Quick Test Commands

### Test Backend Health
```bash
curl http://localhost:8000/health
```

### Test LLM Endpoint
```bash
curl -X POST http://localhost:8000/test/llm \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, how are you?"}'
```

### Test Voice Session
```bash
# Start session
curl -X POST http://localhost:8000/voice/start

# Should return: {"session_id": "..."}
```

## Expected Flow

1. **User clicks microphone** → Frontend logs: `[Voice] Starting voice session...`
2. **Session created** → Backend logs: `Started voice session: <id>`
3. **User speaks and stops** → Frontend logs: `[Voice] Sending audio to backend...`
4. **Backend processes** → Backend logs show each step:
   - `Received audio: <size> bytes`
   - `Transcript: <text>`
   - `Generated response: <response>`
5. **Response received** → Frontend logs: `[Voice] Received response: {...}`
6. **Audio plays** → User hears response

## Still Not Working?

1. **Check all API keys in `.env`**:
   ```env
   GROQ_API_KEY=your_key
   DEEPGRAM_API_KEY=your_key
   MURF_API_KEY=your_key
   LLM_PROVIDER=groq
   ```

2. **Check backend logs** for specific errors

3. **Check browser console** for frontend errors

4. **Use Test LLM tab** to isolate LLM issues

5. **Verify API keys are valid** in respective dashboards

