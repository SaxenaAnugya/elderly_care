"""Sentiment analysis for emotion detection."""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    """Analyze sentiment of user input to adjust voice tone."""
    
    def __init__(self):
        """Initialize sentiment analyzer."""
        self.analyzer = SentimentIntensityAnalyzer()
        
    def analyze(self, text: str) -> Dict[str, any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            Dict with sentiment label and scores
        """
        scores = self.analyzer.polarity_scores(text)
        
        # Determine sentiment label
        compound = scores['compound']
        
        if compound >= 0.3:
            sentiment = "happy"
        elif compound <= -0.3:
            sentiment = "sad"
        else:
            sentiment = "neutral"
        
        result = {
            "sentiment": sentiment,
            "compound": compound,
            "positive": scores['pos'],
            "negative": scores['neg'],
            "neutral": scores['neu']
        }
        
        logger.info(f"Sentiment analysis: {sentiment} (compound: {compound:.2f})")
        
        return result
    
    def is_sad(self, text: str) -> bool:
        """
        Check if text indicates sadness.
        
        Args:
            text: Input text
            
        Returns:
            bool: True if sad sentiment detected
        """
        result = self.analyze(text)
        return result["sentiment"] == "sad"

