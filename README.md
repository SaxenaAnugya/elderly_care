# Loneliness Companion - Voice Agent for Elderly Care

A voice-first AI companion specifically designed for senior citizens. The companion uses advanced speech recognition (ASR) and text-to-speech (TTS) technologies to provide emotional warmth and connection through natural conversation.

## ✨ Dynamic System

**The system is now fully dynamic!** All responses, templates, and configurations are loaded from `config.json` - no code changes needed to customize behavior.

- **LLM-Based Responses**: Uses free LLM APIs (Hugging Face, Groq) for dynamic conversation
- **Configurable Templates**: Medication reminders, word database, voice styles all in JSON
- **Runtime Updates**: Change behavior without restarting
- **See [DYNAMIC_SYSTEM.md](DYNAMIC_SYSTEM.md) for details**

## Features

### 🎤 Active Listener (STT/ASR)
- **Patience Mode**: Extended silence detection (2000ms) to accommodate slower speech patterns
- **Whisper & Tremor Support**: Optimized for conversational audio, handling imperfect speech
- **Listening Sounds**: Gentle prompts during pauses to encourage continued conversation

### 🗣️ Empathic Speaker (Murf Falcon TTS)
- **Reminiscence Therapy**: Voice style adapts based on sentiment (Whisper for sad memories, Excited for happy ones)
- **Sundowning Support**: Automatically switches to calmer, slower voice after 5 PM
- **Emotion-Aware Responses**: Detects user's emotional state and adjusts tone accordingly

### 🛡️ Guardian Features
- **Medication Reminders**: Conversational reminders that feel like a caring companion, not an alarm
- **Word of the Day**: Cognitive exercise to keep the mind active
- **Conversation Memory**: Remembers past conversations for continuity

## Architecture

```
murfai/
├── src/
│   ├── asr/              # Speech-to-Text (Deepgram)
│   │   ├── deepgram_client.py
│   │   └── audio_capture.py
│   ├── tts/              # Text-to-Speech (Murf Falcon)
│   │   └── murf_client.py
│   ├── sentiment/        # Sentiment Analysis
│   │   └── analyzer.py
│   ├── memory/           # Conversation Memory
│   │   └── conversation_db.py
│   ├── features/         # Special Features
│   │   ├── medication_reminder.py
│   │   └── word_of_day.py
│   ├── utils/            # Utilities
│   │   └── audio_player.py
│   ├── core/             # Main Orchestrator
│   │   └── companion.py
│   └── config.py         # Configuration
├── backend/              # Backend scripts and services
│   ├── main.py           # Entry point
│   ├── api_server.py     # REST API for frontend
│   ├── create_env.py     # .env helper script
│   ├── setup.py          # Setup verification
│   └── test_setup.py     # Component testing
├── requirements.txt      # Dependencies
├── .env.example          # Environment Variables Template
└── README.md
```

## Quick Start - How to Run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file with your API keys
python backend/create_env.py
# OR manually create .env file with your keys

# 3. Verify setup
python backend/setup.py

