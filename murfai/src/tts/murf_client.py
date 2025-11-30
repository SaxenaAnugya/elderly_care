"""Murf Falcon TTS client using official Murf Python SDK."""
import asyncio
import logging
import time
from typing import Optional, List, Dict
from datetime import datetime

import aiohttp
import importlib
import sys
try:
    from murf import Murf
except Exception:
    Murf = None


from ..config import Config

logger = logging.getLogger(__name__)


class MurfTTSClient:
    """TTS client using Murf Falcon API via Murf SDK."""

    def __init__(self, api_key: str, api_url: str):
        # api_url kept for backwards compatibility, SDK handles endpoints
        self.api_key = api_key
        self.api_url = api_url
        self.client: Optional[Murf] = None
        # cache for voices to avoid repeated API calls
        self._voices_cache: Dict[str, object] = {"voices": [], "ts": 0}

    def _get_client(self) -> Murf:
        if self.client is None:
            # Attempt a dynamic import if the top-level import failed.
            # Avoid assigning to the module-level `Murf` name here (no shadowing).
            if Murf is None:
                try:
                    murf_mod = importlib.import_module('murf')
                    MurfClass = getattr(murf_mod, 'Murf', None) or getattr(murf_mod, 'Client', None) or murf_mod
                except Exception:
                    python_exec = sys.executable or 'python'
                    raise RuntimeError(
                        "Murf SDK is not installed in the current Python environment. "
                        f"Install it with: `{python_exec} -m pip install murf`"
                    )
            else:
                MurfClass = Murf

            if not self.api_key:
                raise ValueError("Murf API key not configured")

            # Instantiate the discovered Murf client class
            self.client = MurfClass(api_key=self.api_key)
        return self.client

    async def synthesize(
        self,
        text: str,
        sentiment: str = "neutral",
        voice_id: Optional[str] = None,
        speech_rate: Optional[float] = None,
        sundowning_hour: Optional[int] = None,
        voice_gender: Optional[str] = None,
    ) -> bytes:
        """Synthesize speech using Murf SDK and return audio bytes (wav)."""
        if not text or not text.strip():
            raise ValueError("Text is empty for TTS")

        # Determine or validate a supported voice id (may call Murf REST API)
        selected_voice_id = voice_id
        if not selected_voice_id:
            selected_voice_id = await self._choose_voice_id(voice_gender)

        # Use SDK in a thread (SDK is sync/blocking)
        def _generate():
            client = self._get_client()
            tts = getattr(client, 'text_to_speech', client)

            # Build a payload with conservative keys (avoid modelVersion which some SDKs don't accept)
            payload = {
                'text': text,
                'voice_id': selected_voice_id,
                'format': 'WAV',
                'sample_rate': 24000.0,
                'style': 'Conversation',
            }

            # Try the full payload first, but gracefully fall back if the SDK rejects unknown kwargs
            try:
                resp = tts.generate(**payload)
            except TypeError:
                # Retry with minimal args
                try:
                    resp = tts.generate(text=text, voice_id=selected_voice_id)
                except TypeError:
                    try:
                        resp = tts.generate(text=text, voice=selected_voice_id)
                    except Exception as e:
                        raise RuntimeError(f"Murf TTS generate failed: {e}") from e
            except Exception as e:
                raise RuntimeError(f"Murf TTS generate call failed: {e}") from e

            # The SDK may return either a dict with an audio URL, a string URL, or raw bytes
            if isinstance(resp, bytes):
                return resp

            if isinstance(resp, str):
                return resp

            # dict-like response: try common keys
            if isinstance(resp, dict):
                audio_url = resp.get('audioFile') or resp.get('audio_file') or resp.get('audio_url') or resp.get('url')
                if audio_url:
                    return audio_url

                # Some SDKs may embed raw base64 audio or bytes
                audio_bytes = resp.get('audio') or resp.get('data') or resp.get('audioData')
                if isinstance(audio_bytes, (bytes, bytearray)):
                    return bytes(audio_bytes)

            # If SDK returned a model/object (e.g., pydantic model), try to extract common attributes
            try:
                # pydantic models expose dict()
                if hasattr(resp, 'dict') and callable(getattr(resp, 'dict')):
                    resp_dict = resp.dict()
                    audio_url = resp_dict.get('audioFile') or resp_dict.get('audio_file') or resp_dict.get('audio_url') or resp_dict.get('url')
                    if audio_url:
                        return audio_url
                    audio_bytes = resp_dict.get('audio') or resp_dict.get('data') or resp_dict.get('audioData') or resp_dict.get('encoded_audio')
                    if isinstance(audio_bytes, (bytes, bytearray)):
                        return bytes(audio_bytes)
                    if isinstance(audio_bytes, str):
                        try:
                            import base64
                            return base64.b64decode(audio_bytes)
                        except Exception:
                            pass
            except Exception:
                pass

            # Try attribute access patterns (audio_file, audioFile, encoded_audio, etc.)
            audio_attr = None
            for attr in ('audio_file', 'audioFile', 'audio_file_url', 'audio_url', 'audioUrl', 'url'):
                try:
                    val = getattr(resp, attr, None)
                except Exception:
                    val = None
                if val:
                    audio_attr = val
                    break
            if audio_attr:
                return audio_attr

            # encoded audio as base64 string or bytes on the object
            enc = None
            for attr in ('encoded_audio', 'encodedAudio', 'audio', 'audio_bytes', 'data'):
                try:
                    enc = getattr(resp, attr, None)
                except Exception:
                    enc = None
                if enc:
                    break
            if isinstance(enc, (bytes, bytearray)):
                return bytes(enc)
            if isinstance(enc, str):
                try:
                    import base64
                    return base64.b64decode(enc)
                except Exception:
                    pass

            raise RuntimeError(f"Murf SDK did not return audio or URL. Response: {repr(resp)}")

        audio_result = await asyncio.to_thread(_generate)
        # If we received raw bytes directly from the SDK, return them
        if isinstance(audio_result, (bytes, bytearray)):
            data = bytes(audio_result)
            logger.info(f"Received {len(data)} bytes of Murf audio (direct from SDK)")
            return data

        # Otherwise treat audio_result as a URL and download
        audio_url = str(audio_result)
        logger.info(f"Murf generated audio at URL: {audio_url}")

        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url) as resp:
                if resp.status != 200:
                    text_err = await resp.text()
                    raise RuntimeError(f"Failed to download Murf audio: {resp.status} {text_err}")
                data = await resp.read()
                logger.info(f"Downloaded {len(data)} bytes of Murf audio")
                return data

    async def _fetch_voices(self) -> List[Dict]:
        """Fetch available voices from Murf REST API and cache the result."""
        now = time.time()
        # cache TTL 1 hour
        if self._voices_cache.get("voices") and (now - self._voices_cache.get("ts", 0) < 3600):
            return self._voices_cache.get("voices")

        base = self.api_url.rstrip('/')
        # Avoid duplicating '/v1' if api_url already contains it
        if base.endswith('/v1'):
            url = f"{base}/speech/voices"
        else:
            url = f"{base}/v1/speech/voices"
        # Murf API accepts either `api-key` or `token` header; include both to be safe
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "api-key": self.api_key,
            "token": self.api_key,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 404:
                    # Try alternate path (in case api_url already had /v1 or not)
                    alt_url = f"{base}/speech/voices" if not base.endswith('/v1') else f"{base}/v1/speech/voices"
                    async with session.get(alt_url, headers=headers) as resp2:
                        if resp2.status != 200:
                            text = await resp2.text()
                            raise RuntimeError(f"Failed to fetch Murf voices: {resp2.status} {text}")
                        data = await resp2.json()
                else:
                    if resp.status != 200:
                        text = await resp.text()
                        raise RuntimeError(f"Failed to fetch Murf voices: {resp.status} {text}")
                    data = await resp.json()

        # data may be a dict containing 'voices' or a list
        voices = []
        if isinstance(data, dict):
            voices = data.get("voices") or data.get("data") or []
        elif isinstance(data, list):
            voices = data

        # normalize voices: ensure each has an 'id'
        normalized = []
        for v in voices:
            if isinstance(v, dict) and (v.get("id") or v.get("voiceId") or v.get("name")):
                normalized.append(v)

        self._voices_cache = {"voices": normalized, "ts": now}
        return normalized

    async def _choose_voice_id(self, voice_gender: Optional[str] = None) -> str:
        """Choose a valid voice id from Murf voices, prefer gender when possible."""
        voices = await self._fetch_voices()
        if not voices:
            raise RuntimeError("No Murf voices available from API")

        # Helper to read an id from voice object
        def vid(v: Dict) -> Optional[str]:
            return v.get("id") or v.get("voiceId") or v.get("name")

        # Try exact gender match if voice metadata exposes 'gender'
        if voice_gender:
            matches = [v for v in voices if str(v.get("gender", "")).lower() == voice_gender.lower()]
            if matches:
                first = vid(matches[0])
                if first:
                    return first

        # Try to infer gender from name
        if voice_gender:
            keyword = "female" if voice_gender.lower() == "female" else "male"
            for v in voices:
                name = str(v.get("name", "") or "").lower()
                if keyword in name:
                    vidx = vid(v)
                    if vidx:
                        return vidx

        # Prefer voices that support Falcon model if present
        for v in voices:
            models = v.get("models") or v.get("model") or v.get("supportedModels") or []
            if isinstance(models, (list, tuple)) and any("falcon" in str(m).lower() for m in models):
                vidx = vid(v)
                if vidx:
                    return vidx

        # Last resort: return the first available voice id
        first = vid(voices[0])
        if not first:
            raise RuntimeError("Unable to determine a valid Murf voice id")
        return first

    async def close(self):
        """Close underlying resources if any."""
        # Murf SDK does not expose an async close; nothing to do here.
        return

