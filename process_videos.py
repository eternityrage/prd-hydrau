import os
import subprocess
import glob
import shutil

def is_ffmpeg_available():
    return shutil.which('ffmpeg') is not None

def get_video_dimensions(input_path):
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', input_path]
        out = subprocess.check_output(cmd, text=True).strip()
        w, h = map(int, out.split(','))
        return w, h
    except Exception:
        return 720, 1280

def process_video(input_path, output_dir='Processed_Videos'):
    if not is_ffmpeg_available():
        print("[WARN] ffmpeg not found in PATH. Skipping ffmpeg processing.")
        return input_path

    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.basename(input_path)
    output_path = os.path.join(output_dir, filename)

    if os.path.exists(output_path):
        print(f"[SKIP] Already processed: {filename}")
        return output_path

    print(f"[PROCESS] Processing video: {filename}...")

    w, h = get_video_dimensions(input_path)
    # Remove Google Gemini watermark from the bottom-right corner
    delogo_w = max(40, int(w * 0.13))
    delogo_h = max(40, int(h * 0.09))
    delogo_x = min(w - delogo_w - 2, int(w * 0.77))
    delogo_y = min(h - delogo_h - 2, int(h * 0.87))

    vf_filters = [
        f"delogo=x={delogo_x}:y={delogo_y}:w={delogo_w}:h={delogo_h}",
        "scale=1080:1920:force_original_aspect_ratio=decrease",
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
        "unsharp=3:3:0.8"
    ]
    vf_chain = ",".join(vf_filters)

    cmd = [
        'ffmpeg', '-y', '-i', input_path,
        '-vf', vf_chain,
        '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11',
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-movflags', '+faststart',
        '-t', '60',
        output_path
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"  Processed: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Error processing {filename}: {e.stderr}")
        return None

def process_all_videos(input_dir='Videos', output_dir='Processed_Videos'):
    videos = glob.glob(os.path.join(input_dir, '*.mp4')) + \
             glob.glob(os.path.join(input_dir, '*.mov')) + \
             glob.glob(os.path.join(input_dir, '*.avi'))

    if not videos:
        print("[INFO] No videos to process")
        return []

    processed = []
    for v in videos:
        result = process_video(v, output_dir=output_dir)
        if result:
            processed.append(result)

    return processed

if __name__ == '__main__':
    processed = process_all_videos()
    print(f"\nTotal videos processed: {len(processed)}")
