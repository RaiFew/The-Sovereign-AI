import json
import re
from agents.prompts import PROMPTS
from agents.knowledge_router import KnowledgeRouter
from agents.knowledge_chain import KnowledgeChain, IdeaCard


class Commander:
    def __init__(self, agent_manager):
        self.manager = agent_manager
        self.router = KnowledgeRouter()
        self.knowledge_chain = None

    def process_task(self, task_description, topic="general", subject="", status_callback=None):
        """
        Refactored Commander logic with Idea Card Protocol:
        1. Local Check (Python) first.
        2. Pass context to Agent K.
        3. Execute dynamic pipeline with Idea Card generation.
        """
        self.knowledge_chain = KnowledgeChain(topic, subject)

        self.state = {
            "results": {},
            "task": task_description,
            "topic": topic,
            "subject": subject,
        }

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
                # Save all data to Obsidian and System Logs
                if status_callback:
                    status_callback("💾 **Saving to Knowledge Base...**")
                self._save_all_results(status_callback)
                return self.state["results"]

            elif action == "SHORT_CIRCUIT":
                if status_callback:
                    status_callback(f"⚡ **Short-Circuit!** ใช้ข้อมูลเดิมจากคลัง...")
                # Create Idea Card for Agent A (Gatekeeper)
                card = IdeaCard(
                    agent_id="A",
                    process=f"Local knowledge check found existing data. Route: {route_info['route']}",
                    data_findings=route_info.get("content", "No content found.")[:500],
                    next_step_guidance="Data retrieved from vault. Use for summary."
                )
                self.knowledge_chain.add_card(card)
                self.state["results"]["G"] = route_info.get("content", "No content found.")
                current_input = f"Data retrieved from vault. Ready for summary."
                continue

            elif action == "CALL_AGENT":
                if status_callback:
                    status_callback(f"🤖 **Calling Agent {target}...**")

                # Check if this should be local
                is_local = target in ["J", "F", "A", "I"]
                result = self.manager.execute_agent(target, instruction, is_local, PROMPTS.get(target, ""))

                # Extract and save Idea Card from result
                card = self._extract_idea_card(target, result, instruction)
                if card:
                    self.knowledge_chain.add_card(card)
                    if status_callback:
                        status_callback(f"📝 **Idea Card created by Agent {target}**")

                self.state["results"][target] = result
                current_input = f"Agent {target} Output: {result[:1000]}"

            elif action == "LOOP":
                if status_callback:
                    status_callback(f"🔄 **Looping back to {target}...**")
                current_input = f"RE-RUN REQUESTED for {target}. Reason: {instruction}"

        # Save results even if loop exits early
        self._save_all_results(status_callback)
        return self.state["results"]

    def _extract_idea_card(self, agent_id: str, result: str, instruction: str) -> IdeaCard | None:
        """Extract Idea Card components from agent output."""
        try:
            # Try to extract structured sections
            process_match = re.search(r'\[Process\]:\s*(.+?)(?=\[Data/Findings\]:|$)', result, re.DOTALL)
            findings_match = re.search(r'\[Data/Findings\]:\s*(.+?)(?=\[Next Step Guidance\]:|$)', result, re.DOTALL)
            guidance_match = re.search(r'\[Next Step Guidance\]:\s*(.+?)$', result, re.DOTALL)

            process = process_match.group(1).strip() if process_match else f"Executed instruction: {instruction[:200]}"
            findings = findings_match.group(1).strip() if findings_match else result[:500]
            guidance = guidance_match.group(1).strip() if guidance_match else "Continue to next agent in pipeline."

            return IdeaCard(
                agent_id=agent_id,
                process=process,
                data_findings=findings,
                next_step_guidance=guidance
            )
        except Exception:
            # If extraction fails, create a basic card
            return IdeaCard(
                agent_id=agent_id,
                process=f"Executed task for {agent_id}",
                data_findings=result[:500],
                next_step_guidance="Proceed to next agent."
            )

    def _save_all_results(self, status_callback=None):
        """Save session log and research file to Obsidian."""
        try:
            # Save session log
            log_path = self.knowledge_chain.save_session_log()
            if status_callback:
                status_callback(f"📋 **Session Log saved:** {log_path}")

            # Save research file (if we have cards)
            if self.knowledge_chain.cards:
                research_path = self.knowledge_chain.save_research_file()
                if status_callback:
                    status_callback(f"📁 **Research File saved:** {research_path}")
        except Exception as e:
            if status_callback:
                status_callback(f"❌ **Error saving results:** {str(e)[:100]}")

    def _build_k_prompt(self, current_input, route_info):
        return (
            f"Task: {self.state['task']}\n"
            f"Topic: {self.state['topic']} | Subject: {self.state['subject']}\n"
            f"Knowledge Route: {route_info['route']}\n"
            f"Pipeline History: {list(self.state['results'].keys())}\n"
            f"Current Context/Input: {current_input}\n\n"
            "What is the next decision?"
        )
