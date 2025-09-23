import requests
from .config import settings

class OllamaClient:
    def __init__(self, base_url: str = None, default_model: str = None):
        self.base_url = base_url or settings.ollama_base_url.rstrip("/")
        self.default_model = default_model or getattr(settings, "ollama_default_model", "llama3.2:1b")

    def chat(self, model: str, messages: list[dict], stream: bool = False):
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "assistant", "content": "Você é uma IA de suporte emocional. Responda sempre de forma empática e compreensiva. Sempre responda em português"}] + messages,
            "stream": stream
        }
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def generate(self, model: str, prompt: str, stream: bool = False):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    def ask(self, prompt: str, model: str = None) -> str:
        """
        Faz uma pergunta simples ao modelo e retorna apenas o texto da resposta.
        """
        model = model or self.default_model
        response = self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        # A resposta do Ollama geralmente vem como {"message": {"content": "..."}}
        try:
            return response["message"]["content"]
        except (KeyError, TypeError):
            return str(response)  # fallback para debug