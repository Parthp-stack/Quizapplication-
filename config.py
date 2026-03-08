import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'quiz_app_secret_key'
    
    # Use SQLite by default for easy hosting/local dev
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Quiz API / LLM Configuration
    QUIZ_API_KEY = os.environ.get('QUIZ_API_KEY') or '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'
    
    # Use free vision models on OpenRouter for both vision and chat tasks
    # NVIDIA Nemotron-Nano-12B-V2-VL is a free vision model
    BASE_MODEL = os.environ.get('QUIZ_MODEL_NAME') or 'nvidia/nemotron-nano-12b-v2-vl:free'
    
    QUIZ_VISION_MODEL = os.environ.get('QUIZ_VISION_MODEL') or BASE_MODEL
    QUIZ_CHAT_MODEL = os.environ.get('QUIZ_CHAT_MODEL') or BASE_MODEL
