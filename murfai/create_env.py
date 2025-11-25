"""Helper script to create .env file."""
import os

def create_env_file():
    """Create .env file from template."""
    if os.path.exists('.env'):
        response = input(".env file already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return
    
    print("Creating .env file...")
    print("Please enter your API keys when prompted.")
    print("(Press Enter to leave as placeholder)")
    
    murf_key = input("\nMurf API Key: ").strip() or "your_murf_api_key_here"
    murf_url = input("Murf API URL [https://api.murf.ai/v1]: ").strip() or "https://api.murf.ai/v1"
    deepgram_key = input("Deepgram API Key: ").strip() or "your_deepgram_api_key_here"
    
    silence_ms = input("Patience Mode Silence (ms) [2000]: ").strip() or "2000"
    sundowning_hour = input("Sundowning Hour (24h format) [17]: ").strip() or "17"
    reminder_interval = input("Medication Reminder Interval (minutes) [60]: ").strip() or "60"
    
    env_content = f"""# Murf Falcon TTS API Key
MURF_API_KEY={murf_key}
MURF_API_URL={murf_url}

# Deepgram ASR API Key
DEEPGRAM_API_KEY={deepgram_key}

# Application Settings
PATIENCE_MODE_SILENCE_MS={silence_ms}
SUNDOWNING_HOUR={sundowning_hour}
MEDICATION_REMINDER_INTERVAL_MINUTES={reminder_interval}
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("\n✓ .env file created successfully!")
    print("\nNext steps:")
    print("1. Edit .env file and add your actual API keys")
    print("2. Run: python setup.py (to verify configuration)")
    print("3. Run: python main.py (to start the companion)")

if __name__ == "__main__":
    create_env_file()

