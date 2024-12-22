import os
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change'
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '').strip().strip('"')  # Remove quotes and whitespace
    if not GITHUB_TOKEN:
        logging.warning("No GitHub token found in environment variables")
    else:
        logging.info("GitHub token loaded from environment")
    
    LLM_API_URL = 'http://0.0.0.0:4000'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    LOG_LEVEL = 'INFO'
