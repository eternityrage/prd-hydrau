# Hydraulic Press ASMR (prd-hydrau)

Automated content pipeline for **ASMR Hydraulic Press & Fruit Juice Extraction** videos — publishing high-retention Reels, Stories, and Pinned Comments across multiple Facebook Pages.

## What it does

1. **Fetches** satisfying fruit-crushing videos from Google Drive (`1NbBvT_JHzlPaG83U6f5aSNFdyNqbNgjn`).
2. **Processes** them using FFmpeg (vertical 1080x1920 9:16 aspect ratio, unsharp sharpening, and loudness normalization for ultra-crisp ASMR crunch and juice extraction sounds).
3. **Generates SEO Captions** using Pollinations AI (detects fruit/item from filename and crafts viral, high-retention titles, descriptions, and hashtags like `#hydraulicpress #asmr #oddlysatisfying #fruitjuice`).
4. **Publishes to Multiple Facebook Pages**:
   - Publishes **Facebook Reels** (with auto video transfer & container finalization).
   - Posts a **Pinned Comment** containing the title/description and future custom link placeholder.
   - Publishes **Facebook Stories** (24h story format).
5. **Multi-Page & Meta Token Support**: Automatically derives page access tokens for all chosen Facebook pages from `META_LONG_LIVED_ACCESS_TOKEN`.
6. **Instagram Support**: Automatically publishes to Instagram when `INSTAGRAM_ACCOUNT_ID` is provided.

---

## Setup & Configuration

### GitHub Secrets

| Secret | Required | Description |
|---|---|---|
| `META_LONG_LIVED_ACCESS_TOKEN` | Yes | Meta long-lived user access token (resolves page tokens dynamically) |
| `TARGET_FB_PAGE_IDS` | Recommended | Comma-separated list of 5-6 target Facebook Page IDs |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Yes | Google Service Account JSON credentials |
| `GOOGLE_DRIVE_FOLDER_ID` | Yes | Google Drive folder ID containing raw videos (`1NbBvT_JHzlPaG83U6f5aSNFdyNqbNgjn`) |
| `POLLINATIONS_API_KEY` | Optional | Pollinations AI key for dynamic SEO ASMR caption generation |
| `PINNED_COMMENT_LINK` | Optional | Link / URL to append inside the pinned comment |
| `FB_PAGE_ID` | Optional | Single page fallback ID |
| `FB_PAGE_ACCESS_TOKEN` | Optional | Single page fallback access token |
| `INSTAGRAM_ACCOUNT_ID` | Optional | Instagram professional account ID |

---

## Automation Schedule

The pipeline runs automatically **3 times daily** via GitHub Actions:
- **04:00 UTC**
- **12:00 UTC**
- **20:00 UTC**

It can also be manually triggered anytime via GitHub Actions **Run workflow** button (`workflow_dispatch`).

---

## Local Development

```bash
# Clone the repository
git clone https://github.com/eternityrage/prd-hydrau.git
cd prd-hydrau

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env

# Run pipeline
python auto_pipeline.py
```