# 4. Run the application
python backend/main.py
```

**📖 For detailed instructions, see [HOW_TO_RUN.md](HOW_TO_RUN.md)**

## Prerequisites

- Python 3.8 or higher
- Microphone for audio input
- Speakers/headphones for audio output
- API keys for:
  - [Murf Falcon TTS](https://murf.ai/) - 1,000,000 free characters for new accounts
  - [Deepgram ASR](https://deepgram.com/) - Free tier available

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd murfai
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root with the following content:
   ```env
   MURF_API_KEY=your_murf_api_key_here
   MURF_API_URL=https://api.murf.ai/v1
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   PATIENCE_MODE_SILENCE_MS=2000
   SUNDOWNING_HOUR=17
   MEDICATION_REMINDER_INTERVAL_MINUTES=60
   ```
   
   Replace `your_murf_api_key_here` and `your_deepgram_api_key_here` with your actual API keys.

## Getting API Keys

### Murf Falcon TTS
1. Sign up at [murf.ai](https://murf.ai/)
2. Navigate to API section
3. Generate your API key
4. You'll receive 1,000,000 free TTS characters

### Deepgram ASR
1. Sign up at [deepgram.com](https://deepgram.com/)
2. Create a new project
3. Generate an API key
4. Free tier includes generous usage limits

## Usage

Run the companion:
```bash
python backend/main.py
```

The companion will:
1. Initialize and connect to ASR/TTS services
2. Greet you with a warm welcome
3. Start listening for your voice input
4. Respond with natural, empathetic speech

### Example Conversation Flow

**User**: "Hello"
**AI**: "Hello! It's so good to hear from you. How are you feeling today?"

**User**: "I miss my husband"
**AI**: (Switches to Whisper/Soft tone) "I'm here with you. It's okay to feel this way. Would you like to talk about what's on your mind? I'm listening."

**User**: "He used to love this song"
**AI**: (Maintains soft tone) "He sounds like a wonderful man. Would you like to tell me more about him?"

## Configuration

Edit `src/config.py` or set environment variables to customize:

- `PATIENCE_MODE_SILENCE_MS`: Silence threshold for patience mode (default: 2000ms)
- `SUNDOWNING_HOUR`: Hour when calming mode activates (default: 17 = 5 PM)
- `MEDICATION_REMINDER_INTERVAL_MINUTES`: Check interval for medications (default: 60)

## Features in Detail

### Patience Mode
The ASR is configured with extended endpointing (2000ms) to wait longer for user responses, accommodating slower speech patterns common in elderly users.

### Emotion-Aware Voice
The TTS automatically adjusts:
- **Happy memories**: Excited, energetic tone
- **Sad memories**: Whisper, soft, compassionate tone
- **Sundowning (after 5 PM)**: Calmer, slower speech (10% slower, lower pitch)

### Medication Reminders
Instead of jarring alarms, the companion uses conversational reminders:
- "I noticed it's 9 AM. Usually, we take the blue pill now with some water. Have you had breakfast yet?"
- Follows up based on user response
- Remembers medication schedules

### Word of the Day
Daily cognitive exercises:
- Introduces interesting words with definitions
- Asks engaging questions
- Encourages conversation and memory recall

## Technical Details

### ASR Configuration
- Model: Deepgram Nova-2 (optimized for conversational audio)
- Endpointing: 2000ms (patience mode)
- Language: English (US)
- Format: Real-time streaming via WebSocket

### TTS Configuration
- Engine: Murf Falcon
- Voice Styles: Dynamic switching based on sentiment
- Rate Adjustment: ±10% for Sundowning mode
- Pitch Adjustment: Slight lowering for calming effect

### Sentiment Analysis
- Library: VADER Sentiment Analyzer
- Detection: Happy, Sad, Neutral
- Real-time: Analyzes each user message

### Memory System
- Storage: SQLite database
- Retention: All conversations stored
- Context: Last 3-5 conversations used for context

## Troubleshooting

### Audio Issues
- Ensure microphone permissions are granted
- Check audio device settings
- Verify PyAudio installation (may require system audio libraries)

### API Connection Issues
- Verify API keys in `.env` file
- Check internet connection
- Ensure API keys have sufficient credits/quota

### No Speech Output
- Check Murf API key and quota
- Verify audio output device
- Check logs in `companion.log`

## Development

### Project Structure
- `src/asr/`: Speech-to-text implementation
- `src/tts/`: Text-to-speech implementation
- `src/sentiment/`: Emotion detection
- `src/memory/`: Conversation persistence
- `src/features/`: Special features (medications, word of day)
- `src/core/`: Main orchestrator

### Adding New Features
1. Create feature module in `src/features/`
2. Integrate into `src/core/companion.py`
3. Update configuration if needed

## License

This project is created for the IITB Hackathon.

## Acknowledgments

- Murf AI for Falcon TTS API
- Deepgram for ASR API
- VADER Sentiment for emotion detection

## Support

For issues or questions, please check the logs in `companion.log` or review the configuration in `src/config.py`.
