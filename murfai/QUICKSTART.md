# Quick Start Guide

## Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Get API Keys

### Murf Falcon TTS
1. Go to [murf.ai](https://murf.ai/)
2. Sign up for a free account
3. Navigate to API section in dashboard
4. Generate API key
5. Note: You get 1,000,000 free TTS characters

### Deepgram ASR
1. Go to [deepgram.com](https://deepgram.com/)
2. Sign up for a free account
3. Create a new project
4. Generate API key
5. Free tier includes generous usage

## Step 3: Configure Environment

Create a `.env` file in the project root:

```env
# Murf Falcon TTS API Key
MURF_API_KEY=your_murf_api_key_here
MURF_API_URL=https://api.murf.ai/v1

# Deepgram ASR API Key
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Application Settings (optional)
PATIENCE_MODE_SILENCE_MS=2000
SUNDOWNING_HOUR=17
MEDICATION_REMINDER_INTERVAL_MINUTES=60
```

Replace `your_murf_api_key_here` and `your_deepgram_api_key_here` with your actual API keys.

## Step 4: Verify Setup

Run the setup check:
```bash
python setup.py
```

This will verify:
- All dependencies are installed
- `.env` file exists
- API keys are configured

## Step 5: Adjust API Integration (If Needed)

**Important**: The Murf Falcon API structure may need adjustment based on actual API documentation.

1. Review `API_INTEGRATION.md` for details
2. Check Murf API docs in your dashboard
3. Adjust `src/tts/murf_client.py` if needed:
   - API endpoint URL
   - Request payload structure
   - Authentication method

## Step 6: Run the Companion

```bash
python main.py
```

The companion will:
1. Initialize all components
2. Connect to ASR and TTS services
3. Greet you with a warm welcome
4. Start listening for your voice

## Testing Individual Components

### Test TTS Only
```python
from src.tts.murf_client import MurfTTSClient
import asyncio

async def test_tts():
    client = MurfTTSClient("your_key", "https://api.murf.ai/v1")
    audio = await client.synthesize("Hello, this is a test", sentiment="happy")
    print(f"Received {len(audio)} bytes")
    await client.close()

asyncio.run(test_tts())
```

### Test Sentiment Analysis
```python
from src.sentiment.analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()
result = analyzer.analyze("I'm feeling sad today")
print(result)  # {'sentiment': 'sad', 'compound': -0.5, ...}
```

## Troubleshooting

### Audio Issues
- **No microphone input**: Check system microphone permissions
- **No audio output**: Verify speakers/headphones are connected
- **PyAudio errors**: May need to install system audio libraries
  - Windows: Usually works out of the box
  - Linux: `sudo apt-get install portaudio19-dev python3-pyaudio`
  - Mac: `brew install portaudio`

### API Connection Issues
- **Murf API errors**: 
  - Verify API key is correct
  - Check API endpoint URL
  - Review API documentation for correct payload structure
  - Check quota/credits in dashboard
  
- **Deepgram API errors**:
  - Verify API key and project settings
  - Check WebSocket connection
  - Review endpointing configuration

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt` again
- Check Python version (3.8+ required)

## Next Steps

1. **Customize Voice Styles**: Adjust voice styles in `src/config.py`
2. **Add Medications**: Use the memory system to schedule medications
3. **Customize Responses**: Modify `_generate_response()` in `src/core/companion.py`
4. **Add More Words**: Extend `WORD_DATABASE` in `src/features/word_of_day.py`

## Support

- Check logs in `companion.log` for detailed error messages
- Review `API_INTEGRATION.md` for API-specific guidance
- See `README.md` for full documentation

