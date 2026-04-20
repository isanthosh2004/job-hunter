"""
╔═══════════════════════════════════════════════════════════════════╗
║           GLOBAL JOB HUNTER AGENT v3.0                           ║
║  Strategy: Use Google as universal crawler — finds jobs on        ║
║  ANY company's ATS, LinkedIn posts, job boards, career pages      ║
║                                                                   ║
║  Geographies: India (all cities) · Gulf (UAE/Qatar/Saudi)         ║
║               Singapore · Malaysia · Remote                       ║
║  Schedule: Every 6 hours via GitHub Actions                       ║
╚═══════════════════════════════════════════════════════════════════╝
"""

import os, re, json, time, smtplib, hashlib, requests
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup

try:
    from jobspy import scrape_jobs
    JOBSPY_OK = True
except ImportError:
    JOBSPY_OK = False

try:
    from googlesearch import search as google_free_search
    GFREE_OK = True
except ImportError:
    GFREE_OK = False

# ════════════════════════════════════════════════════════════
#  SECRETS  (set as GitHub Secrets / local env vars)
# ════════════════════════════════════════════════════════════
GMAIL_USER     = os.getenv("GMAIL_USER", "")
GMAIL_PASS     = os.getenv("GMAIL_PASSWORD", "")
RECIPIENT      = os.getenv("RECIPIENT_EMAIL", "santhoshkumarsp222004@gmail.com")
SERPAPI_KEY    = os.getenv("SERPAPI_KEY", "")     # serpapi.com — 100 free/month trial
JSEARCH_KEY    = os.getenv("JSEARCH_KEY", "")     # rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch — free tier

LOOKBACK_HRS   = 7    # 6hr cycle + 1hr overlap

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ════════════════════════════════════════════════════════════
#  GEOGRAPHIES — all target cities / countries
# ════════════════════════════════════════════════════════════
INDIA_LOCATIONS = [
    "Bangalore", "Hyderabad", "Chennai", "Mumbai", "Pune",
    "Delhi", "Gurgaon", "Noida", "Kolkata", "Kochi",
    "Ahmedabad", "Jaipur", "India",
]
GULF_LOCATIONS = [
    "Dubai", "Abu Dhabi", "Sharjah", "UAE",
    "Doha", "Qatar",
    "Riyadh", "Jeddah", "Saudi Arabia",
]
SEA_LOCATIONS = [
    "Singapore",
    "Kuala Lumpur", "Malaysia",
]
ALL_LOCATIONS = INDIA_LOCATIONS + GULF_LOCATIONS + SEA_LOCATIONS + ["Remote"]

# ════════════════════════════════════════════════════════════
#  SEARCH QUERIES — role keywords
# ════════════════════════════════════════════════════════════
ROLE_KEYWORDS = [
    "Software Engineer Intern",
    "Software Engineer Fresher",
    "Backend Developer Intern",
    "Backend Developer Fresher",
    "Java Developer Fresher",
    "Python Developer Fresher",
    "Full Stack Developer Fresher",
    "ML Engineer Intern",
    "AI Engineer Intern",
    "Cloud Engineer Intern",
    "DevOps Engineer Intern",
    "Spring Boot Developer",
    "Data Engineer Intern",
    "React Developer Fresher",
    "Graduate Software Engineer",
    "Entry Level Software Engineer",
    "Campus Hire Software Engineer",
    "Associate Software Engineer",
]

# ════════════════════════════════════════════════════════════
#  LINKEDIN POST QUERIES — "we are hiring" posts (not job listings)
# ════════════════════════════════════════════════════════════
LINKEDIN_POST_QUERIES = [
    # India hiring posts
    'site:linkedin.com/posts "we are hiring" "software engineer" "fresher" India',
    'site:linkedin.com/posts "freshers required" ("java" OR "python" OR "cloud") India',
    'site:linkedin.com/posts "hiring fresher" ("0-1 year" OR "0 to 1") India',
    'site:linkedin.com/posts "we are looking for" "software engineer" "fresher" India 2025',
    'site:linkedin.com/posts "campus hiring" OR "fresher drive" India 2025',
    'site:linkedin.com/posts "intern" "hiring" "software" India ("apply" OR "DM") 2025',
    'site:linkedin.com/posts "batch 2025" OR "batch 2026" "hiring" India software',
    'site:linkedin.com/posts "off campus" hiring India software engineer 2025',
    # Gulf hiring posts
    'site:linkedin.com/posts "we are hiring" "software engineer" Dubai 2025',
    'site:linkedin.com/posts "hiring" "developer" "fresher" OR "junior" Dubai UAE 2025',
    'site:linkedin.com/posts "we are hiring" "software" Singapore 2025',
    # Remote
    'site:linkedin.com/posts "remote" "we are hiring" "software engineer" "fresher" 2025',
    'site:linkedin.com/posts "work from home" "hiring" "developer" "fresher" India 2025',
    # LinkedIn company/activity pages
    'site:linkedin.com/company "hiring" "software engineer" "fresher" India 2025',
    'site:linkedin.com/in "hiring" "software engineer" "fresher" "DM me" India 2025',
]

