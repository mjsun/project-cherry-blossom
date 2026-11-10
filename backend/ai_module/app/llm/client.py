"""
Single switchboard for every LLM call in the app (chat + embeddings).

Which provider is used is controlled entirely by the LLM_PROVIDER env var
(see .env.example) -- "ollama" (local, default) or "openai". Call sites
never import ollama/openai directly; they call chat()/embed() here.
"""

import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

_DEFAULT_ANSWER_MODEL = {
    "openai": "gpt-4o-mini",
    "ollama": "qwen2.5:14b",
}
_DEFAULT_EMBED_MODEL = {
    "openai": "text-embedding-3-small",
    "ollama": "nomic-embed-text",
}

ANSWER_MODEL = os.getenv("ANSWER_MODEL", _DEFAULT_ANSWER_MODEL[PROVIDER])
EMBED_MODEL = os.getenv("EMBED_MODEL", _DEFAULT_EMBED_MODEL[PROVIDER])

_openai_client = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set (check your .env)"
            )
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def chat(prompt: str, *, temperature: float = 0.7, json_mode: bool = False) -> str:
    """Send a single user-turn prompt, return the model's text reply.

    json_mode constrains the model to emit valid JSON, using each
    provider's own mechanism for it (OpenAI's response_format, Ollama's
    format="json") instead of relying on prompt wording alone.
    """
    if PROVIDER == "openai":
        extra = {"response_format": {"type": "json_object"}} if json_mode else {}
        response = _get_openai_client().chat.completions.create(
            model=ANSWER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            **extra,
        )
        return response.choices[0].message.content

    if PROVIDER == "ollama":
        import ollama

        extra = {"format": "json"} if json_mode else {}
        response = ollama.chat(
            model=ANSWER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": temperature},
            **extra,
        )
        return response["message"]["content"]

    raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER!r} (expected 'ollama' or 'openai')")


def embed(text: str) -> list[float]:
    """Embed a piece of text, return its vector."""
    if PROVIDER == "openai":
        response = _get_openai_client().embeddings.create(model=EMBED_MODEL, input=text)
        return response.data[0].embedding

    if PROVIDER == "ollama":
        import ollama

        return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]

    raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER!r} (expected 'ollama' or 'openai')")
