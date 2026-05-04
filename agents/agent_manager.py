import requests
import json
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, OLLAMA_BASE_URL

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class AgentManager:
    def __init__(self):
        self.gemini_model = "gemini-2.5-flash"
        self.ollama_model = "phi3"  # default local model, or llama3
        self.ollama_available = self._check_ollama()

    def _check_ollama(self) -> bool:
        """Check if Ollama is running locally"""
        try:
            r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
            if r.status_code == 200:
                models = [m['name'] for m in r.json().get('models', [])]
                print(f"✅ Ollama connected — Available models: {models}")
                return True
        except Exception:
            pass
        print(f"⚠️ Ollama not available at {OLLAMA_BASE_URL} — Local agents will fallback to Cloud")
        return False

    def run_cloud_agent(self, prompt: str, system_instruction: str = None) -> str:
        """Runs the task on Gemini 2.5 Flash (Cloud)"""
        try:
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"[System Instructions]\n{system_instruction}\n\n[Task]\n{full_prompt}"

            model = genai.GenerativeModel(model_name=self.gemini_model)
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            print(f"Error running cloud agent: {e}")
            return f"Error: {e}"

    def run_local_agent(self, prompt: str, system_instruction: str = None, model: str = None) -> str:
        """Runs the task on Ollama (Local)"""
        model_to_use = model or self.ollama_model
        payload = {
            "model": model_to_use,
            "prompt": prompt,
            "system": system_instruction,
            "stream": False
        }

        try:
            response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except requests.exceptions.RequestException as e:
            print(f"Error running local agent: {e}")
            return f"Error: {e}"

    def execute_agent(self, agent_name: str, task: str, is_local: bool = False, system_prompt: str = "") -> str:
        """
        Executes a specific agent with its persona.
        If local is requested but Ollama is not available, fallback to cloud.
        """
        use_local = is_local and self.ollama_available

        if use_local:
            print(f"Executing Agent: {agent_name} | 🖥️ LOCAL (Ollama)")
            return self.run_local_agent(prompt=task, system_instruction=system_prompt)
        else:
            if is_local:
                print(f"Executing Agent: {agent_name} | ☁️ CLOUD (Fallback — Ollama unavailable)")
            else:
                print(f"Executing Agent: {agent_name} | ☁️ CLOUD")
            return self.run_cloud_agent(prompt=task, system_instruction=system_prompt)
