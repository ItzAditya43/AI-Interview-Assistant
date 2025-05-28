import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Remove Cloudinary Configuration
# CLOUDINARY_CONFIG = {
#     'cloud_name': os.getenv('CLOUDINARY_CLOUD_NAME', 'your_cloud_name'),
#     'api_key': os.getenv('CLOUDINARY_API_KEY', 'your_api_key'),
#     'api_secret': os.getenv('CLOUDINARY_API_SECRET', 'your_api_secret')
# }

# Ollama Configuration
OLLAMA_CONFIG = {
    'base_url': 'http://localhost:11434',
    'model': 'llama3.2:3b'
}

# Application Configuration
APP_CONFIG = {
    'data_dir': 'data',
    'temp_video_dir': 'data/temp_videos',
    'candidates_file': 'data/candidates.json',
    'max_video_duration': 300,  # 5 minutes in seconds
    'allowed_video_formats': ['webm', 'mp4'],
    'max_video_size': 100 * 1024 * 1024  # 100MB in bytes
} 