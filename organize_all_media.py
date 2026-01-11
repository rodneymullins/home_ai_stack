#!/usr/bin/env python3
"""
Complete Media Library Organizer
- Organizes existing media and new downloads
- Cleans up YouTube video names
- Separates Rod vs Julien content
- Detects Movies vs TV Shows
"""

import os
import re
import shutil
from pathlib import Path
import json

# Configuration - UPDATE THESE PATHS
BASE_MEDIA = "/mnt/raid0/media"  # Adjust based on your setup
SOURCE_DIRS = [
    "/mnt/raid0/data/videos",
    "/mnt/raid0/data/downloads",
    "/media",
    "/data/media",
]

# Destination structure
DEST_BASE = "/mnt/raid0/media"
MOVIES_DIR = f"{DEST_BASE}/Rod/Movies"
TV_DIR = f"{DEST_BASE}/Rod/TV"
JULIEN_MOVIES_DIR = f"{DEST_BASE}/Julien/Movies"
JULIEN_TV_DIR = f"{DEST_BASE}/Julien/TV"

# YouTube video ID pattern (11 characters)
YOUTUBE_ID_PATTERN = r'[-_][a-zA-Z0-9_-]{11}(?:\.[a-z]{3,4})?$'

# TV show patterns
TV_PATTERNS = [
    r'[Ss]\d{1,2}[Ee]\d{1,2}',
    r'\d{1,2}x\d{1,2}',
    r'Season\s*\d+',
    r'Episode\s*\d+',
]

# Julien's content keywords
JULIEN_KEYWORDS = [
    'julien', 'bluey', 'paw patrol', 'peppa pig', 
    'kids', 'cartoon', 'baby', 'toddler',
    'cocomelon', 'blippi', 'disney', 'pixar',
    'pokemon', 'despicable me', 'minion', 'dreamworks',
    'illumination', 'animation', 'animated', 'sponge bob',
    'mickey mouse', 'nickelodeon', 'cartoon network',
    'studio ghibli', 'frozen', 'toy story', 'lego',
    'sesame street', 'barney', 'thomas and friends',
    'curious george', 'paddington', 'shrek', 'kung fu panda',
    'madagascar', 'ice age', 'sonic', 'mario'
]

VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.wmv', '.flv', '.webm'}


def clean_youtube_filename(filename):
    """Clean YouTube video names"""
    name, ext = os.path.splitext(filename)
    
    # Remove YouTube video ID (11 character string at end)
    name = re.sub(YOUTUBE_ID_PATTERN, '', name)
    
    # Remove common YouTube patterns
    name = re.sub(r'\[.*?\]', '', name)  # Remove [tags]
    name = re.sub(r'\(.*?\)', '', name)  # Remove (tags)
    name = re.sub(r'_+', ' ', name)      # Underscores to spaces
    name = re.sub(r'-+', ' ', name)      # Dashes to spaces
    name = re.sub(r'\s+', ' ', name)     # Multiple spaces to single
    
    # Remove common suffixes
    name = re.sub(r'(?i)(480|720|1080|2160)p?', '', name)
    name = re.sub(r'(?i)(hdtv|web-?dl|bluray|brrip|webrip)', '', name)
    name = re.sub(r'(?i)x26[45]', '', name)
    
    # Clean up
    name = name.strip(' -_.')
    
    return f"{name}{ext}"


def is_tv_show(filename):
    """Detect TV shows"""
    for pattern in TV_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            return True
    return False


def is_julien_content(filename):
    """Detect Julien's content"""
    filename_lower = filename.lower()
    # Check for Spiderman (special case: kids vs adult)
    if 'spiderman' in filename_lower or 'spider-man' in filename_lower:
        # Exclude known adult/live-action keywords
        adult_keywords = ['homecoming', 'far from home', 'no way home', 'tobey', 'andrew', 'holland', 'maguire']
        if any(k in filename_lower for k in adult_keywords):
            return False
        # Include if it matches kids keywords or is just generic animated
        return True

    for keyword in JULIEN_KEYWORDS:
        if keyword in filename_lower:
            return True
    return False


