import json
from agents.prompts import PROMPTS
from agents.knowledge_router import KnowledgeRouter

class Commander:
    def __init__(self, agent_manager):
        self.manager = agent_manager
        self.router = KnowledgeRouter()
        self.state = {
            "results": {},
            "task": "",
            "topic": "general",
            "subject": ""
        }

    def process_task(self, task_description, topic="general", subject="", status_callback=None):
        """
        Refactored Commander logic:
        1. Local Check (Python) first.
        2. Pass context to Agent K.
        3. Execute dynamic pipeline.
        """
        self.state["task"] = task_description
        self.state["topic"] = topic
        self.state["subject"] = subject
        self.state["results"] = {}

        # ─── STEP 1: LOCAL KNOWLEDGE CHECK (0 Tokens used) ───
        if status_callback:
            status_callback("🔍 **Commander:** กำลังตรวจสอบคลังความรู้ (Local Check)...")
        
        route_info = self.router.search_existing_knowledge(topic, subject)
        lessons = self.router.read_lessons_learned()
        
        context = (
            f"Knowledge Check Result: {route_info['route']}\n"
            f"Found File: {route_info['file_path']}\n"
            f"Lessons Learned Context: {lessons[:1000]}...\n"
        )
        
        current_input = context
        
        # ─── STEP 2: DYNAMIC ORCHESTRATION ───
        for step_count in range(10):
            k_prompt = self._build_k_prompt(current_input, route_info)
            decision_json = self.manager.execute_agent("K", k_prompt, False, PROMPTS["K"])
            
            try:
                # Clean and parse JSON
                clean_json = decision_json.strip()
                if "```json" in clean_json:
                    clean_json = clean_json.split("```json")[1].split("```")[0].strip()
                decision = json.loads(clean_json)
            except Exception as e:
                if status_callback:
                    status_callback(f"⚠️ **Commander Error:** ไม่สามารถประมวลผลคำสั่งจาก Agent K ได้ (อาจติด Quota)")
                break

            action = decision.get("decision", "")
            target = decision.get("target", "")
            instruction = decision.get("input", "")

            if status_callback:
                status_callback(f"🧠 **Commander Thought:** {decision.get('thought', '')}")

            if action == "FINALIZE":
                return self.state["results"]

            elif action == "SHORT_CIRCUIT":
                if status_callback:
                    status_callback(f"⚡ **Short-Circuit!** ใช้ข้อมูลเดิมจากคลัง...")
                # Forward existing content to Secretary
                self.state["results"]["G"] = route_info.get("content", "No content found.")
                # We move to H next
                current_input = f"Data retrieved from vault. Ready for summary."
                continue

            elif action == "CALL_AGENT":
                if status_callback:
                    status_callback(f"🤖 **Calling Agent {target}...**")
                
                # Check if this should be local
                is_local = target in ["J", "F", "A", "I"]
                result = self.manager.execute_agent(target, instruction, is_local, PROMPTS.get(target, ""))
                
                self.state["results"][target] = result
                current_input = f"Agent {target} Output: {result[:1000]}"
                
            elif action == "LOOP":
                if status_callback:
                    status_callback(f"🔄 **Looping back to {target}...**")
                current_input = f"RE-RUN REQUESTED for {target}. Reason: {instruction}"

        return self.state["results"]

    def _build_k_prompt(self, current_input, route_info):
        return (
            f"Task: {self.state['task']}\n"
            f"Topic: {self.state['topic']} | Subject: {self.state['subject']}\n"
            f"Knowledge Route: {route_info['route']}\n"
            f"Pipeline History: {list(self.state['results'].keys())}\n"
            f"Current Context/Input: {current_input}\n\n"
            "What is the next decision?"
        )
