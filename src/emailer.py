from __future__ import annotations

import logging
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

from jinja2 import Template

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "email_template.html"


def _render_html(
    stories: list[dict[str, Any]],
    date_str: str,
    source_count: int,
    tweet_count: int,
) -> str:
    template_text = TEMPLATE_PATH.read_text()
    template = Template(template_text)
    return template.render(
        stories=stories,
        date=date_str,
        source_count=source_count,
        tweet_count=tweet_count,
    )


def _render_plain_text(stories: list[dict[str, Any]]) -> str:
    lines: list[str] = ["AI DAILY BRIEF", "=" * 40, ""]
    for i, story in enumerate(stories, 1):
        importance = story.get("importance", "INTERESTING")
        category = story.get("category", "")
        lines.append(f"{i}. [{importance}] [{category}] {story['headline']}")
        lines.append(f"   {story['summary']}")
        sources = story.get("sources", [])
        if sources:
            source_strs = [f"@{s['handle']} ({s['url']})" for s in sources]
            lines.append(f"   Sources: {', '.join(source_strs)}")
        lines.append("")
    return "\n".join(lines)


def send_brief(
    stories: list[dict[str, Any]],
    source_count: int = 0,
    tweet_count: int = 0,
    sender: str | None = None,
    recipients: list[str] | str | None = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    subject_prefix: str = "AI Daily Brief",
) -> None:
    """Send the daily brief email via Gmail SMTP."""
    password = os.environ.get("GMAIL_APP_PASSWORD")
    if not password:
        raise RuntimeError("GMAIL_APP_PASSWORD environment variable is not set")

    sender = sender or os.environ.get("EMAIL_SENDER", "rathinamurthy.ai@gmail.com")
    if recipients is None:
        recipients = [os.environ.get("EMAIL_RECIPIENT", "rathinamurthy.ai@gmail.com")]
    elif isinstance(recipients, str):
        recipients = [recipients]

    date_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    subject = f"{subject_prefix} — {date_str}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)

    plain_text = _render_plain_text(stories)
    html = _render_html(stories, date_str, source_count, tweet_count)

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html, "html"))

    logger.info("Sending email to %s via %s:%d", ", ".join(recipients), smtp_host, smtp_port)
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())

    logger.info("Email sent successfully")
