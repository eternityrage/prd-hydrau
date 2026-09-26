import os
import sys
from dotenv import load_dotenv

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

def check_secrets():
    # Google credentials check
    has_google = bool(os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
    if not has_google:
        print("[ERROR] Missing GOOGLE_SERVICE_ACCOUNT_KEY or GOOGLE_APPLICATION_CREDENTIALS")
        sys.exit(1)

    # Facebook credentials check
    has_tokens_json = bool(os.environ.get('FB_PAGE_TOKENS_JSON'))
    has_single_fb = bool(os.environ.get('FB_PAGE_ID') and os.environ.get('FB_PAGE_ACCESS_TOKEN'))

    if not has_tokens_json and not has_single_fb:
        print("[ERROR] Missing Facebook credentials. Please provide either FB_PAGE_TOKENS_JSON or (FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN)")
        sys.exit(1)

    target_pages = os.environ.get('TARGET_FB_PAGE_IDS', '')
    if target_pages:
        pids = [p.strip() for p in target_pages.split(',') if p.strip()]
        print(f"[OK] Multi-Page mode configured with {len(pids)} target Facebook page(s)")
    elif has_single_fb:
        print(f"[OK] Single Page mode configured with FB_PAGE_ID: {os.environ.get('FB_PAGE_ID')}")

    # Optional checks
    if not os.environ.get('POLLINATIONS_API_KEY'):
        print("[INFO] POLLINATIONS_API_KEY not set. Built-in high-converting fallback ASMR captions will be used.")

    if os.environ.get('INSTAGRAM_ACCOUNT_ID'):
        print(f"[OK] Instagram publishing enabled: {os.environ.get('INSTAGRAM_ACCOUNT_ID')}")

    print("[OK] Environment validation successful.\n")

def main():
    print("=" * 60)
    print("      PRD-HYDRAU - ASMR Hydraulic Press Video Pipeline")
    print("=" * 60)

    # Step 1: Validate secrets
    check_secrets()

    # Step 2: Fetch videos from Google Drive
    print("\n--- Step 1: Fetching videos from Google Drive ---")
    from google_drive_fetch import fetch_videos
    new_videos = fetch_videos()
    print(f"Videos fetched/checked: {len(new_videos)}")

    # Step 3: Select video & process on demand
    print("\n--- Step 2: Selecting and processing video on demand ---")
    import glob
    from daily_publisher import select_video, load_published, publish, save_published
    from process_videos import process_video

    raw_videos = glob.glob('Videos/*.mp4') + glob.glob('Videos/*.mov') + glob.glob('Videos/*.avi')
    published = load_published()
    selected_raw = select_video(raw_videos, published)

    if not selected_raw:
        print("[INFO] No videos available to publish.")
        return

    filename = os.path.basename(selected_raw)
    print(f"[TARGET VIDEO] Selected: {filename}")

    # Process only the selected video with FFmpeg
    processed_path = process_video(selected_raw)
    if not processed_path:
        print(f"[ERROR] Failed to process video: {selected_raw}")
        return

    # Step 4: Publish to platforms
    print("\n--- Step 3: Publishing to Facebook (Reels + Pinned Comments + Stories) ---")
    publish_ig = bool(os.environ.get('INSTAGRAM_ACCOUNT_ID'))
    results = publish(processed_path, publish_to_facebook=True, publish_to_instagram=publish_ig)

    # Record
    entry = {
        'filename': filename,
        'results': results
    }
    published.append(entry)
    save_published(published)

    # Summary
    print("\n" + "=" * 60)
    print("Pipeline Execution Summary:")
    print(f"  Videos in library:    {len(new_videos)}")
    print(f"  Selected video:       {filename}")
    print(f"  Processed video:      {os.path.basename(processed_path)}")
    print(f"  Publish action items: {len(results)}")
    for r in results:
        status = r.get('status', 'unknown')
        platform = r.get('platform', 'unknown')
        page_name = r.get('page_name', r.get('page_id', ''))
        vid = r.get('video_id', '')
        comment_id = r.get('comment_id', '')
        print(f"    - [{platform}] Page: {page_name} -> Status: {status} (Video ID: {vid}, Comment ID: {comment_id})")
    print("=" * 60)

if __name__ == '__main__':
    main()
