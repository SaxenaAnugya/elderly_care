"""Setup script for Loneliness Companion."""
import os
import sys

def check_dependencies():
    """Check if required dependencies are installed."""
    # Map package names to their import names
    package_imports = {
        'deepgram-sdk': 'deepgram',
        'requests': 'requests',
        'python-dotenv': 'dotenv',
        'vaderSentiment': 'vaderSentiment',
        'pyaudio': 'pyaudio',
        'websockets': 'websockets',
        'aiohttp': 'aiohttp'
    }
    
    missing = []
    for package, import_name in package_imports.items():
        try:
            __import__(import_name)
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
    # Check in parent directory (project root)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    if not os.path.exists(env_path):
        print("Warning: .env file not found!")
        print("Please create .env file in the project root (murfai folder) and add your API keys:")
        print("  python backend/create_env.py")
        print("  OR manually create .env file in murfai/ folder")
        return False
    return True

def check_api_keys():
    """Check if API keys are configured."""
    from dotenv import load_dotenv
    # Load .env from parent directory (project root)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
    
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
        # Determine correct command based on where script is run from
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        if os.getcwd() == script_dir:
            print("\nRun: python main.py")
        else:
            print("\nRun: python backend/main.py")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main()


