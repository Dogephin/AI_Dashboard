import os
from dotenv import load_dotenv

load_dotenv()

SQL_USER = os.getenv("DB_USER")
SQL_PASSWORD = os.getenv("DB_PASSWORD")
SQL_HOST = os.getenv("DB_HOST")
SQL_PORT = os.getenv("DB_PORT")
SQL_DATABASE = os.getenv("DB_DATABASE")

DB_URI = (
    f"mysql+mysqlconnector://{SQL_USER}:{SQL_PASSWORD}@{SQL_HOST}:{SQL_PORT}/{SQL_DATABASE}"
)

if not all([SQL_USER, SQL_PASSWORD, SQL_HOST, SQL_PORT, SQL_DATABASE]):
    raise ValueError("Missing one or more SQL environment variables.")
