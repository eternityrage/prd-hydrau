import os
import requests
import time

GRAPH_API_VERSION = 'v21.0'
GRAPH_URL = f'https://graph.facebook.com/{GRAPH_API_VERSION}'

def upload_reel(video_path, caption="", page_token=None, ig_account_id=None):
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN', '')
    ig_account_id = ig_account_id or os.environ.get('INSTAGRAM_ACCOUNT_ID', '')

    if not page_token or not ig_account_id:
        print("[SKIP] Instagram credentials not set")
        return {'status': 'skipped', 'platform': 'instagram'}

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'instagram'}

    file_size = os.path.getsize(video_path)
    print(f"[IG] Uploading reel: {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB)")

    # Auto-compress if over 100MB
    if file_size > 100 * 1024 * 1024:
        print("  Compressing video to fit under 100MB...")
        import subprocess
        compressed_path = video_path.replace('.mp4', '_compressed.mp4')
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-c:v', 'libx264', '-crf', '28', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '96k',
            '-fs', '95M',
            compressed_path
        ], capture_output=True)
        video_path = compressed_path

    # Step 1: Create media container
    container_url = f"{GRAPH_URL}/{ig_account_id}/media"
    with open(video_path, 'rb') as f:
        files = {'video': (os.path.basename(video_path), f, 'video/mp4')}
        data = {
            'media_type': 'REELS',
            'caption': caption,
            'access_token': page_token
        }
        resp = requests.post(container_url, data=data, files=files, timeout=120)

    if resp.status_code != 200:
        print(f"  [ERROR] Container creation failed: {resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    container_id = resp.json().get('id')
    if not container_id:
        print(f"  [ERROR] No container ID: {resp.json()}")
        return {'status': 'failed', 'platform': 'instagram'}

    print(f"  Container created: {container_id}")

    # Step 2: Wait for processing and publish
    for attempt in range(30):
        time.sleep(10)
        status_url = f"{GRAPH_URL}/{container_id}?fields=status_code&access_token={page_token}"
        status_resp = requests.get(status_url, timeout=30)
        status = status_resp.json().get('status_code', '')

        if status == 'FINISHED':
            break
        elif status == 'ERROR':
            print(f"  [ERROR] Processing failed: {status_resp.json()}")
            return {'status': 'failed', 'platform': 'instagram'}
        print(f"  Processing... ({attempt + 1}/30)")

    # Step 3: Publish
    publish_url = f"{GRAPH_URL}/{ig_account_id}/media_publish"
    publish_data = {
        'creation_id': container_id,
        'access_token': page_token
    }
    resp = requests.post(publish_url, data=publish_data, timeout=30)
    if resp.status_code != 200:
        print(f"  [ERROR] Publish failed: {resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    media_id = resp.json().get('id')
    print(f"  Reel published on Instagram: {media_id}")
    return {'status': 'success', 'platform': 'instagram', 'media_id': media_id}

def upload_story(video_path, page_token=None, ig_account_id=None):
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN', '')
    ig_account_id = ig_account_id or os.environ.get('INSTAGRAM_ACCOUNT_ID', '')

    if not page_token or not ig_account_id:
        print("[SKIP] Instagram credentials not set")
        return {'status': 'skipped', 'platform': 'instagram_story'}

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    print(f"[IG] Uploading story: {os.path.basename(video_path)}")

    container_url = f"{GRAPH_URL}/{ig_account_id}/media"
    with open(video_path, 'rb') as f:
        files = {'video': (os.path.basename(video_path), f, 'video/mp4')}
        data = {
            'media_type': 'STORIES',
            'access_token': page_token
        }
        resp = requests.post(container_url, data=data, files=files, timeout=120)

    if resp.status_code != 200:
        print(f"  [ERROR] Story container failed: {resp.text}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    container_id = resp.json().get('id')

    time.sleep(15)

    publish_url = f"{GRAPH_URL}/{ig_account_id}/media_publish"
    publish_data = {
        'creation_id': container_id,
        'access_token': page_token
    }
    resp = requests.post(publish_url, data=publish_data, timeout=30)
    if resp.status_code != 200:
        print(f"  [ERROR] Story publish failed: {resp.text}")
        return {'status': 'failed', 'platform': 'instagram_story'}

    print("  Story published on Instagram")
    return {'status': 'success', 'platform': 'instagram_story'}
