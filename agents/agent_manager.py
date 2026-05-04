import requests
import json
import time
from config.settings import OLLAMA_BASE_URL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL

class AgentManager:
    def __init__(self):
        # OpenRouter Models
        self.commander_model = "tencent/hy3-preview:free"
        self.worker_model = "tencent/hy3-preview:free"

        self.ollama_model = "gemma4:26b"
        self.ollama_available = self._check_ollama()
        self.openrouter_available = bool(OPENROUTER_API_KEY)

        if self.openrouter_available:
            print("✅ OpenRouter API initialized")
        else:
            print("⚠️ OpenRouter API key not found")

    def _check_ollama(self) -> bool:
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def run_openrouter_agent(self, prompt: str, system_instruction: str = None, model_name: str = None) -> str:
        if not self.openrouter_available:
            return "Error: OpenRouter API key not configured"

        model = model_name or self.worker_model

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages
        }

        try:
            response = requests.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {e}"

    def run_cloud_agent(self, prompt: str, system_instruction: str = None, model_name: str = None) -> str:
        return self.run_openrouter_agent(prompt, system_instruction, model_name)

    def run_local_agent(self, prompt: str, system_instruction: str = None) -> str:
        try:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "system": system_instruction,
                "stream": False
            }
            response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            return f"Error: {e}"

    def execute_agent(self, agent_name: str, task: str, is_local: bool = False, system_prompt: str = "") -> str:
        model_to_use = self.commander_model if agent_name == "K" else self.worker_model

        if is_local and self.ollama_available:
            print(f"Executing Agent: {agent_name} | 🖥️ LOCAL ({self.ollama_model})")
            return self.run_local_agent(prompt=task, system_instruction=system_prompt)
        else:
            print(f"Executing Agent: {agent_name} | ☁️ CLOUD ({model_to_use})")
            return self.run_cloud_agent(prompt=task, system_instruction=system_prompt, model_name=model_to_use)
