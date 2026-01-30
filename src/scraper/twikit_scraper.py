from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import twikit

from .base import BaseScraper, Tweet

logger = logging.getLogger(__name__)

COOKIES_FILE = Path(__file__).resolve().parent.parent.parent / "cookies.json"


class TwikitScraper(BaseScraper):
    def __init__(self, cookies_json: str | None = None):
        self._client = twikit.Client("en-US")
        self._cookies_json = cookies_json or os.getenv("TWITTER_COOKIES", "")
        self._authenticated = False

    async def _ensure_auth(self) -> None:
        if self._authenticated:
            return

        # 1. Try TWITTER_COOKIES env var (JSON string)
        if self._cookies_json:
            try:
                cookies = json.loads(self._cookies_json)
                self._client.set_cookies(cookies)
                self._authenticated = True
                logger.info("Authenticated with cookies from env var")
                return
            except json.JSONDecodeError as e:
                raise RuntimeError(f"TWITTER_COOKIES is not valid JSON: {e}") from e

        # 2. Try cookies.json file (created by setup_cookies.py)
        if COOKIES_FILE.exists():
            self._client.load_cookies(str(COOKIES_FILE))
            self._authenticated = True
            logger.info("Authenticated with cookies from %s", COOKIES_FILE)
            return

        raise RuntimeError(
            "No Twitter cookies found. Either:\n"
            "  1. Run: python setup_cookies.py  (easiest)\n"
            "  2. Set TWITTER_COOKIES env var with a JSON cookie string\n"
            "  3. Place a cookies.json file in the project root"
        )

    async def scrape_user(self, handle: str, max_tweets: int = 50) -> list[Tweet]:
        await self._ensure_auth()
        tweets: list[Tweet] = []
        try:
            user = await self._client.get_user_by_screen_name(handle)
            if user is None:
                logger.warning("User @%s not found", handle)
                return tweets

            user_tweets = await self._client.get_user_tweets(
                user.id, tweet_type="Tweets", count=max_tweets
            )
            for t in user_tweets:
                created_at = self._parse_time(t.created_at)
                is_retweet = bool(
                    getattr(t, "retweeted_tweet", None)
                    or (t.text and t.text.startswith("RT @"))
                )
                media_urls = []
                if hasattr(t, "media") and t.media:
                    for m in t.media:
                        url = getattr(m, "media_url_https", None) or getattr(m, "url", None)
                        if url:
                            media_urls.append(url)

                tweets.append(
                    Tweet(
                        id=t.id,
                        author_handle=handle,
                        author_name=getattr(user, "name", handle),
                        text=t.text or "",
                        created_at=created_at,
                        likes=getattr(t, "favorite_count", 0) or 0,
                        retweets=getattr(t, "retweet_count", 0) or 0,
                        replies=getattr(t, "reply_count", 0) or 0,
                        views=getattr(t, "view_count", 0) or 0,
                        url=f"https://x.com/{handle}/status/{t.id}",
                        is_retweet=is_retweet,
                        media_urls=media_urls,
                    )
                )
        except Exception as e:
            logger.warning("Failed to scrape @%s: %s", handle, e)

        return tweets

    async def search_tweets(self, query: str, count: int = 20) -> list[Tweet]:
        await self._ensure_auth()
        tweets: list[Tweet] = []
        try:
            results = await self._client.search_tweet(query, product="Top", count=count)
            for t in results:
                created_at = self._parse_time(t.created_at)
                is_retweet = bool(
                    getattr(t, "retweeted_tweet", None)
                    or (t.text and t.text.startswith("RT @"))
                )
                user = getattr(t, "user", None)
                handle = getattr(user, "screen_name", "unknown") if user else "unknown"
                name = getattr(user, "name", handle) if user else handle

                media_urls = []
                if hasattr(t, "media") and t.media:
                    for m in t.media:
                        url = getattr(m, "media_url_https", None) or getattr(m, "url", None)
                        if url:
                            media_urls.append(url)

                tweets.append(
                    Tweet(
                        id=t.id,
                        author_handle=handle,
                        author_name=name,
                        text=t.text or "",
                        created_at=created_at,
                        likes=getattr(t, "favorite_count", 0) or 0,
                        retweets=getattr(t, "retweet_count", 0) or 0,
                        replies=getattr(t, "reply_count", 0) or 0,
                        views=getattr(t, "view_count", 0) or 0,
                        url=f"https://x.com/{handle}/status/{t.id}",
                        is_retweet=is_retweet,
                        media_urls=media_urls,
                    )
                )
        except Exception as e:
            logger.warning("Failed to search '%s': %s", query, e)

        return tweets

    async def close(self) -> None:
        pass

    @staticmethod
    def _parse_time(time_str: str | None) -> datetime:
        if not time_str:
            return datetime.now(timezone.utc)
        try:
            # Twitter format: "Wed Oct 10 20:19:24 +0000 2018"
            dt = datetime.strptime(time_str, "%a %b %d %H:%M:%S %z %Y")
            return dt
        except ValueError:
            return datetime.now(timezone.utc)
