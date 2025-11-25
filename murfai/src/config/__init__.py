# Configuration Module
# Export Config from parent config.py to maintain backward compatibility
import importlib.util
from pathlib import Path

# Load config.py from parent directory
config_path = Path(__file__).parent.parent / "config.py"
spec = importlib.util.spec_from_file_location("config", config_path)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)

# Export Config class
Config = config_module.Config

__all__ = ['Config']

