"""
KnowledgeChain - Accumulates Idea Cards from all agents and handles persistence.
"""
import json
from datetime import datetime
from pathlib import Path
from config.settings import SYSTEM_LOGS_DIR, RESEARCH_DIR


class IdeaCard:
    """Represents a single Idea Card from an agent."""
    def __init__(self, agent_id: str, process: str, data_findings: str, next_step_guidance: str):
        self.agent_id = agent_id
        self.process = process
        self.data_findings = data_findings
        self.next_step_guidance = next_step_guidance
        self.timestamp = datetime.now()

    def to_markdown(self) -> str:
        return f"""---
Agent: {self.agent_id}
Timestamp: {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
Type: Idea Card
---

# Idea Card - Agent {self.agent_id}

## Process
{self.process}

## Data / Findings
{self.data_findings}

## Next Step Guidance
{self.next_step_guidance}

---
"""

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat(),
            "process": self.process,
            "data_findings": self.data_findings,
            "next_step_guidance": self.next_step_guidance
        }


class KnowledgeChain:
    """Accumulates Idea Cards and handles saving to Obsidian and System Logs."""

    def __init__(self, topic: str, subject: str):
        self.topic = topic
        self.subject = subject
        self.cards: list[IdeaCard] = []
        self.session_id = datetime.now().strftime("%Y-%m-%d_%H%M%S")

    def add_card(self, card: IdeaCard):
        self.cards.append(card)

    def save_session_log(self):
        """Append all cards to 03_System_Logs/Session_Log_[Date].md"""
        log_dir = Path(SYSTEM_LOGS_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"Session_Log_{datetime.now().strftime('%Y-%m-%d')}.md"

        content = f"\n\n## Session {self.session_id}\n\n"
        content += f"**Topic:** {self.topic} | **Subject:** {self.subject}\n\n"
        content += "---\n\n"

        for card in self.cards:
            content += card.to_markdown() + "\n"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(content)

        return str(log_file)

    def save_research_file(self) -> str:
        """Merge ALL cards into a single Comprehensive Research File in Obsidian."""
        research_dir = Path(RESEARCH_DIR) / self.topic.capitalize()
        research_dir.mkdir(parents=True, exist_ok=True)

        filename = self.subject.lower().replace(" ", "_") + ".md"
        file_path = research_dir / filename

        content = f"# {self.subject}\n\n"
        content += f"**Topic:** {self.topic.capitalize()}\n"
        content += f"**Last Researched:** {datetime.now().strftime('%Y-%m-%d')}\n\n"
        content += "---\n\n"

        for card in self.cards:
            content += f"## Agent {card.agent_id} Contribution\n\n"
            content += f"### Process\n{card.process}\n\n"
            content += f"### Findings\n{card.data_findings}\n\n"
            content += f"### Next Step Guidance\n{card.next_step_guidance}\n\n"
            content += "---\n\n"

        # Add metadata block
        metadata = {
            "sovereign_metadata": {
                "topic": self.topic,
                "subject": self.subject,
                "last_researched_date": datetime.now().strftime("%Y-%m-%d"),
                "route_used": "FULL",
                "version": 1,
                "session_id": self.session_id
            }
        }
        content += f"\n\n<!-- Sovereign AI Metadata -->\n```json\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n```\n"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return str(file_path)
