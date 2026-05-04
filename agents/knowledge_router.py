"""
KnowledgeRouter — The "Smart Router" Protocol
Checks existing Obsidian knowledge before initiating cloud-based research.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from config.settings import RESEARCH_DIR, LESSONS_LEARNED_DIR


class KnowledgeRouter:
    # How many days before existing data is considered "stale" and needs update
    STALE_THRESHOLD_DAYS = 7

    def __init__(self):
        self.research_dir = Path(RESEARCH_DIR)
        self.lessons_dir = Path(LESSONS_LEARNED_DIR)

    def search_existing_knowledge(self, topic: str, subject: str) -> dict:
        """
        Searches 01_Research/{Topic}/ for an existing Markdown file related to the query.
        Returns:
            {
                "found": bool,
                "file_path": str or None,
                "content": str or None,
                "metadata": dict or None,
                "is_stale": bool,
                "route": "SKIP" | "DELTA" | "FULL"
            }
        """
        # Normalize topic folder name
        topic_dir = self.research_dir / topic.capitalize()

        if not topic_dir.exists():
            return self._route_result(found=False, route="FULL")

        # Search for matching files
        subject_normalized = subject.lower().replace(" ", "_")
        best_match = None
        best_score = 0

        for md_file in topic_dir.glob("*.md"):
            filename = md_file.stem.lower().replace(" ", "_")
            # Check exact match
            if filename == subject_normalized:
                best_match = md_file
                best_score = 100
                break
            # Check partial match (subject appears in filename or vice versa)
            if subject_normalized in filename or filename in subject_normalized:
                score = len(set(subject_normalized.split("_")) & set(filename.split("_")))
                if score > best_score:
                    best_match = md_file
                    best_score = score

        if not best_match:
            return self._route_result(found=False, route="FULL")

        # Read the file
        content = best_match.read_text(encoding="utf-8")
        metadata = self._extract_metadata(content)
        is_stale = self._check_staleness(metadata)

        return self._route_result(
            found=True,
            file_path=str(best_match),
            content=content,
            metadata=metadata,
            is_stale=is_stale,
            route="DELTA" if is_stale else "SKIP"
        )

    def read_lessons_learned(self) -> str:
        """
        Reads all files in 02_Lessons_Learned/ and returns their combined content.
        Used by Agent A (Gatekeeper) to extract constraints.
        """
        lessons = []
        if not self.lessons_dir.exists():
            return "No lessons learned files found."

        for md_file in self.lessons_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                lessons.append(f"--- {md_file.name} ---\n{content}")
            except Exception as e:
                lessons.append(f"Error reading {md_file.name}: {e}")

        return "\n\n".join(lessons) if lessons else "No lessons learned files found."

    def _extract_metadata(self, content: str) -> dict:
        """
        Extracts the JSON metadata block from the bottom of a Markdown file.
        Looks for a ```json block containing sovereign_metadata.
        """
        # Look for JSON metadata block
        json_pattern = r'```json\s*\n(.*?)\n\s*```'
        matches = re.findall(json_pattern, content, re.DOTALL)

        for match in reversed(matches):  # Check from bottom
            try:
                data = json.loads(match)
                if "sovereign_metadata" in data or "last_researched_date" in data:
                    return data
            except json.JSONDecodeError:
                continue

        return {}

    def _check_staleness(self, metadata: dict) -> bool:
        """
        Checks if the data is stale based on last_researched_date.
        """
        last_date_str = metadata.get("last_researched_date")
        if not last_date_str:
            return True  # No date = assume stale

        try:
            last_date = datetime.strptime(last_date_str, "%Y-%m-%d")
            return (datetime.now() - last_date) > timedelta(days=self.STALE_THRESHOLD_DAYS)
        except ValueError:
            return True

    def _route_result(self, found=False, file_path=None, content=None,
                      metadata=None, is_stale=False, route="FULL") -> dict:
        return {
            "found": found,
            "file_path": file_path,
            "content": content,
            "metadata": metadata or {},
            "is_stale": is_stale,
            "route": route  # "SKIP" | "DELTA" | "FULL"
        }

    @staticmethod
    def generate_metadata_block(topic: str, subject: str, route_used: str) -> str:
        """
        Generates a standardized JSON metadata block for the bottom of Markdown files.
        """
        metadata = {
            "sovereign_metadata": {
                "topic": topic,
                "subject": subject,
                "last_researched_date": datetime.now().strftime("%Y-%m-%d"),
                "route_used": route_used,
                "version": 1
            }
        }
        return f"\n\n<!-- Sovereign AI Metadata -->\n```json\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n```\n"
