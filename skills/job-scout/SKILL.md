# Job Scout — Autonomous Job Application Agent

## Description
An autonomous job hunting agent that searches for Product Manager, Product Owner, and AI PM roles across Dubai, US, and UK job boards. Scores listings against the user's profile, generates tailored resumes, and sends daily email digests with top matches.

## Trigger
Run daily via cron at 10:00 AM GST, or on-demand via "find me jobs" / "job search" / "scout jobs".

## Workflow

### Step 1: Load Profile
Read `profile.yaml` from the project directory. Extract target titles, skills, location preferences, and scoring keywords.

### Step 2: Search Job Boards
For each configured job board, search for listings matching:
- Target titles (all variations from profile)
- Target locations: Dubai (onsite/hybrid/remote), US (remote), UK (remote)
- Posted within the last 24 hours (for daily runs) or 7 days (for first run)

Use the browser tool to scrape job listings. For each listing, extract:
- Job title
- Company name
- Location & work model (remote/hybrid/onsite)
- Job description (full text)
- Application URL
- Date posted
- Salary range (if listed)

### Step 3: Score & Rank
For each job listing, calculate a match score (0-100) based on:

**Title Match (30 points)**
- Exact title match from target_titles: 30 pts
- Partial match (contains "product manager" or "product owner"): 20 pts
- Adjacent role (business analyst, program manager with PM duties): 10 pts

**Skills Match (40 points)**
- Count matching high_weight_keywords in JD: up to 15 pts
- Count matching ai_bonus_keywords: up to 15 pts
- Count matching technical_bonus_keywords: up to 10 pts

**Location & Remote Fit (20 points)**
- Dubai onsite/hybrid: 20 pts
- Dubai remote: 20 pts
- US/UK with "remote - anywhere" or "remote - worldwide": 20 pts
- US/UK with "remote" but no timezone flexibility mentioned: 15 pts
- US/UK requiring timezone overlap with mention of flexibility: 18 pts

**Negative Signals (-10 to -30 points)**
- Contains negative_keywords: -30 pts per match
- Requires experience significantly above candidate's level: -15 pts
- No remote option for US/UK roles: -20 pts

### Step 4: Filter & Classify
- **Tier 1 (Score 80-100):** Strong match — recommend immediate application
- **Tier 2 (Score 60-79):** Good match — worth reviewing
- **Tier 3 (Score 40-59):** Marginal — only apply if slow week
- **Discard (Score < 40):** Skip

### Step 5: Company Research
For Tier 1 and Tier 2 matches, briefly research the company:
- What the company does (1-2 sentences)
- Company size and funding stage
- Any recent AI/product news
- Glassdoor rating if available

### Step 6: Generate Email Report
Compose an email digest with:

**Subject:** `Job Scout Daily — [date] | [X] new matches ([Y] Tier 1)`

**Body structure:**
```
TIER 1 — STRONG MATCHES (apply now)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#1 | Score: 94/100
Role: [title] at [company]
Location: [location] | [remote/hybrid/onsite]
Why it matches: [2-3 reasons from scoring]
Company: [1-2 sentence summary]
Salary: [if listed]
Apply: [URL]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIER 2 — GOOD MATCHES (worth reviewing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[same format]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
Total scanned: [N]
Tier 1: [N] | Tier 2: [N] | Tier 3: [N] | Discarded: [N]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Reply with the numbers you want to apply to, or "apply all tier 1".
```

Send to: manishareddy560@gmail.com

### Step 7: Track Applications
Save results to:
- `state/queue/jobs_[date].json` — all scored jobs
- `state/reports/report_[date].md` — the email digest in markdown
- `state/applied/applied.json` — append when user confirms application

### Step 8: Handle Apply Requests
When user replies with job numbers:
1. Load the job listing details
2. Open the application URL in browser
3. Fill in standard fields from profile.yaml (name, email, phone, LinkedIn)
4. Attach the resume PDF from resume_path
5. Flag any custom questions for user to answer
6. Log the application to state/applied/applied.json

## Tools Required
- browser (for scraping job boards and filling applications)
- email (for sending daily digests and receiving apply confirmations)
- file operations (for reading profile, saving state)
- shell (for PDF generation if resume tailoring is needed)

## Files
- `profile.yaml` — user profile and preferences (NEVER commit — contains PII)
- `state/queue/` — scraped and scored job listings
- `state/applied/` — application tracking log
- `state/reports/` — daily report archives
