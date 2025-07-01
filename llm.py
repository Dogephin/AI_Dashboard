import os
from dotenv import load_dotenv
from openai import OpenAI
import subprocess
import requests

load_dotenv()


def create_llm_client(type="API", model=None):

    print(f"Creating LLM client of type: {type} with model: {model}")

    if type == "API":
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

    elif type == "LOCAL":
        if not is_ollama_running():
            raise RuntimeError("Ollama server is not running at http://localhost:11434")

        if not model:
            raise ValueError("No model name provided for LOCAL LLM")

        else:
            print(f"LLM client created. Using local model: {model}")

        def local_llm(prompt):
            messages = [
                {"role": "system", "content": "You are a gameplay data analyst."},
                {"role": "user", "content": prompt},
            ]
            payload = {"model": model, "messages": messages, "stream": False}
            try:
                response = requests.post(
                    "http://localhost:11434/api/chat", json=payload
                )
                response.raise_for_status()
                result = response.json()
                return result.get("message", {}).get("content", "").strip()
            except Exception as e:
                print("Local LLM error:", e)
                raise

        return local_llm


def get_models():
    ollama_path = os.getenv("OLLAMA_PATH")

    if not ollama_path:
        print("Error: OLLAMA_PATH not set in environment variables.")
        return []

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

        # Arrange models by size in ascending order
        if deepseek_models:
            deepseek_models = sorted(
                deepseek_models, key=lambda x: int(x.split(":")[1].replace("b", ""))
            )

        print(deepseek_models if deepseek_models else "No DeepSeek models found.")
        return deepseek_models

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        return []  # return an empty list on failure


def is_ollama_running():
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False
