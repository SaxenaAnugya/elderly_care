# Voice API Setup Guide

## Complete Voice Flow

```
User Voice Input → Deepgram ASR → Groq LLM → Murf TTS → Voice Output
```

## Where to Put API Keys

### 1. Create/Edit `.env` file in project root:

```env
# Murf AI TTS API Key (for voice output)
MURF_API_KEY=your_murf_api_key_here
MURF_API_URL=https://api.murf.ai/v1

# Deepgram ASR API Key (for voice input - speech to text)
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Groq LLM API Key (for generating responses)
GROQ_API_KEY=your_groq_api_key_here
LLM_PROVIDER=groq

# Optional Settings
PATIENCE_MODE_SILENCE_MS=2000
SUNDOWNING_HOUR=17
```

**Location**: `.env` file in the root directory:
```
murfai/
├── .env          ← Add all API keys here
├── backend/
│   └── api_server.py
└── ...
```

## Getting API Keys

### Murf AI TTS (Voice Output)
1. Go to [https://murf.ai/](https://murf.ai/)
2. Sign up for free account
3. Get 1,000,000 free TTS characters
4. Copy API key from dashboard
5. Add to `.env` as `MURF_API_KEY`

### Deepgram ASR (Voice Input)
1. Go to [https://deepgram.com/](https://deepgram.com/)
2. Sign up for free account
3. Create project and get API key
4. Add to `.env` as `DEEPGRAM_API_KEY`

### Groq LLM (Response Generation)
1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up for free account
3. Get API key
4. Add to `.env` as `GROQ_API_KEY`

## Complete Voice Pipeline

The system processes voice in these steps:

1. **User speaks** → Frontend captures audio
2. **Audio sent to backend** → `/voice/message/{session_id}`
3. **Deepgram ASR** → Converts audio to text (transcript)
4. **Sentiment Analysis** → Detects emotion
5. **Groq LLM** → Generates response based on transcript + sentiment
6. **Murf TTS** → Converts response text to speech (audio)
7. **Audio returned** → Frontend plays response

## Verification

After adding keys, verify they're loaded:

```python
from src.config import Config

print(f"Murf Key: {'✓' if Config.MURF_API_KEY else '✗'}")
print(f"Deepgram Key: {'✓' if Config.DEEPGRAM_API_KEY else '✗'}")
print(f"Groq Key: {'✓' if os.getenv('GROQ_API_KEY') else '✗'}")
```

## Example .env File

```env
# Voice Input (Speech-to-Text)
DEEPGRAM_API_KEY=gsk_your_deepgram_key_here

# Voice Output (Text-to-Speech)
MURF_API_KEY=your_murf_api_key_here
MURF_API_URL=https://api.murf.ai/v1

# Response Generation
GROQ_API_KEY=gsk_your_groq_key_here
LLM_PROVIDER=groq

# Settings
PATIENCE_MODE_SILENCE_MS=2000
SUNDOWNING_HOUR=17
```

## Troubleshooting

### "Murf API key not found"
- Check `.env` file exists in project root
- Verify key is `MURF_API_KEY=your_key` (no quotes, no spaces)
- Restart the API server after adding key

### "Deepgram connection failed"
- Verify `DEEPGRAM_API_KEY` in `.env`
- Check internet connection
- Verify API key is valid in Deepgram dashboard

### "Groq API error"
- Check `GROQ_API_KEY` in `.env`
- Verify `LLM_PROVIDER=groq` is set
- Check Groq dashboard for quota/limits

### Voice not working
1. Check all three API keys are set
2. Verify API server is running
3. Check browser console for errors
4. Ensure microphone permissions are granted

## Security

⚠️ **Never commit `.env` file to git!**

- `.env` is already in `.gitignore`
- Use `.env.example` for documentation
- Keep API keys secret

