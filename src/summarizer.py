from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import anthropic

from .scraper.base import Tweet

logger = logging.getLogger(__name__)


def prefilter_tweets(
    tweets: list[Tweet],
    lookback_hours: int = 24,
    max_tweets: int = 200,
) -> list[Tweet]:
    """Remove retweets, filter to recent, sort by engagement, take top N."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    filtered = [
        t for t in tweets
        if not t.is_retweet and t.created_at >= cutoff
    ]

    filtered.sort(key=lambda t: t.engagement_score, reverse=True)
    return filtered[:max_tweets]


def _build_tweet_block(tweets: list[Tweet]) -> str:
    lines: list[str] = []
    for t in tweets:
        lines.append(
            f"[@{t.author_handle}] ({t.created_at.strftime('%Y-%m-%d %H:%M')} UTC) "
            f"[Likes:{t.likes} RT:{t.retweets} Replies:{t.replies}]\n"
            f"{t.text}\n"
            f"URL: {t.url}\n"
        )
    return "\n---\n".join(lines)


def summarize_tweets(
    tweets: list[Tweet],
    curation_prompt: str,
    model: str = "claude-sonnet-4-20250514",
    max_stories: int = 15,
    max_tokens: int = 4096,
) -> list[dict[str, Any]]:
    """Send tweets to Claude and get structured JSON stories back."""
    if not tweets:
        logger.warning("No tweets to summarize")
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set")

    client = anthropic.Anthropic(api_key=api_key)

    tweet_block = _build_tweet_block(tweets)

    system_prompt = (
        "You are an AI news curator. You will receive a batch of tweets from AI companies "
        "and researchers. Your job is to identify the most important stories, group related "
        "tweets together, and produce a structured JSON summary.\n\n"
        f"Curation instructions from the user:\n{curation_prompt}\n\n"
        "Output a JSON array of story objects. Each story has:\n"
        '- "headline": concise headline (max 15 words)\n'
        '- "summary": 2-3 sentence summary of the story\n'
        '- "sources": list of objects with "handle" and "url" fields\n'
        '- "importance": one of "BREAKING", "NOTABLE", or "INTERESTING"\n'
        '- "category": one of "Models", "Products", "Research", "Open Source", '
        '"Industry", "Policy", "Insights"\n\n'
        f"Return at most {max_stories} stories, ordered by importance.\n"
        "Return ONLY the JSON array, no markdown fences or extra text."
    )

    user_message = f"Here are today's tweets:\n\n{tweet_block}"

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = response.content[0].text.strip()

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[: raw_text.rfind("```")]
        raw_text = raw_text.strip()

    try:
        stories = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.error("Failed to parse Claude response as JSON:\n%s", raw_text)
        return []

    if not isinstance(stories, list):
        logger.error("Expected JSON array, got %s", type(stories))
        return []

    return stories
