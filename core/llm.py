"""Ollama LLM Bağlantısı."""
import os
from langchain_community.llms import Ollama

def get_llm():
    model = os.getenv("OLLAMA_MODEL", "llama3.2")
    llm = Ollama(
        model=model,
        base_url="http://localhost:11434",  # Agent host'ta çalıştığı için localhost
        temperature=0.1,
    )
    return llm
