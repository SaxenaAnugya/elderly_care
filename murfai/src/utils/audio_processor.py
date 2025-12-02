"""Audio processing utilities for ASR and TTS."""
import aiohttp
import logging
import tempfile
import shutil
import subprocess
import os
from typing import Optional, List
from ..config import Config

logger = logging.getLogger(__name__)


def _ffmpeg_reencode_to_wav(input_bytes: bytes) -> Optional[bytes]:
    """Attempt to re-encode raw bytes to WAV using ffmpeg.

    Returns WAV bytes on success or None on failure.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        logger.debug("ffmpeg not found in PATH; skipping re-encode")
        return None

    try:
        with tempfile.TemporaryDirectory() as td:
            in_path = os.path.join(td, "input.webm")
            out_path = os.path.join(td, "out.wav")
            with open(in_path, "wb") as f:
                f.write(input_bytes)

            # Try a straightforward re-encode; don't fail loudly
            cmd = [ffmpeg_path, "-y", "-nostdin", "-i", in_path, "-ar", "16000", "-ac", "1", out_path]
            logger.debug(f"Running ffmpeg re-encode: {' '.join(cmd)}")
            proc = subprocess.run(cmd, capture_output=True)
            if proc.returncode != 0:
                logger.warning(f"ffmpeg re-encode failed: rc={proc.returncode} stderr={proc.stderr.decode(errors='ignore')}")
                return None

            # Read and return wav bytes
            with open(out_path, "rb") as outf:
                return outf.read()
    except Exception as e:
        logger.exception(f"Exception during ffmpeg re-encode: {e}")
        return None


async def transcribe_audio_with_deepgram(
    audio_data: bytes,
    api_key: str,
    content_type: str = "audio/webm",
    patience_mode_ms: Optional[int] = None,
    language: Optional[str] = None,
    fallback_languages: Optional[List[str]] = None,
) -> str:
    """
    Transcribe audio using Deepgram REST API.

    Tries a multipart/form-data upload first. If the service returns a non-200
    or an empty transcription, attempts a local ffmpeg re-encode to WAV and
    retries the request.

    Args:
        audio_data: Audio file bytes
        api_key: Deepgram API key
        content_type: Audio MIME type (webm, wav, mp3, etc.)

    Returns:
        Transcribed text or empty string on failure.
    """
    try:
        # Use provided patience_mode or fall back to Config
        patience = patience_mode_ms if patience_mode_ms is not None else Config.PATIENCE_MODE_SILENCE_MS

        # Log input size and a small snippet for debugging
        try:
            logger.info(f"transcribe_audio_with_deepgram input: {len(audio_data)} bytes (snippet: {audio_data[:64].hex()})")
        except Exception:
            logger.info(f"transcribe_audio_with_deepgram input: {len(audio_data)} bytes")

        def build_url(lang: Optional[str]) -> tuple[str, str]:
            language_param = (lang or Config.DEFAULT_VOICE_LOCALE or "en-US")
            endpointing_param = "&endpointing=100" if language_param == "multi" else ""
            return (
                "https://api.deepgram.com/v1/listen"
                f"?model={Config.ASR_MODEL}&language={language_param}&punctuate=true&interim_results=false{endpointing_param}"
            ), language_param

        primary_language = language or Config.DEFAULT_VOICE_LOCALE or "en-US"
        languages_to_try: List[str] = [primary_language]
        if fallback_languages:
            for fallback_lang in fallback_languages:
                if fallback_lang and fallback_lang not in languages_to_try:
                    languages_to_try.append(fallback_lang)
        if "en-US" not in languages_to_try:
            languages_to_try.append("en-US")

        # Some browsers send just 'audio/webm' — Deepgram prefers codec when available
        ct = content_type
        if ct == "audio/webm":
            ct = "audio/webm;codecs=opus"

        headers = {
            "Authorization": f"Token {api_key}"
        }

        async def request_transcript(payload_bytes: bytes, lang_code: str, mime_type: str) -> Optional[str]:
            url, normalized_lang = build_url(lang_code)
            async with aiohttp.ClientSession() as session:
                form = aiohttp.FormData()
                filename = "utterance.wav" if mime_type == "audio/wav" else "utterance.webm"
                form.add_field("file", payload_bytes, filename=filename, content_type=mime_type)

                async with session.post(url, data=form, headers=headers) as response:
                    status = response.status
                    text = await response.text()
                    try:
                        import json
                        result = json.loads(text)
                    except Exception:
                        result = text

                    if status == 200:
                        transcript = ""
                        try:
                            if isinstance(result, dict):
                                results = result.get("results") or result
                                if isinstance(results, dict) and "channels" in results:
                                    channels = results.get("channels", [])
                                    if channels and len(channels) > 0:
                                        alternatives = channels[0].get("alternatives", [])
                                        if alternatives and len(alternatives) > 0:
                                            transcript = alternatives[0].get("transcript", "")
                                else:
                                    if isinstance(results, dict) and "channels" not in results:
                                        for k in ("alternatives",):
                                            if k in results and isinstance(results[k], list) and results[k]:
                                                transcript = results[k][0].get("transcript", "")
                                                break
                        except Exception as e:
                            logger.warning(f"Error parsing Deepgram response: {e}", exc_info=True)

                        if transcript:
                            logger.info(f"Deepgram transcript (language={normalized_lang}): '{transcript}'")
                            return transcript
                        logger.info(f"Deepgram transcript blank for language={normalized_lang}")
                        return None

                    truncated_text = text[:500] + "..." if len(text) > 500 else text
                    logger.warning(
                        "Deepgram request failed (status=%s) language=%s body=%s",
                        status,
                        normalized_lang,
                        truncated_text,
                    )
                    return None

        async def try_languages(data_bytes: bytes, mime_type: str) -> Optional[str]:
            for lang_code in languages_to_try:
                transcript = await request_transcript(data_bytes, lang_code, mime_type)
                if transcript:
                    if lang_code != languages_to_try[0]:
                        logger.info("Deepgram succeeded after retry with fallback language=%s", lang_code)
                    return transcript
            return None

        transcript = await try_languages(audio_data, ct)
        if transcript:
            return transcript

        logger.info("Attempting ffmpeg re-encode and retrying Deepgram transcription")
        wav_bytes = _ffmpeg_reencode_to_wav(audio_data)
        if wav_bytes:
            transcript = await try_languages(wav_bytes, "audio/wav")
            if transcript:
                logger.info(f"Transcribed after re-encode: {transcript}")
                return transcript
            logger.info("Transcribed after re-encode: BLANK_OR_EMPTY")

        # All attempts failed
        return ""
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}", exc_info=True)
        return ""

async def synthesize_speech_with_murf(
    text: str,
    sentiment: str = "neutral",
    api_key: str = None,
    api_url: str = None,
    speech_rate: Optional[float] = None,
    sundowning_hour: Optional[int] = None,
    voice_gender: Optional[str] = None,
    voice_locale: Optional[str] = None
) -> bytes:
    """
    Synthesize speech using Murf TTS API.
    
    Args:
        text: Text to synthesize
        sentiment: Sentiment for voice style
        api_key: Murf API key (uses Config if not provided)
        api_url: Murf API URL (uses Config if not provided)
        
    Returns:
        Audio bytes (WAV format)
    """
    try:
        api_key = api_key or Config.MURF_API_KEY
        api_url = api_url or Config.MURF_API_URL
        
        if not api_key:
            raise ValueError("Murf API key not configured")
        
        # Import TTS client
        from ..tts.murf_client import MurfTTSClient
        
        tts_client = MurfTTSClient(api_key, api_url)
        # Pass settings to synthesize method
        audio_data = await tts_client.synthesize(
            text, 
            sentiment=sentiment,
            speech_rate=speech_rate,
            sundowning_hour=sundowning_hour,
            voice_gender=voice_gender,
            voice_locale=voice_locale or Config.DEFAULT_VOICE_LOCALE
        )
        await tts_client.close()
        
        return audio_data
    except Exception as e:
        logger.error(f"Error synthesizing speech: {e}")
        raise

