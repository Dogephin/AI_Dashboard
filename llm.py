import os
from dotenv import load_dotenv
from openai import OpenAI
import subprocess

load_dotenv()


def create_llm_client():
    try:
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1",
        )
        print("LLM client created.")
        return client
    except Exception as e:
        print("Failed to initialize LLM:", e)
        raise


def get_models():
    ollama_path = os.getenv("OLLAMA_PATH")
    if not os.path.exists(ollama_path):
        print(f"Error: Ollama executable not found at {ollama_path}")
        return []  # return empty list

    try:
        result = subprocess.run(
            [ollama_path, "list"], capture_output=True, text=True, check=True
        )
        lines = result.stdout.strip().split("\n")

        deepseek_models = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                model_name = parts[0]
                if model_name.startswith("deepseek"):
                    deepseek_models.append(model_name)

        print(deepseek_models if deepseek_models else "No DeepSeek models found.")
        return deepseek_models

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return []  # return an empty list on failure