# ════════════════════════════════════════════════════════════
#  GOOGLE JOBS QUERIES — finds jobs on ANY ATS via Google Jobs
#  (Workday, Greenhouse, Lever, Taleo, iCIMS, SAP, Naukri, etc.)
# ════════════════════════════════════════════════════════════
GOOGLE_JOBS_QUERIES = [
    # India
    ("software engineer intern", "India"),
    ("software engineer fresher", "India"),
    ("backend developer intern", "Bangalore, India"),
    ("java developer fresher 0-1 year", "India"),
    ("python developer fresher", "Hyderabad, India"),
    ("ml engineer intern", "India"),
    ("cloud engineer intern", "India"),
    ("devops intern", "India"),
    ("associate software engineer", "India"),
    ("graduate software engineer", "India"),
    # Gulf
    ("software engineer fresher", "Dubai, UAE"),
    ("software engineer intern", "Dubai"),
    ("junior developer", "Dubai UAE"),
    ("software engineer", "Doha, Qatar"),
    ("software engineer fresher", "Riyadh, Saudi Arabia"),
    # SEA
    ("software engineer intern", "Singapore"),
    ("junior software engineer", "Singapore"),
    ("software engineer fresher", "Kuala Lumpur, Malaysia"),
    # Remote
    ("remote software engineer intern", ""),
    ("remote backend developer fresher", ""),
    ("remote ml engineer intern", ""),
]

# ════════════════════════════════════════════════════════════
#  WEB SEARCH QUERIES — jobs on any career page via Google
# ════════════════════════════════════════════════════════════
WEB_JOB_QUERIES = [
    # ATS platforms — finds ANY company using them
    'site:greenhouse.io "software engineer" ("intern" OR "fresher") India',
    'site:lever.co "software engineer" ("intern" OR "junior") India',
    'site:jobs.lever.co "software engineer" ("intern" OR "junior") India',
    'site:myworkdayjobs.com "software engineer" intern India',
    'site:careers.smartrecruiters.com "software engineer" ("entry level" OR "intern") India',
    'site:icims.com "software engineer" ("intern" OR "entry level") India',
    'site:jobs.workable.com "software engineer" ("intern" OR "junior") India',
    'site:eightfold.ai "software engineer" ("intern" OR "fresher") India',
    'site:hiring.cafe "software engineer" ("intern" OR "fresher") India',
    'site:wellfound.com "software engineer" ("intern" OR "entry") India',
    # Gulf ATS
    'site:greenhouse.io "software engineer" ("intern" OR "junior") Dubai',
    'site:myworkdayjobs.com "software engineer" "Dubai" OR "Singapore"',
    # Indian job boards
    'site:naukri.com "software engineer" "fresher" "0-1 year" posted:"last 7 days"',
    'site:indeed.co.in "software engineer" "fresher" "0-1 year"',
    'site:shine.com "software engineer" "fresher"',
    'site:monster.com "software engineer" "fresher" India',
    'site:foundit.in "software engineer" "fresher" India',
    # Gulf job boards
    'site:bayt.com "software engineer" ("fresher" OR "junior" OR "intern") 2025',
    'site:gulftalent.com "software engineer" ("fresher" OR "junior") 2025',
    'site:naukrigulf.com "software engineer" "fresher" OR "0-1 year"',
    'site:dubizzle.com "software engineer" ("fresher" OR "intern") 2025',
    # Singapore / Malaysia
    'site:jobstreet.com "software engineer" ("junior" OR "intern" OR "fresh graduate") Singapore',
    'site:jobstreet.com.my "software engineer" ("junior" OR "fresh graduate") Malaysia',
    'site:jobsdb.com "software engineer" ("junior" OR "intern") Singapore',
    # Tech company career pages
    '"careers" "software engineer" "intern" 2025 India (site:amazon.jobs OR site:careers.google.com OR site:microsoft.com/jobs)',
    '"software engineer" "intern" OR "fresher" site:infosys.com/careers OR site:careers.tcs.com OR site:wipro.com/careers',
]

# ════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════
def now_utc():
    return datetime.now(timezone.utc)

def is_recent(date_str: str) -> bool:
    if not date_str:
        return True
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S+00:00", "%Y-%m-%d"):
        try:
            s = date_str[:19].replace("T", "T")
            dt = datetime.strptime(s, fmt[:len(s)])
            dt = dt.replace(tzinfo=timezone.utc)
            return (now_utc() - dt) <= timedelta(hours=LOOKBACK_HRS)
        except ValueError:
            continue
    return True

def safe_get(url, timeout=12, **kw):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, **kw)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"    ↳ GET error: {str(e)[:60]}")
        return None

def is_relevant(title: str) -> bool:
    t = title.lower()
    bad = ["senior", "sr.", " lead ", "principal", "staff engineer",
           "director", "manager", "head of", "architect", "vp ",
           "10+ yr", "8+ yr", "7+ yr", "5+ yr", "6+ yr",
           "10 years", "8 years", "7 years"]
    return not any(b in t for b in bad)

def make_job(title, company, location, link, source, posted="", jtype=""):
    return {
        "title":    str(title).strip()[:120],
        "company":  str(company).strip()[:80],
        "location": str(location).strip()[:80],
        "link":     str(link).strip(),
        "source":   source,
        "posted":   str(posted)[:10],
        "type":     str(jtype),
    }

def job_id(j):
    return hashlib.md5(
        f"{j['title'][:30].lower()}{j['company'][:20].lower()}".encode()
    ).hexdigest()

def dedupe(jobs):
    seen, out = set(), []
    for j in jobs:
        k = job_id(j)
        if k not in seen:
            seen.add(k)
            out.append(j)
    return out

def serpapi_search(query: str, engine="google", extra_params=None) -> dict:
    if not SERPAPI_KEY:
        return {}
    params = {"api_key": SERPAPI_KEY, "engine": engine, "q": query,
              "num": 10, "hl": "en"}
    if extra_params:
        params.update(extra_params)
    try:
        r = requests.get("https://serpapi.com/search", params=params, timeout=15)
        return r.json()
    except Exception as e:
        print(f"    ↳ SerpAPI error: {e}")
        return {}

