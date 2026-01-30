from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Tweet:
    id: str
    author_handle: str
    author_name: str
    text: str
    created_at: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    url: str = ""
    is_retweet: bool = False
    media_urls: list[str] = field(default_factory=list)

    @property
    def engagement_score(self) -> float:
        return self.likes + self.retweets * 2 + self.replies * 0.5


class BaseScraper(ABC):
    @abstractmethod
    async def scrape_user(self, handle: str, max_tweets: int = 50) -> list[Tweet]:
        """Fetch recent tweets for a single user handle (without @)."""
        ...

    @abstractmethod
    async def search_tweets(self, query: str, count: int = 20) -> list[Tweet]:
        """Search tweets by keyword query."""
        ...

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""
        ...


def parse_config(config_path: str | Path) -> tuple[list[str], list[str], str]:
    """Parse config.md and return (handles, search_queries, prompt text)."""
    text = Path(config_path).read_text()

    accounts_section = ""
    search_section = ""
    prompt_section = ""

    sections = re.split(r"^# ", text, flags=re.MULTILINE)
    for section in sections:
        lower = section.lower()
        if lower.startswith("accounts"):
            accounts_section = section
        elif lower.startswith("search"):
            search_section = section
        elif lower.startswith("prompt"):
            prompt_section = "\n".join(section.split("\n")[1:]).strip()

    handles: list[str] = []
    for line in accounts_section.splitlines():
        line = line.strip()
        if line.startswith("- @"):
            handle = line.lstrip("- @").strip()
            if handle:
                handles.append(handle)

    queries: list[str] = []
    for line in search_section.splitlines():
        line = line.strip()
        if line.startswith("- "):
            query = line[2:].strip()
            if query:
                queries.append(query)

    return handles, queries, prompt_section
