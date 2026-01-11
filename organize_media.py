#!/usr/bin/env python3
"""
Automated Media Organizer
Sorts downloaded movies and TV shows with separate directories for different users
"""

import os
import re
import shutil
from pathlib import Path

# Configuration
DOWNLOAD_DIR = "/downloads"
MOVIES_DIR = "/mnt/media/Movies"
TV_DIR = "/mnt/media/TV"
JULIEN_MOVIES_DIR = "/mnt/media/Julien/Movies"
JULIEN_TV_DIR = "/mnt/media/Julien/TV"

# Patterns to identify TV shows
TV_PATTERNS = [
    r'[Ss]\d{1,2}[Ee]\d{1,2}',  # S01E01, s01e01
    r'\d{1,2}x\d{1,2}',         # 1x01
    r'Season\s*\d+',            # Season 1
    r'Episode\s*\d+',           # Episode 1
]

# Julien's content keywords (customize as needed)
JULIEN_KEYWORDS = [
    'julien',
    'bluey',
    'paw patrol',
    'peppa pig',
    'kids',
    'cartoon',
]

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.wmv'}


def is_tv_show(filename):
    """Detect if file is a TV show based on naming patterns"""
    filename_lower = filename.lower()
    
    for pattern in TV_PATTERNS:
        if re.search(pattern, filename_lower):
            return True
    
    return False


def is_julien_content(filename):
    """Detect if content is for Julien"""
    filename_lower = filename.lower()
    
    for keyword in JULIEN_KEYWORDS:
        if keyword in filename_lower:
            return True
    
    return False


def clean_filename(filename):
    """Clean up filename for better organization"""
    # Remove common torrent indicators
    name = re.sub(r'\[.*?\]', '', filename)
    name = re.sub(r'\(.*?\)', '', filename)
    name = re.sub(r'\.', ' ', name)
    name = re.sub(r'\s+', ' ', name)
    
    return name.strip()


def organize_file(file_path):
    """Move file to appropriate directory"""
    filename = os.path.basename(file_path)
    file_ext = os.path.splitext(filename)[1].lower()
    
    if file_ext not in VIDEO_EXTENSIONS:
        print(f"  ⏭️  Skipping non-video: {filename}")
        return
    
    # Determine content type and owner
    is_tv = is_tv_show(filename)
    is_julien = is_julien_content(filename)
    
    # Choose destination
    if is_julien:
        dest_dir = JULIEN_TV_DIR if is_tv else JULIEN_MOVIES_DIR
        owner = "Julien"
    else:
        dest_dir = TV_DIR if is_tv else MOVIES_DIR
        owner = "Rod"
    
    content_type = "TV Show" if is_tv else "Movie"
    
    # Create destination directory if needed
    os.makedirs(dest_dir, exist_ok=True)
    
    # Move file
    dest_path = os.path.join(dest_dir, filename)
    
    # Handle duplicates
    if os.path.exists(dest_path):
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest_path):
            dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
            counter += 1
    
    try:
        shutil.move(file_path, dest_path)
        print(f"  ✅ {owner}'s {content_type}: {filename}")
        print(f"     → {dest_path}")
        return True
    except Exception as e:
        print(f"  ❌ Error moving {filename}: {e}")
        return False


def scan_and_organize(directory):
    """Scan directory and organize all media files"""
    print(f"🎬 Media Organizer")
    print(f"=" * 70)
    print(f"Scanning: {directory}\n")
    
    files_moved = 0
    files_skipped = 0
    
    # Walk through download directory
    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            
            if organize_file(file_path):
                files_moved += 1
            else:
                files_skipped += 1
    
    print(f"\n{'=' * 70}")
    print(f"✅ Complete!")
    print(f"   Files moved: {files_moved}")
    print(f"   Files skipped: {files_skipped}")
    
    # Clean up empty directories
    for root, dirs, files in os.walk(directory, topdown=False):
        for dirname in dirs:
            dir_path = os.path.join(root, dirname)
            try:
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)
                    print(f"   Removed empty directory: {dir_path}")
            except:
                pass


if __name__ == "__main__":
    # Ensure media directories exist
    for directory in [MOVIES_DIR, TV_DIR, JULIEN_MOVIES_DIR, JULIEN_TV_DIR]:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created: {directory}")
    
    print()
    
    # Organize downloads
    if os.path.exists(DOWNLOAD_DIR):
        scan_and_organize(DOWNLOAD_DIR)
    else:
        print(f"❌ Download directory not found: {DOWNLOAD_DIR}")