# ════════════════════════════════════════════════════════════
#  SOURCE 1: JobSpy → LinkedIn Jobs, Indeed, Glassdoor
# ════════════════════════════════════════════════════════════
def fetch_jobspy():
    if not JOBSPY_OK:
        return []
    jobs = []
    search_sets = [
        # India
        [("Software Engineer Intern", "India"),
         ("Software Engineer Fresher", "India"),
         ("Backend Developer Fresher", "Bangalore"),
         ("ML Engineer Intern", "Hyderabad"),
         ("Java Developer Fresher", "India"),
         ("Python Developer Fresher", "India"),
         ("DevOps Intern", "India"),
         ("Associate Software Engineer", "India")],
        # Gulf
        [("Software Engineer Intern", "Dubai"),
         ("Junior Software Engineer", "UAE"),
         ("Software Engineer Fresher", "Singapore")],
    ]
    for group in search_sets:
        for query, loc in group:
            try:
                sites = ["linkedin", "indeed", "glassdoor"]
                df = scrape_jobs(
                    site_name=sites,
                    search_term=query,
                    location=loc,
                    results_wanted=15,
                    hours_old=LOOKBACK_HRS,
                    country_indeed="india" if "India" in loc or loc in INDIA_LOCATIONS else "worldwide",
                )
                if df is not None and not df.empty:
                    for _, r in df.iterrows():
                        t = str(r.get("title", ""))
                        if is_relevant(t):
                            jobs.append(make_job(
                                t, r.get("company", "N/A"),
                                r.get("location", loc),
                                r.get("job_url", "#"),
                                str(r.get("site", "")).capitalize(),
                                str(r.get("date_posted", "")),
                                str(r.get("job_type", "")),
                            ))
                time.sleep(2)
            except Exception as e:
                print(f"    ↳ JobSpy '{query}/{loc}': {e}")
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 2: Google Jobs via SerpAPI
#  → Crawls Workday, Greenhouse, Lever, Taleo, Naukri, etc.
# ════════════════════════════════════════════════════════════
def fetch_google_jobs():
    if not SERPAPI_KEY:
        print("    ↳ Skipping — SERPAPI_KEY not set (highly recommended)")
        return []
    jobs = []
    for query, location in GOOGLE_JOBS_QUERIES:
        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": SERPAPI_KEY,
            "chips": "date_posted:today",
            "hl": "en",
        }
        if location:
            params["location"] = location
        try:
            r = requests.get("https://serpapi.com/search", params=params, timeout=15)
            data = r.json()
            for j in data.get("jobs_results", [])[:8]:
                if not is_relevant(j.get("title", "")):
                    continue
                via = j.get("via", "")
                # Get the best apply link
                apply_link = "#"
                for opt in j.get("apply_options", []):
                    apply_link = opt.get("link", "#")
                    break
                if apply_link == "#":
                    apply_link = j.get("share_link", "#")
                jobs.append(make_job(
                    j.get("title"), j.get("company_name", "N/A"),
                    j.get("location", location or "Remote"),
                    apply_link,
                    f"Google Jobs ({via})" if via else "Google Jobs",
                    j.get("detected_extensions", {}).get("posted_at", ""),
                    j.get("detected_extensions", {}).get("schedule_type", ""),
                ))
            time.sleep(0.5)
        except Exception as e:
            print(f"    ↳ Google Jobs '{query}': {e}")
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 3: LinkedIn POSTS — "We are hiring" / "Freshers required"
#  This finds SOCIAL POSTS, not job listings
# ════════════════════════════════════════════════════════════
def fetch_linkedin_posts():
    jobs = []

    if SERPAPI_KEY:
        for q in LINKEDIN_POST_QUERIES:
            data = serpapi_search(q, engine="google", extra_params={"tbs": "qdr:d2"})
            for result in data.get("organic_results", []):
                link = result.get("link", "")
                if "linkedin.com" not in link:
                    continue
                title = result.get("title", "LinkedIn Hiring Post")
                snippet = result.get("snippet", "")
                # Extract company name from snippet or title
                company = "LinkedIn Post"
                if " | LinkedIn" in title:
                    company = title.split(" | LinkedIn")[0].strip()[:60]
                elif " - LinkedIn" in title:
                    company = title.split(" - LinkedIn")[0].strip()[:60]
                jobs.append(make_job(
                    snippet[:100] if snippet else title[:100],
                    company,
                    infer_location(title + " " + snippet),
                    link,
                    "LinkedIn Post 💼",
                    result.get("date", ""),
                ))
            time.sleep(0.8)

    elif GFREE_OK:
        for q in LINKEDIN_POST_QUERIES[:6]:
            try:
                for url in google_free_search(q, num_results=5, sleep_interval=3):
                    if "linkedin.com" in url:
                        jobs.append(make_job(
                            "LinkedIn Hiring Post — click link for details",
                            "LinkedIn Post",
                            "India / Various",
                            url,
                            "LinkedIn Post 💼",
                        ))
            except Exception as e:
                print(f"    ↳ LinkedIn posts (free search): {e}")
    return jobs

def infer_location(text: str) -> str:
    text_l = text.lower()
    for city in ["bangalore", "hyderabad", "chennai", "mumbai", "pune", "delhi",
                 "gurgaon", "noida", "kochi", "kolkata", "dubai", "singapore",
                 "malaysia", "qatar", "riyadh", "remote"]:
        if city in text_l:
            return city.title()
    return "India / Various"

