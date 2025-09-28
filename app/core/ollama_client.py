import requests
from .config import settings

class OllamaClient:
    def __init__(self, base_url: str = None, default_model: str = None):
        self.base_url = base_url or settings.ollama_base_url.rstrip("/")
        self.default_model = default_model or getattr(settings, "ollama_default_model", "llama3.2:1b")

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

        # Usar generate ao invés de chat
        response = self.generate(
            model=model,
            prompt=prompt
        )

        # A resposta do Ollama generate vem como {"response": "..."}
        try:
            return response["response"]
        except (KeyError, TypeError):
            return str(response)  # fallback para debug