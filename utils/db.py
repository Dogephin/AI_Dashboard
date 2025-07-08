from sqlalchemy import create_engine
from config import Config

engine = create_engine(Config.DB_URI)


def test_db_connection():
    try:
        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