# ════════════════════════════════════════════════════════════
#  SOURCE 4: Web-wide search for jobs on ANY ATS / job board
# ════════════════════════════════════════════════════════════
def fetch_web_job_search():
    """Use Google search to find jobs on any site: Greenhouse, Lever,
       Workday, Workable, Eightfold, Naukri, Bayt, JobStreet, etc."""
    if not SERPAPI_KEY and not GFREE_OK:
        return []
    jobs = []

    if SERPAPI_KEY:
        for q in WEB_JOB_QUERIES:
            data = serpapi_search(q, extra_params={"tbs": "qdr:w"})  # last week
            for res in data.get("organic_results", []):
                link = res.get("link", "#")
                title = res.get("title", "Job Opening")
                snippet = res.get("snippet", "")
                source_name = detect_ats_source(link)
                if not is_relevant(title):
                    continue
                company = extract_company_from_snippet(title, snippet, link)
                jobs.append(make_job(
                    clean_job_title(title),
                    company,
                    infer_location(title + " " + snippet),
                    link,
                    source_name,
                    res.get("date", ""),
                ))
            time.sleep(0.6)
    elif GFREE_OK:
        for q in WEB_JOB_QUERIES[:8]:
            try:
                for url in google_free_search(q, num_results=5, sleep_interval=3):
                    jobs.append(make_job(
                        "Job Opening — click to view",
                        detect_ats_source(url),
                        "India / Various",
                        url,
                        detect_ats_source(url),
                    ))
            except Exception as e:
                print(f"    ↳ Web search: {e}")
    return jobs

def detect_ats_source(url: str) -> str:
    u = url.lower()
    mapping = [
        ("greenhouse.io",          "Greenhouse ATS"),
        ("lever.co",               "Lever ATS"),
        ("myworkdayjobs.com",       "Workday ATS"),
        ("smartrecruiters.com",    "SmartRecruiters"),
        ("workable.com",           "Workable ATS"),
        ("eightfold.ai",           "Eightfold AI"),
        ("taleo.net",              "Taleo ATS"),
        ("icims.com",              "iCIMS ATS"),
        ("jobs.sap.com",           "SAP Careers"),
        ("wellfound.com",          "Wellfound"),
        ("naukri.com",             "Naukri"),
        ("indeed.",                "Indeed"),
        ("linkedin.com/jobs",      "LinkedIn Jobs"),
        ("glassdoor.",             "Glassdoor"),
        ("bayt.com",               "Bayt (Gulf)"),
        ("naukrigulf.com",         "NaukriGulf"),
        ("gulftalent.com",         "GulfTalent"),
        ("jobstreet.",             "JobStreet (SEA)"),
        ("jobsdb.com",             "JobsDB (SEA)"),
        ("foundit.in",             "foundit"),
        ("monster.",               "Monster"),
        ("shine.com",              "Shine"),
        ("internshala.com",        "Internshala 🎓"),
        ("amazon.jobs",            "Amazon Careers"),
        ("careers.google.",        "Google Careers"),
        ("microsoft.com",          "Microsoft Careers"),
        ("meta.com",               "Meta Careers"),
        ("apple.com/careers",      "Apple Careers"),
    ]
    for pattern, name in mapping:
        if pattern in u:
            return name
    return "Company Career Page"

def clean_job_title(title: str) -> str:
    for remove in [" | LinkedIn", " - LinkedIn", " - Indeed", " - Glassdoor",
                   " | Naukri", " | Greenhouse", " | Lever"]:
        title = title.replace(remove, "")
    return title.strip()[:100]

def extract_company_from_snippet(title: str, snippet: str, link: str) -> str:
    for sep in [" at ", " @ ", " | "]:
        if sep in title:
            parts = title.split(sep)
            if len(parts) > 1:
                return parts[-1].strip()[:60]
    try:
        from urllib.parse import urlparse
        domain = urlparse(link).netloc.replace("www.", "")
        parts = domain.split(".")
        return parts[0].title()[:40]
    except Exception:
        return "N/A"

