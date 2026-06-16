# Job Scout Agent

Autonomous AI-powered job hunting agent built with [Hermes Agent](https://github.com/NousResearch/hermes-agent) (Nous Research).

## What it does

- Scrapes job listings daily across LinkedIn, Wellfound, and Instahyre
- Scores each role 0–100 against a structured profile (title match, skills alignment, location fit, negative signal detection)
- Delivers ranked daily email digests with match reasoning and direct apply links
- Runs unattended via cron scheduling

## Profile

The agent targets 14 PM/PO/AI PM title variations across 4 markets (Dubai, US, UK, India), configured in `profile.yaml`.

## Architecture

```
profile.yaml          → Candidate profile, target titles, scoring keywords
skills/job-scout/     → Hermes skill definition (8-step workflow)
state/                → Runtime data (queue, reports, applied — gitignored)
templates/            → Email digest templates
```

## Tech Stack

- **Agent Framework**: Hermes Agent (Nous Research)
- **LLM**: Claude API (Sonnet)
- **Email**: IMAP/SMTP gateway (Gmail)
- **Scheduling**: cron

## Setup

1. Install [Hermes Agent](https://github.com/NousResearch/hermes-agent)
2. Configure `.env` with your Anthropic API key and Gmail app password
3. Update `profile.yaml` with your details
4. Run: `hermes --skill job-scout`
