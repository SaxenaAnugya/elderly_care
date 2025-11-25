# Quick Voice API Setup

## Where to Put API Keys

### Create/Edit `.env` file in project root:

```env
# Voice Input (Speech-to-Text) - Deepgram
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Voice Output (Text-to-Speech) - Murf AI
MURF_API_KEY=your_murf_api_key_here
MURF_API_URL=https://api.murf.ai/v1

# Response Generation - Groq
GROQ_API_KEY=your_groq_api_key_here
LLM_PROVIDER=groq
```

## Complete Voice Flow

```
1. User speaks → Frontend captures audio
2. Audio sent to backend → POST /voice/message/{session_id}
3. Deepgram ASR → Converts audio to text (transcript)
4. Sentiment Analysis → Detects emotion (happy/sad/neutral)
5. Groq LLM → Generates response based on transcript + sentiment
6. Murf TTS → Converts response text to speech (audio)
7. Audio returned → Frontend plays response voice
```

## Getting API Keys

### 1. Murf AI TTS (Voice Output)
- Go to: https://murf.ai/
- Sign up (free: 1M characters)
- Get API key from dashboard
- Add to `.env` as `MURF_API_KEY`

### 2. Deepgram ASR (Voice Input)
- Go to: https://deepgram.com/
- Sign up (free tier available)
- Create project, get API key
- Add to `.env` as `DEEPGRAM_API_KEY`

### 3. Groq LLM (Response Generation)
- Go to: https://console.groq.com/
- Sign up (free tier)
- Get API key
- Add to `.env` as `GROQ_API_KEY`
- Set `LLM_PROVIDER=groq`

## Verify Setup

After adding keys, test:

```bash
# Start API server
python api_server.py

# In another terminal, test health
curl http://localhost:8000/health
```

## Example Complete .env File

```env
# Voice Input (Speech-to-Text)
DEEPGRAM_API_KEY=gsk_abc123your_deepgram_key_here

# Voice Output (Text-to-Speech)  
MURF_API_KEY=your_murf_api_key_here
MURF_API_URL=https://api.murf.ai/v1

# Response Generation
GROQ_API_KEY=gsk_xyz789your_groq_key_here
LLM_PROVIDER=groq

# Optional Settings
PATIENCE_MODE_SILENCE_MS=2000
SUNDOWNING_HOUR=17
```

## Testing Voice Flow

1. **Start backend**: `python api_server.py`
2. **Start frontend**: `cd frontend && npm run dev`
3. **Open browser**: http://localhost:3000
4. **Click microphone** → Speak → Get voice response!

## Troubleshooting

### "Deepgram API key not configured"
- Check `.env` file has `DEEPGRAM_API_KEY=your_key`
- No quotes, no spaces around `=`
- Restart API server after adding

### "Murf API key not configured"
- Check `.env` file has `MURF_API_KEY=your_key`
- Verify key is valid in Murf dashboard
- Check API quota/credits

### "Groq API error"
- Verify `GROQ_API_KEY` in `.env`
- Check `LLM_PROVIDER=groq` is set
- Verify Groq account has credits

### No voice output
- Check all three API keys are set
- Check browser console for errors
- Verify microphone permissions
- Check API server logs for errors

## File Locations

```
murfai/
├── .env                    ← Add all API keys here
├── api_server.py          ← Backend server (uses keys)
├── src/
│   ├── config.py          ← Loads keys from .env
│   ├── utils/
│   │   └── audio_processor.py  ← ASR & TTS functions
│   └── ...
└── frontend/              ← Frontend (connects to backend)
```

## That's It!

Once you add all three API keys to `.env`, the complete voice flow will work:
- **Input**: Your voice → Deepgram → Text
- **Processing**: Text → Groq → Response
- **Output**: Response → Murf → Voice

🎤 → 📝 → 🤖 → 🔊

