#!/usr/bin/env python3
"""
One-time setup: logs into Twitter/X and saves cookies to a JSON file.
Run this once locally, then copy the cookie JSON into your .env or GitHub secret.

Usage:
    python setup_cookies.py
"""

import asyncio
import json
import getpass

import twikit


async def main():
    client = twikit.Client("en-US")

    print("=== Twitter/X Cookie Setup ===\n")
    username = input("Twitter username (without @): ").strip()
    email = input("Email address on account: ").strip()
    password = getpass.getpass("Password: ")

    print("\nLogging in...")
    try:
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
        )
    except Exception as e:
        print(f"\nLogin failed: {e}")
        print("If you have 2FA enabled, you may need to use the browser method instead.")
        return

    # Save to file
    client.save_cookies("cookies.json")
    print("\nCookies saved to cookies.json")

    # Also print as a single-line JSON string for .env / GitHub secrets
    cookies = client.get_cookies()
    cookie_str = json.dumps(cookies)

    print("\n--- Copy the line below into your .env file ---\n")
    print(f"TWITTER_COOKIES={cookie_str}")
    print("\n--- Or add as a GitHub Actions secret named TWITTER_COOKIES ---\n")


if __name__ == "__main__":
    asyncio.run(main())
