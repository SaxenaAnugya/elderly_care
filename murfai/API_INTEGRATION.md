# API Integration Guide

This document provides guidance for integrating with the required APIs.

## Murf Falcon TTS API

### Getting Started
1. Sign up at [murf.ai](https://murf.ai/)
2. Navigate to your dashboard
3. Generate an API key
4. Review the API documentation in your dashboard

### API Configuration
The Murf API integration is in `src/tts/murf_client.py`. You may need to adjust:

1. **Endpoint URL**: Update `MURF_API_URL` in `.env` based on actual API endpoint
2. **Request Payload**: Adjust the payload structure in `synthesize()` method based on Murf API documentation
3. **Authentication**: Verify the authentication header format (Bearer token, API key, etc.)
4. **Voice Parameters**: 
   - Verify available voice IDs
   - Check supported styles (Excited, Whisper, Soft, Conversational)
   - Confirm rate and pitch parameter formats

### Common Adjustments Needed
- API endpoint path (may be `/v1/tts`, `/api/tts`, etc.)
- Request payload structure
- Authentication header format
- Response format (may return JSON with audio URL vs direct audio bytes)

### Testing
Test the API integration separately before running the full application:
```python
from src.tts.murf_client import MurfTTSClient
import asyncio

async def test():
    client = MurfTTSClient("your_key", "https://api.murf.ai/v1")
    audio = await client.synthesize("Hello, this is a test", sentiment="neutral")
    print(f"Received {len(audio)} bytes of audio")

asyncio.run(test())
```

## Deepgram ASR API

### Getting Started
1. Sign up at [deepgram.com](https://deepgram.com/)
2. Create a new project
3. Generate an API key
4. Review the WebSocket API documentation

### API Configuration
The Deepgram integration is in `src/asr/deepgram_client.py`. The current implementation uses:

- **Model**: `nova-2` (optimized for conversational audio)
- **Language**: `en-US`
- **Endpointing**: Configurable via `PATIENCE_MODE_SILENCE_MS` (default: 2000ms)
- **Connection**: WebSocket for real-time streaming

### Adjustments
The Deepgram WebSocket API structure is well-documented. You may need to adjust:
- WebSocket URL format
- Authentication header format
- Response parsing based on actual response structure

### Testing
Test Deepgram connection:
```python
from src.asr.deepgram_client import DeepgramASRClient
import asyncio

async def on_transcript(text):
    print(f"Transcript: {text}")

async def test():
    client = DeepgramASRClient("your_key", on_transcript)
    await client.connect()
    # Test with audio stream...

asyncio.run(test())
```

## Environment Variables

Create a `.env` file with:
```
MURF_API_KEY=your_actual_murf_api_key
MURF_API_URL=https://api.murf.ai/v1  # Adjust based on actual endpoint
DEEPGRAM_API_KEY=your_actual_deepgram_api_key
```

## Troubleshooting

### Murf API Issues
- Verify API key is correct
- Check API quota/credits
- Review API response format
- Ensure endpoint URL is correct
- Check if API requires different authentication method

### Deepgram API Issues
- Verify API key and project settings
- Check WebSocket connection
- Review endpointing settings
- Ensure audio format matches requirements

## Free Tier Limits

### Murf
- 1,000,000 free TTS characters for new accounts
- Check dashboard for current usage

### Deepgram
- Free tier includes generous usage
- Check dashboard for limits and usage

