import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def create_llm_client():
    try:
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )
        print("LLM client created.")
        return client
    except Exception as e:
        print("Failed to initialize LLM:", e)
        raise
