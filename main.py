import time
import os
from github import Github
from github.Issue import Issue
from dotenv import load_dotenv

from config.settings import GITHUB_TOKEN, GITHUB_REPO
from agents.agent_manager import AgentManager
from agents.prompts import PROMPTS

load_dotenv()

class SovereignOrchestrator:
    def __init__(self):
        if not GITHUB_TOKEN or not GITHUB_REPO:
            print("Warning: GITHUB_TOKEN or GITHUB_REPO not set. Polling won't work.")
            self.repo = None
        else:
            self.gh = Github(GITHUB_TOKEN)
            try:
                self.repo = self.gh.get_repo(GITHUB_REPO)
            except Exception as e:
                print(f"Warning: Failed to initialize GitHub repo: {e}")
                self.repo = None
        
        self.agent_manager = AgentManager()

    def fetch_new_tasks(self):
        """Polls GitHub issues for new tasks"""
        if not self.repo:
            return []
        
        # Look for open issues with a specific label, e.g., 'task'
        issues = self.repo.get_issues(state='open')
        tasks = []
        for issue in issues:
            if 'processed' not in [label.name for label in issue.labels]:
                tasks.append(issue)
        return tasks

    def mark_task_processed(self, issue: Issue):
        """Tags the issue as processed and closes it or leaves a comment"""
        issue.add_to_labels("processed")
        issue.edit(state="closed")

    def run_pipeline(self, task_description: str) -> dict:
        """Executes the full agent pipeline sequentially"""
        results = {}
        print(f"--- Starting Pipeline for Task: {task_description[:50]}... ---")

        # 1. Agent A (Gatekeeper)
        results['A'] = self.agent_manager.execute_agent(
            "Gatekeeper", task_description, is_local=False, system_prompt=PROMPTS['A']
        )

        # 2. Agent B (Strategist)
        prompt_b = f"Task: {task_description}\n\nConstraints from Gatekeeper:\n{results['A']}"
        results['B'] = self.agent_manager.execute_agent(
            "Strategist", prompt_b, is_local=False, system_prompt=PROMPTS['B']
        )

        # 3. Agent C (Hunter)
        prompt_c = f"Research Plan:\n{results['B']}"
        results['C'] = self.agent_manager.execute_agent(
            "Hunter", prompt_c, is_local=False, system_prompt=PROMPTS['C']
        )

        # 4. Agent J (Compressor - LOCAL)
        prompt_j = f"Raw Data:\n{results['C']}"
        results['J'] = self.agent_manager.execute_agent(
            "Compressor", prompt_j, is_local=True, system_prompt=PROMPTS['J']
        )

        # 5. Agent D (Weaver)
        prompt_d = f"Compressed Data:\n{results['J']}"
        results['D'] = self.agent_manager.execute_agent(
            "Weaver", prompt_d, is_local=False, system_prompt=PROMPTS['D']
        )

        # 6. Agent E (Opponent)
        prompt_e = f"Draft to review:\n{results['D']}"
        results['E'] = self.agent_manager.execute_agent(
            "Opponent", prompt_e, is_local=False, system_prompt=PROMPTS['E']
        )

        # 7. Agent F (Auditor - LOCAL)
        prompt_f = f"Draft:\n{results['D']}\n\nCritique:\n{results['E']}\n\nPlease finalize and ensure formatting."
        results['F'] = self.agent_manager.execute_agent(
            "Auditor", prompt_f, is_local=True, system_prompt=PROMPTS['F']
        )

        # 8. Agent G (Architect)
        prompt_g = f"Final QA'd Content:\n{results['F']}"
        results['G'] = self.agent_manager.execute_agent(
            "Architect", prompt_g, is_local=False, system_prompt=PROMPTS['G']
        )

        # 9. Agent H (Secretary)
        prompt_h = f"Task: {task_description}\nPipeline results ready. Final output:\n{results['G']}"
        results['H'] = self.agent_manager.execute_agent(
            "Secretary", prompt_h, is_local=False, system_prompt=PROMPTS['H']
        )

        # 10. Agent I (Optimizer)
        prompt_i = "Analyze this pipeline run and output logs."
        results['I'] = self.agent_manager.execute_agent(
            "Optimizer", prompt_i, is_local=False, system_prompt=PROMPTS['I']
        )

        return results

    def start_polling(self, interval_seconds=60):
        print("Starting Sovereign AI Orchestrator loop...")
        while True:
            try:
                tasks = self.fetch_new_tasks()
                for task_issue in tasks:
                    print(f"Found new task: {task_issue.title}")
                    
                    # Execute Pipeline
                    pipeline_results = self.run_pipeline(task_issue.body or task_issue.title)
                    
                    # Log to GitHub Issue
                    task_issue.create_comment(f"Task Processed. Secretary Output:\n{pipeline_results['H']}")
                    
                    self.mark_task_processed(task_issue)
                    
                time.sleep(interval_seconds)
            except KeyboardInterrupt:
                print("Stopping orchestrator.")
                break
            except Exception as e:
                print(f"Error in polling loop: {e}")
                time.sleep(interval_seconds)

if __name__ == "__main__":
    orchestrator = SovereignOrchestrator()
    orchestrator.start_polling()
