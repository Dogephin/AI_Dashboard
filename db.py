from sqlalchemy import create_engine
from config import DB_URI

engine = create_engine(DB_URI)

def test_db_connection():
    try:
        print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
