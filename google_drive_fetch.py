import os
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
DEFAULT_FOLDER_ID = '1NbBvT_JHzlPaG83U6f5aSNFdyNqbNgjn'

def get_drive_service():
    key_data = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY', '')
    if not key_data:
        key_data = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')

    if not key_data:
        raise ValueError("Neither GOOGLE_SERVICE_ACCOUNT_KEY nor GOOGLE_APPLICATION_CREDENTIALS is set.")

    if os.path.isfile(key_data):
        creds = service_account.Credentials.from_service_account_file(key_data, scopes=SCOPES)
    else:
        key_dict = json.loads(key_data)
        creds = service_account.Credentials.from_service_account_info(key_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def fetch_videos(destination_dir='Videos'):
    folder_id = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', DEFAULT_FOLDER_ID)
    if not folder_id:
        print("[SKIP] No GOOGLE_DRIVE_FOLDER_ID set")
        return []

    os.makedirs(destination_dir, exist_ok=True)

    try:
        service = get_drive_service()
    except Exception as e:
        print(f"[ERROR] Failed to initialize Google Drive service: {e}")
        return []

    print(f"[DRIVE] Checking folder: {folder_id}")
    results = service.files().list(
        q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed=false",
        fields="files(id, name, mimeType, size)",
        orderBy="createdTime desc",
        pageSize=100
    ).execute()

    files = results.get('files', [])
    if not files:
        print("[INFO] No video files found in Google Drive folder")
        return []

    downloaded = []
    for f in files:
        filepath = os.path.join(destination_dir, f['name'])
        if os.path.exists(filepath):
            print(f"[SKIP] Already downloaded: {f['name']}")
            downloaded.append(filepath)
            continue

        print(f"[DOWNLOAD] {f['name']}...")
        request = service.files().get_media(fileId=f['id'])
        fh = io.FileIO(filepath, 'wb')
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"  Progress: {int(status.progress() * 100)}%")

        print(f"  Saved: {filepath}")
        downloaded.append(filepath)

    return downloaded

if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    videos = fetch_videos()
    print(f"\nTotal videos available: {len(videos)}")
