#!/usr/bin/env python3
"""
Job Scout v4 - Final version with fixed company extraction.
Searches LinkedIn for all markets, extracts real PM roles,
scores with proper descriptions, sends email.
"""
import json, re, urllib.request, urllib.parse, time, html, os
from datetime import datetime

PROJECT_DIR = "/Users/manisha/Documents/job-scout-agent"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

profile = {
    "target_titles": [
        "Associate Product Manager", "APM", "Junior Product Manager",
        "Associate PM", "Associate Product Manager - AI", "Associate Technical Product Manager",
        "AI Product Manager", "AI/ML Product Manager", "Technical Product Manager",
        "AI Platform PM", "Product Manager - AI", "Product Manager - ML",
        "Product Manager - Platform", "Product Manager", "Product Operations Manager",
        "Digital Product Manager", "Product Owner"
    ],
    "high_weight_keywords": ["product manager", "product owner", "PRD", "roadmap",
                              "cross-functional", "stakeholder", "agile", "scrum"],
    "ai_bonus_keywords": ["LLM", "Claude", "GPT", "AI", "ML", "machine learning",
                          "prompt", "RAG", "agents", "responsible AI", "generative"],
    "technical_bonus_keywords": ["API", "system design", "SQL", "Python", "SaaS"],
    "too_senior_titles": ["senior product manager", "lead product manager",
                          "principal product manager", "staff product manager",
                          "group product manager", "director of product",
                          "vp product", "head of product", "chief product officer",
                          "sr. product manager", "sr product manager"],
    "negative_keywords": [
        "must be located in", "must be based in", "required to work from our office",
        "relocation required", "not eligible for remote", "us citizens only",
        "security clearance required"
    ],
    "email_to": "pmmanishareddy@gmail.com"
}

def fetch_html(url, timeout=15):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml',
    })
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        return ""