# ════════════════════════════════════════════════════════════
#  SOURCE 5: JSearch API via RapidAPI (free tier: 200 req/month)
#  Best Google Jobs alternative — no SerpAPI needed
# ════════════════════════════════════════════════════════════
def fetch_jsearch():
    if not JSEARCH_KEY:
        return []
    jobs = []
    queries = [
        ("software engineer intern", "India"),
        ("software engineer fresher", "India"),
        ("backend developer fresher", "India"),
        ("ml engineer intern", "India"),
        ("software engineer intern", "Dubai"),
        ("software engineer intern", "Singapore"),
        ("remote software engineer intern", ""),
    ]
    for query, country in queries:
        try:
            r = requests.get(
                "https://jsearch.p.rapidapi.com/search",
                headers={
                    "X-RapidAPI-Key": JSEARCH_KEY,
                    "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
                },
                params={
                    "query": f"{query} {country}".strip(),
                    "page": "1",
                    "num_pages": "1",
                    "date_posted": "today",
                    "employment_types": "INTERN,FULLTIME",
                    "job_requirements": "under_3_years_experience,no_experience",
                },
                timeout=15,
            )
            for j in r.json().get("data", []):
                title = j.get("job_title", "")
                if not is_relevant(title):
                    continue
                jobs.append(make_job(
                    title,
                    j.get("employer_name", "N/A"),
                    f"{j.get('job_city','')}, {j.get('job_country','')}".strip(", "),
                    j.get("job_apply_link") or j.get("job_google_link", "#"),
                    f"JSearch ({j.get('job_publisher', 'various')})",
                    j.get("job_posted_at_datetime_utc", "")[:10],
                    j.get("job_employment_type", ""),
                ))
            time.sleep(0.5)
        except Exception as e:
            print(f"    ↳ JSearch '{query}': {e}")
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 6: Adzuna — India + Gulf + Singapore
# ════════════════════════════════════════════════════════════
def fetch_adzuna():
    if not ADZUNA_ID:
        return []
    jobs = []
    country_map = [
        ("in", "India",         ROLE_KEYWORDS[:6]),
        ("ae", "UAE/Dubai",     ROLE_KEYWORDS[:3]),
        ("sg", "Singapore",     ROLE_KEYWORDS[:3]),
        ("gb", "Remote/Global", ["software engineer intern", "backend developer"]),
    ]
    for country_code, label, queries in country_map:
        for q in queries:
            url = (
                f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1"
                f"?app_id={ADZUNA_ID}&app_key={ADZUNA_KEY}"
                f"&results_per_page=15&what={requests.utils.quote(q)}"
                f"&max_days_old=1&content-type=application/json"
            )
            r = safe_get(url)
            if r:
                for j in r.json().get("results", []):
                    if is_relevant(j.get("title", "")):
                        jobs.append(make_job(
                            j.get("title"), j.get("company", {}).get("display_name", "N/A"),
                            j.get("location", {}).get("display_name", label),
                            j.get("redirect_url", "#"), "Adzuna",
                            j.get("created", ""),
                        ))
        time.sleep(0.5)
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 7: Free Job Board APIs (Remotive, Jobicy, Arbeitnow, The Muse)
# ════════════════════════════════════════════════════════════
def fetch_remotive():
    jobs = []
    for tag in ["java", "python", "machine-learning", "backend", "devops", "cloud", "spring"]:
        r = safe_get(f"https://remotive.com/api/remote-jobs?category=software-dev&search={tag}&limit=10")
        if r:
            for j in r.json().get("jobs", []):
                if is_recent(j.get("publication_date", "")) and is_relevant(j.get("title", "")):
                    jobs.append(make_job(
                        j.get("title"), j.get("company_name"),
                        "Remote", j.get("url", "#"), "Remotive 🌍",
                        j.get("publication_date", ""), j.get("job_type", ""),
                    ))
    return jobs

def fetch_jobicy():
    jobs = []
    for tag in ["java", "python", "cloud", "backend", "ml"]:
        r = safe_get(f"https://jobicy.com/api/v2/remote-jobs?tag={tag}&count=10")
        if r:
            for j in r.json().get("jobs", []):
                if is_relevant(j.get("jobTitle", "")):
                    jobs.append(make_job(
                        j.get("jobTitle"), j.get("companyName"),
                        j.get("jobGeo", "Remote"), j.get("url", "#"),
                        "Jobicy 🌍", j.get("pubDate", ""),
                    ))
    return jobs

def fetch_arbeitnow():
    jobs = []
    r = safe_get("https://arbeitnow.com/api/job-board-api?page=1")
    if r:
        for j in r.json().get("data", [])[:40]:
            title = j.get("title", "")
            tags  = " ".join(j.get("tags", [])).lower()
            if is_relevant(title) and any(
                kw in tags for kw in ["java", "python", "cloud", "ml", "backend", "devops"]
            ):
                jobs.append(make_job(
                    title, j.get("company_name"),
                    j.get("location", "Remote"), j.get("url", "#"),
                    "Arbeitnow 🌍", j.get("created_at", ""),
                ))
    return jobs

def fetch_the_muse():
    jobs = []
    for cat in ["Engineering", "Data+Science"]:
        r = safe_get(
            f"https://www.themuse.com/api/public/jobs?category={cat}"
            f"&level=Entry+Level&level=Internship&page=1&descending=true"
        )
        if r:
            for j in r.json().get("results", []):
                locs = ", ".join(l.get("name", "") for l in j.get("locations", []))
                jobs.append(make_job(
                    j.get("name"), j.get("company", {}).get("name", "N/A"),
                    locs or "Remote/Various",
                    j.get("refs", {}).get("landing_page", "#"),
                    "The Muse", j.get("publication_date", ""),
                ))
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 8: Internshala (India #1 intern platform)
# ════════════════════════════════════════════════════════════
def fetch_internshala():
    jobs = []
    pages = [
        "computer-science-engineering-internship",
        "machine-learning-internship",
        "java-internship",
        "python-internship",
        "cloud-computing-internship",
        "work-from-home-computer-science-engineering-internship",
    ]
    for page in pages:
        r = safe_get(f"https://internshala.com/internships/{page}")
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".individual_internship")[:10]:
            try:
                title   = card.select_one(".profile h3, .profile .job-title-href")
                company = card.select_one(".company_name a, .company-name")
                loc     = card.select_one(".location_link span, .location-link")
                link_el = card.select_one("a.view_detail_button, a[href*='/internship/detail']")
                if title and link_el:
                    href = link_el.get("href", "")
                    jobs.append(make_job(
                        title.get_text(strip=True),
                        company.get_text(strip=True) if company else "N/A",
                        loc.get_text(strip=True) if loc else "India",
                        href if href.startswith("http") else f"https://internshala.com{href}",
                        "Internshala 🎓",
                    ))
            except Exception:
                pass
        time.sleep(1)
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 9: Wellfound / AngelList (startups globally)
# ════════════════════════════════════════════════════════════
def fetch_wellfound():
    jobs = []
    urls = [
        "https://wellfound.com/role/l/software-engineer/india",
        "https://wellfound.com/role/l/software-engineer/singapore",
        "https://wellfound.com/role/l/software-engineer/dubai",
    ]
    for url in urls:
        r = safe_get(url)
        if not r:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select("[data-test='StartupResult']")[:10]:
            try:
                co   = card.select_one("[data-test='startup-link']")
                roles = card.select("[data-test='role']")
                for role in roles:
                    title = role.get_text(strip=True)
                    if is_relevant(title):
                        jobs.append(make_job(
                            title,
                            co.get_text(strip=True) if co else "Startup",
                            url.split("/")[-1].title(),
                            "https://wellfound.com" + (co.get("href", "") if co else ""),
                            "Wellfound 🚀",
                        ))
            except Exception:
                pass
        time.sleep(1)
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 10: Greenhouse + Lever broad search
#  (no hardcoded companies — search by keyword across ALL boards)
# ════════════════════════════════════════════════════════════
def fetch_greenhouse_broad():
    """Search Greenhouse's job API without knowing company names."""
    if not SERPAPI_KEY:
        return []
    jobs = []
    queries = [
        'site:boards.greenhouse.io "software engineer" ("intern" OR "fresher" OR "entry level") India',
        'site:boards.greenhouse.io "software engineer" ("intern" OR "junior") (Dubai OR Singapore)',
        'site:boards.greenhouse.io "machine learning" ("intern" OR "entry level")',
        'site:boards.greenhouse.io "backend" ("intern" OR "junior" OR "new grad")',
    ]
    for q in queries:
        data = serpapi_search(q, extra_params={"tbs": "qdr:w"})
        for res in data.get("organic_results", []):
            link = res.get("link", "#")
            title = clean_job_title(res.get("title", "Job Opening"))
            if is_relevant(title):
                snippet = res.get("snippet", "")
                jobs.append(make_job(
                    title,
                    extract_company_from_snippet(title, snippet, link),
                    infer_location(title + " " + snippet),
                    link, "Greenhouse ATS",
                    res.get("date", ""),
                ))
        time.sleep(0.5)
    return jobs

