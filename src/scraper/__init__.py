from .base import BaseScraper, Tweet, parse_config
from .twikit_scraper import TwikitScraper


def create_scraper(**kwargs) -> BaseScraper:
    """Factory: returns the default scraper implementation."""
    return TwikitScraper(**kwargs)


__all__ = ["BaseScraper", "Tweet", "parse_config", "create_scraper", "TwikitScraper"]
