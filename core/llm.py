"""Hybrid LLM Connection — Factory Pattern (Ollama / Gemini)."""
import os


def get_llm():
    """
    Factory function that returns the configured LLM instance.

    Reads LLM_PROVIDER from environment:
    - "gemini" → Google Gemini API (cloud, requires GEMINI_API_KEY)
    - "ollama" → Local Ollama server (default, no API key needed)

    core/agent.py calls this function without knowing which
    provider is active — the factory encapsulates the selection.
    """
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()

    if provider == "gemini":
        # Cloud mode: Google Gemini API
        # Import here to avoid ImportError when langchain-google-genai
        # is not installed (Ollama-only deployments)
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required when LLM_PROVIDER=gemini. "
                "Get your key from https://aistudio.google.com/apikey"
            )

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.1,
        )
        return llm

    else:
        # Local mode: Ollama (default)
        from langchain_ollama import OllamaLLM

        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        llm = OllamaLLM(
            model=model,
            base_url="http://localhost:11434",
            temperature=0.1,
        )
        return llm
