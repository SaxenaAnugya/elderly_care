# Groq API Setup Guide

## Where to Place Your Groq API Key

You have **two options** to configure your Groq API key:

### Option 1: Environment Variable (Recommended)

Add your Groq API key to the `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
LLM_PROVIDER=groq
```

**Location**: Create or edit `.env` file in the root directory:
```
murfai/
├── .env          ← Add your key here
├── backend/
│   └── main.py
└── ...
```

### Option 2: Configuration File

Add your Groq API key to `config.json`:

```json
{
  "llm": {
    "provider": "groq",
    "api_key": "your_groq_api_key_here",
    "model": "llama-3.1-8b-instant",
    "temperature": 0.7,
    "max_tokens": 100
  }
}
```

**Location**: `config.json` in the project root (auto-created on first run)

## Priority Order

The system checks for API keys in this order:
1. Environment variable (`GROQ_API_KEY`)
2. Config file (`config.json` → `llm.api_key`)
3. Falls back to rule-based responses if not found

## Getting Your Groq API Key

1. Go to [https://console.groq.com/](https://console.groq.com/)
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key and add it to your `.env` or `config.json`

## Setting the Provider

To use Groq, you need to set the provider:

### Via Environment Variable:
```env
LLM_PROVIDER=groq
```

### Via Config File:
```json
{
  "llm": {
    "provider": "groq"
  }
}
```

## Complete Example

### `.env` file:
```env
# Groq API Configuration
GROQ_API_KEY=gsk_your_actual_api_key_here
LLM_PROVIDER=groq

# Other API keys
MURF_API_KEY=your_murf_key
DEEPGRAM_API_KEY=your_deepgram_key
```

### `config.json` file:
```json
{
  "llm": {
    "provider": "groq",
    "api_key": "gsk_your_actual_api_key_here",
    "model": "llama-3.1-8b-instant",
    "temperature": 0.7,
    "max_tokens": 100
  },
  "voice_styles": {
    "happy": "Excited",
    "sad": "Whisper",
    "neutral": "Conversational",
    "calm": "Soft"
  }
}
```

## Verification

After adding your API key, you can verify it's working:

1. Run the application: `python backend/main.py`
2. Check the logs - you should see:
   - "Using Groq API for responses" (if provider is set to groq)
   - No "API key not found" warnings

## Troubleshooting

### "Groq API key not found"
- Check that `GROQ_API_KEY` is in `.env` file
- Or check that `llm.api_key` is in `config.json`
- Make sure there are no extra spaces or quotes around the key

### "Using rule-based fallback"
- Your API key might be invalid
- Check your Groq account for API quota/limits
- Verify the key is correct

### Provider not switching to Groq
- Set `LLM_PROVIDER=groq` in `.env`
- Or set `"provider": "groq"` in `config.json`
- Restart the application

## Security Note

⚠️ **Never commit your API keys to git!**

- `.env` is already in `.gitignore`
- `config.json` should also be in `.gitignore` if it contains keys
- Use `config.json.example` for version control

## Free Tier Limits

Groq offers a generous free tier:
- Fast response times
- High rate limits
- No credit card required (for most models)

Check [Groq's documentation](https://console.groq.com/docs) for current limits.

