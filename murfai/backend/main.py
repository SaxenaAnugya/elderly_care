"""Main entry point for Loneliness Companion."""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to Python path so we can import from src
backend_dir = Path(__file__).parent
project_root = backend_dir.parent
sys.path.insert(0, str(project_root))

from src.core.companion import LonelinessCompanion
from src.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('companion.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def validate_config():
    """Validate that required API keys are configured."""
    if not Config.MURF_API_KEY:
        logger.error("MURF_API_KEY not found in environment variables")
        return False
    
    if not Config.DEEPGRAM_API_KEY:
        logger.error("DEEPGRAM_API_KEY not found in environment variables")
        return False
    
    return True

async def main():
    """Main application entry point."""
    logger.info("=" * 60)
    logger.info("Loneliness Companion - Voice Agent for Elderly Care")
    logger.info("=" * 60)
    
    # Validate configuration
    if not validate_config():
        logger.error("Please configure your API keys in .env file")
        logger.error("See .env.example for reference")
        sys.exit(1)
    
    # Create and start companion
    companion = LonelinessCompanion()
    
    try:
        await companion.start()
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal, shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await companion.stop()

if __name__ == "__main__":
    asyncio.run(main())


