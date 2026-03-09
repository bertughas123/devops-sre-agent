"""Ollama LLM Connection."""
import os
from langchain_ollama import OllamaLLM

def get_llm():
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    llm = OllamaLLM(
        model=model,
        base_url="http://localhost:11434",
        temperature=0.1,
    )
    return llm