def fetch_lever_broad():
    if not SERPAPI_KEY:
        return []
    jobs = []
    queries = [
        'site:jobs.lever.co "software engineer" ("intern" OR "fresher" OR "junior") India',
        'site:jobs.lever.co "software engineer" ("intern" OR "junior") (Dubai OR Singapore)',
        'site:jobs.lever.co "backend" OR "machine learning" ("intern" OR "entry level")',
    ]
    for q in queries:
        data = serpapi_search(q, extra_params={"tbs": "qdr:w"})
        for res in data.get("organic_results", []):
            link = res.get("link", "#")
            title = clean_job_title(res.get("title", "Job Opening"))
            if is_relevant(title):
                snippet = res.get("snippet", "")
                jobs.append(make_job(
                    title,
                    extract_company_from_snippet(title, snippet, link),
                    infer_location(title + " " + snippet),
                    link, "Lever ATS",
                    res.get("date", ""),
                ))
        time.sleep(0.5)
    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 11: Hacker News — Who's Hiring
# ════════════════════════════════════════════════════════════
def fetch_hn_hiring():
    jobs = []
    try:
        r = requests.get(
            "https://hn.algolia.com/api/v1/search?query=Ask+HN+Who+is+hiring"
            "&tags=story&hitsPerPage=5", timeout=10
        )
        hits = r.json().get("hits", [])
        story = next(
            (h for h in hits if "who is hiring" in h.get("title", "").lower()
             and h.get("author") == "whoishiring"), None
        )
        if not story:
            return []
        sid = story.get("objectID")
        r2 = requests.get(
            f"https://hn.algolia.com/api/v1/search?tags=comment,story_{sid}"
            f"&hitsPerPage=100", timeout=10
        )
        kws = ["intern", "junior", "entry level", "fresher", "india",
               "dubai", "singapore", "remote", "java", "python", "backend"]
        for c in r2.json().get("hits", []):
            text = re.sub(r"<[^>]+>", "", c.get("comment_text", ""))
            tl = text.lower()
            if sum(1 for k in kws if k in tl) >= 2:
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                preview = lines[0][:120] if lines else text[:120]
                jobs.append(make_job(
                    preview, "HN Poster", "Remote / Various",
                    f"https://news.ycombinator.com/item?id={c.get('objectID','')}",
                    "Hacker News 🟠", c.get("created_at", ""),
                ))
    except Exception as e:
        print(f"    ↳ HN: {e}")
    return jobs[:12]

# ════════════════════════════════════════════════════════════
#  SOURCE 12: Gulf-specific job boards
# ════════════════════════════════════════════════════════════
def fetch_gulf_boards():
    jobs = []

    # Bayt.com
    for keyword in ["software engineer intern", "junior developer", "software engineer fresher"]:
        r = safe_get(
            f"https://www.bayt.com/en/international/jobs/{keyword.replace(' ', '-')}-jobs/",
        )
        if r:
            soup = BeautifulSoup(r.text, "html.parser")
            for card in soup.select("[data-js-aid='jobTitle']")[:10]:
                try:
                    title = card.get_text(strip=True)
                    link_el = card.find("a")
                    link = ("https://www.bayt.com" + link_el["href"]) if link_el else "#"
                    jobs.append(make_job(title, "N/A", "Gulf / MENA", link, "Bayt.com 🇦🇪"))
                except Exception:
                    pass
        time.sleep(1)

    return jobs

# ════════════════════════════════════════════════════════════
#  SOURCE 13: SEA job boards (JobStreet)
# ════════════════════════════════════════════════════════════
def fetch_sea_boards():
    jobs = []
    for country, url_base in [
        ("Singapore", "https://www.jobstreet.com.sg/en/job-search/software-engineer-jobs/"),
        ("Malaysia",  "https://www.jobstreet.com.my/en/job-search/software-engineer-jobs/"),
    ]:
        r = safe_get(url_base)
        if r:
            soup = BeautifulSoup(r.text, "html.parser")
            for card in soup.select("[data-automation='job-card-title']")[:10]:
                try:
                    title = card.get_text(strip=True)
                    link_el = card.find("a")
                    href = link_el.get("href", "#") if link_el else "#"
                    link = href if href.startswith("http") else url_base + href
                    if is_relevant(title):
                        jobs.append(make_job(title, "N/A", country, link, f"JobStreet ({country})"))
                except Exception:
                    pass
        time.sleep(1)
    return jobs

