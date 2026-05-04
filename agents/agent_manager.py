import requests
import json
import google.generativeai as genai
from config.settings import GEMINI_API_KEY, OLLAMA_BASE_URL

# Initialize Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class AgentManager:
    def __init__(self):
        self.gemini_model = "gemini-1.5-flash"
        self.ollama_model = "phi3" # default local model, or llama3

    def run_cloud_agent(self, prompt: str, system_instruction: str = None) -> str:
        """Runs the task on Gemini 1.5 Flash (Cloud)"""
        try:
            # We can configure system instructions depending on the Gemini API version
            # Using standard generate_content
            model = genai.GenerativeModel(
                model_name=self.gemini_model,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
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
            response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except requests.exceptions.RequestException as e:
            print(f"Error running local agent: {e}")
            return f"Error: {e}"

    def execute_agent(self, agent_name: str, task: str, is_local: bool = False, system_prompt: str = "") -> str:
        """
        Executes a specific agent with its persona.
        """
        print(f"Executing Agent: {agent_name} | Local: {is_local}")
        if is_local:
            return self.run_local_agent(prompt=task, system_instruction=system_prompt)
        else:
            return self.run_cloud_agent(prompt=task, system_instruction=system_prompt)
