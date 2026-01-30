# AI Daily Brief

Automated daily AI news digest. Scrapes tweets from AI companies, researchers, and topic searches, uses Claude to curate and summarize the top stories, and emails a formatted brief.

## How It Works

```
Twitter/X accounts + search queries
        |
        v
   Scrape tweets (twikit)
        |
        v
   Pre-filter (remove RTs, 24h window, rank by engagement)
        |
        v
   Summarize with Claude (group stories, tag importance)
        |
        v
   Send HTML email via Gmail
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up Twitter cookies (interactive login)
python setup_cookies.py

# 3. Create .env file
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, GMAIL_APP_PASSWORD, TWITTER_COOKIES

# 4. Run
python run.py
```

## Project Structure

```
ai-daily-brief/
├── config.md                  # Accounts, search queries, curation prompt
├── settings.yaml              # Scraper, summarizer, email settings
├── run.py                     # Entry point
├── setup_cookies.py           # One-time Twitter auth setup
├── src/
│   ├── main.py                # Orchestrator
│   ├── scraper/
│   │   ├── base.py            # Tweet dataclass + abstract scraper
│   │   └── twikit_scraper.py  # Twitter scraper implementation
│   ├── summarizer.py          # Pre-filter + Claude summarization
│   └── emailer.py             # Gmail SMTP sender
├── templates/
│   └── email_template.html    # Jinja2 HTML email template
├── .github/workflows/
│   └── daily_brief.yml        # GitHub Actions daily cron
├── .env.example               # Template for environment variables
├── requirements.txt
└── .gitignore
```

---

## Configuration Guide

### Adding / Removing Twitter Accounts

Edit `config.md` under `# Accounts`. Add any `@handle` as a bullet point:

```markdown
## Companies
- @OpenAI
- @AnthropicAI
- @NewCompany      <-- add here

## Individuals
- @karpathy
- @newresearcher   <-- add here
```

Handles are scraped individually. Each adds ~2 seconds to the run due to rate-limit delays.

### Adding / Removing Search Queries

Edit `config.md` under `# Search Queries`. Each bullet is a Twitter search:

```markdown
# Search Queries
- AI model release
- new LLM benchmark
- your new topic here   <-- add here
```

Search queries find relevant tweets from *any* account on Twitter, not just the ones you follow. Results are deduplicated against account tweets so you won't get duplicates.

### Changing the Curation Prompt

Edit `config.md` under `# Prompt`. This text is sent directly to Claude as instructions for what to focus on and what to ignore:

```markdown
# Prompt

Focus on AI/ML developments. Look for:
- New model releases and benchmarks
- Your custom focus area        <-- add here

Ignore: personal life updates, memes, engagement bait, promotional fluff.
```

This controls what Claude considers important when selecting and summarizing stories.

### Changing the Pre-Filter

The pre-filter runs *before* Claude and is configured in `settings.yaml`:

```yaml
scraper:
  lookback_hours: 24         # Only include tweets from the last N hours
  max_tweets_per_user: 50    # Max tweets fetched per account
  max_tweets_per_search: 20  # Max tweets per search query

summarizer:
  max_input_tweets: 200      # Top N tweets (by engagement) sent to Claude
```

**Engagement score** used for ranking: `likes + retweets * 2 + replies * 0.5`

Retweets are always excluded. After filtering to the lookback window, tweets are sorted by engagement and the top `max_input_tweets` are sent to Claude.

### Changing the Summary Output

In `settings.yaml`:

```yaml
summarizer:
  model: "claude-sonnet-4-20250514"   # Claude model to use
  max_stories: 15                      # Max stories in the brief
  max_tokens: 4096                     # Max response length
```

Claude returns structured JSON for each story:

| Field | Description |
|-------|-------------|
| `headline` | Concise headline (max 15 words) |
| `summary` | 2-3 sentence summary |
| `sources` | List of `{handle, url}` linking to original tweets |
| `importance` | `BREAKING`, `NOTABLE`, or `INTERESTING` |
| `category` | `Models`, `Products`, `Research`, `Open Source`, `Industry`, `Policy`, or `Insights` |

### Adding / Removing Email Recipients

Edit `settings.yaml`:

```yaml
email:
  sender: "you@gmail.com"
  recipients:
    - "you@gmail.com"
    - "colleague@example.com"    <-- add here
  subject_prefix: "AI Daily Brief"
```

### Changing the Email Template

Edit `templates/email_template.html`. It's a Jinja2 template with inline CSS. Available variables:

- `{{ date }}` -- formatted date string
- `{{ stories }}` -- list of story objects (loop with `{% for story in stories %}`)
- `{{ source_count }}` -- number of unique Twitter accounts
- `{{ tweet_count }}` -- total tweets analyzed

Each story has: `story.headline`, `story.summary`, `story.importance`, `story.category`, `story.sources` (list of `{handle, url}`).

### Changing the Schedule

Edit `.github/workflows/daily_brief.yml`:

```yaml
on:
  schedule:
    - cron: '0 7 * * *'    # 7:00 AM UTC daily
```

Some examples:
- `'0 12 * * *'` -- noon UTC
- `'0 7 * * 1-5'` -- weekdays only at 7 AM UTC
- `'0 7,19 * * *'` -- twice daily at 7 AM and 7 PM UTC

You can also trigger manually from the Actions tab via `workflow_dispatch`.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | API key from [console.anthropic.com](https://console.anthropic.com) |
| `GMAIL_APP_PASSWORD` | Yes | App password from Google Account > Security > App Passwords |
| `TWITTER_COOKIES` | Yes | JSON cookie string (run `setup_cookies.py` or export from browser) |

For local development, store these in a `.env` file (git-ignored). For GitHub Actions, add them as repository secrets under Settings > Secrets and variables > Actions.

## Swapping the Scraper

The scraper uses an abstract base class (`BaseScraper`). To use a different Twitter API client:

1. Create a new file in `src/scraper/` implementing `BaseScraper`
2. Implement `scrape_user()`, `search_tweets()`, and `close()`
3. Update the factory in `src/scraper/__init__.py`

---

Built with [twikit](https://github.com/d60/twikit) and [Claude](https://www.anthropic.com).
