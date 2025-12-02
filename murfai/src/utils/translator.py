"""Helpers for calling Murf translation API."""
import asyncio
import logging
from typing import List, Optional

from ..config import Config

logger = logging.getLogger(__name__)


async def translate_texts(texts: List[str], target_language: str) -> Optional[List[str]]:
    """
    Translate the given texts into the target language using Murf Translation API.

    Returns a list of translated strings (same order as inputs) or None on failure.
    """
    if not texts:
        return []
    if not target_language:
        logger.warning("translate_texts called without target_language")
        return None
    if not Config.MURF_API_KEY:
        logger.warning("Murf API key not configured; cannot translate")
        return None

    def _translate():
        try:
            from murf import Murf
        except Exception as exc:
            logger.error("Failed to import Murf SDK for translation: %s", exc)
            return None

        try:
            client = Murf(api_key=Config.MURF_API_KEY)
        except Exception as exc:
            logger.error("Failed to initialize Murf client for translation: %s", exc)
            return None

        # Murf SDK exposes translation via client.text.translate(...)
        translator = getattr(client, "text", None) or client
        translate_fn = getattr(translator, "translate", None)
        if not callable(translate_fn):
            logger.error("Murf translation function not available on client")
            return None

        try:
            response = translate_fn(target_language=target_language, texts=texts)
        except TypeError:
            # Some SDK releases require positional args (texts, target_language)
            try:
                response = translate_fn(texts=texts, target_language=target_language)
            except Exception as exc:
                logger.error("Murf translate call failed: %s", exc)
                return None
        except Exception as exc:
            logger.error("Murf translate call failed: %s", exc)
            return None

        return _normalize_translation_response(response, len(texts))

    return await asyncio.to_thread(_translate)


def _normalize_translation_response(response, expected_count: int) -> Optional[List[str]]:
    """Attempt to standardize Murf translation responses."""
    if response is None:
        return None

    # Direct list of strings
    if isinstance(response, list) and all(isinstance(item, str) for item in response):
        return response

    # Dict responses
    if isinstance(response, dict):
        translations = (
            response.get("translations")
            or response.get("data")
            or response.get("texts")
            or response.get("results")
        )
        if isinstance(translations, list):
            normalized: List[str] = []
            for entry in translations:
                if isinstance(entry, str):
                    normalized.append(entry)
                elif isinstance(entry, dict):
                    text = (
                        entry.get("text")
                        or entry.get("translatedText")
                        or entry.get("translated_text")
                        or entry.get("translation")
                    )
                    if text:
                        normalized.append(str(text))
            if normalized:
                return normalized

        # Some SDKs may wrap results under "response" -> {...}
        resp_obj = response.get("response")
        if isinstance(resp_obj, dict):
            return _normalize_translation_response(resp_obj, expected_count)

    # Object with attributes
    text_attr = getattr(response, "translations", None) or getattr(response, "data", None)
    if isinstance(text_attr, list):
        normalized_attr: List[str] = []
        for entry in text_attr:
            if isinstance(entry, str):
                normalized_attr.append(entry)
            elif isinstance(entry, dict):
                text = (
                    entry.get("text")
                    or entry.get("translatedText")
                    or entry.get("translated_text")
                    or entry.get("translation")
                )
                if text:
                    normalized_attr.append(str(text))
            else:
                # Handle Translation objects with attributes (e.g., Translation(translated_text='...'))
                text = (
                    getattr(entry, "translated_text", None)
                    or getattr(entry, "translatedText", None)
                    or getattr(entry, "text", None)
                )
                if text:
                    normalized_attr.append(str(text))
        if normalized_attr:
            return normalized_attr

    logger.warning("Unable to parse Murf translation response: %s", response)
    return None