def strip_html(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_jobs(keyword, location, market):
    """Extract job cards from a LinkedIn search page"""
    kw_enc = urllib.parse.quote(keyword)
    loc_enc = urllib.parse.quote(location)
    url = f"https://www.linkedin.com/jobs/search?keywords={kw_enc}&location={loc_enc}&f_TPR=r86400"
    
    html = fetch_html(url, timeout=20)
    if not html:
        return []
    
    jobs = []
    cards = re.split(r'<div[^>]*class="[^"]*base-search-card[^"]*job-search-card[^"]*"', html)[1:]
    
    for card_html in cards[:30]:
        job = {"source": "LinkedIn", "market": market, "work_model": "unknown", "salary": None, "job_description": ""}
        
        # Job ID
        jid = re.search(r'data-entity-urn="urn:li:jobPosting:(\d+)"', card_html)
        if not jid: continue
        job["job_id"] = jid.group(1)
        
        # URL
        url_match = re.search(r'href="([^"]*/jobs/view/[^"]*?)"', card_html)
        if not url_match: continue
        job["application_url"] = url_match.group(1).split('?')[0]
        
        # Title
        title_match = re.search(r'base-search-card__title[^>]*>\s*(.*?)\s*</h3>', card_html, re.DOTALL)
        if not title_match: continue
        job["job_title"] = strip_html(title_match.group(1))
        
        # Company - split card into subtitle section to find <a> inside
        sub_idx = card_html.find('base-search-card__subtitle')
        if sub_idx >= 0:
            sub_section = card_html[sub_idx:sub_idx+800]
            co_match = re.search(r'<a[^>]*>\s*(.*?)\s*</a>', sub_section)
            job["company_name"] = strip_html(co_match.group(1)) if co_match else "Unknown"
        else:
            job["company_name"] = "Unknown"
        
        # Location
        loc_match = re.search(r'job-search-card__location[^>]*>\s*([^<]+)', card_html)
        job["location"] = strip_html(loc_match.group(1)) if loc_match else location
        
        # Date
        date_match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', card_html)
        job["date_posted"] = date_match.group(1) if date_match else ""
        
        jobs.append(job)
    
    return jobs

def extract_jobs_remoteok():
    """Scrape RemoteOK for product manager roles."""
    url = "https://remoteok.com/remote-product-manager-jobs"
    page = fetch_html(url, timeout=20)
    if not page:
        return []
    jobs = []
    cards = re.findall(
        r'<tr[^>]*class="job[^"]*"[^>]*data-slug="([^"]*)"[^>]*>(.+?)</tr>',
        page, re.DOTALL
    )
    for slug, card in cards[:30]:
        title_m = re.search(r'<h2[^>]*>(.*?)</h2>', card, re.DOTALL)
        co_m = re.search(r'<h3[^>]*>(.*?)</h3>', card, re.DOTALL)
        if not title_m:
            continue
        title = strip_html(title_m.group(1))
        company = strip_html(co_m.group(1)) if co_m else "Unknown"
        jobs.append({
            "job_id": f"rok_{slug}",
            "job_title": title,
            "company_name": company,
            "location": "Remote",
            "work_model": "remote",
            "market": "us",
            "source": "RemoteOK",
            "application_url": f"https://remoteok.com/{slug}",
            "date_posted": "",
            "salary": None,
            "job_description": "",
        })
    return jobs


def extract_jobs_remotive():
    """Scrape Remotive API for product manager roles."""
    url = "https://remotive.com/api/remote-jobs?category=product&limit=30"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return []
    jobs = []
    for item in (data.get("jobs") or [])[:30]:
        jobs.append({
            "job_id": f"rmtv_{item.get('id', '')}",
            "job_title": item.get("title", ""),
            "company_name": item.get("company_name", "Unknown"),
            "location": item.get("candidate_required_location", "Remote"),
            "work_model": "remote",
            "market": "us",
            "source": "Remotive",
            "application_url": item.get("url", ""),
            "date_posted": (item.get("publication_date") or "")[:10],
            "salary": item.get("salary", None),
            "job_description": strip_html(item.get("description", ""))[:3000],
        })
    return jobs


def extract_jobs_himalayas():
    """Scrape Himalayas API for product manager roles."""
    url = "https://himalayas.app/api/jobs?category=Product&limit=30"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return []
    jobs = []
    for item in (data.get("jobs") or [])[:30]:
        jobs.append({
            "job_id": f"hml_{item.get('id', '')}",
            "job_title": item.get("title", ""),
            "company_name": item.get("companyName", "Unknown"),
            "location": item.get("location", "Remote"),
            "work_model": "remote",
            "market": "us",
            "source": "Himalayas",
            "application_url": item.get("applicationUrl", "") or f"https://himalayas.app/jobs/{item.get('id', '')}",
            "date_posted": (item.get("pubDate") or "")[:10],
            "salary": None,
            "job_description": strip_html(item.get("description", ""))[:3000],
        })
    return jobs


def extract_jobs_bayt(keyword, market="dubai"):
    """Scrape Bayt.com for PM roles in the Gulf."""
    kw_enc = urllib.parse.quote(keyword)
    url = f"https://www.bayt.com/en/uae/jobs/{kw_enc}-jobs/"
    page = fetch_html(url, timeout=20)
    if not page:
        return []
    jobs = []
    cards = re.findall(r'<li[^>]*class="[^"]*has-item-card[^"]*"[^>]*>(.*?)</li>', page, re.DOTALL)
    for card in cards[:20]:
        title_m = re.search(r'<h2[^>]*>.*?<a[^>]*>(.*?)</a>', card, re.DOTALL)
        co_m = re.search(r'<div[^>]*class="[^"]*t-company[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', card, re.DOTALL)
        url_m = re.search(r'<h2[^>]*>.*?<a[^>]*href="([^"]*)"', card, re.DOTALL)
        if not title_m:
            continue
        title = strip_html(title_m.group(1))
        company = strip_html(co_m.group(1)) if co_m else "Unknown"
        href = url_m.group(1) if url_m else ""
        if href and not href.startswith("http"):
            href = f"https://www.bayt.com{href}"
        jid = re.sub(r'[^a-zA-Z0-9]', '_', href[-40:]) if href else title[:20]
        jobs.append({
            "job_id": f"bayt_{jid}",
            "job_title": title,
            "company_name": company,
            "location": "Dubai, UAE",
            "work_model": "unknown",
            "market": market,
            "source": "Bayt",
            "application_url": href,
            "date_posted": "",
            "salary": None,
            "job_description": "",
        })
    return jobs


def extract_jobs_gulftalent(keyword, market="dubai"):
    """Scrape GulfTalent for PM roles."""
    kw_enc = urllib.parse.quote(keyword)
    url = f"https://www.gulftalent.com/jobs/search?keywords={kw_enc}&locations=uae"
    page = fetch_html(url, timeout=20)
    if not page:
        return []
    jobs = []
    cards = re.findall(r'<div[^>]*class="[^"]*job-listing[^"]*"[^>]*>(.*?)</div>\s*</div>', page, re.DOTALL)
    for card in cards[:20]:
        title_m = re.search(r'<a[^>]*class="[^"]*job-title[^"]*"[^>]*>(.*?)</a>', card, re.DOTALL)
        co_m = re.search(r'<span[^>]*class="[^"]*company[^"]*"[^>]*>(.*?)</span>', card, re.DOTALL)
        url_m = re.search(r'<a[^>]*class="[^"]*job-title[^"]*"[^>]*href="([^"]*)"', card, re.DOTALL)
        if not title_m:
            continue
        title = strip_html(title_m.group(1))
        company = strip_html(co_m.group(1)) if co_m else "Unknown"
        href = url_m.group(1) if url_m else ""
        if href and not href.startswith("http"):
            href = f"https://www.gulftalent.com{href}"
        jid = re.sub(r'[^a-zA-Z0-9]', '_', href[-40:]) if href else title[:20]
        jobs.append({
            "job_id": f"gt_{jid}",
            "job_title": title,
            "company_name": company,
            "location": "UAE",
            "work_model": "unknown",
            "market": market,
            "source": "GulfTalent",
            "application_url": href,
            "date_posted": "",
            "salary": None,
            "job_description": "",
        })
    return jobs


def extract_jobs_generic_html(board_name, url, market, id_prefix):
    """Generic HTML scraper for simpler job boards (The Product Folks, Mind the Product)."""
    page = fetch_html(url, timeout=20)
    if not page:
        return []
    jobs = []
    body = re.sub(r'<script[^>]*>.*?</script>', '', page, flags=re.DOTALL)
    body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
    links = re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', body, re.DOTALL)
    seen = set()
    for href, link_text in links:
        text = strip_html(link_text)
        if not text or len(text) < 5 or len(text) > 120:
            continue
        text_lower = text.lower()
        if not any(t in text_lower for t in ["product manager", "product owner", "apm", "associate product"]):
            continue
        if text in seen:
            continue
        seen.add(text)
        if not href.startswith("http"):
            href = urllib.parse.urljoin(url, href)
        jid = re.sub(r'[^a-zA-Z0-9]', '_', href[-50:])
        jobs.append({
            "job_id": f"{id_prefix}_{jid}",
            "job_title": text,
            "company_name": "Unknown",
            "location": "Remote" if market != "dubai" else "Dubai",
            "work_model": "unknown",
            "market": market,
            "source": board_name,
            "application_url": href,
            "date_posted": "",
            "salary": None,
            "job_description": "",
        })
    return jobs[:20]


def is_pm_role(title, company=""):
    title_lower = title.lower()
    pm_terms = ["product manager", "product owner", "technical product manager",
                "ai product", "product operations", "digital product", "apm"]
    return any(t in title_lower for t in pm_terms)

def is_too_senior(title):
    title_lower = title.lower()
    return any(t in title_lower for t in profile["too_senior_titles"])

def score_job(title, company, description, location, market):
    title_lower = title.lower()
    desc_lower = description.lower() if description else ""
    loc_lower = location.lower()
    total = 0
    breakdown = []
    
    # Title Match (30 points)
    target_lower = [t.lower() for t in profile["target_titles"]]
    if title_lower in target_lower:
        total += 30; breakdown.append("Exact title match: +30")
    elif "product manager" in title_lower or "product owner" in title_lower:
        total += 20; breakdown.append("Partial title match (PM/PO): +20")
    elif "product" in title_lower:
        total += 10; breakdown.append("Adjacent role: +10")
    
    # Skills Match (40 points)
    if description:
        hw = min(sum(2 for kw in profile["high_weight_keywords"] if kw in desc_lower), 15)
        if hw: total += hw; breakdown.append(f"High-weight keywords: +{hw}")
        
        ai = min(sum(2 for kw in profile["ai_bonus_keywords"] if kw.lower() in desc_lower), 15)
        if ai: total += ai; breakdown.append(f"AI/ML keywords: +{ai}")
        
        tech = min(sum(2 for kw in profile["technical_bonus_keywords"] if kw.lower() in desc_lower), 10)
        if tech: total += tech; breakdown.append(f"Technical keywords: +{tech}")
    
    # Location & Remote Fit (20 points)
    if market == "dubai":
        total += 20; breakdown.append("Dubai location (UAE resident): +20")
    elif market in ("us", "uk"):
        remote_worldwide = any(p in desc_lower for p in [
            "remote worldwide", "remote anywhere", "global remote",
            "remote - worldwide", "remote - anywhere", "work from anywhere",
            "remote from anywhere", "worldwide remote",
            "100% remote", "fully remote", "remote-first"])
        if remote_worldwide:
            total += 20; breakdown.append(f"{market.upper()} remote (worldwide): +20")
        elif "remote" in desc_lower or "remote" in loc_lower:
            total += 15; breakdown.append(f"{market.upper()} remote: +15")
        else:
            total -= 100; breakdown.append(f"{market.upper()} not remote: DISCARD")
    
    # Seniority (15 bonus for APM / 10 for mid / -20 penalty for senior)
    if is_too_senior(title):
        total -= 20; breakdown.append("Senior title penalty: -20")
    elif any(t in title_lower for t in ["associate product manager", "apm", "junior product manager", "associate pm"]):
        total += 15; breakdown.append("APM/entry-level match (ideal seniority): +15")
    else:
        total += 10; breakdown.append("Seniority OK: +10")
    
    # Negative signals
    if description:
        for neg in profile["negative_keywords"]:
            if neg.lower() in desc_lower:
                total -= 30; breakdown.append(f"Negative keyword: -30")
        if re.search(r'\b[57]\+?\s*years.*(?:pm|product management|product manager)', desc_lower):
            total -= 10; breakdown.append("5+ years PM exp: -10")
    
    return total, breakdown


def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    today = datetime.now().strftime("%B %d, %Y")
    
    # Load dedup
    dedup_keys = set()
    for fname in os.listdir(os.path.join(PROJECT_DIR, "state/queue")):
        if fname.endswith(".json"):
            with open(os.path.join(PROJECT_DIR, "state/queue", fname)) as f:
                try:
                    data = json.load(f)
                    for j in data:
                        dedup_keys.add(f"{j.get('job_title','').strip().lower()}|{j.get('company_name','').strip().lower()}")
                except: pass
    
    print(f"Dedup: {len(dedup_keys)} keys")
    
    # Search all markets
    searches = [
        ("Product Manager", "Dubai, United Arab Emirates", "dubai"),
        ("AI Product Manager", "Dubai, United Arab Emirates", "dubai"),
        ("Technical Product Manager", "Dubai, United Arab Emirates", "dubai"),
        ("Product Owner", "Dubai, United Arab Emirates", "dubai"),
        ("Associate Product Manager", "Dubai, United Arab Emirates", "dubai"),
        ("Product Manager", "United States", "us"),
        ("AI Product Manager", "United States", "us"),
        ("Technical Product Manager", "United States", "us"),
        ("Associate Product Manager", "United States", "us"),
        ("Product Manager", "United Kingdom", "uk"),
        ("AI Product Manager", "United Kingdom", "uk"),
        ("Associate Product Manager", "United Kingdom", "uk"),
    ]
    
    all_jobs = {}
    total_cards = 0

    # --- LinkedIn ---
    for keyword, location, market in searches:
        print(f"LI '{keyword}' / {market}...", end=" ", flush=True)
        jobs = extract_jobs(keyword, location, market)
        print(f"{len(jobs)} cards", flush=True)
        total_cards += len(jobs)
        for j in jobs:
            all_jobs[j["job_id"]] = j
        time.sleep(0.5)

    # --- Bayt (Dubai) ---
    for kw in ["Product Manager", "Associate Product Manager"]:
        print(f"Bayt '{kw}'...", end=" ", flush=True)
        jobs = extract_jobs_bayt(kw, "dubai")
        print(f"{len(jobs)} cards", flush=True)
        total_cards += len(jobs)
        for j in jobs:
            all_jobs[j["job_id"]] = j
        time.sleep(0.5)

    # --- GulfTalent (Dubai) ---
    for kw in ["Product Manager", "Associate Product Manager"]:
        print(f"GulfTalent '{kw}'...", end=" ", flush=True)
        jobs = extract_jobs_gulftalent(kw, "dubai")
        print(f"{len(jobs)} cards", flush=True)
        total_cards += len(jobs)
        for j in jobs:
            all_jobs[j["job_id"]] = j
        time.sleep(0.5)

    # --- RemoteOK ---
    print("RemoteOK...", end=" ", flush=True)
    jobs = extract_jobs_remoteok()
    print(f"{len(jobs)} cards", flush=True)
    total_cards += len(jobs)
    for j in jobs:
        all_jobs[j["job_id"]] = j

    # --- Remotive ---
    print("Remotive...", end=" ", flush=True)
    jobs = extract_jobs_remotive()
    print(f"{len(jobs)} cards", flush=True)
    total_cards += len(jobs)
    for j in jobs:
        all_jobs[j["job_id"]] = j

    # --- Himalayas ---
    print("Himalayas...", end=" ", flush=True)
    jobs = extract_jobs_himalayas()
    print(f"{len(jobs)} cards", flush=True)
    total_cards += len(jobs)
    for j in jobs:
        all_jobs[j["job_id"]] = j

    # --- The Product Folks ---
    print("The Product Folks...", end=" ", flush=True)
    jobs = extract_jobs_generic_html("The Product Folks", "https://theproductfolks.com/jobs", "dubai", "tpf")
    print(f"{len(jobs)} cards", flush=True)
    total_cards += len(jobs)
    for j in jobs:
        all_jobs[j["job_id"]] = j

    # --- Mind the Product ---
    print("Mind the Product...", end=" ", flush=True)
    jobs = extract_jobs_generic_html("Mind the Product", "https://www.mindtheproduct.com/jobs", "us", "mtp")
    print(f"{len(jobs)} cards", flush=True)
    total_cards += len(jobs)
    for j in jobs:
        all_jobs[j["job_id"]] = j

    print(f"\nTotal: {len(all_jobs)} unique | Cards fetched: {total_cards}")
    
    # Filter PM roles
    pm_jobs = [j for j in all_jobs.values() if is_pm_role(j["job_title"], j.get("company_name", ""))]
    
    # Dedup
    new_jobs = []
    for job in pm_jobs:
        dk = f"{job['job_title'].strip().lower()}|{job['company_name'].strip().lower()}"
        if dk not in dedup_keys:
            dedup_keys.add(dk)
            new_jobs.append(job)
    
    print(f"PM roles: {len(pm_jobs)} | New: {len(new_jobs)}")
    
    # Fetch descriptions for all new jobs
    if new_jobs:
        print("Fetching descriptions...")
        for i, job in enumerate(new_jobs):
            page_html = fetch_html(job["application_url"], timeout=10)
            if page_html:
                # Get description from meta or page text
                meta = re.search(r'<meta name="description"[^>]*content="([^"]*)"', page_html)
                if meta and len(meta.group(1)) > 50:
                    job["job_description"] = strip_html(meta.group(1))[:3000]
                else:
                    # Try to extract from body content
                    body = re.sub(r'<script[^>]*>.*?</script>', '', page_html, flags=re.DOTALL)
                    body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL)
                    text = strip_html(body)
                    # Find the job description section
                    for marker in ["About the job", "Job Description", "Job description"]:
                        if marker in text:
                            idx = text.index(marker)
                            job["job_description"] = text[idx:idx+3000]
                            break
            time.sleep(0.4)
    
    # Score
    scored = []
    for job in new_jobs:
        score, breakdown = score_job(
            job["job_title"], job.get("company_name", ""),
            job.get("job_description", ""), job["location"], job["market"]
        )
        job["score"] = score
        job["breakdown"] = breakdown
        
        if score >= 75: job["tier"] = "T1"
        elif score >= 55: job["tier"] = "T2"
        elif score >= 40: job["tier"] = "T3"
        else: job["tier"] = "DISCARD"
        
        if job["tier"] != "DISCARD":
            scored.append(job)
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    
    t1 = [j for j in scored if j["tier"] == "T1"]
    t2 = [j for j in scored if j["tier"] == "T2"]
    t3 = [j for j in scored if j["tier"] == "T3"]
    
    market_counts = {}
    for j in scored:
        market_counts[j["market"]] = market_counts.get(j["market"], 0) + 1
    
    # Build email
    lines = []
    lines.append(f"Job Scout Daily — {today} | {len(scored)} new matches ({len(t1)} Tier 1)")
    lines.append("")
    
    lines.append("=" * 60)
    lines.append("TIER 1 — STRONG MATCHES (apply now)")
    lines.append("=" * 60)
    if not t1:
        lines.append("  No Tier 1 matches today.")
    for j in t1:
        lines.append(f"")
        lines.append(f"Score: {j['score']}/100")
        lines.append(f"Role: {j['job_title']} at {j['company_name']}")
        lines.append(f"Location: {j['location']} | Market: {j['market'].upper()}")
        lines.append("Why it matches:")
        for b in j.get("breakdown", [])[:5]:
            lines.append(f"  • {b}")
        lines.append(f"Apply: {j['application_url']}")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("TIER 2 — GOOD MATCHES (worth reviewing)")
    lines.append("=" * 60)
    if not t2:
        lines.append("  No Tier 2 matches today.")
    for i, j in enumerate(t2, 1):
        lines.append(f"")
        lines.append(f"#{i} | Score: {j['score']}/100")
        lines.append(f"Role: {j['job_title']} at {j['company_name']}")
        lines.append(f"Location: {j['location']} | Market: {j['market'].upper()}")
        for b in j.get("breakdown", [])[:4]:
            lines.append(f"  • {b}")
        lines.append(f"Apply: {j['application_url']}")
    
    if t3:
        lines.append("")
        lines.append("=" * 60)
        lines.append("TIER 3 — MARGINAL")
        lines.append("=" * 60)
        for j in t3:
            lines.append(f"  {j['score']}/100 - {j['job_title']} @ {j['company_name']} ({j['market']})")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("SUMMARY")
    lines.append("=" * 60)
    lines.append(f"Total job cards scanned: {total_cards}")
    lines.append(f"Unique listings: {len(all_jobs)}")
    lines.append(f"New (not seen before): {len(new_jobs)}")
    lines.append(f"Tier 1: {len(t1)} | Tier 2: {len(t2)} | Tier 3: {len(t3)} | Discarded: {len(new_jobs) - len(scored)}")
    lines.append(f"Markets: {' | '.join(f'{m.title()} ({c})' for m, c in sorted(market_counts.items()))}")
    source_counts = {}
    for j in scored:
        source_counts[j["source"]] = source_counts.get(j["source"], 0) + 1
    lines.append(f"Sources: {', '.join(f'{s} ({c})' for s, c in sorted(source_counts.items()))}" if source_counts else "Sources: none")
    
    email_body = "\n".join(lines)
    subject = f"Job Scout Daily — {date_str} | {len(scored)} new matches ({len(t1)} Tier 1)"
    
    # Save report
    report_path = os.path.join(PROJECT_DIR, f"state/reports/report_{date_str}.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        f.write(email_body)
    
    # Save queue
    queue_path = os.path.join(PROJECT_DIR, f"state/queue/jobs_{date_str}.json")
    with open(queue_path, 'w') as f:
        json.dump(scored, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"RESULTS: {len(scored)} scored | T1:{len(t1)} T2:{len(t2)} T3:{len(t3)}")
    for j in scored:
        print(f"  [{j['tier']}] {j['score']:3d} - {j['job_title'][:50]} @ {j['company_name'][:25]} ({j['market']})")
    
    # Final output for email
    print(f"\n=== EMAIL_READY ===")
    print(f"SUBJECT: {subject}")
    print(f"TO: {profile['email_to']}")
    print(f"---EMAIL_BODY---")
    print(email_body)

if __name__ == "__main__":
    main()