# ════════════════════════════════════════════════════════════
#  EMAIL BUILDER
# ════════════════════════════════════════════════════════════
GEO_SECTIONS = [
    ("🇮🇳 India",                  INDIA_LOCATIONS + ["india", "N/A", "India / Various"]),
    ("🇦🇪 Gulf (UAE · Qatar · Saudi)", ["dubai", "abu dhabi", "uae", "sharjah", "doha",
                                         "qatar", "riyadh", "jeddah", "saudi", "gulf", "mena"]),
    ("🌏 Singapore & Malaysia",    ["singapore", "kuala lumpur", "malaysia"]),
    ("🌍 Remote / Global",         ["remote", "worldwide", "global", "various"]),
]

SOURCE_COLORS = {
    "LinkedIn":             "#0077B5",
    "Indeed":               "#003A9B",
    "Glassdoor":            "#0CAA41",
    "Adzuna":               "#E85D26",
    "Remotive":             "#13B2A2",
    "The Muse":             "#FF6B6B",
    "Arbeitnow":            "#7C3AED",
    "Jobicy":               "#059669",
    "Greenhouse":           "#26a65b",
    "Lever":                "#1a1a2e",
    "SmartRecruiters":      "#e74c3c",
    "Workday":              "#0875e1",
    "Internshala":          "#fc5c65",
    "Wellfound":            "#fb7a37",
    "Hacker News":          "#ff6600",
    "LinkedIn Post":        "#0077B5",
    "Google Jobs":          "#4285F4",
    "JSearch":              "#34a853",
    "Bayt":                 "#1B4F72",
    "JobStreet":            "#E74C3C",
    "Company Career":       "#6C63FF",
    "Naukri":               "#FF7555",
}

def get_color(source: str) -> str:
    for k, v in SOURCE_COLORS.items():
        if k.lower() in source.lower():
            return v
    return "#6C63FF"

def tag(text: str, color: str = "#6C63FF") -> str:
    return (f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:10px;'
            f'font-size:10px;font-weight:600;white-space:nowrap;">{text}</span>')

def build_card(j: dict) -> str:
    color = get_color(j["source"])
    posted = f'<span style="color:#999;font-size:11px;">⏰ {j["posted"]}</span>' if j.get("posted") else ""
    return f"""
<div style="background:#fff;border:1px solid #edf0f5;border-left:3px solid {color};
            border-radius:8px;padding:14px 16px;margin-bottom:10px;">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap;">
    <div style="flex:1;min-width:0;">
      <p style="margin:0 0 3px;font-weight:700;font-size:14px;color:#1a202c;line-height:1.3;">{j['title']}</p>
      <p style="margin:0;font-size:12px;color:#64748b;">
        🏢 {j['company']} &nbsp;·&nbsp; 📍 {j['location']}
      </p>
    </div>
    {tag(j['source'], color)}
  </div>
  <div style="margin-top:10px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    <a href="{j['link']}"
       style="background:{color};color:#fff;padding:6px 14px;border-radius:6px;
              text-decoration:none;font-size:12px;font-weight:700;display:inline-block;">
      Apply / View Post →
    </a>
    {posted}
  </div>
</div>"""

def categorize_by_geo(jobs: list) -> dict:
    sections = {s[0]: [] for s in GEO_SECTIONS}
    sections["🌍 Remote / Global"] = []
    for j in jobs:
        loc = j["location"].lower()
        src = j["source"].lower()
        placed = False
        for section_name, loc_kws in GEO_SECTIONS:
            if any(kw.lower() in loc for kw in loc_kws):
                sections[section_name].append(j)
                placed = True
                break
        if not placed:
            # LinkedIn posts / web results with no clear geo → India default
            if "linkedin post" in src or "india" in src:
                sections["🇮🇳 India"].append(j)
            else:
                sections["🌍 Remote / Global"].append(j)
    return sections

def build_source_summary(jobs: list) -> str:
    counts = {}
    for j in jobs:
        counts[j["source"]] = counts.get(j["source"], 0) + 1
    items = sorted(counts.items(), key=lambda x: -x[1])
    pills = "".join(
        f'<span style="display:inline-block;background:#f1f5f9;border:1px solid #e2e8f0;'
        f'color:#475569;padding:3px 10px;border-radius:20px;font-size:11px;margin:3px 2px;">'
        f'{src} <strong>{cnt}</strong></span>'
        for src, cnt in items
    )
    return pills

