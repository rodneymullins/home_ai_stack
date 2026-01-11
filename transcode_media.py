#!/usr/bin/env python3
"""
HandBrake Batch Transcoder
Optimizes videos for network streaming with h.265 compression
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime

# Configuration
MEDIA_DIRS = [
    "/mnt/raid0/media/Rod/Movies",
    "/mnt/raid0/media/Rod/TV",
    "/mnt/raid0/media/Julien/Movies",
    "/mnt/raid0/media/Julien/TV"
]

# HandBrake preset optimized for network streaming
HANDBRAKE_PRESET = "Very Fast 1080p30"  # Built-in preset
CUSTOM_OPTIONS = [
    "--encoder", "x265",           # H.265 for better compression
    "--encoder-preset", "medium",  # Balance speed vs quality
    "--quality", "22",             # CRF 22 (excellent quality)
    "--audio-copy-mask", "aac,ac3,eac3,truehd,dts,dtshd,mp3,flac",
    "--audio-fallback", "av_aac",
    "--subtitle-lang-list", "eng",
    "--all-subtitles"
]

# Skip files already optimized
SKIP_CODECS = {"hevc", "h265", "x265"}
SKIP_EXTENSIONS = {".optimized.mkv", ".optimized.mp4"}

LOG_FILE = "/var/log/handbrake_transcode.log"


def log(message):
    """Log to file and print"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_msg + '\n')


def get_video_info(file_path):
    """Get video codec and resolution using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-select_streams', 'v:0',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data.get('streams'):
                stream = data['streams'][0]
                return {
                    'codec': stream.get('codec_name', 'unknown'),
                    'width': stream.get('width', 0),
                    'height': stream.get('height', 0),
                    'bitrate': int(stream.get('bit_rate', 0)) // 1000 if stream.get('bit_rate') else 0
                }
    except Exception as e:
        log(f"Error getting video info for {file_path}: {e}")
    
    return None


def should_transcode(file_path):
    """Determine if file needs transcoding"""
    # Skip already optimized files
    if any(file_path.endswith(ext) for ext in SKIP_EXTENSIONS):
        return False
    
    info = get_video_info(file_path)
    if not info:
        return False
    
    # Already h.265?
    if info['codec'] in SKIP_CODECS:
        log(f"  ⏭️  Already H.265: {os.path.basename(file_path)}")
        return False
    
    # Very small bitrate = already compressed
    if info['bitrate'] > 0 and info['bitrate'] < 2000:  # < 2 Mbps
        log(f"  ⏭️  Already compressed: {os.path.basename(file_path)}")
        return False
    
    return True


def transcode_file(input_path, dry_run=False):
    """Transcode a single file"""
    try:
        filename = os.path.basename(input_path)
        directory = os.path.dirname(input_path)
        name, ext = os.path.splitext(filename)
        
        # Output path
        output_path = os.path.join(directory, f"{name}.optimized.mkv")
        temp_path = output_path + ".tmp"
        
        if os.path.exists(output_path):
            log(f"  ⏭️  Already exists: {filename}")
            return True
        
        log(f"  🎬 Transcoding: {filename}")
        
        if dry_run:
            log(f"     Would create: {os.path.basename(output_path)}")
            return True
        
        # Build HandBrake command
        cmd = [
            'HandBrakeCLI',
            '--input', input_path,
            '--output', temp_path,
            '--preset', HANDBRAKE_PRESET
        ] + CUSTOM_OPTIONS
        
        log(f"     Command: {' '.join(cmd[:10])}...")
        
        # Run transcoding
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            # Success! Replace original
            if os.path.exists(temp_path):
                # Get file sizes
                original_size = os.path.getsize(input_path) / (1024*1024*1024)
                new_size = os.path.getsize(temp_path) / (1024*1024*1024)
                savings = ((original_size - new_size) / original_size) * 100
                
                log(f"     ✅ Complete!")
                log(f"        Original: {original_size:.2f} GB")
                log(f"        New: {new_size:.2f} GB")
                log(f"        Savings: {savings:.1f}%")
                
                # Rename temp to final
                os.rename(temp_path, output_path)
                
                # Optionally delete original (DANGEROUS - be careful!)
                # os.remove(input_path)
                
                return True
        else:
            log(f"     ❌ Failed: {result.stderr[:200]}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
            
    except Exception as e:
        log(f"  ❌ Error transcoding {input_path}: {e}")
        return False


def scan_and_transcode(directories, dry_run=False):
    """Scan directories and transcode videos"""
    log("=" * 70)
    log("🎬 HandBrake Batch Transcoder")
    log("=" * 70)
    
    if dry_run:
        log("🔍 DRY RUN MODE\n")
    
    total_files = 0
    transcoded = 0
    skipped = 0
    
    for directory in directories:
        if not os.path.exists(directory):
            continue
        
        log(f"\n📂 Scanning: {directory}")
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                if not filename.lower().endswith(('.mkv', '.mp4', '.avi', '.mov', '.m4v')):
                    continue
                
                total_files += 1
                file_path = os.path.join(root, filename)
                
                if should_transcode(file_path):
                    if transcode_file(file_path, dry_run):
                        transcoded += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1
    
    log("\n" + "=" * 70)
    log("✅ SUMMARY")
    log(f"   Total files: {total_files}")
    log(f"   Transcoded: {transcoded}")
    log(f"   Skipped: {skipped}")
    log("=" * 70)


if __name__ == "__main__":
    import sys
    
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    # Check for HandBrake
    try:
        subprocess.run(['HandBrakeCLI', '--version'], capture_output=True, check=True)
    except FileNotFoundError:
        print("❌ HandBrakeCLI not found!")
        print("   Install: sudo apt install handbrake-cli")
        sys.exit(1)
    
    scan_and_transcode(MEDIA_DIRS, dry_run)
