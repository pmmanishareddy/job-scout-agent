# Job Scout — Autonomous Job Application Agent

## Description
An autonomous job hunting agent that searches for Product Manager, Product Owner, and AI PM roles across Dubai, US, UK, and India job boards. Scores listings against the user's profile, flags seniority mismatches and remote eligibility, and sends daily email digests with top matches. The candidate is based in Dubai and will NOT relocate — all US/UK/India roles must be fully remote with no in-country requirement.

## Trigger
Run daily via cron at 10:00 AM GST, or on-demand via "find me jobs" / "job search" / "scout jobs".

## Workflow

### Step 1: Load Profile
Read `profile.yaml` from the project directory. Extract:
- Target titles and seniority level
- Skills and scoring keywords
- Location preferences and remote policy
- Notification email address
- Job boards to search

### Step 2: Load Previous Results (Deduplication)
Check `state/queue/` for existing job files. Build a dedup index from all previous results using the combination of: job title + company name + location. Skip any listing that matches a previous entry. This prevents the same job from appearing in multiple daily reports.

### Step 3: Search Job Boards
Search ALL configured job boards from profile.yaml:

**LinkedIn** (dubai, us, uk, india markets):
- Search linkedin.com/jobs for each target title in each market

**Wellfound** (us, uk, india markets):
- Search wellfound.com for each target title in each market

**Instahyre** (dubai, india markets):
- Search instahyre.com for each target title in each market

For each board and market, search for listings matching:
- Target titles (all variations from profile)
- Target locations:
  - Dubai: onsite, hybrid, or remote (any work model)
  - US: remote ONLY — must allow working from outside the US, no in-country requirement
  - UK: remote ONLY — must allow working from outside the UK, no in-country requirement
  - India: remote ONLY — must allow working from outside India, no in-country requirement

**Date filter (STRICT):**
- Daily runs: posted within the last 48 hours only
- First run (no previous queue files): posted within the last 7 days
- REJECT any listing older than these thresholds — do not score or include it

For each listing, extract:
- Job title
- Company name
- Location & work model (remote/hybrid/onsite)
- Job description (full text)
- Application URL
- Date posted
- Salary range (if listed)
- Remote policy details (worldwide remote / country-restricted / office required)

### Step 4: Score & Rank
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
- Dubai (any work model): 20 pts
- US/UK/India with "remote - worldwide" or "remote - anywhere" or no country restriction: 20 pts
- US/UK/India with "remote" but says "must be based in [country]" or restricts to specific country: DISCARD
- US/UK/India requiring onsite, hybrid, or relocation: DISCARD
- If unclear whether the remote role allows working from outside the country: 10 pts and flag as [REMOTE - CHECK ELIGIBILITY]

**Seniority Match (10 bonus / -20 penalty)**
- Title matches candidate seniority level (mid-level PM): +10 pts bonus
- Title contains "Senior", "Lead", "Principal", "Staff", "Head of", "Director", "VP": -20 pts penalty
- JD requires 5+ years PM experience: -10 pts penalty
- JD requires 7+ years PM experience: -20 pts penalty

**Negative Signals (-10 to -30 points)**
- Contains any negative_keywords from profile: -30 pts per match
- US/UK/India role requires being in-country or has location restriction: DISCARD entirely

### Step 5: Filter & Classify
- **Tier 1 (Score 75-100):** Strong match — recommend immediate application
- **Tier 2 (Score 55-74):** Good match — worth reviewing
- **Tier 3 (Score 40-54):** Marginal — only apply if slow week
- **Discard (Score < 40):** Skip entirely, do not include in report

### Step 6: Company Research
For Tier 1 and Tier 2 matches, briefly research the company:
- What the company does (1-2 sentences)
- Company size and funding stage
- Any recent AI/product news
- Glassdoor rating if available

### Step 7: Generate & SEND Email Report
**This step MUST send an actual email, not just save a file.**

Use the email tool to send the digest to the address in profile.yaml `notification.email_to`.

Compose an email digest with:

**Subject:** `Job Scout Daily — [date] | [X] new matches ([Y] Tier 1)`

**Body structure:**
```
TIER 1 — STRONG MATCHES (apply now)

#1 | Score: 94/100
Role: [title] at [company]
Location: [location] | [remote/hybrid/onsite]
Seniority: [OK / SENIOR - may be stretch]
Remote: [Dubai-based OK / CHECK ELIGIBILITY]
Why it matches: [2-3 reasons from scoring]
Company: [1-2 sentence summary]
Salary: [if listed]
Source: [LinkedIn / Wellfound / Instahyre]
Apply: [URL]


TIER 2 — GOOD MATCHES (worth reviewing)
[same format]


SUMMARY
Total scanned: [N]
New (not seen before): [N]
Duplicates skipped: [N]
Tier 1: [N] | Tier 2: [N] | Tier 3: [N] | Discarded: [N]
Markets: Dubai ([N]) | US Remote ([N]) | UK Remote ([N]) | India Remote ([N])
Sources: [list boards that returned results]
```

Reply with the numbers you want to apply to, or "apply all tier 1".

**ALSO save the report to:** `state/reports/report_[date].md`

### Step 8: Track Applications
Save results to:
- `state/queue/jobs_[date].json` — all scored jobs (used for deduplication)
- `state/reports/report_[date].md` — the email digest in markdown
- `state/applied/applied.json` — append when user confirms application

Each entry in jobs_[date].json must include: title, company, location, score, url, date_posted, source_board — to support deduplication across runs.

### Step 9: Handle Apply Requests
When user replies with job numbers:
1. Load the job listing details
2. Open the application URL in browser
3. Fill in standard fields from profile.yaml (name, email, phone, LinkedIn)
4. Attach the resume from resume_path
5. Flag any custom questions for user to answer
6. Log the application to state/applied/applied.json

## Tools Required
- browser (for scraping job boards and filling applications)
- email (for sending daily digests — MUST actually send, not just save to file)
- file operations (for reading profile, saving state, deduplication)
- shell (for PDF generation if resume tailoring is needed)

## Files
- `profile.yaml` — user profile and preferences (NEVER commit — contains PII)
- `state/queue/` — scraped and scored job listings (used for dedup)
- `state/applied/` — application tracking log
- `state/reports/` — daily report archives