def build_email(jobs: list, run_time: str, cycle_num: int) -> str:
    sections = categorize_by_geo(jobs)
    body = ""
    for section_name, section_jobs in sections.items():
        if not section_jobs:
            continue
        cards = "".join(build_card(j) for j in section_jobs)
        body += f"""
<div style="margin-bottom:28px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;
              padding-bottom:8px;border-bottom:2px solid #e8ecf3;">
    <h2 style="margin:0;font-size:16px;color:#1e293b;">{section_name}</h2>
    <span style="background:#e8ecf3;color:#64748b;padding:2px 10px;border-radius:20px;
                 font-size:12px;font-weight:600;">{len(section_jobs)} jobs</span>
  </div>
  {cards}
</div>"""

    if not jobs:
        body = '<p style="color:#94a3b8;text-align:center;padding:40px;">No new jobs this cycle — try again in 6 hours.</p>'

    cycle_labels = {1: "🌅 Morning", 2: "☀️ Afternoon", 3: "🌆 Evening", 4: "🌙 Night"}
    cycle_label = cycle_labels.get(cycle_num, "🕐 Update")

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:680px;margin:0 auto;padding:20px 12px;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 50%,#0c4a6e 100%);
              border-radius:16px;padding:28px 24px;text-align:center;margin-bottom:18px;">
    <div style="font-size:13px;color:rgba(255,255,255,0.6);margin-bottom:6px;">{cycle_label} Digest · {run_time}</div>
    <h1 style="margin:0 0 10px;color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">
      🎯 Job Hunt Report
    </h1>
    <div style="display:inline-flex;gap:12px;flex-wrap:wrap;justify-content:center;margin-top:8px;">
      <span style="background:rgba(255,255,255,0.15);color:#fff;padding:5px 14px;border-radius:20px;font-size:13px;">
        🇮🇳 India
      </span>
      <span style="background:rgba(255,255,255,0.15);color:#fff;padding:5px 14px;border-radius:20px;font-size:13px;">
        🇦🇪 Gulf
      </span>
      <span style="background:rgba(255,255,255,0.15);color:#fff;padding:5px 14px;border-radius:20px;font-size:13px;">
        🌏 SEA
      </span>
      <span style="background:rgba(255,255,255,0.15);color:#fff;padding:5px 14px;border-radius:20px;font-size:13px;">
        🌍 Remote
      </span>
    </div>
    <div style="margin-top:16px;background:rgba(255,255,255,0.12);border-radius:10px;
                padding:12px;display:inline-block;">
      <span style="color:#fff;font-size:32px;font-weight:800;">{len(jobs)}</span>
      <span style="color:rgba(255,255,255,0.7);font-size:14px;"> new opportunities</span>
    </div>
  </div>

  <!-- Source Breakdown -->
  <div style="background:#fff;border-radius:10px;padding:14px 16px;margin-bottom:18px;
              border:1px solid #e2e8f0;">
    <p style="margin:0 0 8px;font-size:12px;font-weight:700;color:#64748b;text-transform:uppercase;
              letter-spacing:0.5px;">📡 Sources Searched</p>
    {build_source_summary(jobs)}
  </div>

  <!-- Geo Sections -->
  {body}

  <!-- Footer -->
  <div style="text-align:center;padding:20px 0;color:#94a3b8;font-size:11px;
              border-top:1px solid #e2e8f0;margin-top:10px;">
    <p style="margin:0 0 4px;">
      LinkedIn Posts · Google Jobs · JobSpy · Adzuna · JSearch · Greenhouse · Lever ·
      Internshala · Wellfound · Remotive · Arbeitnow · Jobicy · The Muse · Bayt · JobStreet · HN
    </p>
    <p style="margin:4px 0 0;color:#cbd5e1;">Next digest in 6 hours · Tailored for Santhosh Kumar S P</p>
  </div>

</div>
</body></html>"""

# ════════════════════════════════════════════════════════════
#  SEND EMAIL
# ════════════════════════════════════════════════════════════
def send_email(subject: str, html: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, RECIPIENT, msg.as_string())
    print(f"  ✓ Email sent → {RECIPIENT}")

# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
ALL_SOURCES = [
    ("JobSpy — LinkedIn · Indeed · Glassdoor",      fetch_jobspy),
    ("Google Jobs (SerpAPI)",                        fetch_google_jobs),
    ("LinkedIn Hiring Posts",                        fetch_linkedin_posts),
    ("Web-wide ATS Search (Google)",                 fetch_web_job_search),
    ("JSearch (RapidAPI)",                           fetch_jsearch),
    ("Remotive",                                     fetch_remotive),
    ("Jobicy",                                       fetch_jobicy),
    ("Arbeitnow",                                    fetch_arbeitnow),
    ("The Muse",                                     fetch_the_muse),
    ("Internshala 🎓",                               fetch_internshala),
    ("Wellfound 🚀",                                 fetch_wellfound),
    ("Greenhouse (broad Google search)",             fetch_greenhouse_broad),
    ("Lever (broad Google search)",                  fetch_lever_broad),
    ("Gulf Boards (Bayt)",                           fetch_gulf_boards),
    ("SEA Boards (JobStreet)",                       fetch_sea_boards),
    ("Hacker News — Who's Hiring",                   fetch_hn_hiring),
]

def main():
    run_time = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%d %b %Y · %I:%M %p IST")
    hour = datetime.now(timezone(timedelta(hours=5, minutes=30))).hour
    cycle    = 1 if 5<=hour<11 else 2 if 11<=hour<17 else 3 if 17<=hour<23 else 4

    print(f"\n{'═'*58}")
    print(f"  GLOBAL JOB HUNTER v3 — {run_time}")
    print(f"{'═'*58}\n")

    all_jobs = []
    for name, fn in ALL_SOURCES:
        print(f"[→] {name}")
        try:
            results = fn()
            print(f"    ✓ {len(results)} jobs")
            all_jobs.extend(results)
        except Exception as e:
            print(f"    ✗ Error: {e}")

    all_jobs = dedupe(all_jobs)
    print(f"\n  ─────────────────────────────────")
    print(f"  Total unique jobs: {len(all_jobs)}")
    print(f"  ─────────────────────────────────\n")

    html    = build_email(all_jobs, run_time, cycle)
    subject = (
        f"🎯 {len(all_jobs)} Jobs | "
        f"India · Gulf · SEA · Remote | "
        f"{datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime('%d %b %Y %I:%M %p IST')}"
    )
    send_email(subject, html)

if __name__ == "__main__":
    main()
