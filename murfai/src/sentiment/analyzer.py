"""Sentiment analysis for emotion detection.

This module prefers `vaderSentiment` if available, but falls back to a
lightweight rule-based analyzer when the package is not installed so the
application can run without additional dependencies.
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
except Exception:
    SentimentIntensityAnalyzer = None


class SentimentAnalyzer:
    """Analyze sentiment of user input to adjust voice tone.

    If `vaderSentiment` is installed the class delegates to it. Otherwise a
    simple heuristic analyzer is used as a fallback.
    """

    def __init__(self):
        """Initialize sentiment analyzer."""
        if SentimentIntensityAnalyzer is not None:
            self.analyzer = SentimentIntensityAnalyzer()
            self._use_vader = True
        else:
            self.analyzer = None
            self._use_vader = False

    def analyze(self, text: str) -> Dict[str, any]:
        """Analyze sentiment of text and return a result dict.

        Returns keys: sentiment (happy|neutral|sad), compound, positive, negative, neutral
        """
        if self._use_vader:
            scores = self.analyzer.polarity_scores(text)
            compound = scores.get("compound", 0.0)
            pos = scores.get("pos", 0.0)
            neg = scores.get("neg", 0.0)
            neu = scores.get("neu", 0.0)
        else:
            # Lightweight fallback: count positive/negative words
            positive_words = {"happy", "good", "great", "love", "excellent", "nice", "joy", "pleased"}
            negative_words = {"sad", "bad", "angry", "hate", "terrible", "upset", "lonely", "depressed"}
            words = [w.strip(".,!?;:") .lower() for w in text.split()]
            pos_count = sum(1 for w in words if w in positive_words)
            neg_count = sum(1 for w in words if w in negative_words)
            total = max(len(words), 1)
            pos = pos_count / total
            neg = neg_count / total
            neu = max(0.0, 1.0 - (pos + neg))
            # compound in [-1,1] approximate
            compound = pos - neg

        if compound >= 0.3:
            sentiment = "happy"
        elif compound <= -0.3:
            sentiment = "sad"
        else:
            sentiment = "neutral"

        result = {
            "sentiment": sentiment,
            "compound": compound,
            "positive": pos,
            "negative": neg,
            "neutral": neu,
        }

        logger.info(f"Sentiment analysis: {sentiment} (compound: {compound:.2f})")
        return result

    def is_sad(self, text: str) -> bool:
        """Return True if the analyzed sentiment is sad."""
        return self.analyze(text)["sentiment"] == "sad"

