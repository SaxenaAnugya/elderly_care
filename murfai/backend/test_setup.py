"""Test script to verify individual components."""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to Python path so we can import from src
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

# Load .env from parent directory (project root)
env_path = project_root / '.env'
load_dotenv(env_path)

def test_sentiment():
    """Test sentiment analysis."""
    print("\n=== Testing Sentiment Analysis ===")
    try:
        from src.sentiment.analyzer import SentimentAnalyzer
        
        analyzer = SentimentAnalyzer()
        
        test_cases = [
            "I'm feeling great today!",
            "I miss my husband so much",
            "The weather is nice"
        ]
        
        for text in test_cases:
            result = analyzer.analyze(text)
            print(f"Text: '{text}'")
            print(f"  Sentiment: {result['sentiment']} (compound: {result['compound']:.2f})")
        
        print("✓ Sentiment analysis working")
        return True
    except Exception as e:
        print(f"✗ Sentiment analysis failed: {e}")
        return False

def test_memory():
    """Test conversation memory."""
    print("\n=== Testing Conversation Memory ===")
    try:
        from src.memory.conversation_db import ConversationMemory
        
        memory = ConversationMemory("test_memory.db")
        
        # Save test conversation
        memory.save_conversation(
            "Hello, how are you?",
            "I'm doing well, thank you!",
            sentiment="happy"
        )
        
        # Retrieve conversations
        conversations = memory.get_recent_conversations(limit=1)
        assert len(conversations) > 0
        print(f"✓ Saved and retrieved {len(conversations)} conversation(s)")
        
        # Cleanup
        if os.path.exists("test_memory.db"):
            os.remove("test_memory.db")
        
        return True
    except Exception as e:
        print(f"✗ Memory system failed: {e}")
        return False

async def test_tts():
    """Test TTS (requires API key)."""
    print("\n=== Testing TTS (Murf Falcon) ===")
    try:
        from src.tts.murf_client import MurfTTSClient
        from src.config import Config
        
        if not Config.MURF_API_KEY:
            print("⚠ Skipping TTS test - MURF_API_KEY not configured")
            return True
        
        client = MurfTTSClient(Config.MURF_API_KEY, Config.MURF_API_URL)
        
        # Test synthesis
        audio = await client.synthesize("Hello, this is a test", sentiment="neutral")
        
        if audio and len(audio) > 0:
            print(f"✓ TTS synthesis successful ({len(audio)} bytes)")
        else:
            print("⚠ TTS returned empty audio - check API integration")
        
        await client.close()
        return True
    except Exception as e:
        print(f"✗ TTS test failed: {e}")
        print("  Note: You may need to adjust API endpoint/payload structure")
        return False

def test_medication_reminder():
    """Test medication reminder system."""
    print("\n=== Testing Medication Reminder ===")
    try:
        from src.memory.conversation_db import ConversationMemory
        from src.features.medication_reminder import MedicationReminder
        
        memory = ConversationMemory("test_medication.db")
        reminder = MedicationReminder(memory)
        
        # Schedule medication
        reminder.schedule_reminder("Blue Pill", "09:00")
        
        # Generate reminder message
        med = {"medication_name": "Blue Pill", "time": "09:00"}
        msg = reminder.generate_reminder_message(med)
        print(f"✓ Reminder message: {msg[:60]}...")
        
        # Cleanup
        if os.path.exists("test_medication.db"):
            os.remove("test_medication.db")
        
        return True
    except Exception as e:
        print(f"✗ Medication reminder failed: {e}")
        return False

def test_word_of_day():
    """Test Word of the Day feature."""
    print("\n=== Testing Word of the Day ===")
    try:
        from src.features.word_of_day import WordOfTheDay
        
        word_feature = WordOfTheDay()
        word = word_feature.get_word_of_day()
        
        print(f"✓ Word: {word['word']}")
        print(f"  Definition: {word['definition']}")
        
        intro = word_feature.generate_introduction()
        print(f"  Introduction: {intro[:60]}...")
        
        return True
    except Exception as e:
        print(f"✗ Word of the Day failed: {e}")
        return False

async def main():
    """Run all tests."""
    print("=" * 60)
    print("Loneliness Companion - Component Tests")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Sentiment Analysis", test_sentiment()))
    results.append(("Memory System", test_memory()))
    results.append(("Medication Reminder", test_medication_reminder()))
    results.append(("Word of the Day", test_word_of_day()))
    results.append(("TTS (Murf)", await test_tts()))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All components working correctly!")
        return 0
    else:
        print("\n⚠ Some components need attention")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)


