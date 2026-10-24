import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_client = None

DEFAULT_MODELS = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash,gemini-3.1-flash-lite"


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing. Check your .env file.")
        # timeout is in milliseconds: give up on a model after 15 seconds
        _client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=15000))
    return _client


def generate(prompt: str) -> str:
    models = [m.strip() for m in os.getenv("GEMINI_MODELS", DEFAULT_MODELS).split(",")]
    last_error = None
    for model in models:
        try:
            response = _get_client().models.generate_content(model=model, contents=prompt)
            return response.text
        except Exception as exc:
            last_error = exc
            print(f"[llm] {model} failed: {str(exc)[:120]}")  # shows in your server terminal
    raise last_error