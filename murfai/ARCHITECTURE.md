# System Architecture

## Overview

The Loneliness Companion is a voice-first AI application built with a modular architecture. It integrates multiple APIs and services to provide a natural, empathetic conversation experience for elderly users.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│            Main Application (backend/main.py)               │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              LonelinessCompanion (core/companion.py)         │
│  - Orchestrates all components                              │
│  - Manages conversation flow                                │
│  - Handles state management                                 │
└─────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────┘
      │      │      │      │      │      │      │
      ▼      ▼      ▼      ▼      ▼      ▼      ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│  ASR   │ │  TTS   │ │Sentiment│ │ Memory │ │Features│ │ Utils  │
└────────┘ └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
```

## Component Details

### 1. ASR (Speech-to-Text) Module
**Location**: `src/asr/`

#### Components:
- **`deepgram_client.py`**: Deepgram WebSocket client
  - Real-time streaming transcription
  - Patience mode (2000ms endpointing)
  - Handles interim and final results
  
- **`audio_capture.py`**: Microphone input capture
  - PyAudio-based audio streaming
  - Configurable sample rate and chunk size
  - Async generator for audio chunks

#### Features:
- Extended silence detection (2000ms)
- Optimized for conversational audio (Nova-2 model)
- Real-time streaming via WebSocket

### 2. TTS (Text-to-Speech) Module
**Location**: `src/tts/`

#### Components:
- **`murf_client.py`**: Murf Falcon TTS client
  - Emotion-based voice style switching
  - Sundowning support (time-based adjustments)
  - Dynamic rate and pitch adjustment

#### Features:
- **Reminiscence Therapy**: 
  - Happy memories → Excited style
  - Sad memories → Whisper/Soft style
  - Neutral → Conversational style
  
- **Sundowning Support**:
  - After 5 PM: 10% slower rate, lower pitch
  - Automatic style switch to "Soft"

### 3. Sentiment Analysis Module
**Location**: `src/sentiment/`

#### Components:
- **`analyzer.py`**: VADER Sentiment Analyzer wrapper
  - Real-time sentiment detection
  - Returns: happy, sad, neutral
  - Provides compound scores

#### Integration:
- Analyzes every user message
- Results feed into TTS voice style selection
- Used for response generation

### 4. Memory Module
**Location**: `src/memory/`

#### Components:
- **`conversation_db.py`**: SQLite-based conversation storage
  - Stores all conversations with timestamps
  - Tracks sentiment per conversation
  - Medication schedule management
  - User preferences storage

#### Features:
- Conversation history retrieval
- Context building for responses
- Medication tracking
- Persistent storage

### 5. Features Module
**Location**: `src/features/`

#### Components:

##### **`medication_reminder.py`**
- Conversational medication reminders
- Time-based scheduling
- Follow-up conversation handling
- Meal context awareness

##### **`word_of_day.py`**
- Daily cognitive exercises
- Word database with definitions
- Conversation prompts
- Follow-up question generation

### 6. Core Orchestrator
**Location**: `src/core/`

#### Components:
- **`companion.py`**: Main companion agent
  - Initializes all components
  - Manages conversation flow
  - Coordinates ASR → Sentiment → Response → TTS pipeline
  - Background tasks (medications, word of day)

#### Conversation Flow:
```
User Speech → ASR → Transcript → Sentiment Analysis
                                           ↓
Response Generation ← Memory Context ← Sentiment
        ↓
    TTS Synthesis (with emotion-based styling)
        ↓
    Audio Playback
```

## Data Flow

### 1. User Input Flow
```
Microphone → AudioCapture → DeepgramASR → Transcript
                                              ↓
                                    SentimentAnalyzer
                                              ↓
                                    Companion._process_user_message()
```

### 2. Response Generation Flow
```
User Message + Sentiment + Context → _generate_response()
                                              ↓
                                    Response Text
                                              ↓
                                    Memory.save_conversation()
                                              ↓
                                    TTS.synthesize() (with sentiment)
                                              ↓
                                    AudioPlayer.play_bytes()
```

### 3. Background Tasks
- **Medication Checker**: Runs every 60 seconds
  - Checks current time against schedule
  - Generates conversational reminders
  - Handles user responses
  
- **Word of Day**: Introduces new word periodically
  - Triggers during idle conversation
  - Encourages cognitive engagement

## Configuration

### Environment Variables
- `MURF_API_KEY`: Murf Falcon TTS API key
- `MURF_API_URL`: Murf API endpoint
- `DEEPGRAM_API_KEY`: Deepgram ASR API key
- `PATIENCE_MODE_SILENCE_MS`: Silence threshold (default: 2000)
- `SUNDOWNING_HOUR`: Hour for calming mode (default: 17)

### Config File
**Location**: `src/config.py`

Contains:
- API configuration
- Voice style mappings
- Timing parameters
- Default values

## State Management

### Conversation States
- `idle`: Normal conversation
- `medication_reminder`: Handling medication reminder
- `word_of_day`: Discussing word of the day

### State Transitions
```
idle → medication_reminder (when medication due)
idle → word_of_day (when introducing word)
medication_reminder → idle (after response)
word_of_day → idle (after discussion)
```

## Error Handling

### API Failures
- ASR errors: Logged, connection retried
- TTS errors: Logged, text printed as fallback (no TTS fallback per requirements)
- Sentiment errors: Defaults to neutral

### Audio Issues
- Microphone errors: Logged, graceful degradation
- Playback errors: Logged, continues operation

## Extensibility Points

### Adding New Features
1. Create feature module in `src/features/`
2. Integrate into `LonelinessCompanion` class
3. Add state management if needed
4. Update configuration if required

### Customizing Responses
- Modify `_generate_response()` in `companion.py`
- Add new sentiment-based responses
- Extend conversation context usage

### Adding Voice Styles
- Update `VOICE_STYLES` in `config.py`
- Adjust `_get_voice_style()` in `murf_client.py`
- Verify style names with Murf API

## Performance Considerations

### Async Operations
- All I/O operations are async
- Non-blocking audio capture and playback
- Concurrent background tasks

### Memory Management
- SQLite for persistent storage
- Limited conversation context (last 3-5)
- Efficient audio streaming

## Security

### API Keys
- Stored in `.env` file (not committed)
- Loaded via `python-dotenv`
- Validated on startup

### Data Privacy
- Conversations stored locally (SQLite)
- No external data transmission (except APIs)
- User data remains on device

## Future Enhancements

### Potential Additions
1. **Listening Sounds**: Trigger gentle prompts during pauses
2. **Multi-language Support**: Extend to other languages
3. **Voice Cloning**: Personalized voice for user
4. **Health Monitoring**: Integration with health devices
5. **Family Notifications**: Alert family on concerning patterns

## API Integration Notes

### Murf Falcon TTS
- **Status**: Placeholder structure (needs API docs verification)
- **Adjustments Needed**:
  - Endpoint URL
  - Request payload structure
  - Authentication method
  - Response format

### Deepgram ASR
- **Status**: Standard WebSocket implementation
- **Configuration**: Well-documented API
- **Model**: Nova-2 (conversational optimized)

## Testing Strategy

### Unit Tests
- Individual component testing
- Mock API responses
- Database operations

### Integration Tests
- End-to-end conversation flow
- API integration verification
- Audio pipeline testing

### Test Script
- `test_setup.py`: Component verification
- Individual feature testing
- API connectivity checks

