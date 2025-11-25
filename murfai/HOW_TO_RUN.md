# How to Run the Loneliness Companion

## Step-by-Step Guide

### Step 1: Install Python Dependencies

First, make sure you have Python 3.8 or higher installed.

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate

# On Linux/Mac:
source venv/bin/activate

# Install all required packages
pip install -r requirements.txt
```

**Note**: If you encounter issues installing `pyaudio`:
- **Windows**: Usually works, but if not, download wheel from: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
- **Linux**: `sudo apt-get install portaudio19-dev python3-pyaudio`
- **Mac**: `brew install portaudio`

### Step 2: Get API Keys

#### Get Murf Falcon TTS API Key
1. Go to [https://murf.ai/](https://murf.ai/)
2. Sign up for a free account
3. Navigate to your dashboard
4. Find the API section
5. Generate your API key
6. **Note**: You get 1,000,000 free TTS characters!

#### Get Deepgram ASR API Key
1. Go to [https://deepgram.com/](https://deepgram.com/)
2. Sign up for a free account
3. Create a new project
4. Generate an API key
5. **Note**: Free tier includes generous usage

### Step 3: Configure Environment Variables

You have two options:

#### Option A: Use the Helper Script (Easier)
```bash
python create_env.py
```
Follow the prompts to enter your API keys.

#### Option B: Create .env File Manually
Create a file named `.env` in the project root with this content:

```env
MURF_API_KEY=your_actual_murf_api_key_here
MURF_API_URL=https://api.murf.ai/v1
DEEPGRAM_API_KEY=your_actual_deepgram_api_key_here
PATIENCE_MODE_SILENCE_MS=2000
SUNDOWNING_HOUR=17
MEDICATION_REMINDER_INTERVAL_MINUTES=60
```

Replace `your_actual_murf_api_key_here` and `your_actual_deepgram_api_key_here` with your real API keys.

### Step 4: Verify Setup

Run the setup verification script:

```bash
python setup.py
```

This will check:
- ✅ All dependencies are installed
- ✅ `.env` file exists
- ✅ API keys are configured

### Step 5: Test Components (Optional but Recommended)

Test individual components before running the full application:

```bash
python test_setup.py
```

This tests:
- Sentiment analysis
- Memory system
- Medication reminders
- Word of the day
- TTS (if API key is configured)

### Step 6: Adjust Murf API Integration (If Needed)

**Important**: The Murf Falcon API structure may need adjustment based on their actual API documentation.

1. Check your Murf dashboard for API documentation
2. Review `API_INTEGRATION.md` for guidance
3. If needed, adjust `src/tts/murf_client.py`:
   - API endpoint URL
   - Request payload structure
   - Authentication header format

### Step 7: Run the Application

```bash
python main.py
```

The companion will:
1. Initialize all components
2. Connect to ASR and TTS services
3. Greet you: "Hello! I'm your companion. I'm here to listen and chat with you. How are you doing today?"
4. Start listening for your voice input

### Step 8: Interact with the Companion

- **Speak into your microphone** - The companion will transcribe your speech
- **Wait for response** - The AI will respond with appropriate voice tone
- **Try different emotions**:
  - Say "I'm feeling great!" → Happy, excited voice
  - Say "I miss my husband" → Soft, whisper voice
  - Say "The weather is nice" → Neutral, conversational voice

### Step 9: Stop the Application

Press `Ctrl+C` to stop the companion gracefully.

## Quick Start (TL;DR)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file with your API keys
python create_env.py
# OR manually create .env file

# 3. Verify setup
python setup.py

# 4. Run the application
python main.py
```

## Troubleshooting

### Issue: "MURF_API_KEY not found"
**Solution**: Make sure your `.env` file exists and contains your actual API key (not the placeholder text).

### Issue: "ModuleNotFoundError: No module named 'pyaudio'"
**Solution**: 
- Windows: `pip install pipwin && pipwin install pyaudio`
- Linux: `sudo apt-get install portaudio19-dev && pip install pyaudio`
- Mac: `brew install portaudio && pip install pyaudio`

### Issue: "Murf API error"
**Solution**: 
1. Verify your API key is correct
2. Check your API quota/credits in Murf dashboard
3. Review `API_INTEGRATION.md` and adjust API endpoint/payload if needed
4. Check `companion.log` for detailed error messages

### Issue: "Deepgram connection failed"
**Solution**:
1. Verify your API key is correct
2. Check your Deepgram project settings
3. Ensure internet connection is working
4. Check `companion.log` for detailed error messages

### Issue: "No audio input/output"
**Solution**:
1. Check microphone permissions (Windows Settings → Privacy → Microphone)
2. Verify microphone is connected and working
3. Check speakers/headphones are connected
4. Test microphone in another application first

### Issue: "Import errors"
**Solution**:
1. Make sure virtual environment is activated
2. Run `pip install -r requirements.txt` again
3. Check Python version: `python --version` (needs 3.8+)

## Checking Logs

If something goes wrong, check the log file:

```bash
# View the log file
# Windows:
type companion.log

# Linux/Mac:
cat companion.log
```

The log file contains detailed information about:
- API connections
- Audio processing
- Errors and warnings
- Conversation flow

## Testing Individual Components

### Test TTS Only
```python
from src.tts.murf_client import MurfTTSClient
import asyncio

async def test():
    client = MurfTTSClient("your_key", "https://api.murf.ai/v1")
    audio = await client.synthesize("Hello, this is a test", sentiment="happy")
    print(f"Received {len(audio)} bytes")
    await client.close()

asyncio.run(test())
```

### Test Sentiment Analysis
```python
from src.sentiment.analyzer import SentimentAnalyzer

analyzer = SentimentAnalyzer()
result = analyzer.analyze("I'm feeling sad today")
print(result)  # {'sentiment': 'sad', 'compound': -0.5, ...}
```

### Test Memory System
```python
from src.memory.conversation_db import ConversationMemory

memory = ConversationMemory("test.db")
memory.save_conversation("Hello", "Hi there!", sentiment="happy")
conversations = memory.get_recent_conversations()
print(conversations)
```

## Expected Behavior

When running successfully, you should see:

```
2024-XX-XX XX:XX:XX - __main__ - INFO - ============================================================
2024-XX-XX XX:XX:XX - __main__ - INFO - Loneliness Companion - Voice Agent for Elderly Care
2024-XX-XX XX:XX:XX - __main__ - INFO - ============================================================
2024-XX-XX XX:XX:XX - src.asr.deepgram_client - INFO - Connected to Deepgram ASR
2024-XX-XX XX:XX:XX - src.asr.audio_capture - INFO - Audio stream started
2024-XX-XX XX:XX:XX - src.core.companion - INFO - Starting Loneliness Companion...
```

Then the companion will speak: "Hello! I'm your companion..."

## Next Steps After Running

1. **Schedule Medications**: The system can track medication schedules
2. **Customize Responses**: Edit `src/core/companion.py` to customize AI responses
3. **Add More Words**: Extend `WORD_DATABASE` in `src/features/word_of_day.py`
4. **Adjust Voice Styles**: Modify `VOICE_STYLES` in `src/config.py`

## Need Help?

- Check `README.md` for full documentation
- Review `ARCHITECTURE.md` for system details
- See `API_INTEGRATION.md` for API-specific help
- Check `companion.log` for error details

---

**Ready to run!** Follow the steps above and you'll have your Loneliness Companion up and running. 🎤🤖

