from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import yaml

from .emailer import send_brief
from .scraper import Tweet, create_scraper, parse_config
from .summarizer import prefilter_tweets, summarize_tweets

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.md"
SETTINGS_PATH = ROOT_DIR / "settings.yaml"


def load_settings() -> dict[str, Any]:
    return yaml.safe_load(SETTINGS_PATH.read_text())


async def fetch_all_tweets(
    handles: list[str],
    search_queries: list[str],
    settings: dict[str, Any],
) -> list[Tweet]:
    scraper_cfg = settings.get("scraper", {})
    delay = scraper_cfg.get("delay_between_users", 2)
    max_per_user = scraper_cfg.get("max_tweets_per_user", 50)
    search_count = scraper_cfg.get("max_tweets_per_search", 20)

    scraper = create_scraper()
    seen_ids: set[str] = set()
    all_tweets: list[Tweet] = []

    def _add(tweets: list[Tweet]) -> int:
        added = 0
        for t in tweets:
            if t.id not in seen_ids:
                seen_ids.add(t.id)
                all_tweets.append(t)
                added += 1
        return added

    # 1. Scrape accounts
    for handle in handles:
        logger.info("Scraping @%s ...", handle)
        tweets = await scraper.scrape_user(handle, max_tweets=max_per_user)
        added = _add(tweets)
        logger.info("  Got %d tweets from @%s (%d new)", len(tweets), handle, added)
        await asyncio.sleep(delay)

    # 2. Search by queries
    for query in search_queries:
        logger.info("Searching '%s' ...", query)
        tweets = await scraper.search_tweets(query, count=search_count)
        added = _add(tweets)
        logger.info("  Got %d results for '%s' (%d new)", len(tweets), query, added)
        await asyncio.sleep(delay)

    await scraper.close()
    return all_tweets


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Loading config and settings")
    handles, search_queries, curation_prompt = parse_config(CONFIG_PATH)
    settings = load_settings()

    logger.info("Found %d accounts and %d search queries", len(handles), len(search_queries))

    # 1. Scrape accounts + search queries
    all_tweets = await fetch_all_tweets(handles, search_queries, settings)
    logger.info("Total tweets fetched: %d", len(all_tweets))

    if not all_tweets:
        logger.warning("No tweets fetched. Exiting.")
        return

    # 2. Pre-filter
    summarizer_cfg = settings.get("summarizer", {})
    scraper_cfg = settings.get("scraper", {})
    filtered = prefilter_tweets(
        all_tweets,
        lookback_hours=scraper_cfg.get("lookback_hours", 24),
        max_tweets=summarizer_cfg.get("max_input_tweets", 200),
    )
    logger.info("Tweets after pre-filtering: %d", len(filtered))

    if not filtered:
        logger.warning("No tweets passed pre-filter. Exiting.")
        return

    # 3. Summarize with Claude
    stories = summarize_tweets(
        filtered,
        curation_prompt=curation_prompt,
        model=summarizer_cfg.get("model", "claude-sonnet-4-20250514"),
        max_stories=summarizer_cfg.get("max_stories", 15),
        max_tokens=summarizer_cfg.get("max_tokens", 4096),
    )
    logger.info("Generated %d stories", len(stories))

    if not stories:
        logger.warning("No stories generated. Exiting.")
        return

    # 4. Send email
    email_cfg = settings.get("email", {})
    unique_handles = {t.author_handle for t in all_tweets}
    send_brief(
        stories=stories,
        source_count=len(unique_handles),
        tweet_count=len(all_tweets),
        sender=email_cfg.get("sender"),
        recipients=email_cfg.get("recipients"),
        smtp_host=email_cfg.get("smtp_host", "smtp.gmail.com"),
        smtp_port=email_cfg.get("smtp_port", 587),
        subject_prefix=email_cfg.get("subject_prefix", "AI Daily Brief"),
    )

    logger.info("Daily brief complete!")
