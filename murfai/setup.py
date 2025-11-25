"""Setup script for Loneliness Companion."""
import os
import sys

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'deepgram-sdk',
        'requests',
        'python-dotenv',
        'vaderSentiment',
        'pyaudio',
        'websockets',
        'aiohttp'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print("Missing dependencies:")
        for pkg in missing:
            print(f"  - {pkg}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists."""
    if not os.path.exists('.env'):
        print("Warning: .env file not found!")
        print("Please copy .env.example to .env and add your API keys:")
        print("  cp .env.example .env")
        return False
    return True

def check_api_keys():
    """Check if API keys are configured."""
    from dotenv import load_dotenv
    load_dotenv()
    
    murf_key = os.getenv("MURF_API_KEY", "")
    deepgram_key = os.getenv("DEEPGRAM_API_KEY", "")
    
    issues = []
    if not murf_key or murf_key == "your_murf_api_key_here":
        issues.append("MURF_API_KEY not configured")
    
    if not deepgram_key or deepgram_key == "your_deepgram_api_key_here":
        issues.append("DEEPGRAM_API_KEY not configured")
    
    if issues:
        print("API Key Issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    return True

def main():
    """Run setup checks."""
    print("Loneliness Companion - Setup Check")
    print("=" * 40)
    
    all_ok = True
    
    print("\n1. Checking dependencies...")
    if not check_dependencies():
        all_ok = False
    
    print("\n2. Checking .env file...")
    if not check_env_file():
        all_ok = False
    
    print("\n3. Checking API keys...")
    if not check_api_keys():
        all_ok = False
    
    print("\n" + "=" * 40)
    if all_ok:
        print("✓ All checks passed! You're ready to run the companion.")
        print("\nRun: python main.py")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()

