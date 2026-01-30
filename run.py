#!/usr/bin/env python3
"""Entry point for the AI Daily Brief."""

import asyncio

from dotenv import load_dotenv

load_dotenv()

from src.main import run

if __name__ == "__main__":
    asyncio.run(run())
