from typing import Optional
from langchain_openai import ChatOpenAI


def get_llm(api_key: str, provider: str = "openai", model: str = "", base_url: str = ""):
    if not api_key:
        return None

    if provider == "github":
        return ChatOpenAI(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            base_url=base_url or "https://models.inference.ai.azure.com",
            temperature=0,
        )
    elif provider == "openai":
        return ChatOpenAI(
            api_key=api_key,
            model=model or "gpt-4o-mini",
            temperature=0,
        )
    elif provider == "openrouter":
        return ChatOpenAI(
            api_key=api_key,
            model=model or "openai/gpt-4o-mini",
            base_url=base_url or "https://openrouter.ai/api/v1",
            temperature=0,
        )
    elif provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model or "models/gemini-2.0-flash",
            temperature=0,
        )
    return None
