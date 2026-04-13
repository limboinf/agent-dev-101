"""LLM client initialization."""

from openai import OpenAI

from app.config import settings

client = OpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url,
)


def chat(prompt: str, model: str | None = None, **kwargs) -> str:
    """Send a simple chat request and return the response text."""
    response = client.responses.create(
        model=model or settings.openai_model,
        input=prompt,
        **kwargs,
    )
    return response.output_text
