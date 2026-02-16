import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Workspace
    WORKSPACE_ROOT = os.getenv('WORKSPACE_ROOT', os.path.join(os.path.dirname(__file__), 'workspace'))
    
    # Database
    database_url = os.getenv('DATABASE_URL', 'sqlite:///users.db')
    # Fix for SQLAlchemy 1.4+ (requires 'postgresql://' instead of 'postgres://')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Grok API
    GROK_API_KEY = os.getenv('GROK_API_KEY', '')
    GROK_API_URL = os.getenv('GROK_API_URL', 'https://api.x.ai/v1/chat/completions')
    GROK_MODEL = os.getenv('GROK_MODEL', 'grok-2-latest')
    
    # OpenAI for embeddings
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')
    
    # Index persistence
    INDEX_PERSIST_DIR = os.getenv('INDEX_PERSIST_DIR', os.path.join(WORKSPACE_ROOT, '.mcp_grok_index'))
    
    # Static analysis tool paths
    PYLINT_PATH = os.getenv('PYLINT_PATH', 'pylint')
    FLAKE8_PATH = os.getenv('FLAKE8_PATH', 'flake8')
    MYPY_PATH = os.getenv('MYPY_PATH', 'mypy')