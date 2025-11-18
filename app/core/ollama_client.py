import httpx
from .config import settings

class OllamaClient:
    def __init__(self, base_url: str = None, default_model: str = None):
        self.base_url = base_url or settings.ollama_base_url.rstrip("/")
        self.default_model = default_model or getattr(settings, "ollama_default_model", "llama3.2:3b")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            # Increase timeout to 120 seconds for slower models
            # This prevents context cancellation for longer generation times
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def generate(self, model: str, prompt: str, stream: bool = False):
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream
        }
        client = await self._get_client()
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()

    async def ask(self, prompt: str, model: str = None) -> str:
        """
        Faz uma pergunta simples ao modelo e retorna apenas o texto da resposta.
        """
        model = model or self.default_model

        # Usar generate ao invés de chat
        response = await self.generate(
            model=model,
            prompt=prompt
        )

        # A resposta do Ollama generate vem como {"response": "..."}
        try:
            return response["response"]
        except (KeyError, TypeError):
            return str(response)  # fallback para debug

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()