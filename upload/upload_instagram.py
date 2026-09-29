import os
import requests
import time
import subprocess

GRAPH_API_VERSION = 'v21.0'
GRAPH_URL = f'https://graph.facebook.com/{GRAPH_API_VERSION}'

def upload_reel(video_path, caption="", page_token=None, ig_account_id=None, share_to_feed=False):
    page_token = page_token or os.environ.get('FB_PAGE_ACCESS_TOKEN', '')
    ig_account_id = ig_account_id or os.environ.get('INSTAGRAM_ACCOUNT_ID', '')

    if not page_token or not ig_account_id:
        print("[SKIP] Instagram credentials not set (FB_PAGE_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID missing)")
        return {'status': 'skipped', 'platform': 'instagram'}

    if not os.path.exists(video_path):
        print(f"[ERROR] Video not found: {video_path}")
        return {'status': 'failed', 'platform': 'instagram'}

    file_size = os.path.getsize(video_path)
    print(f"[IG] Uploading Reel: {os.path.basename(video_path)} ({file_size / 1024 / 1024:.1f}MB)")

    # Auto-compress if over 100MB
    if file_size > 100 * 1024 * 1024:
        print("  Compressing video to fit under 100MB...")
        compressed_path = video_path.replace('.mp4', '_compressed.mp4')
        subprocess.run([
            'ffmpeg', '-y', '-i', video_path,
            '-c:v', 'libx264', '-crf', '28', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '96k',
            '-fs', '95M',
            compressed_path
        ], capture_output=True)
        video_path = compressed_path
        file_size = os.path.getsize(video_path)

    # Step 1: Initialize Resumable Media Container
    feed_flag = 'true' if share_to_feed else 'false'
    init_url = f"{GRAPH_URL}/{ig_account_id}/media"
    init_data = {
        'media_type': 'REELS',
        'upload_type': 'resumable',
        'caption': caption,
        'share_to_feed': feed_flag,  # 'false' ensures posting ONLY to Reels tab, NEVER to profile grid
        'access_token': page_token
    }
    init_params = {
        'share_to_feed': feed_flag
    }

    try:
        resp = requests.post(init_url, params=init_params, data=init_data, timeout=30)
    except Exception as e:
        print(f"  [ERROR] Container init request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram'}

    if resp.status_code != 200:
        print(f"  [ERROR] Reel container creation failed ({resp.status_code}): {resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    init_json = resp.json()
    container_id = init_json.get('id')
    upload_uri = init_json.get('uri') or f"https://rupload.facebook.com/ig-api-upload/{GRAPH_API_VERSION}/{container_id}"

    if not container_id:
        print(f"  [ERROR] No container ID in response: {init_json}")
        return {'status': 'failed', 'platform': 'instagram'}

    print(f"  Reel container initialized: {container_id}")

    # Step 2: Binary Video Upload to rupload.facebook.com
    upload_headers = {
        'Authorization': f'OAuth {page_token}',
        'offset': '0',
        'file_size': str(file_size),
        'Content-Type': 'application/octet-stream'
    }

    try:
        with open(video_path, 'rb') as f:
            upload_resp = requests.post(upload_uri, headers=upload_headers, data=f, timeout=180)
    except Exception as e:
        print(f"  [ERROR] Binary upload request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram'}

    if upload_resp.status_code not in (200, 201):
        print(f"  [ERROR] Binary upload failed ({upload_resp.status_code}): {upload_resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    print("  Binary video uploaded successfully. Polling processing status...")

    # Step 3: Wait for Meta processing
    for attempt in range(40):
        time.sleep(10)
        status_url = f"{GRAPH_URL}/{container_id}?fields=status_code&access_token={page_token}"
        try:
            status_resp = requests.get(status_url, timeout=30)
            if status_resp.status_code == 200:
                status = status_resp.json().get('status_code', '')
                if status == 'FINISHED':
                    print("  Processing complete!")
                    break
                elif status == 'ERROR':
                    print(f"  [ERROR] Media processing failed: {status_resp.json()}")
                    return {'status': 'failed', 'platform': 'instagram'}
        except Exception as e:
            print(f"  [WARN] Status check transient error: {e}")
        print(f"  Processing Reel... ({attempt + 1}/40)")
    else:
        print("  [WARN] Processing timed out after 400 seconds.")

    # Step 4: Publish
    publish_url = f"{GRAPH_URL}/{ig_account_id}/media_publish"
    publish_data = {
        'creation_id': container_id,
        'access_token': page_token
    }

    try:
        resp = requests.post(publish_url, data=publish_data, timeout=30)
    except Exception as e:
        print(f"  [ERROR] Publish request failed: {e}")
        return {'status': 'failed', 'platform': 'instagram'}

    if resp.status_code != 200:
        print(f"  [ERROR] Publish failed ({resp.status_code}): {resp.text}")
        return {'status': 'failed', 'platform': 'instagram'}

    media_id = resp.json().get('id')
    print(f"  [SUCCESS] Reel published on Instagram: {media_id}")
    return {'status': 'success', 'platform': 'instagram', 'media_id': media_id}
