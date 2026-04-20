# 🎯 Global Job Hunter v3.0

**17 sources · 4 geographies · Every 6 hours · Every company's ATS**

---

## 🔑 Quick Setup (15 min)

### Step 1 — GitHub Repo
```bash
mkdir job-hunter && cd job-hunter
# Copy all files (keep .github/workflows/ folder structure)
git init && git add . && git commit -m "init"
git remote add origin https://github.com/YOUR_USERNAME/job-hunter.git
git push -u origin main
```

### Step 2 — Gmail App Password
1. Enable 2FA: https://myaccount.google.com/security
2. Create App Password: https://myaccount.google.com/apppasswords
3. App: Mail, Device: Other ("JobHunter") → copy 16-char password

### Step 3 — GitHub Secrets
Repo → Settings → Secrets and variables → Actions:

| Secret | How to get | Required? |
|--------|-----------|-----------|
| `GMAIL_USER` | your Gmail | ✅ |
| `GMAIL_PASSWORD` | App Password from Step 2 | ✅ |
| `RECIPIENT_EMAIL` | santhoshkumarsp222004@gmail.com | ✅ |
| `SERPAPI_KEY` | serpapi.com → free 100/mo trial | ⭐ Highly recommended |
| `JSEARCH_KEY` | rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch → Subscribe free tier | ⭐ Recommended |
| `ADZUNA_APP_ID` | developer.adzuna.com → free | 👍 Optional |
| `ADZUNA_API_KEY` | developer.adzuna.com → free | 👍 Optional |

### Step 4 — Enable & Test
- Repo → Actions tab → "I understand my workflows, go ahead"
- Click **"Run workflow"** → manually trigger to test immediately

---

## 📡 All 17 Sources

### Job Boards
| Source | Coverage |
|--------|---------|
| **LinkedIn Jobs** | via JobSpy — most comprehensive |
| **Indeed** | India + Global via JobSpy |
| **Glassdoor** | via JobSpy |
| **Adzuna** | India, UAE, Singapore, UK |
| **Remotive** | Remote tech jobs |
| **Jobicy** | Remote dev jobs |
| **Arbeitnow** | Remote + EU |
| **The Muse** | Entry-level focus |
| **Internshala 🎓** | India's #1 intern platform |
| **Wellfound 🚀** | Startups — India, Dubai, Singapore |

### ATS Platforms (Any Company, Not Hardcoded)
| Source | What it finds |
|--------|--------------|
| **Google Jobs (SerpAPI)** | Aggregates Workday, Naukri, iCIMS, Taleo, greenhouse, lever — ANY ATS |
| **Greenhouse** (Google search) | `site:boards.greenhouse.io` — finds ALL companies using Greenhouse |
| **Lever** (Google search) | `site:jobs.lever.co` — finds ALL companies using Lever |
| **Web-wide ATS search** | Eightfold, Workable, SmartRecruiters, Naukri, Bayt, JobStreet, etc. |
| **JSearch (RapidAPI)** | Real-time Google Jobs index — backup to SerpAPI |

### Social & Community
| Source | What it finds |
|--------|--------------|
| **LinkedIn Posts** 💼 | "We are hiring" / "freshers required" / "batch 2025" social posts |
| **Hacker News** 🟠 | Monthly "Who's Hiring" thread |

### Regional Boards
| Source | Coverage |
|--------|---------|
| **Bayt.com** | UAE, Saudi, Qatar, Kuwait |
| **JobStreet** | Singapore, Malaysia |
| **NaukriGulf** | via web search |

---

## ⏰ Email Schedule (IST)

| Time | Label |
|------|-------|
| 6:00 AM | 🌅 Morning Digest |
| 12:00 PM | ☀️ Afternoon Digest |
| 6:00 PM | 🌆 Evening Digest |
| 12:00 AM | 🌙 Night Digest |

---

## 🌍 Geographies Covered

- **🇮🇳 India**: Bangalore, Hyderabad, Chennai, Mumbai, Pune, Delhi/NCR, Kochi, Kolkata, Ahmedabad, Jaipur
- **🇦🇪 Gulf**: Dubai, Abu Dhabi, Sharjah, Qatar/Doha, Riyadh, Jeddah, Saudi Arabia
- **🌏 SEA**: Singapore, Kuala Lumpur, Malaysia
- **🌍 Remote**: Any remote-first role globally

---

## 💡 Pro Tips

**To add LinkedIn searching without SerpAPI**, the free `googlesearch-python`
library is already included as fallback (slower, may hit rate limits).

**SerpAPI free trial** gives 100 searches/month — enough for ~4 cycles/day
if you limit queries. After trial it's $50/mo. For heavy use, **JSearch on
RapidAPI** has a free tier of 200 calls/month.

**To test just one source**, comment out others in `ALL_SOURCES` list at the bottom.

**To add a company's ATS manually** (e.g. Greenhouse):
- Visit https://boards.greenhouse.io/{company-token}
- Add the token to `GREENHOUSE_COMPANIES` in the old v2 script
- Or just let Google search find them automatically via v3

---

## ⚠️ Notes

- All scraping is for personal use only
- LinkedIn rate-limits aggressively — JobSpy handles retries automatically
- Workday URLs vary per company — Google Jobs handles this transparently
- Run from a **private** GitHub repo to protect your secrets
