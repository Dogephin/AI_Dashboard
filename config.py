import os
from dotenv import load_dotenv

load_dotenv()  # This will load variables from the .env file into environment


class Config:

    # List of required environment variables
    REQUIRED_VARS = [
        "DB_USER",
        "DB_PASSWORD",
        "DB_HOST",
        "DB_PORT",
        "DB_DATABASE",
        "DEEPSEEK_API_KEY",
        "OLLAMA_PATH",
    ]

    # Check if all required environment variables are set
    missing = [var for var in REQUIRED_VARS if os.getenv(var) is None]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    # Load environment variables
    SQL_USER = os.getenv("DB_USER")
    SQL_PASSWORD = os.getenv("DB_PASSWORD")
    SQL_HOST = os.getenv("DB_HOST")
    SQL_PORT = os.getenv("DB_PORT")
    SQL_DATABASE = os.getenv("DB_DATABASE")
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    OLLAMA_PATH = os.getenv("OLLAMA_PATH")

    DB_URI = f"mysql+mysqlconnector://{SQL_USER}:{SQL_PASSWORD}@{SQL_HOST}:{SQL_PORT}/{SQL_DATABASE}"


# ? Usage in app.py:
# app.config.from_object(Config)
