
# config.py
import os
from dotenv import load_dotenv
from groq import Groq
import psycopg2

# Load environment variables
load_dotenv()

class Config:
    POSTGRES_DB = os.getenv("POSTGRES_DB")
    POSTGRES_USER = os.getenv("POSTGRES_USER")
    POSTGRES_PW = os.getenv("POSTGRES_PW")
    POSTGRES_HOST = os.getenv("POSTGRES_HOST")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    MODEL = os.getenv("MODEL")
    
def create_db_connection():
    """Create a database connection using the Config class."""
    
    try:
        return psycopg2.connect(
            dbname=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PW,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
        )
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def initialize_groq_client():
    """Initialize and return the Groq client."""
    return Groq(api_key=Config.GROQ_API_KEY)