def organize_file(file_path, dry_run=False):
    """Organize a single file"""
    try:
        original_name = os.path.basename(file_path)
        file_ext = os.path.splitext(original_name)[1].lower()
        
        if file_ext not in VIDEO_EXTENSIONS:
            return None
        
        # Clean filename
        clean_name = clean_youtube_filename(original_name)
        
        # Detect content type and owner
        is_tv = is_tv_show(clean_name)
        is_julien = is_julien_content(clean_name)
        
        # Choose destination
        if is_julien:
            dest_dir = JULIEN_TV_DIR if is_tv else JULIEN_MOVIES_DIR
            owner = "Julien"
        else:
            dest_dir = TV_DIR if is_tv else MOVIES_DIR
            owner = "Rod"
        
        content_type = "TV" if is_tv else "Movie"
        
        # Create destination
        if not dry_run:
            os.makedirs(dest_dir, exist_ok=True)
        
        dest_path = os.path.join(dest_dir, clean_name)
        
        # Handle duplicates
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(clean_name)
            counter = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(dest_dir, f"{base}_{counter}{ext}")
                counter += 1
        
        # Show what we'll do
        action = "WOULD MOVE" if dry_run else "MOVING"
        print(f"  {action}: {owner}'s {content_type}")
        if original_name != clean_name:
            print(f"    FROM: {original_name}")
            print(f"    TO:   {clean_name}")
        else:
            print(f"    FILE: {clean_name}")
        print(f"    DEST: {dest_path}")
        
        # Execute move
        if not dry_run:
            shutil.move(file_path, dest_path)
            return True
        
        return {'action': 'move', 'from': file_path, 'to': dest_path, 'owner': owner, 'type': content_type}
        
    except Exception as e:
        print(f"  ❌ Error processing {file_path}: {e}")
        return None


def scan_directory(directory, dry_run=False):
    """Scan a directory for media files"""
    if not os.path.exists(directory):
        return []
    
    print(f"\n📂 Scanning: {directory}")
    print(f"=" * 70)
    
    results = []
    
    for root, dirs, files in os.walk(directory):
        for filename in files:
            file_path = os.path.join(root, filename)
            result = organize_file(file_path, dry_run)
            if result:
                results.append(result)
    
    return results


def main():
    import sys
    
    dry_run = '--dry-run' in sys.argv or '-n' in sys.argv
    
    if dry_run:
        print("🔍 DRY RUN MODE - No files will be moved\n")
    else:
        print("🎬 ORGANIZING MEDIA LIBRARY\n")
    
    # Create destination directories
    for directory in [MOVIES_DIR, TV_DIR, JULIEN_MOVIES_DIR, JULIEN_TV_DIR]:
        if not dry_run:
            os.makedirs(directory, exist_ok=True)
        print(f"📁 Destination: {directory}")
    
    # Scan all source directories
    all_results = []
    for source_dir in SOURCE_DIRS:
        results = scan_directory(source_dir, dry_run)
        all_results.extend(results)
    
    # Summary
    print(f"\n{'=' * 70}")
    print(f"✅ SUMMARY")
    
    if dry_run and all_results:
        rod_movies = sum(1 for r in all_results if r['owner'] == 'Rod' and r['type'] == 'Movie')
        rod_tv = sum(1 for r in all_results if r['owner'] == 'Rod' and r['type'] == 'TV')
        julien_movies = sum(1 for r in all_results if r['owner'] == 'Julien' and r['type'] == 'Movie')
        julien_tv = sum(1 for r in all_results if r['owner'] == 'Julien' and r['type'] == 'TV')
        
        print(f"   Rod's Movies: {rod_movies}")
        print(f"   Rod's TV: {rod_tv}")
        print(f"   Julien's Movies: {julien_movies}")
        print(f"   Julien's TV: {julien_tv}")
        print(f"   TOTAL: {len(all_results)}")
        print(f"\n💡 Run without --dry-run to actually move files")
    else:
        print(f"   Files organized: {len([r for r in all_results if r is True])}")
    

if __name__ == "__main__":
    main()
