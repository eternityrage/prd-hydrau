import os
import sys
import json
import random
import re
import urllib.parse
import requests
from upload.upload_facebook import upload_reel, upload_story, get_page_tokens

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PUBLISHED_FILE = 'published_videos.json'

def load_published():
    if os.path.exists(PUBLISHED_FILE):
        try:
            with open(PUBLISHED_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_published(data):
    with open(PUBLISHED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def extract_subject_from_filename(filename):
    """
    Extracts the item being crushed (e.g., 'watermelon', 'cantaloupe') from video filename.
    """
    name = os.path.splitext(filename)[0]
    # Remove dates/timestamps like _20260926031626
    name = re.sub(r'_\d{8,}', '', name)
    name = re.sub(r'\d+', '', name)
    name = name.replace('_', ' ').replace('-', ' ').strip()
    # Strip leading phrases like "Hydraulic press crushing" or "Hydraulic press crushes"
    name = re.sub(r'^(hydraulic\s+press\s+(crushing|crushes|vs)\s+)', '', name, flags=re.IGNORECASE).strip()
    return name or "fresh juicy fruits"

def clean_caption(text, subject="fruits"):
    if not text:
        return None
    # 1. Remove think tags
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # 2. Filter reasoning / meta lines
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        l = line.strip()
        if re.search(r'^(role\s*:?\s*assistant|reasoning\s*:|thought\s*:|thinking\s*:)', l, re.IGNORECASE):
            continue
        if re.search(r'^(here\s+is|here\'s|as\s+requested|certainly|sure,|note:|\*using\s+key|\*this\s+caption|---)', l, re.IGNORECASE):
            continue
        filtered_lines.append(line)
    text = '\n'.join(filtered_lines)
    # 3. Remove Title / Description / Caption / Hashtags labels
    text = re.sub(r'\*\*(title|description|caption|hashtags)[^\*]*\*\*[:\s]*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^(title|description|caption|hashtags)\s*:\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
    # 4. Remove Pollinations ads / footers
    text = re.sub(r'(Support\s+Pollinations|Powered\s+by\s+Pollinations|🌸\s*Ad\s*🌸).*$', '', text, flags=re.IGNORECASE | re.DOTALL).strip()
    # 5. Remove quotes, asterisks, and normalize spaces
    text = text.replace('"', '').replace('“', '').replace('”', '').replace('*', '').strip()
    text = re.sub(r'\s+', ' ', text).strip()

    # 5. Blacklist check - if ANY meta/reasoning words remain, reject
    blacklist = [
        'role assistant', 'assistant reasoning', 'reasoning', '<think>',
        'we must produce', 'here is a', 'title:', 'description:',
        'seo optimized', 'social media post', 'char)'
    ]
    lower_text = text.lower()
    for bad in blacklist:
        if bad in lower_text:
            return None

    if len(text) < 25:
        return None

    if len(text) > 280:
        text = text[:280].rsplit(' ', 1)[0]

    return text

def generate_caption(filename=""):
    pollinations_key = os.environ.get('POLLINATIONS_API_KEY', '').strip()
    subject = extract_subject_from_filename(filename) if filename else "fresh fruits"

    if not pollinations_key:
        return get_fallback_caption(subject)

    system_prompt = (
        "You are an expert social media copywriter for viral short-form Facebook Reels. "
        "OUTPUT ONLY the final single-line caption with hashtags. "
        "NEVER output your thoughts, NEVER output reasoning, NEVER output role tags, "
        "and NEVER use labels like Title: or Description:. "
        "Start immediately with an emoji and the hook."
    )
    user_prompt = (
        f"Write a viral, exciting ASMR caption for a 100-ton hydraulic press crushing {subject} "
        f"and extracting extreme satisfying juice with crisp ASMR sound. "
        f"Include high-ranking hashtags (#hydraulicpress #asmr #oddlysatisfying #crush #fruitjuice #satisfying). "
        f"Under 220 characters."
    )

    try:
        url = f"https://text.pollinations.ai/{urllib.parse.quote(user_prompt)}"
        params = {
            'system': system_prompt,
            'model': 'openai',
            'seed': random.randint(1, 999999)
        }
        headers = {'Authorization': f'Bearer {pollinations_key}'} if pollinations_key else {}
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        if resp.status_code == 200:
            cleaned = clean_caption(resp.text, subject)
            if cleaned:
                return cleaned
            else:
                print(f"  [WARN] Pollinations response contained meta/reasoning or failed validation. Using fallback.")
    except Exception as e:
        print(f"  [WARN] Pollinations caption generation failed: {e}")

    return get_fallback_caption(subject)

def get_fallback_caption(subject="fruits"):
    captions = [
        f"💥 Hydraulic Press vs {subject.title()}! Ultra Satisfying ASMR Juice Extraction 🧃 #hydraulicpress #asmr #satisfying #oddlysatisfying #fruitjuice",
        f"Extreme Pressure vs {subject.title()} 🍉 Watch the satisfying juice burst! #hydraulicpress #asmr #satisfying #crunch #oddlysatisfying",
        f"Crushing {subject.title()} with 100 Tons Hydraulic Press! Most relaxing ASMR crunch 💥 #hydraulicpress #satisfying #asmr #oddlysatisfying",
        f"Satisfying Hydraulic Press vs {subject.title()} 💦 Fresh Juice Burst ASMR #hydraulicpress #crushing #oddlysatisfying #satisfyingvideo",
        f"Watch what happens when 100 TONS crushes {subject.title()}! Pure ASMR crunch 🔊 #hydraulicpress #asmr #satisfying #oddlysatisfying",
        f"Extremely juicy {subject} under the hydraulic press! Oddly satisfying crunch 🍇 #hydraulicpress #asmr #fruitjuice #satisfying",
        f"Ultimate ASMR: Hydraulic Press crushing {subject.title()} into pure juice 🧃💥 #hydraulicpress #satisfying #asmr #oddlysatisfying",
        f"Can {subject.title()} survive 100 Tons of Pressure? Satisfying Juice Burst 💥 #hydraulicpress #satisfying #asmr #fruitcrush"
    ]
    return random.choice(captions)

def generate_pinned_comment(caption):
    """
    Creates the pinned comment text using the same title & description,
    plus a link or link placeholder for future pinned URLs.
    """
    custom_link = os.environ.get('PINNED_COMMENT_LINK', '').strip()
    if custom_link:
        link_cta = f"\n\n👉 Full Video & Exclusive Links: {custom_link}"
    else:
        link_cta = "\n\n👉 Follow for daily satisfying ASMR Hydraulic Press juice extractions! 🧃💥"

    return f"{caption}{link_cta}"

def select_video(processed_videos, published):
    published_names = {p.get('filename') for p in published}
    unpublished = [v for v in processed_videos if os.path.basename(v) not in published_names]

    if unpublished:
        return random.choice(unpublished)

    # All published - weighted random from ALL processed videos
    if processed_videos:
        counts = {}
        for p in published:
            name = p.get('filename', '')
            counts[name] = counts.get(name, 0) + 1

        weights = []
        for v in processed_videos:
            name = os.path.basename(v)
            count = counts.get(name, 0)
            weight = max(1, 1000 // (3 ** min(count, 6)))
            weights.append(weight)

        chosen = random.choices(processed_videos, weights=weights, k=1)[0]
        return chosen

    return None

def resolve_target_pages():
    """
    Resolves Facebook target pages and page access tokens.
    Supports:
    1. FB_PAGE_TOKENS_JSON (pre-stored dictionary mapping page_id -> {name, token})
    2. TARGET_FB_PAGE_IDS (comma-separated list of page IDs) + META_LONG_LIVED_ACCESS_TOKEN
    3. FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN (single page fallback)
    """
    tokens_json_env = os.environ.get('FB_PAGE_TOKENS_JSON', '').strip()
    if tokens_json_env:
        try:
            tokens_data = json.loads(tokens_json_env)
            page_configs = []
            for pid, info in tokens_data.items():
                if isinstance(info, dict):
                    page_configs.append({
                        'id': str(pid),
                        'name': info.get('name', f'Page {pid}'),
                        'token': info.get('token')
                    })
                elif isinstance(info, str):
                    page_configs.append({
                        'id': str(pid),
                        'name': f'Page {pid}',
                        'token': info
                    })
            if page_configs:
                return page_configs
        except Exception as e:
            print(f"[WARN] Failed to parse FB_PAGE_TOKENS_JSON: {e}")

    # Fallback to single page
    single_page_id = os.environ.get('FB_PAGE_ID', '').strip()
    single_page_token = os.environ.get('FB_PAGE_ACCESS_TOKEN', '').strip()

    if single_page_id and single_page_token:
        return [{
            'id': single_page_id,
            'name': 'Primary Facebook Page',
            'token': single_page_token
        }]

    return []

def publish_to_facebook_pages(video_path, caption, pinned_comment, page_configs):
    """
    Publishes the Reel, Pinned Comment, and Story to all configured Facebook pages.
    """
    results = []
    print(f"\n[FB] Publishing to {len(page_configs)} Facebook Page(s)...")

    for p in page_configs:
        pid = p['id']
        pname = p.get('name', pid)
        token = p['token']
        print(f"\n--- Publishing to Facebook Page: {pname} (ID: {pid}) ---")

        # 1. Reel + Pinned Comment
        reel_res = upload_reel(
            video_path=video_path,
            caption=caption,
            page_id=pid,
            page_token=token,
            pin_comment=True,
            comment_text=pinned_comment
        )
        reel_res['page_name'] = pname
        results.append(reel_res)

        # 2. Story
        story_res = upload_story(
            video_path=video_path,
            page_id=pid,
            page_token=token
        )
        story_res['page_name'] = pname
        results.append(story_res)

    return results

def publish(video_path, publish_to_facebook=True, publish_to_instagram=False):
    filename = os.path.basename(video_path)
    caption = generate_caption(filename)
    pinned_comment = generate_pinned_comment(caption)

    print(f"\n[SEO CAPTION] {caption}")
    print(f"[PINNED COMMENT] {pinned_comment}")

    results = []

    if publish_to_facebook:
        pages = resolve_target_pages()
        if not pages:
            print("[WARN] No target Facebook pages resolved. Please configure TARGET_FB_PAGE_IDS or FB_PAGE_ID.")
        else:
            fb_results = publish_to_facebook_pages(video_path, caption, pinned_comment, pages)
            results.extend(fb_results)

    if publish_to_instagram:
        from upload.upload_instagram import upload_reel as ig_reel, upload_story as ig_story
        ig_account_id = os.environ.get('INSTAGRAM_ACCOUNT_ID', '').strip()
        single_page_token = os.environ.get('FB_PAGE_ACCESS_TOKEN', '').strip()

        if ig_account_id:
            print(f"\n[IG] Publishing to Instagram: {ig_account_id}")
            results.append(ig_reel(video_path, caption, page_token=single_page_token, ig_account_id=ig_account_id))
            results.append(ig_story(video_path, page_token=single_page_token, ig_account_id=ig_account_id))

    return results

def run_daily_publish(processed_videos):
    published = load_published()
    video = select_video(processed_videos, published)

    if not video:
        print("[INFO] No videos available to publish")
        return []

    filename = os.path.basename(video)
    print(f"\n[SELECTED VIDEO] {filename}")

    publish_ig = bool(os.environ.get('INSTAGRAM_ACCOUNT_ID'))
    results = publish(video, publish_to_facebook=True, publish_to_instagram=publish_ig)

    # Record
    entry = {
        'filename': filename,
        'results': results
    }
    published.append(entry)
    save_published(published)

    return results

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    import glob
    processed = glob.glob('Processed_Videos/*.mp4') + glob.glob('Processed_Videos/*.mov')
    results = run_daily_publish(processed)
    print(f"\nPublish results total: {len(results)}")
